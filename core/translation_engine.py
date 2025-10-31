"""
Translation engine using LangGraph for multiple LLM provider support
"""

import json
import re
import time
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import asdict

from langchain.schema import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.schema.runnable import RunnableConfig

from models.data_structures import (
    TranslationChunk,
    TranslationRequest,
    ModelProvider,
    HistoryEntry,
    CustomModel,
)


class TranslationState:
    """State for the translation graph"""

    def __init__(self):
        self.messages: List = []
        self.chunk: TranslationChunk = None
        self.request: TranslationRequest = None
        self.result: List[str] = []
        self.error: str = ""
        self.retry_count: int = 0


class TranslationEngine:
    """LangGraph-based translation engine supporting multiple LLM providers"""

    def __init__(self):
        self.api_keys: Dict[str, str] = {}
        self.models: Dict[str, Any] = {}
        self.custom_models: List[CustomModel] = []
        self.chat_history: List[Dict[str, Any]] = []
        self.history: List[HistoryEntry] = []  # Add missing history attribute
        self.translation_count = 0

        # Translation workflow graph
        self.graph = None
        self._build_translation_graph()

        # System instructions for different types of content
        self.system_instructions = {
            "visual_novel": self._get_visual_novel_system_instruction(),
            "general": self._get_general_system_instruction(),
        }

    def set_api_key(self, provider: ModelProvider, api_key: str):
        """Set API key for a specific provider"""
        self.api_keys[provider.value] = api_key
        self._initialize_model(provider)

    def _initialize_model(self, provider: ModelProvider):
        """Initialize model for a specific provider"""
        api_key = self.api_keys.get(provider.value)
        if not api_key:
            return

        try:
            if provider == ModelProvider.GOOGLE:
                self.models[provider.value] = ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model="gemini-2.0-flash-exp",
                    temperature=0.2,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                )
            elif provider == ModelProvider.OPENAI and ChatOpenAI:
                self.models[provider.value] = ChatOpenAI(
                    openai_api_key=api_key,
                    model="gpt-4",
                    temperature=0.7,
                    max_tokens=4096,
                )
            elif provider == ModelProvider.ANTHROPIC and ChatAnthropic:
                self.models[provider.value] = ChatAnthropic(
                    anthropic_api_key=api_key,
                    model="claude-3-sonnet-20240229",
                    temperature=0.7,
                    max_tokens=4096,
                )
        except Exception as e:
            print(f"Error initializing {provider.value} model: {e}")

    def add_custom_model(self, custom_model: CustomModel):
        """Add a custom model configuration"""
        # Remove existing model with same name and provider
        self.custom_models = [
            m
            for m in self.custom_models
            if not (
                m.provider == custom_model.provider
                and m.model_name == custom_model.model_name
            )
        ]
        self.custom_models.append(custom_model)

        # Initialize the model
        self._initialize_custom_model(custom_model)

    def _initialize_custom_model(self, custom_model: CustomModel):
        """Initialize a custom model"""
        if not custom_model.is_active:
            return

        api_key = self.api_keys.get(custom_model.provider.value)
        if not api_key:
            return

        try:
            model_key = f"{custom_model.provider.value}:{custom_model.model_name}"

            if custom_model.provider == ModelProvider.GOOGLE:
                self.models[model_key] = ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=custom_model.model_name,
                    temperature=custom_model.temperature,
                    max_output_tokens=custom_model.max_tokens,
                )
            elif custom_model.provider == ModelProvider.OPENAI and ChatOpenAI:
                self.models[model_key] = ChatOpenAI(
                    openai_api_key=api_key,
                    model=custom_model.model_name,
                    temperature=custom_model.temperature,
                    max_tokens=custom_model.max_tokens,
                )
            elif custom_model.provider == ModelProvider.ANTHROPIC and ChatAnthropic:
                self.models[model_key] = ChatAnthropic(
                    anthropic_api_key=api_key,
                    model=custom_model.model_name,
                    temperature=custom_model.temperature,
                    max_tokens=custom_model.max_tokens,
                )
        except Exception as e:
            print(f"Error initializing custom model {custom_model.model_name}: {e}")

    def set_chat_history(self, history: List[Dict[str, Any]]):
        """Set the chat history for context"""
        self.chat_history = history

    def _build_translation_graph(self):
        """Build the LangGraph translation workflow"""
        # Define the state schema
        workflow = StateGraph(TranslationState)

        # Add nodes
        workflow.add_node("prepare_request", self._prepare_request)
        workflow.add_node("translate_chunk", self._translate_chunk)
        workflow.add_node("validate_result", self._validate_result)
        workflow.add_node("retry_translation", self._retry_translation)
        workflow.add_node("finalize_result", self._finalize_result)

        # Define edges
        workflow.set_entry_point("prepare_request")
        workflow.add_edge("prepare_request", "translate_chunk")
        workflow.add_conditional_edges(
            "translate_chunk",
            self._should_validate,
            {"validate": "validate_result", "error": "retry_translation"},
        )
        workflow.add_conditional_edges(
            "validate_result",
            self._should_retry,
            {"retry": "retry_translation", "success": "finalize_result"},
        )
        workflow.add_conditional_edges(
            "retry_translation",
            self._should_continue_retry,
            {"retry": "translate_chunk", "error": "finalize_result"},
        )
        workflow.add_edge("finalize_result", END)

        self.graph = workflow.compile()

    def _prepare_request(self, state: TranslationState) -> TranslationState:
        """Prepare the translation request with chat history"""
        try:
            # Create system message
            system_instruction = self.system_instructions.get(
                "visual_novel", self.system_instructions["general"]
            )

            # Start with system message
            messages = [SystemMessage(content=system_instruction)]

            # Add chat history for context (limit to recent messages)
            if self.chat_history:
                recent_history = self.chat_history[-10:]  # Last 10 messages
                for msg in recent_history:
                    role = msg.get("role", "human")
                    content = msg.get("content", "")

                    if role == "human":
                        messages.append(HumanMessage(content=content))
                    elif role == "ai" or role == "assistant":
                        # Add as HumanMessage with prefix to maintain context
                        messages.append(
                            HumanMessage(content=f"Previous AI response: {content}")
                        )

            # Create user message with the chunk
            chunk_data = state.chunk.original_texts

            # Enhanced prompt with target column information
            target_column = state.chunk.target_column
            json_input = []
            for i, text in enumerate(chunk_data):
                if text and text.strip():
                    json_input.append({"line": i + 1, "text": text.strip()})

            payload_str = json.dumps(json_input, ensure_ascii=False)

            user_prompt = f"""I will provide you with a JSON array containing text lines to translate from Japanese to Vietnamese for the "{target_column}" column.

This is for a visual novel translation project. The target column "{target_column}" indicates the quality level expected:
- "Initial": Quick, basic translation
- "Machine translation": Direct, machine-like translation
- "Better translation": Improved, more natural translation  
- "Best translation": Highest quality, polished translation

Input format: [{{ "line": 1, "text": "..." }}, ...]

Please return the translation in this exact JSON format:
{{"translation": [
    {{ "line": 1, "text": "translated text 1" }},
    {{ "line": 2, "text": "translated text 2" }},
    ...
]}}

Important:
- Maintain the exact same line numbers
- Return all lines even if some are names or short phrases
- Adjust translation quality based on target column: {target_column}
- Use natural Vietnamese translation
- For character names, adapt to Vietnamese phonetics when appropriate
- Keep original formatting (quotes, punctuation) where relevant

Input data:
```{payload_str}```"""

            messages.append(HumanMessage(content=user_prompt))
            state.messages = messages

        except Exception as e:
            state.error = f"Error preparing request: {e}"

        return state

    def _translate_chunk(self, state: TranslationState) -> TranslationState:
        """Perform the actual translation with custom model support"""
        try:
            provider = state.request.model_provider
            model_name = state.request.model_name

            # Try to find custom model first
            model = None
            if model_name:
                # Check for custom model
                model_key = f"{provider.value}:{model_name}"
                model = self.models.get(model_key)

                # If not found, try default provider model
                if not model:
                    model = self.models.get(provider.value)
            else:
                model = self.models.get(provider.value)

            if not model:
                state.error = f"No model available for provider: {provider.value}"
                return state

            # Invoke the model
            response = model.invoke(state.messages)

            if hasattr(response, "content"):
                raw_output = response.content
            else:
                raw_output = str(response)

            # Parse the response
            expected_count = len(state.chunk.original_texts)
            parsed_result = self._parse_translation_response(raw_output, expected_count)

            if parsed_result:
                state.result = [item.get("text", "") for item in parsed_result]
            else:
                state.error = "Failed to parse translation response"

        except Exception as e:
            state.error = f"Translation error: {e}"

        return state

    def _validate_result(self, state: TranslationState) -> TranslationState:
        """Validate the translation result"""
        try:
            if not state.result:
                state.error = "No translation result"
                return state

            # For new JSON format, validate structure
            if isinstance(state.result, list) and state.result:
                if isinstance(state.result[0], dict):
                    # New format: list of dicts with line/text
                    expected_lines = set()
                    if isinstance(state.chunk.original_texts[0], dict):
                        expected_lines = {
                            item["line"] for item in state.chunk.original_texts
                        }
                    else:
                        expected_lines = set(
                            range(1, len(state.chunk.original_texts) + 1)
                        )

                    result_lines = {
                        item["line"] for item in state.result if "line" in item
                    }

                    if not expected_lines.issubset(result_lines):
                        missing_lines = expected_lines - result_lines
                        state.error = f"Missing translation for lines: {missing_lines}"
                        return state
                else:
                    # Old format: validate count
                    expected_count = len(state.chunk.original_texts)
                    actual_count = len(state.result)

                    if actual_count != expected_count:
                        state.error = f"Translation count mismatch: expected {expected_count}, got {actual_count}"
                        return state

        except Exception as e:
            state.error = f"Validation error: {e}"

        return state

    def _retry_translation(self, state: TranslationState) -> TranslationState:
        """Handle retry logic"""
        state.retry_count += 1
        state.error = ""  # Clear previous error
        return state

    def _finalize_result(self, state: TranslationState) -> TranslationState:
        """Finalize the translation result"""
        try:
            if state.error:
                # Mark chunk as failed
                state.chunk.status = "failed"
                state.chunk.error_message = state.error
                state.chunk.translated_texts = []
            else:
                # Mark chunk as completed
                state.chunk.status = "completed"
                state.chunk.translated_texts = state.result
                state.chunk.error_message = ""

            # Update statistics
            self.translation_count += 1

            # Add to history
            self._update_history(state)

        except Exception as e:
            state.chunk.status = "failed"
            state.chunk.error_message = f"Finalization error: {e}"

        return state

    def _should_validate(self, state: TranslationState) -> str:
        """Decide whether to validate or handle error"""
        return "validate" if not state.error else "error"

    def _should_retry(self, state: TranslationState) -> str:
        """Decide whether to retry or succeed"""
        return "retry" if state.error else "success"

    def _should_continue_retry(self, state: TranslationState) -> str:
        """Decide whether to continue retrying or give up"""
        max_retries = getattr(state.request, "max_retries", 3)
        return "retry" if state.retry_count < max_retries else "error"

    def _parse_translation_response(
        self, raw_output: str, expected_count: int
    ) -> List[Dict[str, any]]:
        """Parse translation response in new JSON format"""
        try:
            # Clean the output
            cleaned_output = raw_output.strip()

            # Remove markdown code blocks if present
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]
            elif cleaned_output.startswith("```"):
                cleaned_output = cleaned_output[3:]

            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]

            # Remove trailing dots/ellipsis that might break JSON
            cleaned_output = re.sub(r"\.\.\.+\s*$", "", cleaned_output)
            cleaned_output = cleaned_output.strip()

            # Try to fix incomplete JSON by finding the last complete object
            if not cleaned_output.endswith("}") and not cleaned_output.endswith("]"):
                # Find the last complete JSON structure
                brace_count = 0
                bracket_count = 0
                last_valid_pos = -1

                for i, char in enumerate(cleaned_output):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                    elif char == "[":
                        bracket_count += 1
                    elif char == "]":
                        bracket_count -= 1

                    # Check if we have a complete structure
                    if brace_count == 0 and bracket_count == 0 and i > 0:
                        last_valid_pos = i

                if last_valid_pos > 0:
                    cleaned_output = cleaned_output[: last_valid_pos + 1]

            # Parse JSON
            try:
                response_data = json.loads(cleaned_output)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # Try to extract JSON from the response using regex
                json_match = re.search(
                    r'\{[^{}]*"translation"[^{}]*\[[^\]]*\][^{}]*\}',
                    cleaned_output,
                    re.DOTALL,
                )
                if json_match:
                    try:
                        response_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Last resort: try to fix common JSON issues
                        fixed_json = json_match.group()
                        # Fix unescaped quotes in text
                        fixed_json = re.sub(
                            r'(?<!\\)"([^"]*)"([^,:}\]]*)"', r'"\1\"\2"', fixed_json
                        )
                        response_data = json.loads(fixed_json)
                else:
                    raise ValueError("No valid JSON found in response")

            # Extract translation array
            if isinstance(response_data, dict) and "translation" in response_data:
                translations = response_data["translation"]
            elif isinstance(response_data, list):
                # Fallback: assume it's already the translation array
                translations = response_data
            else:
                raise ValueError("Invalid response format")

            # Validate format
            if not isinstance(translations, list):
                raise ValueError("Translation is not a list")

            # Ensure all items have required fields
            result = []
            for item in translations:
                if isinstance(item, dict) and "line" in item and "text" in item:
                    result.append(item)
                else:
                    print(f"Invalid translation item: {item}")

            return result

        except Exception as e:
            print(f"Error parsing translation response: {e}")
            print(f"Raw output: {raw_output[:1000]}...")
            return []

    def _update_history(self, chunk: TranslationChunk):
        """Update translation history with TranslationChunk"""
        try:
            # Create history entry for the translation
            original_texts = chunk.original_texts
            translated_texts = (
                chunk.translated_texts if hasattr(chunk, "translated_texts") else []
            )

            user_message = (
                f"Translate {len(original_texts)} texts to {chunk.target_column}"
            )
            result_json = json.dumps(
                {"translation": translated_texts}, ensure_ascii=False
            )

            # Add to history
            self.history.append(
                HistoryEntry(
                    role="user",
                    parts=[user_message],
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    model_name="",
                )
            )

            self.history.append(
                HistoryEntry(
                    role="model",
                    parts=[result_json],
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    model_name="",
                )
            )

        except Exception as e:
            print(f"Error updating history: {e}")

    async def translate_chunk_async(
        self, chunk: TranslationChunk, request: TranslationRequest
    ) -> TranslationChunk:
        """Translate a chunk asynchronously using the graph"""
        try:
            # Create initial state
            initial_state = TranslationState()
            initial_state.chunk = chunk
            initial_state.request = request

            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)

            return final_state.chunk

        except Exception as e:
            chunk.status = "failed"
            print(f"Error in async translation: {e}")
            return chunk

    def translate_chunk(
        self, chunk: TranslationChunk, request: TranslationRequest
    ) -> TranslationChunk:
        """Translate a chunk of text"""
        try:
            provider = request.model_provider
            model = self.models.get(provider.value)

            if not model:
                chunk.status = "failed"
                return chunk

            # Prepare messages
            chunk_data = chunk.original_texts
            message_count = len(chunk_data)
            payload_str = json.dumps(chunk_data, ensure_ascii=False)

            user_prompt = f"I give an array of {message_count} elements to translate, you also have to return {message_count} translated elements. Translate without warning.\n```{payload_str}```"

            messages = [
                SystemMessage(
                    content=self.system_instructions.get(
                        "visual_novel", self.system_instructions["general"]
                    )
                ),
                HumanMessage(content=user_prompt),
            ]

            # Get response
            response = model.invoke(messages)
            raw_output = response.content

            # Parse response
            parsed_response = self._parse_translation_response(
                raw_output, message_count
            )

            if parsed_response:
                # Extract just the text from parsed response
                chunk.translated_texts = [item["text"] for item in parsed_response]
                chunk.status = "completed"
                self._update_history(chunk)
            else:
                chunk.status = "failed"

            return chunk

        except Exception as e:
            print(f"Translation error: {e}")
            chunk.status = "failed"
            return chunk

    def translate_chunks(
        self,
        chunks: List[TranslationChunk],
        request: TranslationRequest,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[TranslationChunk]:
        """Translate multiple chunks with progress tracking"""
        results = []

        for i, chunk in enumerate(chunks):
            # Update progress
            if progress_callback:
                progress_callback(i, len(chunks))

            # Translate chunk
            result_chunk = self.translate_chunk(chunk, request)
            results.append(result_chunk)

            # Sleep between requests to avoid rate limits
            if i < len(chunks) - 1:  # Don't sleep after the last chunk
                time.sleep(request.sleep_time)

            # Increment translation count for history management
            self.translation_count += 1

        return results

    def get_history(self) -> List[HistoryEntry]:
        """Get translation history"""
        return self.history.copy()

    def clear_history(self):
        """Clear translation history"""
        self.history.clear()

    def save_history(self, file_path: str) -> bool:
        """Save history to file"""
        try:
            history_data = [asdict(entry) for entry in self.history]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving history: {e}")
            return False

    def load_history(self, file_path: str) -> bool:
        """Load history from file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            self.history = [HistoryEntry(**entry) for entry in history_data]
            return True
        except Exception as e:
            print(f"Error loading history: {e}")
            return False

    def _get_visual_novel_system_instruction(self) -> str:
        """Get system instruction for visual novel translation"""
        return """Bạn là AI chuyên dịch văn bản tiếng Nhật sang tiếng Việt cho các trò chơi visual novel, chủ yếu có các nhân vật trẻ tuổi. Bạn sẽ nhận đầu vào ở định dạng mảng JSON và phải xuất bản bản dịch theo đúng cấu trúc đối tượng JSON này:

```json
{
"translation": [
{ "line": 1, "text": "..." },
{ "line": 2, "text": "..." },
...
]
}
```

### Quy tắc định dạng đầu ra:

1. Định dạng đối tượng JSON nghiêm ngặt:

* Đầu ra phải là đối tượng JSON có một khóa duy nhất: `"translation"`, có giá trị là một mảng các đối tượng.
* Mỗi đối tượng phải bao gồm:

* `"line"`: số dòng, bắt đầu từ 1.
* `"text"`: chuỗi đã dịch.

Ví dụ:

```json
{
"translation": [
{ "line": 1, "text": "Thời tiết hôm nay thật đẹp." }, 
{ "line": 2, "text": "Đúng thật. Điều đó làm tôi cảm thấy tràn đầy sức sống." }, 
{ "line": 3, "text": " Chúng ta đi dạo trong công viên nhé?" } 
] 
} 
```

2. Duy trì số lượng và thứ tự phần tử: 

* Số phần tử trong mảng `"dịch"` phải khớp chính xác với đầu vào. 
* Giữ nguyên thứ tự các phần tử.

---

### Nguyên tắc dịch:

3. Bảo tồn văn hóa và bối cảnh: 

* Bảo tồn các biểu hiện và sắc thái văn hóa Nhật Bản. 
* Sử dụng phiên âm (La Mã hóa) cho từ tượng thanh, các thuật ngữ không có từ tương đương trực tiếp trong tiếng Việt hoặc tên gọi cụ thể về mặt văn hóa:

* ví dụ, えと → *Eto*, 青藍島 → *Đảo Seiran*, 麻沙音 → *Asane*.

4. Phong cách tường thuật hài hước và châm biếm:

* Ưu tiên phong cách có sự mỉa mai hoặc hài hước tinh tế, đặc biệt là trong lời tường thuật.
* Lời tường thuật phải phản ánh độc thoại nội tâm của nhân vật chính, thường chế giễu các tình huống hoặc nhân vật.

5. Giọng điệu trẻ trung, không trang trọng:

* Sử dụng ngôn ngữ thông thường phù hợp với thanh thiếu niên hoặc người trẻ tuổi. Bao gồm tiếng lóng khi phù hợp.

6. Giữ nguyên kính ngữ:

* Giữ nguyên hậu tố kính ngữ như chúng xuất hiện: `-san`, `-chan`, `-senpai`, `-kun`, `-sama`, v.v.
* Ví dụ: 橘くん → *Tachibana-kun*, アサちゃん → *Asa-chan*

7. Cấu trúc câu và phân đoạn:

* Nếu nhiều dòng đầu vào tạo thành một câu, trước tiên hãy dịch toàn bộ câu một cách tự nhiên, sau đó phân đoạn đầu ra để khớp với căn chỉnh từng dòng.

Ví dụ: 

```json 
Đầu vào: ["そう、ここは青藍島。", "魑魅魍魎跋扈", "す、エロの", "伏魔殿", "。"] 
Đầu ra: { 
"bản dịch": [ 
{ "line": 1, "text": " Đúng vậy, đây là đảo Seiran." }, 
{ "line": 2, "text": "Nơi yêu quái" }, 
{ "line": 3, "text": " hoành hành," }, 
{ "line": 4, "text": " chứa đầy" }, 
{ "line": 5, "text": " đồi bại." }
]
}
```

8. Tiếng Việt tự nhiên và súc tích:

* Dịch sang tiếng Việt trôi chảy, súc tích, tự nhiên.
* Ưu tiên khẳng định trực tiếp hơn phủ định kép theo nghĩa đen vụng về.

Ví dụ điều chỉnh:

* 原文:「それはないこともない。」→ "Có thể là có." (không phải "Cũng không phải là không có.")

9. Nhận dạng nhân vật rõ ràng:

* Nếu một dòng chỉ chứa tên nhân vật thì dòng sau được coi là lời thoại của nhân vật đó.
* Duy trì cấu trúc này một cách chính xác trong bản dịch. Tên và đoạn hội thoại sẽ xuất hiện dưới dạng hai mục riêng biệt, khớp với thông tin đầu vào.

Ví dụ:

```json
Đầu vào: ["淳之介", " 「ほら、アサちゃん。朝だぞ」", "麻沙音", " 「バカじゃん……」"]
Đầu ra: { 
"bản dịch": [ 
{ "dòng": 1, "văn bản": "Junnosuke" }, 
{ "line": 2, "text": " 「Nè, Asa-chan. Sáng rồi đó」" }, 
{ "dòng": 3, "văn bản": "Asane" }, 
{ "line": 4, "text": " 「Đồ ngu...」" } 
]
}
```

* Luôn dịch tên một cách nhất quán.
* Không kết hợp tên và đoạn hội thoại thành một chuỗi duy nhất.
* Nếu các phân đoạn đầu vào được phân chia thì đầu ra phải tuân theo chính xác phân đoạn tương tự.

10. Trình giữ chỗ Bảo quản:

* Giữ nguyên các chỗ giữ chỗ như `[Color_0]`, `[Ascii_0]` như hiện trạng.

11. Không kiểm duyệt:

* Dịch trung thực, bao gồm nội dung nhạy cảm hoặc rõ ràng mà không lược bỏ hoặc che."""

    def _get_general_system_instruction(self) -> str:
        """Get system instruction for general translation"""
        return """Bạn là AI chuyên dịch văn bản tiếng Nhật sang tiếng Việt cho các trò chơi visual novel, chủ yếu có các nhân vật trẻ tuổi. Bạn sẽ nhận đầu vào ở định dạng mảng JSON và phải xuất bản bản dịch theo đúng cấu trúc đối tượng JSON này:

```json
{
"translation": [
{ "line": 1, "text": "..." },
{ "line": 2, "text": "..." },
...
]
}
```

### Quy tắc định dạng đầu ra:

1. Định dạng đối tượng JSON nghiêm ngặt:

* Đầu ra phải là đối tượng JSON có một khóa duy nhất: `"translation"`, có giá trị là một mảng các đối tượng.
* Mỗi đối tượng phải bao gồm:

* `"line"`: số dòng, bắt đầu từ 1.
* `"text"`: chuỗi đã dịch.

Ví dụ:

```json
{
"translation": [
{ "line": 1, "text": "Thời tiết hôm nay thật đẹp." }, 
{ "line": 2, "text": "Đúng thật. Điều đó làm tôi cảm thấy tràn đầy sức sống." }, 
{ "line": 3, "text": " Chúng ta đi dạo trong công viên nhé?" } 
] 
} 
```

2. Duy trì số lượng và thứ tự phần tử: 

* Số phần tử trong mảng `"dịch"` phải khớp chính xác với đầu vào. 
* Giữ nguyên thứ tự các phần tử.

---

### Nguyên tắc dịch:

3. Bảo tồn văn hóa và bối cảnh: 

* Bảo tồn các biểu hiện và sắc thái văn hóa Nhật Bản. 
* Sử dụng phiên âm (La Mã hóa) cho từ tượng thanh, các thuật ngữ không có từ tương đương trực tiếp trong tiếng Việt hoặc tên gọi cụ thể về mặt văn hóa:

* ví dụ, えと → *Eto*, 青藍島 → *Đảo Seiran*, 麻沙音 → *Asane*.

4. Phong cách tường thuật hài hước và châm biếm:

* Ưu tiên phong cách có sự mỉa mai hoặc hài hước tinh tế, đặc biệt là trong lời tường thuật.
* Lời tường thuật phải phản ánh độc thoại nội tâm của nhân vật chính, thường chế giễu các tình huống hoặc nhân vật.

5. Giọng điệu trẻ trung, không trang trọng:

* Sử dụng ngôn ngữ thông thường phù hợp với thanh thiếu niên hoặc người trẻ tuổi. Bao gồm tiếng lóng khi phù hợp.

6. Giữ nguyên kính ngữ:

* Giữ nguyên hậu tố kính ngữ như chúng xuất hiện: `-san`, `-chan`, `-senpai`, `-kun`, `-sama`, v.v.
* Ví dụ: 橘くん → *Tachibana-kun*, アサちゃん → *Asa-chan*

7. Cấu trúc câu và phân đoạn:

* Nếu nhiều dòng đầu vào tạo thành một câu, trước tiên hãy dịch toàn bộ câu một cách tự nhiên, sau đó phân đoạn đầu ra để khớp với căn chỉnh từng dòng.

Ví dụ: 

```json 
Đầu vào: ["そう、ここは青藍島。", "魑魅魍魎跋扈", "す、エロの", "伏魔殿", "。"] 
Đầu ra: { 
"bản dịch": [ 
{ "line": 1, "text": " Đúng vậy, đây là đảo Seiran." }, 
{ "line": 2, "text": "Nơi yêu quái" }, 
{ "line": 3, "text": " hoành hành," }, 
{ "line": 4, "text": " chứa đầy" }, 
{ "line": 5, "text": " đồi bại." }
]
}
```

8. Tiếng Việt tự nhiên và súc tích:

* Dịch sang tiếng Việt trôi chảy, súc tích, tự nhiên.
* Ưu tiên khẳng định trực tiếp hơn phủ định kép theo nghĩa đen vụng về.

Ví dụ điều chỉnh:

* 原文:「それはないこともない。」→ "Có thể là có." (không phải "Cũng không phải là không có.")

9. Nhận dạng nhân vật rõ ràng:

* Nếu một dòng chỉ chứa tên nhân vật thì dòng sau được coi là lời thoại của nhân vật đó.
* Duy trì cấu trúc này một cách chính xác trong bản dịch. Tên và đoạn hội thoại sẽ xuất hiện dưới dạng hai mục riêng biệt, khớp với thông tin đầu vào.

Ví dụ:

```json
Đầu vào: ["淳之介", " 「ほら、アサちゃん。朝だぞ」", "麻沙音", " 「バカじゃん……」"]
Đầu ra: { 
"bản dịch": [ 
{ "dòng": 1, "văn bản": "Junnosuke" }, 
{ "line": 2, "text": " 「Nè, Asa-chan. Sáng rồi đó」" }, 
{ "dòng": 3, "văn bản": "Asane" }, 
{ "line": 4, "text": " 「Đồ ngu...」" } 
]
}
```

* Luôn dịch tên một cách nhất quán.
* Không kết hợp tên và đoạn hội thoại thành một chuỗi duy nhất.
* Nếu các phân đoạn đầu vào được phân chia thì đầu ra phải tuân theo chính xác phân đoạn tương tự.

10. Trình giữ chỗ Bảo quản:

* Giữ nguyên các chỗ giữ chỗ như `[Color_0]`, `[Ascii_0]` như hiện trạng.

11. Không kiểm duyệt:

* Dịch trung thực, bao gồm nội dung nhạy cảm hoặc rõ ràng mà không lược bỏ hoặc che."""

# Hướng Dẫn Cài Đặt CSV Translator v2.0

## Yêu Cầu Hệ Thống

- Python 3.8 trở lên
- Windows, macOS, hoặc Linux
- 500MB dung lượng đĩa trống
- Kết nối internet (để cài đặt dependencies và sử dụng API)

## Cài Đặt

### Bước 1: Clone Repository

```bash
git clone https://github.com/ILSakurajimaMai/Trans_Clone.git
cd Trans_Clone
```

Hoặc pull branch mới nhất:

```bash
git checkout claude/optimize-csv-translator-app-011CUfEG7mab4fTpoy4YPtJu
git pull
```

### Bước 2: Cài Đặt Dependencies

#### Cách 1: Sử dụng requirements.txt (Khuyến Nghị)

```bash
pip install -r requirements.txt
```

#### Cách 2: Cài Đặt Thủ Công

```bash
# UI Framework
pip install PyQt6>=6.4.0

# Data Processing
pip install pandas>=1.3.0

# AI/LLM Libraries
pip install langgraph>=0.0.55
pip install langchain>=0.1.0
pip install langchain-google-genai>=1.0.0
pip install langchain-openai>=0.1.0
pip install langchain-anthropic>=0.1.0
pip install google-generativeai>=0.3.0

# Security & Networking
pip install cryptography>=41.0.0
pip install requests>=2.31.0

# Utilities
pip install python-dotenv>=0.19.0
pip install typing-extensions>=4.0.0
```

### Bước 3: Kiểm Tra Cài Đặt

```bash
python -c "import PyQt6, pandas, cryptography, requests; print('All dependencies installed successfully!')"
```

Nếu không có lỗi, bạn đã cài đặt thành công!

## Chạy Ứng Dụng

```bash
python main.py
```

## Cấu Hình Lần Đầu

### 1. Không Cần Nhập API Key Ngay

Ứng dụng sẽ khởi động mà không yêu cầu API key. Bạn có thể:
- Khám phá giao diện
- Mở CSV files
- Chỉnh sửa dữ liệu
- Cấu hình sau khi đã làm quen

### 2. Cấu Hình API Keys (Khi Cần Dịch)

1. Chuyển sang tab **"🔑 API Configuration"**
2. Chọn service bạn muốn dùng (Google Gemini, OpenAI, Anthropic, hoặc Custom)
3. Nhập API key của bạn
4. Click **"💾 Save API Key"**
5. (Optional) Click **"🧪 Test Connection"** để kiểm tra

### 3. Lấy API Keys

#### Google Gemini (Miễn Phí - Khuyến Nghị Cho Bắt Đầu)
1. Truy cập: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy API key

#### OpenAI (Trả Phí)
1. Truy cập: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy API key

#### Anthropic Claude (Trả Phí)
1. Truy cập: https://console.anthropic.com/
2. Tạo API key
3. Copy API key

### 4. Cấu Hình System Instructions (Optional)

1. Chuyển sang tab **"📝 Instructions"**
2. Chỉnh sửa **Translation Instruction** (hướng dẫn AI dịch như thế nào)
3. Chỉnh sửa **Summary Instruction** (hướng dẫn AI tóm tắt như thế nào)
4. Click **"💾 Save as Template"** để lưu template của bạn

## Sử Dụng Cơ Bản

### Mở File CSV

1. **File** → **Open CSV Files**
2. Chọn một hoặc nhiều file CSV
3. File sẽ hiển thị trong bảng

### Dịch Toàn Bộ File

1. Click nút **"🚀 Start Translation"**
2. Chọn settings:
   - Target column (cột để lưu bản dịch)
   - Chunk size (số dòng mỗi lần dịch)
   - Sleep time (thời gian chờ giữa các lần gọi API)
3. Click **"Start"**

### Dịch Các Dòng Đã Chọn (NEW!)

1. Bôi đen các dòng cần dịch trong bảng
2. Right-click → **"🌐 Translate Selected Rows"**
3. Chọn mode:
   - **"Without Context"**: Dịch nhanh không dùng context
   - **"With Context..."**: Dịch có context từ file khác (chất lượng tốt hơn)

### Tạo Summary (NEW!)

1. Chuyển sang tab **"📊 Summary"**
2. Click **"➕ New Summary"**
3. Chọn files để lấy context
4. Xem kết quả (lưu tối đa 3 summaries)
5. Export summary ra file text nếu cần

## Xử Lý Lỗi

### Lỗi: "ModuleNotFoundError: No module named 'cryptography'"

**Giải pháp:**
```bash
pip install cryptography requests
```

Sau đó restart ứng dụng.

### Lỗi: "QWidget: Must construct a QApplication before a QWidget"

**Giải pháp:** Đã được fix trong version mới nhất. Pull code mới nhất:
```bash
git pull
```

### Ứng Dụng Khởi Động Nhưng Tab API Configuration Hiển thị Lỗi

**Nguyên nhân:** Thiếu module `cryptography`

**Giải pháp:**
```bash
pip install cryptography requests
python main.py
```

### API Test Connection Failed

**Kiểm tra:**
1. API key đúng chưa?
2. Có kết nối internet không?
3. API service có hoạt động không?
4. Đã hết quota API chưa?

## Tính Năng Mới Trong v2.0

✅ **Tabbed Interface**: Giao diện tabs dễ dùng
✅ **API Configuration Tab**: Quản lý API keys không làm gián đoạn công việc
✅ **System Instructions Tab**: Editor instructions với template system
✅ **Summary Tab**: Tóm tắt nội dung với history
✅ **Selective Row Translation**: Dịch chỉ những dòng đã chọn
✅ **Context-Aware Translation**: Dịch có context từ files khác
✅ **Encrypted API Keys**: API keys được mã hóa an toàn
✅ **Custom API Endpoints**: Thêm custom API endpoints của riêng bạn
✅ **Graceful Error Handling**: Ứng dụng không crash khi thiếu dependencies

## Tips & Tricks

### 1. Sử dụng Context Cho Dịch Chất Lượng Cao

Khi dịch:
- Chọn **"With Context"**
- Chọn các file đã dịch trước đó
- AI sẽ học từ các bản dịch cũ và dịch nhất quán hơn

### 2. Tạo Template Instructions

- Tạo nhiều templates cho các loại nội dung khác nhau
- Ví dụ: Template cho game, manga, novel, technical docs
- Load template phù hợp trước khi dịch

### 3. Summary Để Tracking Progress

- Tạo summary sau mỗi session dịch
- Export summary để làm documentation
- Review summaries để đảm bảo quality

### 4. Keyboard Shortcuts

- `Ctrl+S`: Save
- `Ctrl+Z`: Undo
- `Ctrl+Y`: Redo
- `Ctrl+C`: Copy
- `Ctrl+V`: Paste
- `Ctrl+F`: Find
- `F3`: Find Next
- `Del`: Delete

## Báo Lỗi & Đóng Góp

Nếu gặp lỗi hoặc có đề xuất:
1. Tạo issue trên GitHub
2. Mô tả chi tiết lỗi và các bước tái hiện
3. Attach screenshots nếu có

## License

MIT License - See LICENSE file for details

## Credits

Phát triển bởi ILSakurajimaMai
Optimized by Claude (Anthropic)

---

**Chúc bạn dịch vui vẻ! 🎉**

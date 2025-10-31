"""
CSV Translator with AI - Main Entry Point

A powerful CSV translation tool with support for multiple AI providers,
advanced editing features, and Excel-like functionality.

Features:
- Multi-provider AI translation (Google AI, OpenAI, Anthropic)
- Advanced table editing with undo/redo
- Find and replace functionality
- Dark/Light theme support
- Translation history management
- Batch processing
"""

import sys
import os
import traceback
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.main_window import CSVTranslatorMainWindow
from config.settings import AppSettings


def setup_application():
    """Setup the QApplication with proper configuration"""
    # Enable high DPI support
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("CSV Translator with AI")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("CSV Translator")

    # Set application icon if available
    icon_path = project_root / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    return app


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []

    # Check PyQt6
    try:
        import PyQt6
    except ImportError:
        missing_deps.append("PyQt6")

    # Check pandas
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")

    # Check LangChain components
    try:
        import langchain
    except ImportError:
        missing_deps.append("langchain")

    try:
        import langgraph
    except ImportError:
        missing_deps.append("langgraph")

    # Check Google AI (optional)
    try:
        import langchain_google_genai
    except ImportError:
        print(
            "Warning: Google AI support not available. Install langchain-google-genai for Google AI features."
        )

    if missing_deps:
        error_msg = f"Missing required dependencies: {', '.join(missing_deps)}\n\n"
        error_msg += "Please install them using:\n"
        error_msg += f"pip install {' '.join(missing_deps)}"

        print(error_msg)

        # Show GUI error if PyQt6 is available
        if "PyQt6" not in missing_deps:
            try:
                app = QApplication(sys.argv)
                QMessageBox.critical(None, "Missing Dependencies", error_msg)
            except:
                pass

        return False

    return True


def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "An unexpected error occurred:\n\n"
    error_msg += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    print(error_msg)

    # Try to show error dialog
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, "Unexpected Error", error_msg)
    except Exception as e:
        print(f"Error showing GUI error: {str(e)}")


def main():
    """Main function"""
    print("Starting CSV Translator application...")

    # Set up exception handling
    sys.excepthook = handle_exception

    print("Checking dependencies...")
    # Check dependencies
    if not check_dependencies():
        print("Dependencies check failed")
        sys.exit(1)
    print("Dependencies OK")

    try:
        print("Setting up application...")
        # Setup application
        app = setup_application()

        print("Creating main window...")
        # Create and show main window
        window = CSVTranslatorMainWindow()
        print("Showing window...")
        window.show()

        print("Logging startup...")
        # Log startup
        window.log("CSV Translator with AI started successfully")
        window.log(f"Using theme: {AppSettings.DEFAULT_THEME}")

        print("Starting event loop...")
        # Run application
        sys.exit(app.exec())

    except Exception as e:
        error_msg = f"Failed to start application: {str(e)}\n\n"
        error_msg += traceback.format_exc()

        print(error_msg)

        # Try to show error dialog
        try:
            app = QApplication([])
            QMessageBox.critical(
                None, "Startup Error", f"Failed to start application:\n\n{str(e)}"
            )
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()

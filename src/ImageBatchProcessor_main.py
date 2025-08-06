import sys,os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ImageBatchProcessor_model import ImageBatchModel
from src.ImageBatchProcessor_presenter import ImageBatchPresenter
from src.ImageBatchProcessor_view import ImageBatchView
sys.path.append(os.path.dirname(__file__))
from src import __version__ 
from src import get_resource_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(f"ImageBatchProcessor v{__version__}")
    base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    icon_path = os.path.join(base_dir, "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    try:
        qss_path = get_resource_path("src/style.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print("QSS 加载失败:", e)
    # 加载 QSS 样式

        
    model = ImageBatchModel()
    view = ImageBatchView()
    presenter = ImageBatchPresenter(model, view)
    # 让 view 主动发出初始状态
    view.emit_initial_signals()
    view.show()
    sys.exit(app.exec())
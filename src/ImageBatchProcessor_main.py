import sys,os
from PyQt6.QtWidgets import QApplication
from src.ImageBatchProcessor_model import ImageBatchModel
from src.ImageBatchProcessor_presenter import ImageBatchPresenter
from src.ImageBatchProcessor_view import ImageBatchView
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    model = ImageBatchModel()
    view = ImageBatchView()
    presenter = ImageBatchPresenter(model, view)
    # 让 view 主动发出初始状态
    view.emit_initial_signals()
    view.show()
    sys.exit(app.exec())
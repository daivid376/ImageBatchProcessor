import sys
from PyQt6.QtWidgets import QApplication
from ImageBatchProcessor_model import ImageBatchModel
from ImageBatchProcessor_view import ImageBatchView
from ImageBatchProcessor_presenter import ImageBatchPresenter

if __name__ == "__main__":
    app = QApplication(sys.argv)
    model = ImageBatchModel()
    view = ImageBatchView()
    presenter = ImageBatchPresenter(model, view)
    view.show()
    sys.exit(app.exec())
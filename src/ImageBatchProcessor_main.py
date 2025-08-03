import sys
from PyQt6.QtWidgets import QApplication
from ImageBatchProcessor_ui import ImageBatchProcessorUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ImageBatchProcessorUI()
    win.show()
    sys.exit(app.exec())
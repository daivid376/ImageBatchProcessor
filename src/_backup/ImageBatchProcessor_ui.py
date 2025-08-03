import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox,
    QMessageBox, QAbstractItemView, QHeaderView, QDialog, QScrollArea
)
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtCore import Qt,QSize
from PIL import Image
from ImageBatchProcessor_utils import process_image_v5

class PreviewDialog(QDialog):
    def __init__(self, path):
        super().__init__()
        self.setWindowTitle(os.path.basename(path))
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        lbl = QLabel()
        img = Image.open(path).convert("RGB")
        img_qt = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img_qt)
        lbl.setPixmap(pixmap)
        lbl.setScaledContents(True)
        scroll.setWidget(lbl)
        layout.addWidget(scroll)
        self.resize(800, 800)

class ImageBatchProcessorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量图片处理工具 V13 (PyQt6)")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 输入文件列表在最上方
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["缩略图", "文件路径"])
        self.tree.setIconSize(QSize(60, 60)) 
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(self.preview_image)
        layout.addWidget(self.tree)

        # 输出目录选择
        out_layout = QHBoxLayout()
        self.output_entry = QLineEdit()
        self.output_entry.setPlaceholderText("拖入或选择输出文件夹")
        out_btn = QPushButton("选择输出文件夹")
        out_btn.clicked.connect(self.select_output_folder)
        out_layout.addWidget(self.output_entry)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # 选项
        options_layout = QHBoxLayout()
        self.flip_check = QCheckBox("水平翻转")
        self.flip_check.setChecked(True)
        self.noise_entry = QLineEdit("2.0")
        self.rot_min_entry = QLineEdit("0.5")
        self.rot_max_entry = QLineEdit("1.5")
        options_layout.addWidget(self.flip_check)
        options_layout.addWidget(QLabel("噪点强度:"))
        options_layout.addWidget(self.noise_entry)
        options_layout.addWidget(QLabel("旋转最小:"))
        options_layout.addWidget(self.rot_min_entry)
        options_layout.addWidget(QLabel("旋转最大:"))
        options_layout.addWidget(self.rot_max_entry)
        layout.addLayout(options_layout)

        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.run_processing)
        layout.addWidget(process_btn)

    # 支持拖入文件或文件夹
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            self.add_files([path])

    def add_files(self, files):
        for f in files:
            f = os.path.abspath(f)
            if os.path.isdir(f):
                folder_item = QTreeWidgetItem(["", f])
                self.tree.addTopLevelItem(folder_item)
                for img in os.listdir(f):
                    full = os.path.join(f, img)
                    if full.lower().endswith((".png", ".jpg", ".jpeg")):
                        child = QTreeWidgetItem(["", full])
                        self.set_thumbnail(child, full)
                        folder_item.addChild(child)
            else:
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    item = QTreeWidgetItem(["", f])
                    self.set_thumbnail(item, f)
                    self.tree.addTopLevelItem(item)

    def set_thumbnail(self, item, path):
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((120, 120))
            img_qt = QImage(
                img.tobytes(),
                img.width,
                img.height,
                img.width * 3,
                QImage.Format.Format_RGB888
        )
            pixmap = QPixmap.fromImage(img_qt)
            icon = QIcon(pixmap)
            item.setIcon(0, icon)
        except Exception as e:
            print(f"缩略图加载失败: {e}")


    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_entry.setText(folder)

    def preview_image(self, item, column):
        path = item.text(1)
        if not os.path.isfile(path):
            return
        dlg = PreviewDialog(path)
        dlg.exec()

    def run_processing(self):
        files = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if os.path.isdir(item.text(1)):
                for j in range(item.childCount()):
                    files.append(item.child(j).text(1))
            else:
                files.append(item.text(1))
        if not files:
            QMessageBox.critical(self, "错误", "请选择图片")
            return
        output_dir = self.output_entry.text()
        if not output_dir:
            QMessageBox.critical(self, "错误", "请选择输出文件夹")
            return
        os.makedirs(output_dir, exist_ok=True)
        for img_file in files:
            img_out = process_image_v5(img_file, self.flip_check.isChecked(), float(self.noise_entry.text()), float(self.rot_min_entry.text()), float(self.rot_max_entry.text()))
            filename = os.path.basename(img_file)
            img_out.save(os.path.join(output_dir, "mod_" + filename), quality=95)
        QMessageBox.information(self, "完成", f"处理完成，结果保存在: {output_dir}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ImageBatchProcessorUI()
    win.show()
    sys.exit(app.exec())

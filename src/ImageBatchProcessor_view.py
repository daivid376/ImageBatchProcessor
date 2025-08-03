# ImageBatchProcessor_view.py
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QLineEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox, \
    QMessageBox, QAbstractItemView, QHeaderView, QProgressBar, QSpinBox
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PIL import Image
class DropLineEdit(QLineEdit):
    def __init__(self, callback = None,parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._callback = callback

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and os.path.isdir(urls[0].toLocalFile()):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
        
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.setText(path)
                if self._callback:
                    self._callback(path)

class ImageBatchView(QMainWindow):
    files_dropped = pyqtSignal(list)
    output_folder_selected = pyqtSignal(str)
    process_requested = pyqtSignal(bool, float, float, float)
    file_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量图片处理工具 MVP")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["缩略图", "文件路径"])
        self.tree.setIconSize(QSize(60, 60))
        
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree)

        out_layout = QHBoxLayout()
        self.output_entry = DropLineEdit(self.output_folder_selected.emit,self)
        out_btn = QPushButton("选择输出文件夹")
        out_btn.clicked.connect(self.select_output_folder)
        out_layout.addWidget(self.output_entry)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        options_layout = QHBoxLayout()
        self.flip_check = QCheckBox("水平翻转")
        self.flip_check.setChecked(True)
        self.noise_entry = QLineEdit("2.0")
        self.rot_min_entry = QLineEdit("0.5")
        self.rot_max_entry = QLineEdit("1.5")
        options_layout.addWidget(self.flip_check)
        options_layout.addWidget(QLabel("噪点强度"))
        options_layout.addWidget(self.noise_entry)
        options_layout.addWidget(QLabel("旋转最小"))
        options_layout.addWidget(self.rot_min_entry)
        options_layout.addWidget(QLabel("旋转最大"))
        options_layout.addWidget(self.rot_max_entry)
        layout.addLayout(options_layout)
        
        # 缩略图大小设置
        self.thumb_size_entry = QSpinBox()
        self.thumb_size_entry.setRange(20, 300)
        self.thumb_size_entry.setValue(40)
        options_layout.addWidget(QLabel("缩略图大小"))
        options_layout.addWidget(self.thumb_size_entry)
        self.thumb_size_entry.valueChanged.connect(self.update_thumbnail_size)
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.emit_process)
        layout.addWidget(process_btn)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]

        # 获取当前已有文件路径
        existing_files = set()
        for i in range(self.tree.topLevelItemCount()):
            existing_files.add(self.tree.topLevelItem(i).text(1))

        # 过滤掉已存在的文件
        new_paths = [p for p in paths if p not in existing_files]
        if new_paths:
            self.files_dropped.emit(new_paths)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_entry.setText(folder)
            self.output_folder_selected.emit(folder)

    def emit_process(self):
        try:
            self.process_requested.emit(
                self.flip_check.isChecked(),
                float(self.noise_entry.text()),
                float(self.rot_min_entry.text()),
                float(self.rot_max_entry.text())
            )
        except:
            QMessageBox.critical(self, "错误", "参数输入不正确")
    def set_item_icon(self, item, path, size):
        img = Image.open(path).convert("RGB")
        img.thumbnail((size, size))
        img_qt = QImage(img.tobytes(), img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
        icon = QIcon(QPixmap.fromImage(img_qt))
        item.setIcon(0, icon)
    def update_thumbnail_size(self):
        size = self.thumb_size_entry.value()
        self.tree.setIconSize(QSize(size, size))
        # 重新绘制已有缩略图
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            path = item.text(1)
            self.set_item_icon(item, path, size)
    def add_file_item(self, path):
        """
        向文件列表添加缩略图项，缩略图尺寸可根据当前设置动态调整，
        并修正潜在的倾斜问题。
        """
        size = self.thumb_size_entry.value()
        item = QTreeWidgetItem(["", path])

        # 加载图片并生成缩略图
        img = Image.open(path).convert("RGB")
        img.thumbnail((size, size))

        # 转换为QImage，显式指定bytesPerLine避免倾斜
        data = img.tobytes("raw", "RGB")
        img_qt = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)

        # 设置图标
        icon = QIcon(QPixmap.fromImage(img_qt))
        item.setIcon(0, icon)

        # 添加到列表
        self.tree.addTopLevelItem(item)

        # 强制同步QTreeWidget图标大小
        self.tree.setIconSize(QPixmap.fromImage(img_qt).size())
    def keyPressEvent(self, event):
        # 检测 Delete 键
        if event.key() == Qt.Key.Key_Delete:
            for item in self.tree.selectedItems():
                self.file_removed.emit(item.text(1))  # 发射删除信号
                idx = self.tree.indexOfTopLevelItem(item)
                if idx != -1:
                    self.tree.takeTopLevelItem(idx)
        else:
            super().keyPressEvent(event)
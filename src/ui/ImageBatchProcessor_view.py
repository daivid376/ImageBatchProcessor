import os,sys,json
from dataclasses import asdict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox,
    QMessageBox, QAbstractItemView, QHeaderView, QProgressBar, QMenuBar, QMenu,QDialog,QApplication,QSlider,QDoubleSpinBox,QInputDialog, QStyleOptionSlider, QStyle,QTabWidget,QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QSettings, QRect,pyqtSlot,QTimer
from PyQt6.QtGui import QPixmap, QImage, QIcon, QPainter
from PIL import Image
from src.config import ImageProcessConfig
from src import __version__ ,get_resource_path
from dataclasses import fields
from src.ui.common_widgets import ProgressDialog, FloatSliderWidget, DropLineEdit
from src.ui.menu_bar import MenuManager  
from src.ui.comfyui_section import ComfyUISection
from src.config import GlobalConfig    
class ImageBatchView(QMainWindow):
    files_dropped = pyqtSignal(list)
    output_folder_selected = pyqtSignal(str)
    process_requested = pyqtSignal(ImageProcessConfig)
    file_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量图片处理工具 MVP (动态UI版)")
        self.setGeometry(100, 100, 900, 700)
        
        self.setAcceptDrops(True)
        self.settings = QSettings(GlobalConfig.APP_ORG, GlobalConfig.APP_NAME)

        # 设置窗口图标
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        icon_path = os.path.join(base_dir, "resources", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建菜单栏
        self.menu_manager = MenuManager(self)
        self.setMenuBar(self.menu_manager.build())
        
        # 主体布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        
        # 文件列表
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["缩略图", "文件路径"])
        self.tree.setIconSize(QSize(60, 60))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree)

        # 输出目录选择
        out_layout = QHBoxLayout()
        self.output_entry = DropLineEdit(self.output_folder_selected.emit, self)
        self.output_entry.setObjectName("output_dir")
        self.output_entry.setProperty("persist", True)
        out_btn = QPushButton("选择输出文件夹")
        out_btn.clicked.connect(self.select_output_folder)
        out_layout.addWidget(self.output_entry)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)
        
        # 清空列表
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_all_items)
        layout.addWidget(clear_btn)
        
        # 创建tab
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 第一个 Tab：参数设置
        param_tab = QWidget()
        param_layout = QVBoxLayout(param_tab)

        # 动态参数控件
        self.param_widgets = {}
        param_layout.setSpacing(5)
        self.build_dynamic_params(param_layout)

        # 处理按钮（✅ 要加到布局中）
        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.emit_process)
        param_layout.addWidget(process_btn)

        # 加入 Tab
        self.tab_widget.addTab(param_tab, "图像处理")

        # 第二个 Tab：ComfyUI
        self.comfy_section = ComfyUISection()
        self.tab_widget.addTab(self.comfy_section, "ComfyUI")

        #读取配置
        self.load_settings()
        
    def build_dynamic_params(self, parent_layout):
        params_layout = QVBoxLayout()
        params_layout.setSpacing(5)
        
        for f in fields(ImageProcessConfig):
            row = QHBoxLayout()
            label_text = f.metadata.get("label", f.name)
            tooltip_text = f.metadata.get("tooltip", "")

            label = QLabel(label_text)
            label.setFixedWidth(100)
            label.setToolTip(tooltip_text)

            if f.type == bool:
                widget = QCheckBox()
                widget.setChecked(getattr(ImageProcessConfig(), f.name))
            elif f.metadata.get("slider", False):
                widget = FloatSliderWidget(
                    f.metadata.get("min", 0.0),
                    f.metadata.get("max", 1.0),
                    f.metadata.get("step", 0.01),
                    getattr(ImageProcessConfig(), f.name)
                )
                widget.setValue(getattr(ImageProcessConfig(), f.name))
            else:
                widget = QLineEdit(str(getattr(ImageProcessConfig(), f.name)))
                widget.setFixedWidth(80)

            widget.setObjectName(f.name)
            widget.setProperty("persist", True)
            widget.setToolTip(tooltip_text)

            self.param_widgets[f.name] = widget
            row.addWidget(label)
            row.addWidget(widget)
            row.addStretch()
            params_layout.addLayout(row)
        
        parent_layout.addLayout(params_layout)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_entry.setText(folder)
            self.output_folder_selected.emit(folder)

    def change_thumb_size(self, size):
        self.tree.setIconSize(QSize(size, size))
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            path = item.text(1)
            self.set_item_icon(item, path, size)

    def collect_parameters(self):
        kwargs = {}
        for f in fields(ImageProcessConfig):
            widget = self.param_widgets.get(f.name)
            if not widget:
                continue
            if isinstance(widget, QCheckBox):
                kwargs[f.name] = widget.isChecked()
            elif isinstance(widget, FloatSliderWidget):
                kwargs[f.name] = widget.value()
            else:
                text = widget.text()
                if f.type == bool:
                    kwargs[f.name] = text.lower() in ("true", "1", "yes", "y")
                elif f.type == int:
                    kwargs[f.name] = int(text)
                elif f.type == float:
                    kwargs[f.name] = float(text)
                else:
                    kwargs[f.name] = text
        return ImageProcessConfig(**kwargs)

    def emit_process(self):
        try:
            config = self.collect_parameters()
            # 创建进度对话框
            total_files = len(self.tree.findItems("", Qt.MatchFlag.MatchContains))

            # 发出处理请求
            self.process_requested.emit(config)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"参数输入不正确: {e}")

    def set_item_icon(self, item, path, size):
        img = Image.open(path).convert("RGB")
        img.thumbnail((size, size))
        img_qt = QImage(img.tobytes(), img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
        icon = QIcon(QPixmap.fromImage(img_qt))
        item.setIcon(0, icon)

    def add_file_item(self, path):
        size = self.tree.iconSize().width()
        item = QTreeWidgetItem(["", path])
        img = Image.open(path).convert("RGB")
        img.thumbnail((size, size))
        data = img.tobytes("raw", "RGB")
        img_qt = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
        icon = QIcon(QPixmap.fromImage(img_qt))
        item.setIcon(0, icon)
        self.tree.addTopLevelItem(item)
        self.tree.setIconSize(QPixmap.fromImage(img_qt).size())
    def clear_all_items(self):
        self.tree.clear()
        self.file_removed.emit("__CLEAR_ALL__")
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.tree.selectedItems():
                self.file_removed.emit(item.text(1))
                idx = self.tree.indexOfTopLevelItem(item)
                if idx != -1:
                    self.tree.takeTopLevelItem(idx)
        else:
            super().keyPressEvent(event)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.files_dropped.emit(paths)
    def save_settings(self):
        for widget in self.findChildren(QWidget):
            if widget.property("persist"):
                key = widget.objectName()
                if isinstance(widget, QCheckBox):
                    self.settings.setValue(key, widget.isChecked())
                elif hasattr(widget, "value"):
                    self.settings.setValue(key, widget.value())
                elif hasattr(widget, "text"):
                    self.settings.setValue(key, widget.text())

    def load_settings(self):
        for widget in self.findChildren(QWidget):
            if widget.property("persist"):
                key = widget.objectName()
                val = self.settings.value(key)
                if val is not None:
                    if isinstance(widget, QCheckBox):
                        widget.setChecked(str(val).lower() == 'true')
                    elif hasattr(widget, "value"):
                        widget.setValue(val)
                    elif hasattr(widget, "text"):
                        widget.setText(val)
        saved_dir = self.output_entry.text().strip()
        if saved_dir:
            self.output_folder_selected.emit(saved_dir)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def emit_initial_signals(self):
        saved_dir = self.output_entry.text().strip()
        if saved_dir:
            self.output_folder_selected.emit(saved_dir)
    def show_progress_dialog(self, total):
        self.progress_dialog = ProgressDialog(total=total, parent=self)
        self.progress_dialog.show()


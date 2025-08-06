import os,sys,json
from dataclasses import asdict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox,
    QMessageBox, QAbstractItemView, QHeaderView, QProgressBar, QMenuBar, QMenu,QDialog,QApplication,QSlider,QDoubleSpinBox,QInputDialog, QStyleOptionSlider, QStyle
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QSettings, QRect,pyqtSlot
from PyQt6.QtGui import QPixmap, QImage, QIcon, QPainter, QColor, QFont, QPen, QBrush
from PIL import Image
from src.config import ImageProcessConfig
from src import __version__ ,get_resource_path
from dataclasses import fields

class ProgressDialog(QDialog):
    def __init__(self, total=100, parent=None):
        super().__init__(parent)
        self.setWindowTitle("处理进度")
        self.setModal(True)
        self.resize(300, 100)

        layout = QVBoxLayout(self)
        self.label = QLabel("正在处理，请稍候...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

    @pyqtSlot(int)
    def set_progress(self, value):
        self.progress_bar.setValue(value)

class FloatSliderWidget(QSlider):
    def __init__(self,
                 minimum=0.0,
                 maximum=1.0,
                 step=0.01,
                 init_value=1.0,
                 parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._min = minimum
        self._max = maximum
        self._step = step

        # 映射到内部 int 范围
        self.setRange(0, int((maximum - minimum) / step))
        super().setValue(int((init_value - minimum) / step))
    
        
        # 固定尺寸：宽120，高24
        self.setFixedWidth(80)
        self.setFixedHeight(24)

        # 准备两套样式：inactive / active

        QSLIDER_BORDER = """
        QSlider {
            border: 1px inset #383838;   /* 整个控件的内凹边框 */
            border-radius: 4px;         /* 高度 50px 时半径 25px */
            background: transparent;
        }
        """

        self._style_inactive = QSLIDER_BORDER + """
        QSlider::groove:horizontal {
            height: 16px;
            background: #1c1c1c;
            border-radius: 4px;
            margin: 0px;
            padding: 0px;
        }
        QSlider::sub-page:horizontal {
            background: #383838;
            border-radius: 4px;
            
            margin: 0px;
            padding: 0px;
            margin-left: -20px;
            margin-right: -4px;
        }
        QSlider::add-page:horizontal {
            background: transparent;
            margin: 0px;
            padding: 0px;
        }
        QSlider::handle:horizontal {
            width: 12px;
            height: 16px;
            margin: -11px 0;
            background: transparent;
            border-radius: 6px;
        }
        """
        self._style_active = QSLIDER_BORDER + """
        QSlider::groove:horizontal {
            height: 16px;
            background: #1c1c1c;
            border-radius: 4px;
            margin: 0px;
            padding: 0px;
        }
        QSlider::sub-page:horizontal {
            background: #0a84ff;
            border-radius: 4px;
            margin: 0px;
            padding: 0px;
            margin-left: -20px;
            margin-right: -4px;
        }
        QSlider::add-page:horizontal {
            background: transparent;
            margin: 0px;
            padding: 0px;
        }
        QSlider::handle:horizontal {
            width: 12px;
            height: 16px;
            margin: 0px 0;
            background: transparent;
            border-radius: 6px;
            padding: 0px;
        }
        """

        # 默认 inactive
        self.setStyleSheet(self._style_inactive)

        # 连接按下/释放信号，切换样式
        self.sliderPressed.connect(lambda: self.setStyleSheet(self._style_active))
        self.sliderReleased.connect(lambda: self.setStyleSheet(self._style_inactive))
    def value(self) -> float:
        return self._min + super().value() * self._step
        
    def setValue(self, val):
        """接收 float 或 int 设置数值"""
        try:
            v = float(val)
        except (ValueError, TypeError):
            v = self._min
        int_val = int((v - self._min) / self._step)
        super().setValue(int_val)
    def mouseDoubleClickEvent(self, event):
        val, ok = QInputDialog.getDouble(
            self, "输入数值", "值：",
            self.value(),
            self._min, self._max,
            decimals=4
        )
        if ok:
            self.setValue(val)
    def mousePressEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            x = e.position().x()
            w = self.width()
            ratio = max(0.0, min(1.0, x / w))
            val = int(ratio * (self.maximum() - self.minimum())) + self.minimum()
            self.setValue(val)
            self.valueChanged.emit(int(self.value()))
        super().mousePressEvent(e)
    def paintEvent(self, event):
        # 先让 QSlider 正常画槽 + 交互
        super().paintEvent(event)

        # 再在槽区域中央画数值
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(230, 230, 230))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            groove,
            Qt.AlignmentFlag.AlignCenter,
            f"{self.value():.4f}"
        )
        painter.end()
class DropLineEdit(QLineEdit):
    def __init__(self, callback=None, parent=None):
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
    process_requested = pyqtSignal(ImageProcessConfig)
    file_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量图片处理工具 MVP (动态UI版)")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)
        self.settings = QSettings("EleFlyStudio", "ImageBatchProcessor")

        # 设置窗口图标
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        icon_path = os.path.join(base_dir, "resources", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # 创建菜单栏
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        view_menu = QMenu("视图", self)
        self.thumb_size_menu = view_menu.addMenu("缩略图大小")
        self.thumb_size_menu.addAction("小", lambda: self.change_thumb_size(20))
        self.thumb_size_menu.addAction("中", lambda: self.change_thumb_size(40))
        self.thumb_size_menu.addAction("大", lambda: self.change_thumb_size(80))
        menu_bar.addMenu(view_menu)
        
        # 在菜单栏添加“参数”菜单
        param_menu = QMenu("参数", self)
        reset_action = param_menu.addAction("重置为默认值")
        reset_action.triggered.connect(self.reset_parameters)
        menu_bar.addMenu(param_menu)
        # === 预设菜单 ===
        preset_menu = QMenu("预设", self)
        self.menu_presets = preset_menu

        save_action = preset_menu.addAction("保存当前预设")
        save_action.triggered.connect(self.save_preset)

        self.load_menu = preset_menu.addMenu("加载预设")
        self.delete_menu = preset_menu.addMenu("删除预设")

        menu_bar.addMenu(preset_menu)

        self.refresh_presets_menu()
        # === 帮助菜单 ===
        help_menu = QMenu("帮助", self)

        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about_dialog)

        menu_bar.addMenu(help_menu)
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
        # ==== 动态参数控件区 ====
        self.param_widgets = {}
        params_layout = QVBoxLayout()
        params_layout.setSpacing(5)
        
        self.build_dynamic_params(params_layout)

        layout.addLayout(params_layout)

        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.emit_process)
        layout.addWidget(process_btn)

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
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        existing_files = set()
        for i in range(self.tree.topLevelItemCount()):
            existing_files.add(self.tree.topLevelItem(i).text(1))
        new_paths = [p for p in paths if p not in existing_files]
        if new_paths:
            self.files_dropped.emit(new_paths)

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
    def reset_parameters(self):
        default_config = ImageProcessConfig()  # 获取默认参数
        for f in fields(ImageProcessConfig):
            widget = self.param_widgets.get(f.name)
            if widget:
                default_value = getattr(default_config, f.name)
                if isinstance(widget, QCheckBox):
                    widget.setChecked(default_value)
                elif hasattr(widget, "setValue"):
                    try:
                        widget.setValue(float(default_value))
                    except Exception:
                        try:
                            widget.setValue(int(default_value))
                        except Exception:
                            pass
                elif hasattr(widget, "setText"):
                    widget.setText(str(default_value))
    
    def save_preset(self):
        name, ok = QInputDialog.getText(self, "保存预设", "输入预设名称：")
        if ok and name:
            config = self.collect_parameters()
            data = json.dumps(asdict(config))
            self.settings.setValue(f"Presets/{name}", data)
            self.refresh_presets_menu()     
    def load_preset(self, name):
        data = self.settings.value(f"Presets/{name}")
        if data:
            params = json.loads(data)
            for key, val in params.items():
                widget = self.param_widgets.get(key)
                if widget:
                    if isinstance(widget, QCheckBox):
                        widget.setChecked(val)
                    elif hasattr(widget, "setValue"):
                        try:
                            widget.setValue(float(val))
                        except Exception:
                            try:
                                widget.setValue(int(val))
                            except Exception:
                                pass
                    elif hasattr(widget, "setText"):
                        widget.setText(str(val))
                        
    def delete_preset(self, name):
        self.settings.remove(f"Presets/{name}")
        self.refresh_presets_menu()

    def refresh_presets_menu(self):
        # 清空子菜单
        self.load_menu.clear()
        self.delete_menu.clear()
        # 获取所有预设
        self.settings.beginGroup("Presets")
        names = self.settings.allKeys()
        self.settings.endGroup()

        for name in names:
            load_action = self.load_menu.addAction(name)
            load_action.triggered.connect(lambda checked, n=name: self.load_preset(n))
            del_action = self.delete_menu.addAction(name)
            del_action.triggered.connect(lambda checked, n=name: self.delete_preset(n))

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
    def show_about_dialog(self):
        changelog_path = get_resource_path("Changelog.md")
        changelog_text = "更新日志文件未找到"
        if os.path.exists(changelog_path):
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_text = f.read()

        QMessageBox.information(
            self,
            "关于 ImageBatchProcessor",
            f"版本: {__version__}\n\n{changelog_text}"
        )
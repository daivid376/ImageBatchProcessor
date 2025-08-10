import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QComboBox
)
from PyQt6.QtGui import QPainter,QColor, QFont, QPen, QBrush
from PyQt6.QtCore import Qt, pyqtSlot,pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,QSlider, QLineEdit, QInputDialog, QStyle, QStyleOptionSlider,QHBoxLayout,QWidget
)
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
        if e.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            # 获取 handle 区域
            handle_rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderHandle, self)

            if not handle_rect.contains(int(e.position().x()), int(e.position().y())):
                # 点击在滑块外，手动设置跳转
                groove_rect = self.style().subControlRect(
                    QStyle.ComplexControl.CC_Slider, opt,
                    QStyle.SubControl.SC_SliderGroove, self)
                groove_left = groove_rect.x()
                groove_width = groove_rect.width()

                x = e.position().x()
                ratio = max(0.0, min(1.0, (x - groove_left) / groove_width))
                new_int_val = int(ratio * (self.maximum() - self.minimum())) + self.minimum()
                super().setValue(new_int_val)

            # ✅ 不 return，继续交给 Qt 启动拖动
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
class DropLineEdit(QWidget):
    pathSelectedSignal = pyqtSignal(str)
    def __init__(self, parent=None,label_text = ''):
        super().__init__(parent)
        
        self.label = QLabel(label_text)
        self.line_edit = QLineEdit()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)

        self.setAcceptDrops(True)
        self.line_edit.editingFinished.connect(self._on_edit_finished)

    def text(self): return self.line_edit.text()
    def setText(self, text): 
        self.line_edit.setText(text)
    def setPlaceholderText(self, text): self.line_edit.setPlaceholderText(text)
    def setReadOnly(self, readonly): self.line_edit.setReadOnly(readonly)
    def clear(self): self.line_edit.clear()
    def setFocus(self): self.line_edit.setFocus()
    def _on_edit_finished(self):
        path = self.text().strip()
        print('內部更新了uipath: ', path)
        self.pathSelectedSignal.emit(path)
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
            self.setText(path)
            self._on_edit_finished()

class CustomComboBox(QComboBox):
    def __init__(self,OnRefresh = None, parent=None):
        super().__init__(parent)
        self.OnRefresh = OnRefresh

    def showPopup(self):
        try:
            if callable(self.OnRefresh):
                self.OnRefresh()
        except Exception as e:
            # 避免刷新异常影响弹出
            print("Combo refresh error:", e)
        super().showPopup()
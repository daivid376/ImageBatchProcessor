# src/ui/menu_bar.py

import os
import json
from dataclasses import asdict
from PyQt6.QtWidgets import (
    QMenuBar, QMenu, QInputDialog, QMessageBox,QWidget
)
from PyQt6.QtCore import QSettings
from src import __version__
from src.config import GlobalConfig, ImageProcessConfig
from src import get_resource_path
from src.ui.common_widgets import DropLineEdit


class MenuManager:
    def __init__(self, view):
        self.view = view
        self.settings = QSettings(GlobalConfig.APP_ORG, GlobalConfig.APP_NAME)

    def build(self) -> QMenuBar:
        menu_bar = QMenuBar(self.view)

        # === 视图菜单 ===
        view_menu = QMenu("视图", self.view)
        thumb_size_menu = view_menu.addMenu("缩略图大小")
        thumb_size_menu.addAction("小", lambda: self.view.change_thumb_size(20))
        thumb_size_menu.addAction("中", lambda: self.view.change_thumb_size(40))
        thumb_size_menu.addAction("大", lambda: self.view.change_thumb_size(80))
        menu_bar.addMenu(view_menu)
        self.view.thumb_size_menu = thumb_size_menu

        # === 参数菜单 ===
        param_menu = QMenu("参数", self.view)
        reset_action = param_menu.addAction("重置为默认值")
        reset_action.triggered.connect(self.reset_parameters)
        menu_bar.addMenu(param_menu)

        # === 预设菜单 ===
        preset_menu = QMenu("预设", self.view)
        save_action = preset_menu.addAction("保存当前预设")
        save_action.triggered.connect(self.save_preset)

        self.view.load_menu = preset_menu.addMenu("加载预设")
        self.view.delete_menu = preset_menu.addMenu("删除预设")
        self.refresh_presets_menu()

        menu_bar.addMenu(preset_menu)
        self.view.menu_presets = preset_menu

        # === 帮助菜单 ===
        help_menu = QMenu("帮助", self.view)
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addMenu(help_menu)

        return menu_bar

    def reset_parameters(self):
        default_config = ImageProcessConfig()
        for f in default_config.__dataclass_fields__.values():
            widget = self.view.param_widgets.get(f.name)
            if widget:
                value = getattr(default_config, f.name)
                if hasattr(widget, "setChecked"):
                    widget.setChecked(value)
                elif hasattr(widget, "setValue"):
                    widget.setValue(value)
                elif hasattr(widget, "setText"):
                    widget.setText(str(value))

    def save_preset(self):
        name, ok = QInputDialog.getText(self.view, "保存预设", "输入预设名称：")
        if ok and name:
            config = self.view.collect_parameters()
            data = json.dumps(asdict(config))
            self.settings.setValue(f"Presets/{name}", data)
            self.refresh_presets_menu()

    def load_preset(self, name):
        data = self.settings.value(f"Presets/{name}")
        if data:
            params = json.loads(data)
            for key, val in params.items():
                widget = self.view.param_widgets.get(key)
                if widget:
                    if hasattr(widget, "setChecked"):
                        widget.setChecked(val)
                    elif hasattr(widget, "setValue"):
                        widget.setValue(val)
                    elif hasattr(widget, "setText"):
                        widget.setText(str(val))
            self._emit_loaded_signals()
    def _emit_loaded_signals(self):
        """🆕 配置加载完成后，手动触发必要的信号"""
        for widget in self.findChildren(QWidget):
            if widget.property("persist"):
                key = widget.objectName()
                val = self.settings.value(key)
                
                if val is not None and isinstance(widget, DropLineEdit):
                    path = str(val).strip()
                    if path:  # 只有非空路径才发射信号
                        print(f"🚀 触发信号: {key} -> {path}")
                        widget.pathSelectedSignal.emit(path)
    def delete_preset(self, name):
        self.settings.remove(f"Presets/{name}")
        self.refresh_presets_menu()

    def refresh_presets_menu(self):
        self.view.load_menu.clear()
        self.view.delete_menu.clear()
        self.settings.beginGroup("Presets")
        names = self.settings.allKeys()
        self.settings.endGroup()
        for name in names:
            action_load = self.view.load_menu.addAction(name)
            action_load.triggered.connect(lambda checked, name=name: self.load_preset(name))

    def show_about_dialog(self):
        changelog_path = get_resource_path("Changelog.md")
        changelog_text = "更新日志文件未找到"
        if os.path.exists(changelog_path):
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_text = f.read()

        QMessageBox.information(
            self.view,
            "关于 ImageBatchProcessor",
            f"版本: {__version__}\n\n{changelog_text}"
        )

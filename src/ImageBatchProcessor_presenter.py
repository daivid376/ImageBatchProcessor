# src/ImageBatchProcessor_presenter.py
# 🔄 重构文件：移除ComfyUI相关逻辑，专注于传统图像处理
# 主要改动：
# 1. ❌ 移除：所有ComfyUI相关的import和处理逻辑
# 2. ❌ 移除：handle_comfy_remote_process方法
# 3. ❌ 移除：ComfyUI相关的信号连接
# 4. 🔄 简化：构造函数，移除重复的信号连接
# 5. ✅ 保持：所有传统图像处理功能

from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox,QApplication
from PyQt6.QtCore import QTimer
# ❌ 移除：ComfyUI相关的import
# from src.comfyui_api.submit_worker import ComfySubmitWorker
# from src.comfyui_api.workflow_manager import WorkflowManager
# from src.comfyui_api.api_client import ComfyApiClient
# from src.config import GlobalConfig

class Worker(QThread):
    """🔄 保持原有Worker类，专门处理传统图像处理"""
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, model, config):
        super().__init__()
        self.model = model
        self.config = config

    def run(self):
        for i, file in enumerate(self.model.files, start=1):
            self.model.process_one(file, self.config)
            self.progress.emit(i)
        self.finished.emit()

class ImageBatchPresenter:
    """
    🔄 重构：专注于传统图像处理的Presenter
    职责：只处理文件管理和传统图像处理逻辑
    ComfyUI逻辑已移至ComfyUIPresenter
    """
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.worker = None
        self.comfy_presenter = None

        # 🔄 保持传统图像处理相关的信号连接
        view.files_dropped.connect(self.handle_files)
        view.output_folder_selected.connect(self.handle_output_folder_selected)
        view.process_requested.connect(self.handle_process)
        view.file_removed.connect(self.handle_remove_file)
 
    def set_comfy_presenter(self, presenter):
        self.comfy_presenter = presenter
    def handle_output_folder_selected(self, folder_path):
        self.model.set_output_dir(folder_path)
        self.comfy_presenter.set_output_dir(folder_path)
    def handle_files(self, paths):
        """🔄 保持原有文件处理逻辑"""
        files = self.model.add_files(paths)
        for f in files:
            if isinstance(f, Path):
                f = f.as_posix()
            self.view.add_file_item(f)

    def handle_remove_file(self, filepath):
        """🔄 保持原有文件移除逻辑，合并重复方法"""
        if filepath == "__CLEAR_ALL__":
            self.model.files.clear()
        elif filepath in self.model.files:
            self.model.files.remove(filepath)

    def handle_process(self, config):
        """🔄 保持原有传统图像处理逻辑"""
        if not self.model.files:
            QMessageBox.critical(self.view, "错误", "未选择文件")
            return
        if not self.model.output_dir:
            QMessageBox.critical(self.view, "错误", "未选择输出目录")
            return

        total_files = len(self.model.files)
        self.view.show_progress_dialog(total_files)

        self.worker = Worker(self.model, config)
        self.worker.progress.connect(self.view.progress_dialog.set_progress)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()

    def on_process_finished(self):
        """🔄 保持原有处理完成逻辑"""
        if self.view.progress_dialog:
            dlg = self.view.progress_dialog
            dlg.accept()

        QMessageBox.information(self.view, "完成", "图片处理完成！")
        
    # ❌ 移除：handle_comfy_remote_process方法
    # 原因：ComfyUI相关逻辑已移至ComfyUIPresenter，避免职责混乱
    
    # ❌ 移除：_show_error和_show_info方法
    # 原因：这些方法现在由ComfyUIPresenter处理ComfyUI相关的消息显示
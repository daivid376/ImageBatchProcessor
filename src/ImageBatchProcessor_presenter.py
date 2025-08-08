from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox,QApplication
from PyQt6.QtCore import QTimer
from src.comfyui_api.submit_worker import ComfySubmitWorker
from src.comfyui_api.workflow_manager import WorkflowManager
from src.comfyui_api.api_client import ComfyApiClient
from src.config import GlobalConfig
class Worker(QThread):
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
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.worker = None

        view.files_dropped.connect(self.handle_files)
        view.output_folder_selected.connect(self.model.set_output_dir)
        view.process_requested.connect(self.handle_process)
        view.file_removed.connect(self.handle_remove_file)
        view.comfy_section.submit_comfy_task.connect(self.handle_comfy_remote_process)

    def handle_files(self, paths):
        files = self.model.add_files(paths)
        for f in files:
            self.view.add_file_item(f)

    def handle_remove_file(self, filepath):
        if filepath in self.model.files:
            self.model.files.remove(filepath)

    def handle_process(self, config):
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
        if self.view.progress_dialog:
            dlg = self.view.progress_dialog
            dlg.accept()
            # dlg.deleteLater()
            # self.view.progress_dialog = None

        #QTimer.singleShot(200, lambda: QMessageBox.information(self.view, "完成", "图片处理完成！"))
        QMessageBox.information(self.view, "完成", "图片处理完成！")
        
    def handle_remove_file(self, filepath):
        if filepath == "__CLEAR_ALL__":
            self.model.files.clear()
        elif filepath in self.model.files:
            self.model.files.remove(filepath)
            
    def handle_comfy_remote_process(self, info: dict):
        """处理远程 comfy 提交任务"""
        try:
            # 1. 构造 manager 和 api client
            manager = WorkflowManager(self.model,info)
            client = ComfyApiClient(GlobalConfig.host, GlobalConfig.port) 
            client.is_comfy_alive()
            client.is_port_open()

            # 2. 构造任务列表
            tasks = manager.create_comfy_tasks()

            if not tasks:
                self._show_error("没有任务可以提交")
                return

            # 3. 初始化进度条
            sec = self.view.comfy_section
            sec.progress_bar.setRange(0, len(tasks))
            sec.progress_bar.setValue(0)

            # 4. 提交任务（串行为主，如需异步可加 QThread）
            self._submit_worker = ComfySubmitWorker(client, tasks, wait_timeout=180, wait_interval=2)
            self._submit_worker.status.connect(lambda s: sec.progress_label.setText(f"任务进度：{s}"))
            self._submit_worker.progress.connect(lambda d, t: sec.progress_bar.setValue(d))
            self._submit_worker.finished_ok.connect(lambda: self._show_info("任务提交完成"))
            self._submit_worker.failed.connect(lambda msg: self._show_error(f"提交失败：\n{msg}"))
            self._submit_worker.start()

        except Exception as e:
            self._show_error(f"提交任务失败: {e}")

    def _show_error(self, msg: str):
        QMessageBox.critical(self.view, "错误", msg)

    def _show_info(self, msg: str):
        QMessageBox.information(self.view, "提示", msg)
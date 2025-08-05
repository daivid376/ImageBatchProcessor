from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox,QApplication
from PyQt6.QtCore import QTimer

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
        

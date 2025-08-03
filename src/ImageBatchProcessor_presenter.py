from PyQt6.QtWidgets import QMessageBox

class ImageBatchPresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view

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
    def handle_process(self, flip, noise, rot_min, rot_max):
        if not self.model.files:
            QMessageBox.critical(self.view, "错误", "未选择文件")
            return
        if not self.model.output_dir:
            QMessageBox.critical(self.view, "错误", "未选择输出目录")
            return
        self.model.process_all(flip, noise, rot_min, rot_max)
        QMessageBox.information(self.view, "完成", "图片处理完成！")

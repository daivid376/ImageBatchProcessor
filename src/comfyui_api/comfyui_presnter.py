# src/comfyui_api/comfyui_presenter.py
# 🔄 简化：删除 WorkflowService，直接使用 ComfyModel

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from .comfy_model import ComfyModel

class ComfyUIPresenter(QObject):
    """
    🔄 简化后的 Presenter
    改动说明：
    1. 删除 WorkflowService 依赖
    2. 直接使用 ComfyModel
    3. 代码大幅简化
    """
    
    def __init__(self, main_model, comfy_view):
        super().__init__()
        self.main_model = main_model      # 主应用的 ImageBatchModel
        self.view = comfy_view            # ComfyUISection 视图
        
        # 🔄 改动：直接创建 ComfyModel，不再需要 WorkflowService
        self.comfy_model = ComfyModel()
        
        # 连接信号
        self._connect_view_signals()
        self._connect_model_signals()
    
    def _connect_view_signals(self):
        """连接View信号"""
        self.view.local_network_drive_selected.connect(self.handle_network_drive_selected)
        self.view.submit_comfy_task.connect(self.handle_submit_task)
    
    def _connect_model_signals(self):
        """🔄 改动：直接连接 ComfyModel 的信号"""
        self.comfy_model.status_updated.connect(self.on_status_updated)
        self.comfy_model.progress_updated.connect(self.on_progress_updated)
        self.comfy_model.task_completed.connect(self.on_task_completed)
        self.comfy_model.all_tasks_completed.connect(self.on_all_tasks_completed)
        self.comfy_model.error_occurred.connect(self.on_error_occurred)
        self.comfy_model.task_progress_updated.connect(self.on_task_progress_updated)
    def set_output_dir(self, path: str):
        """设置输出目录"""
        self.comfy_model.set_output_dir(path)
    
    def handle_network_drive_selected(self, local_network_drive_dir: str):
        """处理网络驱动器选择"""
        # 🔄 改动：调用新的集中配置方法
        self.comfy_model.set_network_config(local_network_drive_dir)
    
    @pyqtSlot(dict)
    def handle_submit_task(self, task_info: dict):
        """
        处理提交任务
        🔄 简化：直接调用 model 的方法
        """
        # 🔄 改动：传入文件列表而不是整个 main_model
        image_files = self.main_model.files
        success = self.comfy_model.submit_tasks(image_files, task_info)
        
        if not success:
            # 错误已经通过信号处理了
            pass
    
    # === Model 信号处理 ===
    def on_status_updated(self, status_text: str):
        """更新状态文本"""
        self.view.progress_label.setText(f"任务进度：{status_text}")
    
    def on_progress_updated(self, done: int, total: int):
        """更新进度条"""
        self.view.progress_bar.setRange(0, total)
        self.view.progress_bar.setValue(done)
    
    def on_task_completed(self, prompt_id: str):
        """单个任务完成"""
        # 可以添加单任务完成的UI反馈
        print(f"✅ 任务完成: {prompt_id}")
    
    def on_all_tasks_completed(self):
        """所有任务完成"""
        self._show_info("所有ComfyUI任务处理完成！")
        self.view.progress_label.setText("任务进度：已完成")
        self.view.current_task_label.hide()
        self.view.current_task_progress.hide()
    
    def on_error_occurred(self, error_msg: str):
        """处理错误"""
        self._show_error(error_msg)
    def on_task_progress_updated(self, name: str, done: int, total: int):
        self.view.current_task_label.show()
        self.view.current_task_progress.show()
        if total > 0:
            self.view.current_task_progress.setRange(0, total)
            self.view.current_task_progress.setValue(done)
            self.view.current_task_label.setText(f"{name} [{done}/{total}]")
        else:
            self.view.current_task_progress.setRange(0, 1)
            self.view.current_task_progress.setValue(0)
    # === UI 消息显示 ===
    def _show_error(self, msg: str):
        """显示错误消息"""
        QMessageBox.critical(self.view, "错误", msg)
        print(f"❌ 错误: {msg}")
    
    def _show_info(self, msg: str):
        """显示信息消息"""
        QMessageBox.information(self.view, "提示", msg)
        print(f"ℹ️ 信息: {msg}")
    
    # === 🔄 简化：公共接口直接转发 ===
    def get_task_statistics(self):
        """获取任务统计"""
        return self.comfy_model.get_task_statistics()
    
    def stop_current_tasks(self):
        """停止当前任务"""
        self.comfy_model.stop_current_tasks()
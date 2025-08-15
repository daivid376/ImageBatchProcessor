# src/comfyui_api/comfyui_presenter.py
# 🔄 重构文件：轻量级MVP重构，移除业务逻辑
# 主要改动：
# 1. ✂️ 移除所有业务逻辑，移到WorkflowService
# 2. 🎯 专注于MVP中Presenter的职责：View-Model协调
# 3. 📡 只处理信号转发和UI状态更新
# 4. 🧹 大幅简化代码，提高可维护性

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from .workflow_service import WorkflowService
from src.config import GlobalConfig
class ComfyUIPresenter(QObject):
    """
    🔄 重构后的ComfyUIPresenter - 严格遵循MVP模式
    
    职责：
    - 处理View事件，转发给Service层
    - 接收Service层通知，更新View状态
    - 不包含任何业务逻辑
    
    设计原则：
    - 薄薄一层，只做协调工作
    - 所有业务逻辑委托给WorkflowService
    - 通过信号机制解耦View和Service
    """
    def __init__(self, main_model, comfy_view):
        super().__init__()
        self.main_model = main_model        # 主应用的ImageBatchModel
        self.view = comfy_view              # ComfyUISection视图
        
        # 🆕 使用WorkflowService处理业务逻辑
        self.workflow_service = WorkflowService()
        
        # 🔄 连接View信号到Presenter
        self._connect_view_signals()
        
        # 🆕 连接Service信号到Presenter
        self._connect_service_signals()
        
    def _connect_view_signals(self):
        """连接View信号到Presenter方法"""
        self.view.local_network_drive_selected.connect(self.handle_network_drive_selected)
        self.view.submit_comfy_task.connect(self.handle_submit_task)
    
    def _connect_service_signals(self):
        """连接Service信号到Presenter方法"""
        self.workflow_service.status_updated.connect(self.on_status_updated)
        self.workflow_service.progress_updated.connect(self.on_progress_updated)
        self.workflow_service.task_completed.connect(self.on_task_completed)
        self.workflow_service.all_tasks_completed.connect(self.on_all_tasks_completed)
        self.workflow_service.error_occurred.connect(self.on_error_occurred)
    
    def set_output_dir(self, path):
        """设置输出目录 - 转发给Service"""
        self.workflow_service.set_output_dir(path)
        
    def handle_network_drive_selected(self, local_network_drive_dir):
        """处理网络驱动器选择 - 转发给Service"""
        self.workflow_service.set_tmp_img_output_dir(local_network_drive_dir)
    
    @pyqtSlot(dict)
    def handle_submit_task(self, task_info: dict):
        """
        🔄 重构：纯粹的协调工作，不包含业务逻辑
        所有具体逻辑委托给WorkflowService处理
        """
        # ✅ Presenter只做转发，不做业务逻辑
        success = self.workflow_service.submit_tasks(self.main_model, task_info)
        if not success:
            # 错误处理由Service通过信号通知，这里不需要额外处理
            pass
    
    # === Service层信号处理方法 ===
    # 这些方法只负责更新UI，不包含业务逻辑
    
    def on_status_updated(self, status_text: str):
        """处理状态更新 - 只更新UI"""
        self.view.progress_label.setText(f"任务进度：{status_text}")
    
    def on_progress_updated(self, done: int, total: int):
        """处理进度更新 - 只更新UI"""
        self.view.progress_bar.setRange(0, total)
        self.view.progress_bar.setValue(done)
    
    def on_task_completed(self, prompt_id: str):
        """处理单个任务完成 - 可以添加UI反馈"""
        # 可以在这里添加单个任务完成的UI反馈
        pass
    
    def on_all_tasks_completed(self):
        """处理所有任务完成 - 显示完成消息"""
        self._show_info("所有ComfyUI任务处理完成！")
        self.view.progress_label.setText("任务进度：已完成")
    
    def on_error_occurred(self, error_msg: str):
        """处理错误 - 显示错误消息"""
        self._show_error(error_msg)
    
    # === UI消息显示方法 ===
    # 保持原有的消息显示功能
    
    def _show_error(self, msg: str):
        """显示错误消息"""
        QMessageBox.critical(self.view, "错误", msg)
        print(f"❌ 错误: {msg}")

    def _show_info(self, msg: str):
        """显示信息消息"""
        QMessageBox.information(self.view, "提示", msg)
        print(f"ℹ️ 信息: {msg}")
    
    # === 公共接口方法 ===
    
    def get_task_statistics(self):
        """获取任务统计信息 - 转发给Service"""
        return self.workflow_service.get_task_statistics()
    
    def stop_current_tasks(self):
        """停止当前任务 - 转发给Service"""
        self.workflow_service.stop_current_tasks()
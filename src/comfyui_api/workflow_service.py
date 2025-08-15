# src/comfyui_api/workflow_service.py
# 🆕 新增文件：WorkflowService - ComfyUI业务逻辑辅助类
# 目的：将业务逻辑从ComfyUIPresenter中抽离，保持MVP架构清晰
# 职责：任务创建、工作流管理、提交流程编排

import os
from typing import Dict, List
from PyQt6.QtCore import QObject, pyqtSignal

from .comfy_model import ComfyModel, ComfyTask
from .workflow_manager import WorkflowManager
from .submit_worker import ComfySubmitWorker
from .api_client import ComfyApiClient
from src.config import GlobalConfig


class WorkflowService(QObject):
    """
    🆕 ComfyUI业务逻辑服务类（属于Model层的辅助类）
    
    职责：
    - 任务验证和创建
    - 工作流处理流程编排
    - 提交流程管理
    - 状态变更通知
    
    设计原则：
    - 纯业务逻辑，不直接操作UI
    - 通过信号通知Presenter更新UI
    - 依赖注入，便于测试
    """
    
    # 信号定义：向Presenter通知状态变化
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)
    task_completed = pyqtSignal(str)
    all_tasks_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.comfy_model = ComfyModel()
        self.client = ComfyApiClient()
        self.current_worker = None
        
    def set_output_dir(self, path: str):
        """设置输出目录"""
        self.comfy_model.set_output_dir(path)
        
    def set_tmp_img_output_dir(self, local_network_drive_dir: str):
        """设置临时图片输出目录"""
        tmp_img_output_dir = os.path.join(
            local_network_drive_dir,
            GlobalConfig.code_project_root_rel_dir, 
            GlobalConfig.ai_temp_output_rel_dir
        )
        self.comfy_model.set_tmp_img_output_dir(tmp_img_output_dir)
    
    def submit_tasks(self, main_model, task_info: Dict) -> bool:
        """
        提交ComfyUI任务的主入口
        
        Args:
            main_model: 主应用的ImageBatchModel（包含文件列表）
            task_info: UI收集的任务信息
            
        Returns:
            bool: 提交是否成功
        """
        try:
            # 步骤1：验证输入
            if not self._validate_inputs(main_model, task_info):
                return False
                
            # 步骤2：配置ComfyUI模型
            self._configure_comfy_model(task_info)
            
            # 步骤3：创建任务列表
            tasks = self._create_tasks(main_model, task_info)
            if not tasks:
                self.error_occurred.emit("创建任务失败")
                return False
                
            # 步骤4：启动提交流程
            return self._start_submission_process(tasks)
            
        except Exception as e:
            self.error_occurred.emit(f"提交任务失败: {str(e)}")
            return False
    
    def _validate_inputs(self, main_model, task_info: Dict) -> bool:
        """验证输入参数"""
        if not main_model.files:
            self.error_occurred.emit("没有选择图片文件")
            return False
            
        required_keys = ["workflow_path", "prompt_path", "local_network_drive_dir"]
        for key in required_keys:
            if key not in task_info:
                self.error_occurred.emit(f"缺少必需参数: {key}")
                return False
                
        if not os.path.exists(task_info["workflow_path"]):
            self.error_occurred.emit("工作流文件不存在")
            return False
            
        if not os.path.exists(task_info["prompt_path"]):
            self.error_occurred.emit("提示词文件不存在")
            return False
            
        return True
    
    def _configure_comfy_model(self, task_info: Dict):
        """配置ComfyUI模型"""
        self.comfy_model.set_workflow_config(
            workflow_path=task_info["workflow_path"],
            prompt_path=task_info["prompt_path"],
            network_root=task_info["local_network_drive_dir"]
        )
    
    def _create_tasks(self, main_model, task_info: Dict) -> List[ComfyTask]:
        """创建ComfyUI任务列表"""
        try:
            self.comfy_model.clear_tasks()
            
            # 使用WorkflowManager创建原始任务
            manager = WorkflowManager(main_model, task_info)
            raw_tasks = manager.create_comfy_tasks()
            
            # 转换为ComfyTask对象
            tasks = []
            for raw_task in raw_tasks:
                comfy_task = ComfyTask(
                    image_path=raw_task["image"],
                    rel_input=raw_task["rel_input"],
                    payload=raw_task["payload"]
                )
                self.comfy_model.add_task(comfy_task)
                tasks.append(comfy_task)
                
            self.status_updated.emit(f"创建了 {len(tasks)} 个任务")
            return tasks
            
        except Exception as e:
            self.error_occurred.emit(f"创建任务失败: {str(e)}")
            return []
    
    def _start_submission_process(self, tasks: List[ComfyTask]) -> bool:
        """启动任务提交流程"""
        try:
            pending_tasks = self.comfy_model.get_pending_tasks()
            if not pending_tasks:
                self.error_occurred.emit("没有待处理任务")
                return False
                
            total = len(pending_tasks)
            self.status_updated.emit("准备提交任务...")
            self.progress_updated.emit(0, total)
            
            # 创建并配置Worker
            self.current_worker = ComfySubmitWorker(
                client=self.client,
                comfy_model=self.comfy_model,
                wait_timeout=180,
                wait_interval=2
            )
            
            # 连接Worker信号
            self._connect_worker_signals()
            
            # 启动Worker
            self.current_worker.start()
            self.status_updated.emit("任务提交已启动")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"启动提交流程失败: {str(e)}")
            return False
    
    def _connect_worker_signals(self):
        """连接Worker信号"""
        if not self.current_worker:
            return
            
        # 状态信号
        self.current_worker.status.connect(self.status_updated)
        self.current_worker.progress.connect(self.progress_updated)
        
        # 任务完成信号
        self.current_worker.task_completed.connect(self._on_single_task_completed)
        self.current_worker.all_completed.connect(self._on_all_tasks_completed)
        
        # 错误信号
        self.current_worker.failed.connect(self.error_occurred)
    
    def _on_single_task_completed(self, prompt_id: str):
        """处理单个任务完成"""
        self.comfy_model.update_task_status(prompt_id, "completed")
        completed = self.comfy_model.completed_count
        total = self.comfy_model.get_total_tasks()
        
        self.task_completed.emit(prompt_id)
        self.progress_updated.emit(completed, total)
        self.status_updated.emit(f"任务完成: {completed}/{total}")
    
    def _on_all_tasks_completed(self):
        """处理所有任务完成"""
        self.status_updated.emit("所有任务处理完成")
        self.all_tasks_completed.emit()
        self.current_worker = None
    
    def stop_current_tasks(self):
        """停止当前任务（如果需要的话）"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker = None
            self.status_updated.emit("任务已停止")
    
    def get_task_statistics(self) -> Dict[str, int]:
        """获取任务统计信息"""
        return {
            "total": self.comfy_model.get_total_tasks(),
            "completed": self.comfy_model.completed_count,
            "pending": len(self.comfy_model.get_pending_tasks()),
            "submitted": len(self.comfy_model.get_submitted_tasks())
        }
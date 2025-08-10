# src/comfyui_api/comfy_model.py
# 🆕 新增文件：ComfyUI专用数据模型
# 目的：将ComfyUI相关的数据管理从主模型中分离出来，实现职责分离

from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ComfyTask:
    """
    🆕 新增：单个ComfyUI任务的数据结构
    用于跟踪每个任务的状态和相关信息
    """
    image_path: str
    rel_input: str
    payload: Dict
    prompt_id: Optional[str] = None
    status: str = "pending"  # pending, submitted, completed, failed

class ComfyModel:
    """
    🆕 新增：ComfyUI模块的专用数据模型
    职责：管理ComfyUI任务列表、工作流配置等ComfyUI专用数据
    与主应用的ImageBatchModel分离，避免职责混乱
    """
    def __init__(self):
        self.tasks: List[ComfyTask] = []
        self.current_workflow_path: Optional[Path] = None
        self.current_prompt_path: Optional[Path] = None
        self.local_network_root: Optional[Path] = None
        self.completed_count = 0
        
    def clear_tasks(self):
        """清空所有任务"""
        self.tasks.clear()
        self.completed_count = 0
        
    def add_task(self, task: ComfyTask):
        """添加新任务"""
        self.tasks.append(task)
        
    def get_pending_tasks(self) -> List[ComfyTask]:
        """获取待处理任务"""
        return [t for t in self.tasks if t.status == "pending"]
        
    def get_submitted_tasks(self) -> List[ComfyTask]:
        """获取已提交任务"""
        return [t for t in self.tasks if t.status == "submitted"]
        
    def update_task_status(self, prompt_id: str, status: str):
        """更新指定任务的状态"""
        for task in self.tasks:
            if task.prompt_id == prompt_id:
                task.status = status
                if status == "completed":
                    self.completed_count += 1
                break
                
    def get_total_tasks(self) -> int:
        """获取任务总数"""
        return len(self.tasks)
        
    def is_all_completed(self) -> bool:
        """检查是否所有任务都已完成"""
        return self.completed_count >= len(self.tasks)
        
    def set_workflow_config(self, workflow_path: Path, prompt_path: Path, network_root: Path):
        """设置工作流配置"""
        self.current_workflow_path = workflow_path
        self.current_prompt_path = prompt_path
        self.local_network_root = network_root
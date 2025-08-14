# src/comfyui_api/comfy_model.py
# 🆕 新增文件：ComfyUI专用数据模型
# 目的：将ComfyUI相关的数据管理从主模型中分离出来，实现职责分离

from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
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
    @property
    def orig_filename(self):
        """获取图片文件名"""
        return Path(self.image_path).name
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
        self.output_dir = None
        self.tmp_img_output_dir = None
        self.completed_count = 0
        
        self.prompt_id_to_task: Dict[str, ComfyTask] = {} 
    def clear_tasks(self):
        """清空所有任务"""
        self.tasks.clear()
        self.completed_count = 0
        self.prompt_id_to_task.clear()
    def register_task_prompt_id(self,task:ComfyTask,prompt_id:str):
        task.prompt_id = prompt_id
        self.prompt_id_to_task[prompt_id] = task
    def get_task_by_prompt_id(self, prompt_id: str) -> Optional[ComfyTask]:
        return self.prompt_id_to_task[prompt_id]

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
                print('task.status: ', task.status)
                if status == "completed":
                    print('status: ', status)
                    self.completed_count += 1
                break
                
    def get_total_tasks(self) -> int:
        """获取任务总数"""
        return len(self.tasks)
        
    def is_all_completed(self) -> bool:
        """检查是否所有任务都已完成"""
        return self.completed_count >= len(self.tasks)
    def set_output_dir(self, output_dir: Path):
        self.output_dir = output_dir
    def get_output_dir(self):
        return self.output_dir if self.output_dir else None
    def set_tmp_img_output_dir(self, path):
        self.tmp_img_output_dir = path
    def get_tmp_output_dir(self):
        return self.tmp_img_output_dir if self.tmp_img_output_dir else None
    def get_file_orig_name(self, file_path: str) -> str:
        orig_file_path = self.tasks['image']
        print('orig_file_path: ', orig_file_path)
        file_name = None
        if isinstance(orig_file_path, str):
            orig_file_path = Path(orig_file_path)
        file_name = Path(orig_file_path).name
    def get_task_by_prompt_id(self, prompt_id: str) -> Optional[ComfyTask]:
        """根据prompt_id获取任务"""
        for task in self.tasks:
            if task.prompt_id == prompt_id:
                return task
        return None
    def set_workflow_config(self, workflow_path: Path, prompt_path: Path, network_root: Path):
        """设置工作流配置"""
        self.current_workflow_path = workflow_path
        self.current_prompt_path = prompt_path
        self.local_network_root = network_root
        
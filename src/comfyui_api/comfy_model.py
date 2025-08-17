# src/comfyui_api/comfy_model.py
# 精简版：核心业务逻辑，工具方法拆分到独立文件

import json
import copy
import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from src.comfyui_api.mock_client import MockComfyApiClient

from .api_client import ComfyApiClient
from .websocket_listener import WebSocketListener
from .task_completion_handler import TaskCompletionHandler
from .file_handler import FileHandler
from .workflow_modifier import WorkflowModifier
from src.config import GlobalConfig

# ============ 数据结构 ============
@dataclass
class ComfyTask:
    """任务数据结构"""
    image_path: str
    payload: Dict
    temp_filename: str = None
    prompt_filename: Optional[str] = None
    prompt_id: Optional[str] = None
    status: str = "pending"
    ui_config: Dict = field(default_factory=dict)
    
    @property
    def orig_filename(self):
        return Path(self.image_path).name
    
    @property
    def orig_filestem(self):
        return Path(self.image_path).stem

# ============ Model 主类 ============
class ComfyModel(QObject):
    """ComfyUI 业务逻辑模型 - 精简版"""
    
    # 信号定义
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)
    task_completed = pyqtSignal(str)
    all_tasks_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    task_progress_updated = pyqtSignal(str, int, int) 
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 任务数据
        self.tasks: List[ComfyTask] = []
        self.prompt_id_to_task: Dict[str, ComfyTask] = {}
        self.completed_count = 0
        self.task_count = 0
        
        # 环境配置
        self.output_dir: Optional[Path] = None
        self.temp_input_dir: Optional[Path] = None
        self.temp_input_rel_dir: Optional[str] = None
        
        # 工具类
        self.client = ComfyApiClient()
        #self.client = MockComfyApiClient()
        self.file_handler = FileHandler()
        self.workflow_modifier = WorkflowModifier()
        self.completion_handler = TaskCompletionHandler()
        
        # 运行时对象
        self.ws_listener: Optional[WebSocketListener] = None
        self.submit_thread = None

    
    # ============ 配置方法 ============
    def set_output_dir(self, path: str):
        """设置输出目录"""
        self.output_dir = Path(path) if path else None
    
    def set_network_config(self, local_network_drive_dir: str):
        """设置网络驱动器配置"""
        if not local_network_drive_dir:
            return
        
        root = Path(local_network_drive_dir)
        self.temp_input_dir = root / GlobalConfig.code_project_root_rel_dir / GlobalConfig.ai_temp_input_rel_dir
        self.temp_output_dir = root / GlobalConfig.code_project_root_rel_dir / GlobalConfig.ai_temp_output_rel_dir
        self.temp_input_rel_dir = Path('comfy_api_input')
    def get_temp_output_dir(self):
        return self.temp_output_dir
    
    def get_output_dir(self):
        """获取最终输出目录"""
        return str(self.output_dir) if self.output_dir else None
    
    # ============ 主要业务逻辑 ============
    def submit_tasks(self, image_files: List[str], task_info: Dict) -> bool:
        """提交任务主入口"""
        try:
            # 验证
            if not self._validate_inputs(image_files, task_info):
                return False
            
            # 创建任务
            self.clear_tasks()
            tasks = self._create_tasks(image_files, task_info)
            
            if not tasks:
                self.error_occurred.emit("创建任务失败")
                return False
            
            # 启动异步提交
            self._start_async_submission()
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"提交失败: {str(e)}")
            return False
    
    def _validate_inputs(self, image_files: List[str], task_info: Dict) -> bool:
        """验证输入"""
        if not image_files:
            self.error_occurred.emit("没有选择图片")
            return False
        
        if not self.file_handler.file_exists(task_info.get("workflow_path", "")):
            self.error_occurred.emit("工作流文件不存在")
            return False
        
        return True
    
    def _create_tasks(self, image_files: List[str], task_info: Dict) -> List[ComfyTask]:
        """创建任务列表"""
        prompt_path = task_info.get('prompt_path','')
        prompt_filename = Path(prompt_path).stem
        # 读取模板
        workflow_template = self.file_handler.load_json(task_info["workflow_path"])
        prompt_text = self.file_handler.load_text(prompt_path)
        
        tasks = []
        for img_path in image_files:
            # 拷贝到临时目录
            temp_filename = self.file_handler.copy_to_temp(img_path, self.temp_input_dir)
            rel_input = f"{self.temp_input_rel_dir.name}/{temp_filename}"
            
            # 修改工作流
            workflow = self.workflow_modifier.apply_modifications(
                workflow_template, 
                rel_input=rel_input,
                prompt_text=prompt_text,
                ui_config=task_info
            )
            
            # 创建任务
            task = ComfyTask(
                image_path=img_path,
                payload={"prompt": workflow},
                temp_filename=temp_filename,
                prompt_filename= prompt_filename,
                ui_config=task_info
            )
            
            self.add_task(task)
            tasks.append(task)
        
        self.status_updated.emit(f"创建了 {len(tasks)} 个任务")
        return tasks
    
    def _start_async_submission(self):
        """启动异步提交"""
        import threading
        
        self.status_updated.emit("开始提交任务...")
        
        # 启动WebSocket监听
        prompt_ids = set()
        self.ws_listener = WebSocketListener(
            self.client.host, 
            self.client.port,
            prompt_ids
        )
        self.ws_listener.message_received.connect(self._handle_ws_message)
        self.ws_listener.start()
        
        # 启动提交线程
        self.submit_thread = threading.Thread(
            target=self._submit_all_tasks,
            args=(prompt_ids,),
            daemon=True
        )
        self.submit_thread.start()
    
    def _submit_all_tasks(self, prompt_ids: set):
        """在线程中提交所有任务"""
        try:
            pending = self.get_pending_tasks()
            total = len(pending)
            
            for i, task in enumerate(pending):
                start_time = time.time()
                # 等待文件
                print(f"{i} 任務num")
                if task.temp_filename:
                    self.status_updated.emit(f"等待文件：{task.orig_filestem}")
                    print(f"⏰ {time.strftime('%H:%M:%S')} - 开始等待文件: {task.temp_filename}")
                    if i == 0:
                        time.sleep(4)
                    else:
                        time.sleep(0.1)
                    #self.file_handler.wait_file_accessible(self.client,filename=task.temp_filename,subfolder="comfy_api_input")
                    print(f"⏰ {time.strftime('%H:%M:%S')} - 文件等待完成 (耗时: {time.time()-start_time:.2f}秒)")
                # 提交前
                submit_start = time.time()
                print(f"⏰ {time.strftime('%H:%M:%S')} - 开始提交到 /prompt")
                print(f"   Payload大小: {len(str(task.payload))} 字符")
                # 提交
                prompt_id = self.client.submit(task.payload)
                print(f"⏰ {time.strftime('%H:%M:%S')} - 提交完成 (耗时: {time.time()-submit_start:.2f}秒)")

                # 注册

                self.register_task_prompt_id(task, prompt_id)
                prompt_ids.add(prompt_id)

                # 进度
                self.progress_updated.emit(i + 1, total)
                self.status_updated.emit(f"已提交 {i + 1}/{total}")
                print(f"⏰ 单个任务总耗时: {time.time()-start_time:.2f}秒\n")
                
                if self.client.is_mock:
                # 方案A：同步调用（简单）
                    self._handle_task_complete(prompt_id)
            self.status_updated.emit("所有任务已提交")
            
        except Exception as e:
            self.error_occurred.emit(f"提交失败: {str(e)}")
    
    def _handle_ws_message(self, data: dict):
        """处理WebSocket消息"""
        msg_type = data.get("type")
        msg_data = data.get("data", {})
        prompt_id = msg_data.get("prompt_id")
        task = self.get_task_by_prompt_id(prompt_id)
        name = Path(task.image_path).name
        self.get_pending_tasks
        if not prompt_id:
            return
        
        # 添加更多消息类型处理
        if msg_type == "executed":
            node_id = msg_data.get("node_id")
            self.status_updated.emit(f"[{prompt_id}] 节点执行完成: {node_id}")
            print (f"executed [{prompt_id}] 节点执行完成: {node_id}")
            
        elif msg_type == "execution_success":
            print(f"[{prompt_id}] 任务执行成功")
            self.status_updated.emit(f"[{prompt_id}] 任务执行成功")
            
        elif msg_type == "progress":
            value = msg_data.get("value", 0)
            max_value = msg_data.get("max", 1)
            self.status_updated.emit(f'渲染 {name} [{self.completed_count}/{self.task_count}] ')
            #print(f'{self.completed_count}/{self.task_count} {name} {value}/{max_value}')
            
            # 进度更新
            if max_value > 0:
                self.progress_updated.emit(self.completed_count, self.task_count)
                self.task_progress_updated.emit(name, value, max_value)
            print('not complete self.completed_count: ', self.completed_count)
            # 检查是否完成
            if value >= max_value:
                import threading
                threading.Thread(
                    target=self._handle_task_complete,
                    args=(prompt_id,),
                    daemon=True
                ).start()
                #self._handle_task_complete(prompt_id)
    def _get_task_history(self, prompt_id: str, max_wait: int = 10) -> dict:
        """
        获取任务历史记录（等待服务器写入）
        
        Args:
            prompt_id: 任务ID
            max_wait: 最大等待时间（秒）
        
        Returns:
            包含输出信息的历史记录
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Mock 模式直接返回
                if self.client.is_mock:
                    return self.client.get_history(prompt_id)
                
                # 真实模式从 API 获取
                r = self.client.session.get(
                    f"{self.client.base_url}/history/{prompt_id}", 
                    timeout=5
                )
                data = r.json()
                
                # 检查是否有有效输出
                if prompt_id in data and "outputs" in data[prompt_id] and data[prompt_id]["outputs"]:
                    return data
                    
            except Exception as e:
                print(f"获取 history 失败: {e}")
            
            time.sleep(0.5)
        
        raise TimeoutError(f"获取 history/{prompt_id} 超时（{max_wait}秒）")
    def _handle_task_complete(self, prompt_id: str):
        """处理任务完成 - 使用独立的处理器"""
        task = self.get_task_by_prompt_id(prompt_id)
        name =Path(task.image_path).name
        if not task or task.status == "completed":
            return
        
        try:
            # 获取history
            self.status_updated.emit(f"[{name}] 等待 history 写入...")
            history_data = self._get_task_history(prompt_id)
            original_filename_stem= Path(task.image_path).stem
            prompt_filename =task.prompt_filename
            # 使用处理器处理完成逻辑
            final_path = self.completion_handler.handle_completion(prompt_id=prompt_id,
            history_data=history_data,
            temp_output_dir=str(self.get_temp_output_dir()),
            final_output_dir=str(self.output_dir), original_filename_stem=original_filename_stem,
            prompt_filename= prompt_filename)
            
            if final_path:
                self.status_updated.emit(f"文件已保存: {Path(final_path).name}")
            
            # 更新状态
            self.update_task_status(prompt_id, "completed")
            self.task_completed.emit(name)
            self.progress_updated.emit(self.completed_count, self.task_count)
            self.status_updated.emit(f'渲染 {name} [{self.completed_count}/{self.task_count}] ')
            # 检查全部完成
            if self.is_all_completed():
                self.all_tasks_completed.emit()
                if self.ws_listener:
                    self.ws_listener.stop()
                    
        except Exception as e:
            self.error_occurred.emit(f"处理输出失败: {str(e)}")
        
    # ============ 任务管理 ============
    def clear_tasks(self):
        """清空任务"""
        self.tasks.clear()
        self.prompt_id_to_task.clear()
        self.completed_count = 0
        self.task_count = 0
    
    def add_task(self, task: ComfyTask):
        """添加任务"""
        self.tasks.append(task)
        self.task_count += 1
    
    def register_task_prompt_id(self, task: ComfyTask, prompt_id: str):
        """注册prompt_id"""
        task.prompt_id = prompt_id
        task.status = "submitted"
        self.prompt_id_to_task[prompt_id] = task
    
    def get_task_by_prompt_id(self, prompt_id: str) -> Optional[ComfyTask]:
        """获取任务"""
        return self.prompt_id_to_task.get(prompt_id)
    
    def get_pending_tasks(self) -> List[ComfyTask]:
        """获取待处理任务"""
        return [t for t in self.tasks if t.status == "pending"]
    
    def update_task_status(self, prompt_id: str, status: str):
        """更新任务状态"""
        task = self.get_task_by_prompt_id(prompt_id)
        if task:
            task.status = status
            if status == "completed":
                self.completed_count += 1
    
    def is_all_completed(self) -> bool:
        """是否全部完成"""
        return self.completed_count >= len(self.tasks)
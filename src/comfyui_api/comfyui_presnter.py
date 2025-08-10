# src/comfyui_api/comfyui_presenter.py
# 🔄 重构文件：原 comfyui_presnter.py
# 主要改动：
# 1. 🆕 引入ComfyModel，实现数据管理分离
# 2. 🔄 重构信号处理逻辑，使其更加清晰
# 3. 🆕 添加详细的任务状态跟踪
# 4. 🔄 优化错误处理和用户反馈

import os
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from .comfy_model import ComfyModel, ComfyTask  # 🆕 引入新的数据模型
from .workflow_manager import WorkflowManager
from .submit_worker import ComfySubmitWorker
from .api_client import ComfyApiClient
from src.config import GlobalConfig
class ComfyUIPresenter(QObject):
    def __init__(self, main_model, comfy_view):
        super().__init__()
        # 🔄 重命名：明确区分主模型和ComfyUI模型
        self.main_model = main_model        # 主应用的ImageBatchModel（文件列表等）
        self.comfy_model = ComfyModel()     # 🆕 ComfyUI专用模型（任务管理等）
        self.view = comfy_view              # ComfyUISection视图
        self.client = ComfyApiClient()      # API客户端
        self.current_worker = None          # 当前运行的Worker
        
        # 🔄 保持原有信号连接，但处理逻辑重构
        self.view.local_network_drive_selected.connect(self.set_tmp_img_output_dir)
        self.view.submit_comfy_task.connect(self.handle_submit_task)
        
    def set_output_dir(self, path):
        self.comfy_model.set_output_dir(path)
    def set_tmp_img_output_dir(self, local_network_drive_dir):
        tmp_img_output_dir = os.path.join(local_network_drive_dir,GlobalConfig.code_project_root_rel_dir, GlobalConfig.ai_temp_output_rel_dir)
        self.comfy_model.set_tmp_img_output_dir(tmp_img_output_dir)
    
    @pyqtSlot(dict)
    def handle_submit_task(self, task_info: dict):
        """
        🔄 重构：处理来自ComfyUISection的提交请求
        原来的逻辑分散在ImageBatchPresenter中，现在集中到这里
        改动原因：职责分离，ComfyUI相关逻辑应该由ComfyUI的Presenter处理
        """
        try:
            # 🆕 步骤1：验证输入文件
            if not self.main_model.files:
                self._show_error("没有选择图片文件")
                return
                
            # 🆕 步骤2：设置ComfyUI模型配置
            self.comfy_model.set_workflow_config(
                workflow_path=task_info["workflow_path"],
                prompt_path=task_info["prompt_path"],
                network_root=task_info["local_network_drive_dir"]
            )
            
            # 🆕 步骤3：创建任务列表
            self._create_comfy_tasks(task_info)
            
            # 🆕 步骤4：启动提交流程
            self._start_submission_process(task_info)
            
        except Exception as e:
            self._show_error(f"提交任务失败: {e}")
    
    def _create_comfy_tasks(self, task_info: dict):
        """
        🆕 新增：创建ComfyUI任务列表
        职责：将主模型的文件列表转换为ComfyUI任务
        """
        self.comfy_model.clear_tasks()
        
        # 🔄 使用原有的WorkflowManager，但数据流更清晰
        manager = WorkflowManager(self.main_model, task_info)
        raw_tasks = manager.create_comfy_tasks()
        
        for raw_task in raw_tasks:
            # 🆕 创建结构化的ComfyTask对象
            comfy_task = ComfyTask(
                image_path=raw_task["image"],
                rel_input=raw_task["rel_input"],
                payload=raw_task["payload"]
            )
            self.comfy_model.add_task(comfy_task)
            
        print(f"✅ 创建了 {self.comfy_model.get_total_tasks()} 个ComfyUI任务")
    
    def _start_submission_process(self, task_info: dict):
        """
        🆕 新增：启动任务提交流程
        职责：初始化Worker并建立信号连接
        """
        pending_tasks = self.comfy_model.get_pending_tasks()
        if not pending_tasks:
            self._show_error("没有待处理任务")
            return
            
        total = len(pending_tasks)
        print(f"📋 准备提交 {total} 个任务")
        
        # 🔄 初始化进度显示（保持原有UI逻辑）
        self.view.progress_bar.setRange(0, total)
        self.view.progress_bar.setValue(0)
        self.view.progress_label.setText("准备提交任务...")
        
        # 🔄 创建Worker，但传入新的ComfyModel
        self.current_worker = ComfySubmitWorker(
            client=self.client,
            comfy_model=self.comfy_model,  # 🆕 传入ComfyUI专用模型
            wait_timeout=180,
            wait_interval=2
        )
        
        # 🔄 建立信号连接（保持原有功能）
        self.current_worker.status.connect(self._update_status)
        self.current_worker.progress.connect(self._update_progress)
        self.current_worker.task_completed.connect(self._on_single_task_completed)  # 🆕 新信号
        self.current_worker.all_completed.connect(self._on_all_tasks_completed)    # 🆕 新信号
        self.current_worker.failed.connect(self._show_error)
        
        # 启动Worker
        self.current_worker.start()
        print("🚀 ComfyUI提交流程已启动")
    
    def _update_status(self, status_text: str):
        """🔄 保持原有状态更新逻辑"""
        self.view.progress_label.setText(f"任务进度：{status_text}")
        print(f"📊 状态更新: {status_text}")
    
    def _update_progress(self, done: int, total: int):
        """🔄 保持原有进度更新逻辑"""
        self.view.progress_bar.setValue(done)
        print(f"📈 进度更新: {done}/{total}")
    
    def _on_single_task_completed(self, prompt_id: str):
        """
        🆕 新增：处理单个任务完成
        当WebSocket检测到任务完成时调用
        """
        self.comfy_model.update_task_status(prompt_id, "completed")
        completed = self.comfy_model.completed_count
        total = self.comfy_model.get_total_tasks()
        
        print(f"✅ 任务完成: {prompt_id} ({completed}/{total})")
        self._update_progress(completed, total)
    
    def _on_all_tasks_completed(self):
        """
        🆕 新增：处理所有任务完成
        替代原来的finished_ok信号处理
        """
        print("🎉 所有ComfyUI任务已完成")
        self._show_info("所有ComfyUI任务处理完成！")
        self.current_worker = None
        
        # 🔄 重置进度显示（保持原有UI行为）
        self.view.progress_label.setText("任务进度：已完成")
    
    def _show_error(self, msg: str):
        """🔄 保持原有错误显示逻辑"""
        QMessageBox.critical(self.view, "错误", msg)
        print(f"❌ 错误: {msg}")

    def _show_info(self, msg: str):
        """🔄 保持原有信息显示逻辑"""
        QMessageBox.information(self.view, "提示", msg)
        print(f"ℹ️ 信息: {msg}")
# src/comfyui_api/completion_handler.py
# 🎯 轻量级任务完成处理器 - 单一职责，简洁设计

import os
import shutil
import time
from typing import Dict, Optional
from .comfy_model import ComfyModel


class TaskCompletionHandler:
    """
    🎯 轻量级任务完成处理器
    
    职责：纯粹的文件处理逻辑，不涉及信号、状态管理
    设计原则：单一职责、无副作用、易测试
    """
    
    def __init__(self, file_wait_timeout: int = 15):
        self.file_wait_timeout = file_wait_timeout  # 文件等待超时（秒）
    
    def handle_completion(self, comfy_model: ComfyModel, prompt_id: str, history_data: Dict) -> Optional[str]:
        """
        处理任务完成，返回最终输出文件路径
        
        Args:
            comfy_model: ComfyUI数据模型（实时传入，保证数据最新）
            prompt_id: 任务ID
            history_data: ComfyUI历史数据
            
        Returns:
            str: 最终输出文件路径，失败返回None
        """
        try:
            # 步骤1：解析输出信息
            outputs = history_data.get(prompt_id, {}).get("outputs", {})
            if not outputs:
                print(f"[WARN] 任务 {prompt_id} 无输出数据")
                return None
            
            # 步骤2：等待并获取临时文件
            tmp_file = self._wait_for_temp_file(comfy_model, outputs)
            if not tmp_file:
                print(f"[ERROR] 任务 {prompt_id} 临时文件未生成")
                return None
            
            # 步骤3：移动到最终位置
            final_path = self._move_to_final_location(comfy_model, prompt_id, tmp_file)
            return final_path
            
        except Exception as e:
            print(f"[ERROR] 处理任务 {prompt_id} 完成失败: {e}")
            return None
    
    def _wait_for_temp_file(self, comfy_model: ComfyModel, outputs: Dict) -> Optional[str]:
        """等待临时文件生成并验证完整性"""
        candidates = self._extract_candidate_files(comfy_model, outputs)
        if not candidates:
            return None
        
        # 轮询等待
        start_time = time.time()
        while time.time() - start_time < self.file_wait_timeout:
            for file_path in candidates:
                if self._is_file_ready(file_path):
                    return file_path
            time.sleep(2)
        
        return None
    
    def _extract_candidate_files(self, comfy_model: ComfyModel, outputs: Dict) -> list:
        """从outputs中提取候选文件路径"""
        tmp_dir = comfy_model.get_tmp_output_dir()  # 🎯 实时获取最新路径
        if not tmp_dir:
            return []
        
        files = []
        for node_data in outputs.values():
            if isinstance(node_data, dict):
                images = node_data.get("images", [])
                for img in images:
                    if (isinstance(img, dict) and 
                        img.get("type") == "output" and 
                        "filename" in img):
                        
                        file_path = os.path.join(tmp_dir, img["filename"])
                        files.append(file_path)
        
        return files
    
    def _is_file_ready(self, file_path: str) -> bool:
        """检查文件是否完整可用"""
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
            
            # 简单的文件头检查
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return len(header) > 0
                
        except Exception:
            return False
    
    def _move_to_final_location(self, comfy_model: ComfyModel, prompt_id: str, tmp_file: str) -> str:
        """移动文件到最终位置"""
        output_dir = comfy_model.get_output_dir()  # 🎯 实时获取最新输出目录
        if not output_dir:
            raise ValueError("输出目录未设置")
        
        task = comfy_model.get_task_by_prompt_id(prompt_id)  # 🎯 实时获取最新任务信息
        if not task:
            raise ValueError(f"任务不存在: {prompt_id}")
        
        # 生成最终文件名
        final_name = f"{task.orig_filestem}_processed.png"
        final_path = os.path.join(output_dir, final_name)
        
        # 执行移动
        os.makedirs(output_dir, exist_ok=True)
        shutil.move(tmp_file, final_path)
        
        return final_path
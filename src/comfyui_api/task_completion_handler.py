# src/comfyui_api/task_completion_handler.py
# 🎯 轻量级任务完成处理器 - 单一职责，简洁设计

import os
import re
import shutil
import time
from typing import Dict, Optional
from pathlib import Path


class TaskCompletionHandler:
    """
    🎯 轻量级任务完成处理器
    
    职责：纯粹的文件处理逻辑，不涉及信号、状态管理
    设计原则：单一职责、无副作用、易测试
    """
    
    def __init__(self, file_wait_timeout: int = 15):
        self.file_wait_timeout = file_wait_timeout  # 文件等待超时（秒）
    
    def handle_completion(self, 
                         prompt_id: str,
                         history_data: Dict,
                         temp_output_dir: str,
                         final_output_dir: str,
                         original_filename_stem: str,
                         prompt_filename: str) -> Optional[str]:
        """
        处理任务完成，返回最终输出文件路径
        
        Args:
            prompt_id: 任务ID
            history_data: ComfyUI历史数据
            temp_output_dir: 临时输出目录
            final_output_dir: 最终输出目录
            original_filename_stem: 原始文件名（不含扩展名）
            
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
            tmp_file = self._wait_for_temp_file(temp_output_dir, outputs)
            if not tmp_file:
                print(f"[ERROR] 任务 {prompt_id} 临时文件未生成")
                return None
            
            # 步骤3：移动到最终位置
            final_path = self._move_to_final_location(
                tmp_file, 
                final_output_dir, 
                original_filename_stem,
                prompt_filename
            )
            return final_path
            
        except Exception as e:
            print(f"[ERROR] 处理任务 {prompt_id} 完成失败: {e}")
            return None
    
    def _wait_for_temp_file(self, temp_output_dir: str, outputs: Dict) -> Optional[str]:
        """等待临时文件生成并验证完整性"""
        candidates = self._extract_candidate_files(temp_output_dir, outputs)
        if not candidates:
            return None
        
        # 轮询等待
        start_time = time.time()
        while time.time() - start_time < self.file_wait_timeout:
            for file_path in candidates:
                if self._is_file_ready(file_path):
                    return file_path
            time.sleep(0.5)
        
        return None
    
    def _extract_candidate_files(self, temp_output_dir: str, outputs: Dict) -> list:
        """从outputs中提取候选文件路径"""
        if not temp_output_dir:
            return []
        
        files = []
        for node_data in outputs.values():
            if isinstance(node_data, dict):
                images = node_data.get("images", [])
                for img in images:
                    if (isinstance(img, dict) and 
                        img.get("type") == "output" and 
                        "filename" in img):
                        
                        file_path = os.path.join(temp_output_dir, img["filename"])
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
    
    def _move_to_final_location(self, 
                                tmp_file: str, 
                                output_dir: str, 
                                original_filename_stem:str,
                                prompt_filename:str) -> str:
        """移动文件到最终位置"""
        if not output_dir:
            raise ValueError("输出目录未设置")
        
        # 生成最终文件名
        tags = re.findall(r"\[(.*?)\]", prompt_filename)
        if not tags:
            # 没有 [] → 保持原始文件名
            final_name = f"{original_filename_stem}.png"
        else:
            # 多个 tag → 拼接
            prompt_tag_str = tags[0]
            final_name = f"{original_filename_stem}_{prompt_tag_str}.png"
        final_path = os.path.join(output_dir, final_name)
        
        # 执行移动
        os.makedirs(output_dir, exist_ok=True)
        shutil.move(tmp_file, final_path)
        
        return final_path
    
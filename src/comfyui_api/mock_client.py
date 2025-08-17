# src/comfyui_api/mock_client.py
# 🎯 真正极简Mock：只模拟HTTP通信部分

from pathlib import Path
import uuid
import os
import shutil
import time
import threading

from src.config import GlobalConfig
from .api_client import ComfyApiClient

class MockComfyApiClient(ComfyApiClient):
    """🎯 只模拟Client的HTTP通信职责，不越界做文件处理"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 存储已提交的任务（用于history查询）
        self.submitted_tasks = {}
    @property
    def is_mock(self):
        return True
    
    def submit(self, payload: dict) -> str:
        print('payload: ', payload)
        """🎯 只做Client该做的事：返回prompt_id"""
        prompt_id = f"mock_{uuid.uuid4().hex[:8]}"
        
        self._simulate_server_processing(prompt_id, payload)
        
        print(f"🧪 Mock提交: {prompt_id}")
        return prompt_id
    
    def _simulate_server_processing(self, prompt_id: str, payload: dict):
        """🎯 模拟ComfyUI服务器在后台处理（异步）"""
        # 模拟处理延迟
        local_network_root_dir = Path(r'D:\Temu资料')
        # 🎯 生成模拟输出文件到预期位置
        tmp_output_dir = local_network_root_dir / GlobalConfig.code_project_root_rel_dir/ GlobalConfig.ai_temp_output_rel_dir
        # 🎯 从payload中提取输入文件路径
        input_file = self._extract_input_file_from_payload(payload)
        print(f"🔍 从payload提取输入文件: {input_file}")
        
        if input_file and tmp_output_dir:
            os.makedirs(tmp_output_dir, exist_ok=True)
            
            output_filename = f"mock_output_{prompt_id}.png"
            output_path = os.path.join(tmp_output_dir, output_filename)
            shutil.copy2(input_file, output_path)
            
            # 存储，供history查询
            self.submitted_tasks[prompt_id] = {
                "outputs": {
                    "9": {
                        "images": [{
                            "filename": output_filename,
                            "type": "output"
                        }]
                    }
                }
            }
            print(f"🧪 Mock文件生成完成: {output_path}")

    def _extract_input_file_from_payload(self, payload: dict) -> str:
        """🎯 从payload中找LoadImage相关节点"""
        try:
            prompt = payload.get("prompt", {})
            
            for node_id, node_data in prompt.items():
                if isinstance(node_data, dict):
                    class_type = node_data.get("class_type", "")
                    
                    # 🎯 找LoadImage或LoadImageFromPath节点
                    if class_type in ["LoadImage", "LoadImageFromPath"]:
                        inputs = node_data.get("inputs", {})
                        if "image" in inputs:
                            rel_path = inputs["image"]
                            print(f"🔍 找到图片节点({class_type}): {rel_path}")
                            
                            # 转换为绝对路径
                            abs_path = f"D:/Temu资料/100_Tools/ImageBatchProcessor/AI_process_temp/{rel_path}"
                            print(f"🔍 绝对路径: {abs_path}")
                            print(f"🔍 文件存在: {os.path.exists(abs_path)}")
                            return abs_path
            
            print("🔍 未找到LoadImage相关节点")
            return None
        except Exception as e:
            print(f"提取输入文件失败: {e}")
            return None

    def get_history(self, prompt_id: str) -> dict:
        print(f"🧪 查询历史: {prompt_id}")
        print(f"🧪 可用任务: {list(self.submitted_tasks.keys())}")
        
        if prompt_id in self.submitted_tasks:
            result = {prompt_id: self.submitted_tasks[prompt_id]}
            print(f"🧪 返回数据: {result}")
            return result
        
        print(f"🧪 未找到任务: {prompt_id}")
        return {}
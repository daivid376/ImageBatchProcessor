# src/comfyui_api/file_handler.py
# 文件处理工具类 - 处理文件读写、拷贝、等待等操作

import os
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

class FileHandler:
    """文件处理工具类"""
    
    def file_exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(path) if path else False
    
    def load_json(self, path: str) -> dict:
        """加载JSON文件"""
        if not path or not os.path.exists(path):
            return {}
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_text(self, path: str) -> str:
        """加载文本文件"""
        if not path or not os.path.exists(path):
            return ""
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    def copy_to_temp(self, source_path: str, temp_dir: Path) -> str:
        """拷贝文件到临时目录，返回文件名"""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        source_name = Path(source_path).name
        filename = f"{stamp}_{source_name}"
        dest_path = temp_dir / filename
        shutil.copy2(source_path, dest_path)
        return filename
    
    def wait_file_accessible(self, client, filename: str, subfolder: str, timeout: int = 30):
        """智能等待策略：先等待一段时间再检查"""
        
        # 策略：文件同步通常需要 2-5 秒
        # 与其频繁检查，不如先等待
        
        print("⏳ 等待文件同步到服务器: {filename}")
        
        # 步骤1：先等待固定时间（避免过早检查）
        initial_wait = 3.0  # 根据经验调整
        time.sleep(initial_wait)
        
        # 步骤2：尝试一次 /view 检查
        print("🔍 检查服务器文件访问...")
        try:
            r = client.session.get(
                f"{client.base_url}/view",
                params={
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": "input"
                },
                timeout=25  # 给足够的超时时间
            )
            
            if r.status_code == 200:
                print("✅ 服务器可以访问文件")
                return
            elif r.status_code == 404:
                print("⚠️ 文件未找到，再等待...")
                time.sleep(2.0)
                
                # 再试一次
                r = client.session.get(
                    f"{client.base_url}/view",
                    params={"filename": filename, "subfolder": subfolder, "type": "input"},
                    timeout=25
                )
                
                if r.status_code == 200:
                    print("✅ 第二次检查成功")
                    return
                    
        except Exception as e:
            print("⚠️ 检查失败: {e}")
        
        # 步骤3：无论如何都继续（赌一把）
        print("⚠️ 跳过验证，尝试提交")
        return
        

        
    def move_file(self, source: str, dest: str):
        """移动文件"""
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(source, dest)
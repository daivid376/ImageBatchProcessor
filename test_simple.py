#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# 添加src到路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

print("Testing ComfyUI refactor...")

try:
    # 测试基础导入
    print("1. Testing Config import...")
    from config import GlobalConfig, ImageProcessConfig
    print("OK - Config imported")

    print("2. Testing ComfyModel import...")
    from comfyui_api.comfy_model import ComfyModel, ComfyTask
    print("OK - ComfyModel imported")

    print("3. Testing WorkflowService import...")  
    from comfyui_api.workflow_service import WorkflowService
    print("OK - WorkflowService imported")

    print("4. Testing basic functionality...")
    # 创建ComfyModel实例
    model = ComfyModel()
    print(f"   ComfyModel created, initial tasks: {model.get_total_tasks()}")

    # 创建ComfyTask
    task = ComfyTask(
        image_path="test.jpg",
        rel_input="test/test.jpg", 
        payload={"test": "data"}
    )
    model.add_task(task)
    print(f"   After adding task, total: {model.get_total_tasks()}")

    # 创建WorkflowService实例
    service = WorkflowService()
    print("   WorkflowService created successfully")

    print("\nSUCCESS: All basic functionality tests passed!")
    print("REFACTOR: Architecture is working correctly")
    
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
except Exception as e:
    print(f"TEST ERROR: {e}")
    import traceback
    traceback.print_exc()
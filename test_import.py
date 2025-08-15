#!/usr/bin/env python3
# 简单的导入测试

import sys
import os
from pathlib import Path

# 添加src到路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

print("测试重构后的ComfyUI模块导入...")

try:
    # 测试基础导入
    print("1. 测试Config导入...")
    from config import GlobalConfig, ImageProcessConfig
    print("✅ Config导入成功")

    print("2. 测试ComfyModel导入...")
    from comfyui_api.comfy_model import ComfyModel, ComfyTask
    print("✅ ComfyModel导入成功")

    print("3. 测试WorkflowService导入...")
    from comfyui_api.workflow_service import WorkflowService
    print("✅ WorkflowService导入成功")

    print("4. 测试基本功能...")
    # 创建ComfyModel实例
    model = ComfyModel()
    print(f"   - ComfyModel创建成功，初始任务数: {model.get_total_tasks()}")

    # 创建ComfyTask
    task = ComfyTask(
        image_path="test.jpg",
        rel_input="test/test.jpg",
        payload={"test": "data"}
    )
    model.add_task(task)
    print(f"   - 添加任务后，任务数: {model.get_total_tasks()}")

    # 创建WorkflowService实例
    service = WorkflowService()
    print("   - WorkflowService创建成功")

    print("\n🎉 所有基础功能测试通过！")
    print("🔧 重构后的架构正常工作")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
except Exception as e:
    print(f"❌ 测试错误: {e}")
    import traceback
    traceback.print_exc()
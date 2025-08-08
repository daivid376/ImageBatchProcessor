# test_comfy_submission.py
from src.ImageBatchProcessor_model import ImageBatchModel
from src.comfyui_api.workflow_manager import WorkflowManager
from src.comfyui_api.api_client import ComfyApiClient
from src.config import GlobalConfig

# 模拟 model.files（你拖入图像后的路径）
model = ImageBatchModel()
model.files = [
    r"C:\Users\win10base\Nutstore\1\Temu资料\020_所有商品信息\已上架商品-2507月-M66资料\2、M66型号无人机资料（各种图片的资料）\主图\1.png",
    r"C:\Users\win10base\Nutstore\1\Temu资料\020_所有商品信息\已上架商品-2507月-M66资料\2、M66型号无人机资料（各种图片的资料）\主图\i2.png",
]

# 模拟 UI 选择
info = {
    "workflow_path": "comfyui_assets/workflows/flux_kontext_change_bg_base.json",
    "prompt_path": "comfyui_assets/prompts/change_BG.txt",
    "local_network_drive_dir": r"C:\Users\win10base\Nutstore\1\Temu资料"
}
GlobalConfig.remote_network_drive_dir = r"C:/Users/admin/Nutstore/1/Temu资源"  # ComfyUI能访问的路径

# 构建任务
manager = WorkflowManager(model)
tasks = manager.create_comfy_tasks(info)

# 提交任务
client = ComfyApiClient()
for task in tasks:
    print(f"提交图像: {task['image']}")
    prompt_id = client.submit(task["payload"])
    print(f"返回 prompt_id: {prompt_id}")
    

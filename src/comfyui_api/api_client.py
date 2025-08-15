"http://100.83.51.62"
# src/comfy_api_client.py

from datetime import time as timeModule
import time as pyt
import requests,json
import socket
from typing import List
from pathlib import Path

class ComfyApiClient:
    def __init__(self, host: str = "100.83.51.62", port: int = 8188):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        # 绕过代理设置，避免本地服务器连接问题
        self.session.proxies = {'http': None, 'https': None}

    def is_port_open(self, timeout: float = 2.0) -> bool:
        """测试端口是否可访问"""
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def is_comfy_alive(self) :
        """测试 ComfyUI 是否响应 /system_stats 接口"""
        try:
            res = requests.get(f"{self.base_url}/system_stats", timeout=3)
            return res.status_code == 200
        except Exception:
            return False
        
    def submit(self, payload: dict):
        """
        提交一个 ComfyUI 任务，返回 prompt_id
        """
        url = f"{self.base_url}/prompt"
        try:
            headers = {"Content-Type": "application/json"}
            payload_str = json.dumps(payload, ensure_ascii=False)
            r = self.session.post(url, data=payload_str.encode("utf-8"), headers=headers, timeout=15)
            r.raise_for_status()
            prompt_id = r.json().get("prompt_id", "")
            print(f"✅ 提交成功，prompt_id: {prompt_id}")
            return prompt_id
        except requests.HTTPError as e:
            print("STATUS:", e.response.status_code)
            try:
                print("DETAIL:", e.response.text)
            except Exception:
                pass
            raise
        except Exception as e:
            print(f"❌ 提交失败: {e}")
            raise

def test_comfyui_submission():
    """
    用于调试 ComfyUI 提交接口，验证 payload 格式是否被接受
    """
    import json
    from pathlib import Path

    # 模拟 payload：你可以替换为你自己的路径
    workflow_path = Path("comfyui_assets/workflows/flux_kontext_change_bg_base.json")
    prompt_path = Path("comfyui_assets/prompts/change_BG.txt")
    test_image_path = r"C:\Users\win10base\Nutstore\1\Temu资料\020_所有商品信息\已上架商品-2507月-M66资料\2、M66型号无人机资料（各种图片的资料）\主图\1.png"  # 必须是服务器能读到的路径

    if not workflow_path.exists():
        print(f"❌ 工作流文件不存在: {workflow_path}")
        return
    if not prompt_path.exists():
        print(f"❌ 提示词文件不存在: {prompt_path}")
        return

    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    # 替换 workflow 中的字段（模拟）
    for node in workflow["nodes"]:
        if "inputs" in node:
            if "image" in node["inputs"]:
                node["inputs"]["image"] = test_image_path
            if "positive" in node["inputs"]:
                node["inputs"]["positive"] = prompt
            if "negative" in node["inputs"]:
                node["inputs"]["negative"] = ""

    payload = {"prompt": workflow}
    client = ComfyApiClient()

    print("📦 payload 内容如下：")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        prompt_id = client.submit(payload)
        print(f"✅ 成功提交任务，返回 prompt_id: {prompt_id}")
    except Exception as e:
        print(f"❌ 提交失败: {e}")
if __name__ == "__main__":
    test_comfyui_submission()
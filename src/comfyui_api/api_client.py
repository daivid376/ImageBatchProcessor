"http://100.83.51.62"
# src/comfy_api_client.py

from datetime import time as timeModule
import time
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
        
    def wait_for_input_file(self, rel_input: str, timeout: float = 180.0, interval: float = 2.0) :
        if "/" not in rel_input:
            raise ValueError(f"rel_input 不是 '子目录/文件名' 格式: {rel_input}")

        subfolder, filename = rel_input.split("/", 1)
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": "input",   # 关键：从 input 里读取
        }

        deadline = time.time() + timeout
        last_status = None
        while time.time() < deadline:
            try:
                r = requests.get(f"{self.base_url}/view", params=params, timeout=5)
                last_status = r.status_code
                if r.status_code == 200:
                    return  # 就绪
            except Exception as e:
                last_status = str(e)
            time.sleep(interval)

        raise TimeoutError(f"等待文件出现在 ComfyUI input 超时（{timeout:.0f}s）: {rel_input}，最后状态: {last_status}")
    def submit(self, payload: dict):
        """
        提交一个 ComfyUI 任务。返回任务 prompt_id。
        """
        url = f"{self.base_url}/prompt"
        try:
            headers = {"Content-Type": "application/json"}
            payload_str = json.dumps(payload, ensure_ascii=False)
            r = self.session.post(url, data=payload_str.encode("utf-8"), headers=headers, timeout=15)
            r.raise_for_status()
            print('payload: ', payload)
            return r.json().get("prompt_id", "")
        except requests.HTTPError as e:
            print("STATUS:", e.response.status_code)
            try:
                print("DETAIL:", e.response.text)  # 这里通常会写明是哪个节点/字段不合法
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
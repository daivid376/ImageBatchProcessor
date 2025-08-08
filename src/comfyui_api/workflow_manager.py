# src/workflow_manager.py

import os
import json
import copy
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from src.config import GlobalConfig

class WorkflowManager:
    """
    三步走：
    1) _compute_layout：计算本地/远端中转目录
    2) _stage_image：把原图拷贝到本地共享盘的中转目录（comfy_api_input）
    3) _patch_workflow：根据节点类型写入相对或绝对路径，并覆盖正/负提示词
    """
    def __init__(self, model, info: dict):
        self.model = model
        self.info = info
        self._compute_layout()

    # ---------- Step 1: 目录布局 ----------
    def _compute_layout(self):
        # 本地共享盘根（UI 里选的）
        self.local_root = self.info["local_network_drive_dir"]

        # 本地中转输入目录（落盘位置）
        self.local_input_dir = os.path.join(
            self.local_root, GlobalConfig.ai_process_temp_input
        )

        # 远端可见的中转输入目录（服务器眼中的绝对路径前缀）
        self.remote_input_dir = os.path.join(
            GlobalConfig.remote_network_drive_dir, GlobalConfig.ai_process_temp_input
        )

        os.makedirs(self.local_input_dir, exist_ok=True)

    # ---------- 通用读取 ----------
    def load_workflow(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_prompt(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    # ---------- 小工具 ----------
    def _iter_api_nodes(self, wf: Dict[str, Any]):
        # 只遍历 API Prompt 这种 { "12": {class_type, inputs}, ... } 结构
        for nid, node in wf.items():
            if isinstance(node, dict) and "class_type" in node:
                yield nid, node

    def _posix(self, p: str) -> str:
        return Path(p).as_posix()

    # ---------- Step 2: 落中转区 ----------
    def _stage_image(self, src_abs: str):
        """
        把原图拷到 <local_root>/<ai_temp>/comfy_api_input 下
        返回：
          local_abs  -> 本地绝对路径（拷贝后）
          rel_input  -> 'comfy_api_input/xxx' 供 LoadImage 使用（相对 ComfyUI input/）
          remote_abs -> 远端可见绝对路径 供 LoadImageFromPath 使用
        """
        p = Path(src_abs)
        if not p.exists():
            raise FileNotFoundError(f"源文件不存在: {src_abs}")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        out_name = f"{stamp}_{p.name}"
        local_abs = os.path.join(self.local_input_dir, out_name)
        os.makedirs(self.local_input_dir, exist_ok=True)
        print("p exists?", os.path.exists(p))
        print("dst dir exists?", os.path.exists(self.local_input_dir))
        shutil.copy2(p, local_abs)

        # 取中转目录末级名（通常为 comfy_api_input）
        rel_dir_name = Path(self.local_input_dir).name
        rel_input = f"{rel_dir_name}/{out_name}"
        remote_abs = os.path.join(self.remote_input_dir, out_name)
        return (
            self._posix(local_abs),
            self._posix(rel_input),
            self._posix(remote_abs),
        )

    # ---------- Step 3: 打补丁 ----------
    def _patch_workflow(self, workflow: dict, rel_input: str, remote_abs: str, pos: str, neg: str):
        """
        兼容两种模板：
        - API Prompt（无 "nodes"）：dict[key]={class_type, inputs}
        - GUI Workflow（有 "nodes" 列表）
        """
        wf = copy.deepcopy(workflow)

        # A) API Prompt
        if isinstance(wf, dict) and "nodes" not in wf:
            for _, node in self._iter_api_nodes(wf):
                ctype = node.get("class_type")
                inputs = node.setdefault("inputs", {})

                # 图片节点：按类型区别相对/绝对路径
                if ctype == "LoadImage":
                    inputs["image"] = rel_input
                elif ctype == "LoadImageFromPath":
                    inputs["image"] = rel_input

                # 文本与正负提示
                if ctype in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeWAS"):
                    if "text" in inputs and pos:
                        inputs["text"] = pos
                        
                if ctype == "SaveImage":
                    prefix = inputs.get("filename_prefix", "")
                    base_prefix = os.path.basename(prefix) if prefix else "result"
                    inputs["filename_prefix"] = f"comfy_api_output/{base_prefix}"
            return {"prompt": wf}


    # ---------- 对外主函数 ----------
    def create_comfy_tasks(self):
        """
        收集 UI 数据后，批量构建提交给 Comfy 的任务 JSON。
        每张图都会先落中转区，再 patch workflow。
        """
        workflow = self.load_workflow(self.info["workflow_path"])
        prompt = self.load_prompt(self.info["prompt_path"])

        tasks = []
        for img_path in self.model.files:
            _, rel_input, remote_abs = self._stage_image(img_path)
            payload = self._patch_workflow(workflow, rel_input, remote_abs, prompt, "")
            tasks.append({
                "image": img_path,
                "rel_input": rel_input,
                "payload": payload
            })
        return tasks

# src/comfyui_api/workflow_manager.py
# 🔄 轻微调整：添加调试信息，保持所有原有功能
# 主要改动：
# 1. 🆕 添加调试输出，便于跟踪任务创建过程
# 2. ✅ 保持所有原有的工作流处理逻辑

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
    🔄 保持原有功能：三步走工作流处理
    1) _compute_layout：计算本地/远端中转目录
    2) _stage_image：把原图拷贝到本地共享盘的中转目录（comfy_api_input）
    3) _patch_workflow：根据节点类型写入相对或绝对路径，并覆盖正/负提示词
    """
    def __init__(self, model, info: dict):
        self.model = model
        self.info = info
        self._compute_layout()
        # 🆕 添加调试信息
        print(f"📂 WorkflowManager初始化:")
        print(f"   - 本地输入目录: {self.local_input_dir}")
        print(f"   - 远端输入目录: {self.remote_input_dir}")

    # ---------- Step 1: 目录布局 ---------- 
    def _compute_layout(self):
        """🔄 保持原有目录计算逻辑"""
        # 本地共享盘根（UI 里选的）
        self.local_root = self.info["local_network_drive_dir"]

        # 本地中转输入目录（落盘位置）
        self.local_input_dir = os.path.join(
            self.local_root,GlobalConfig.code_project_root_rel_dir, GlobalConfig.ai_temp_input_rel_dir
        )

        # 远端可见的中转输入目录（服务器眼中的绝对路径前缀）
        self.remote_input_dir = os.path.join(
            GlobalConfig.remote_network_drive_dir, GlobalConfig.code_project_root_rel_dir,GlobalConfig.ai_temp_input_rel_dir
        )

        os.makedirs(self.local_input_dir, exist_ok=True)

    # ---------- 通用读取 ----------
    def load_workflow(self, path: str):
        """🔄 保持原有工作流加载逻辑"""
        with open(path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
        # 🆕 添加调试信息
        print(f"📋 加载工作流: {path}")
        return workflow

    def load_prompt(self, path: str):
        """🔄 保持原有提示词加载逻辑"""
        with open(path, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
        # 🆕 添加调试信息
        print(f"💬 加载提示词: {path} ({len(prompt)} 字符)")
        return prompt

    # ---------- 小工具 ----------
    def _iter_api_nodes(self, wf: Dict[str, Any]):
        """🔄 保持原有API节点遍历逻辑"""
        # 只遍历 API Prompt 这种 { "12": {class_type, inputs}, ... } 结构
        for nid, node in wf.items():
            if isinstance(node, dict) and "class_type" in node:
                yield nid, node

    def _posix(self, p: str):
        """🔄 保持原有路径格式化逻辑"""
        return Path(p).as_posix()

    # ---------- Step 2: 落中转区 ----------
    def _stage_image(self, src_abs: str):
        """
        🔄 保持原有图像暂存逻辑
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
        
        # 🆕 添加调试信息
        print(f"📁 复制图像: {p.name} -> {out_name}")
        print("p exists?", os.path.exists(p))
        print("dst dir exists?", os.path.exists(self.local_input_dir))
        
        shutil.copy2(p, local_abs)

        # 取中转目录末级名（通常为 comfy_api_input）
        rel_dir_name = Path(self.local_input_dir).name
        rel_input = f"{rel_dir_name}/{out_name}"
        remote_abs = os.path.join(self.remote_input_dir, out_name)
        
        # 🆕 添加调试信息
        print(f"   - 本地路径: {local_abs}")
        print(f"   - 相对路径: {rel_input}")
        print(f"   - 远程路径: {remote_abs}")
        
        return (
            self._posix(local_abs),
            self._posix(rel_input),
            self._posix(remote_abs),
        )

    # ---------- Step 3: 打补丁 ----------
    def _patch_workflow(self, workflow: dict, rel_input: str, remote_abs: str, pos: str, neg: str):
        """
        🔄 保持原有工作流补丁逻辑
        兼容两种模板：
        - API Prompt（无 "nodes"）：dict[key]={class_type, inputs}
        - GUI Workflow（有 "nodes" 列表）
        """
        wf = copy.deepcopy(workflow)

        # A) API Prompt
        if isinstance(wf, dict) and "nodes" not in wf:
            # 🆕 添加调试信息
            patch_count = 0
            for _, node in self._iter_api_nodes(wf):
                ctype = node.get("class_type")
                inputs = node.setdefault("inputs", {})

                # 图片节点：按类型区别相对/绝对路径
                if ctype == "LoadImage":
                    inputs["image"] = rel_input
                    patch_count += 1
                    print(f"🔧 补丁LoadImage: {rel_input}")
                elif ctype == "LoadImageFromPath":
                    inputs["image"] = rel_input
                    patch_count += 1
                    print(f"🔧 补丁LoadImageFromPath: {rel_input}")

                # 文本与正负提示
                if ctype in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeWAS"):
                    if "text" in inputs and pos:
                        inputs["text"] = pos
                        patch_count += 1
                        print(f"🔧 补丁提示词: {pos[:50]}...")
                        
                if ctype == "SaveImage":
                    prefix = inputs.get("filename_prefix", "")
                    base_prefix = os.path.basename(prefix) if prefix else "result"
                    inputs["filename_prefix"] = f"comfy_api_output/{base_prefix}"
                    patch_count += 1
                    print(f"🔧 补丁SaveImage: comfy_api_output/{base_prefix}")
            
            print(f"✅ 工作流补丁完成，共修改 {patch_count} 个节点")
            return {"prompt": wf}

    # ---------- 对外主函数 ----------
    def create_comfy_tasks(self):
        """
        🔄 保持原有任务创建逻辑，🆕 添加详细日志
        收集 UI 数据后，批量构建提交给 Comfy 的任务 JSON。
        每张图都会先落中转区，再 patch workflow。
        """
        print(f"🚀 开始创建ComfyUI任务...")
        
        workflow = self.load_workflow(self.info["workflow_path"])
        prompt = self.load_prompt(self.info["prompt_path"])

        tasks = []
        total_files = len(self.model.files)
        print(f"📊 处理 {total_files} 个文件")
        
        for i, img_path in enumerate(self.model.files, 1):
            print(f"📋 创建任务 {i}/{total_files}: {os.path.basename(img_path)}")
            
            _, rel_input, remote_abs = self._stage_image(img_path)
            payload = self._patch_workflow(workflow, rel_input, remote_abs, prompt, "")
            
            task = {
                "image": img_path,
                "rel_input": rel_input,
                "payload": payload
            }
            tasks.append(task)
            
        print(f"✅ 任务创建完成，共 {len(tasks)} 个任务")
        return tasks
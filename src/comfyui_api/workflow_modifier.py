# src/comfyui_api/workflow_modifier.py
# 工作流修改器 - 专门处理workflow的修改逻辑

import copy
from typing import Dict

class WorkflowModifier:
    """工作流修改器 - 集中管理所有workflow修改逻辑"""
    
    def apply_modifications(self, template: Dict, rel_input: str, 
                           prompt_text: str, ui_config: Dict) -> Dict:
        """
        应用所有修改到工作流
        
        Args:
            template: 工作流模板
            rel_input: 输入图片相对路径
            prompt_text: 提示词文本
            ui_config: UI配置字典
            
        Returns:
            修改后的工作流
        """
        workflow = copy.deepcopy(template)
        
        for node_id, node in workflow.items():
            if not isinstance(node, dict) or "class_type" not in node:
                continue
            
            ctype = node.get("class_type")
            inputs = node.setdefault("inputs", {})
            
            # 基础修改
            self._apply_image_input(ctype, inputs, rel_input)
            self._apply_prompt_text(ctype, inputs, prompt_text)
            self._apply_output_prefix(ctype, inputs)
            
            # UI配置修改
            self._apply_ui_config(ctype, inputs, ui_config)
            print('ui_config: ', ui_config)
        
        return workflow
    
    def _apply_image_input(self, ctype: str, inputs: dict, rel_input: str):
        """应用图片输入修改"""
        if ctype in ("LoadImage", "LoadImageFromPath"):
            inputs["image"] = rel_input
    
    def _apply_prompt_text(self, ctype: str, inputs: dict, prompt_text: str):
        """应用提示词修改"""
        if ctype in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeWAS"):
            if "text" in inputs and prompt_text:
                inputs["text"] = prompt_text
    
    def _apply_output_prefix(self, ctype: str, inputs: dict):
        """应用输出前缀修改"""
        if ctype == "SaveImage":
            prefix = inputs.get("filename_prefix", "result")
            inputs["filename_prefix"] = f"comfy_api_output/{prefix}"
    
    def _apply_ui_config(self, ctype: str, inputs: dict, ui_config: dict):
        """应用UI配置修改"""
        if ctype == "KSampler":
            # 种子值
            if "seed" in ui_config:
                inputs["seed"] = ui_config["seed"]
            
            # 迭代步数
            if "steps" in ui_config:
                inputs["steps"] = ui_config["steps"]
            
            # 采样器
            if "sampler" in ui_config:
                inputs["sampler_name"] = ui_config["sampler"]
            
            # 调度器
            if "scheduler" in ui_config:
                inputs["scheduler"] = ui_config["scheduler"]
        
        # 背景图片（示例）
        if ctype == "LoadImage" and inputs.get("name") == "background":
            if "bg_file_path" in ui_config:
                inputs["image"] = ui_config["bg_file_path"]
        
        # CFG Scale（示例）
        if ctype == "KSampler" and "cfg_scale" in ui_config:
            inputs["cfg"] = ui_config["cfg_scale"]
        
        # 未来添加更多UI配置修改...
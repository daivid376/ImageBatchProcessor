from dataclasses import dataclass, field
@dataclass
class GlobalConfig:
    """
    全局配置类，包含应用的基本设置。
    """
    APP_ORG= "EleFlyStudio"
    APP_NAME= "ImageBatchProcessor"
    remote_network_drive_dir:str= "C:/Users/admin/Nutstore/1/Temu资源"
    host: str = "100.83.51.62"
    port: int = 8188
    comfy_base_dir = "C:/Users/admin/Documents/ComfyUI"
    ai_temp_input = "100_Tools/ImageBatchProcessor/AI_process_temp/comfy_api_input"
    ai_temp_output = "100_Tools/ImageBatchProcessor/AI_process_temp/comfy_api_output"
    code_project_root_rel_dir = "100_Tools/ImageBatchProcessor"
    comfy_assets_rel_dir = "comfyui_assets"
    ai_temp_input_rel = "AI_process_temp/comfy_api_input"
    ai_temp_output_rel = "AI_process_temp/comfy_api_output"
    

@dataclass
class ImageProcessConfig:
    hflip: bool = field(default=False, metadata={
        "label": "水平翻转",
        "tooltip": "是否将图片进行水平翻转"
    })
    vflip: bool = field(default=False, metadata={
        "label": "垂直翻转",
        "tooltip": "是否将图片进行垂直翻转"
    })
    opacity: float = field(default=1.0, metadata={
        "label": "透明度调节",
        "tooltip": "设置输出图像透明度 (0.0~1.0)",
        "slider": True,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01
    })
    noise_level: float = field(default=2.0, metadata={
        "label": "噪声强度",
        "tooltip": "添加微弱随机噪声，避免被平台识别"
    })
    rot_min: float = field(default=0.5, metadata={
        "label": "最小旋转角度",
        "tooltip": "随机旋转的最小角度（度）"
    })
    rot_max: float = field(default=1.5, metadata={
        "label": "最大旋转角度",
        "tooltip": "随机旋转的最大角度（度）"
    })
    persp_min: float = field(default=1.0, metadata={
        "label": "透视最小拉伸",
        "tooltip": "透视变换时的最小拉伸百分比"
    })
    persp_max: float = field(default=5.0, metadata={
        "label": "透视最大拉伸",
        "tooltip": "透视变换时的最大拉伸百分比"
    })
    color_jitter: float = field(default=0.02, metadata={
        "label": "颜色微调",
        "tooltip": "轻微调整颜色，增加随机性"
    })
    distortion_strength: float = field(default=5.0, metadata={
        "label": "扭曲强度",
        "tooltip": "扭曲的幅度大小"
    })
    distortion_smoothness: float = field(default=8.0, metadata={
        "label": "扭曲平滑度",
        "tooltip": "扭曲平滑程度，值越大越平滑"
    })
    scale_x: float = field(default=1.0, metadata={
        "label": "水平缩放",
        "tooltip": "水平方向缩放倍数"
    })
    scale_y: float = field(default=1.0, metadata={
        "label": "垂直缩放",
        "tooltip": "垂直方向缩放倍数"
    })
    overwrite: bool = field(default=True, metadata={
    "label": "覆盖已存在文件",
    "tooltip": "若勾选，则处理结果会覆盖已有文件，否则自动重命名"
    })
    
    

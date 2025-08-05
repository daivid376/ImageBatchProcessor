import cv2
import numpy as np
import random
from PIL import Image
from types import SimpleNamespace
from dataclasses import asdict
from src.config import ImageProcessConfig

# =========================
# 图像处理函数 (结构优化版)
# =========================
def process_image_v5(image_path: str, config: ImageProcessConfig) -> Image.Image:
    """
    根据配置参数对图像进行批量处理。
    动态解析 dataclass 配置，避免手动解包参数。
    """
    # 将配置转为可点属性访问对象
    p = SimpleNamespace(**asdict(config))

    # 读取图像
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img)

    # Step 1: 水平翻转
    if getattr(p, 'flip', False):
        img_np = cv2.flip(img_np, 1)

    # Step 2: 垂直翻转
    if getattr(p, 'vflip', False):
        img_np = cv2.flip(img_np, 0)

    # Step 3: 双区间随机旋转
    h, w = img_np.shape[:2]
    center = (w // 2, h // 2)
    min_angle = getattr(p, 'rot_min', 0.5)
    max_angle = getattr(p, 'rot_max', 1.5)
    if random.random() < 0.5:
        angle = random.uniform(-max_angle, -min_angle)
    else:
        angle = random.uniform(min_angle, max_angle)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    img_np = cv2.warpAffine(img_np, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)

    # Step 4: 轻微透视变化
    persp_min = getattr(p, 'persp_min', 1.0)
    persp_max = getattr(p, 'persp_max', 5.0)
    shift = random.uniform(persp_min, persp_max)
    pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    pts2 = np.float32([[0 + shift, 0], [w + shift, 0], [0, h + shift], [w, h + shift]])
    M_persp = cv2.getPerspectiveTransform(pts1, pts2)
    img_np = cv2.warpPerspective(img_np, M_persp, (w, h), borderMode=cv2.BORDER_REFLECT)

    # Step 5: 加入微量噪点
    noise_level = getattr(p, 'noise_level', 2.0)
    noise = np.random.normal(0, noise_level, img_np.shape).astype(np.int16)
    img_np = np.clip(img_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Step 6: 颜色细微扰动
    color_jitter = getattr(p, 'color_jitter', 0.02)
    factor = random.uniform(1 - color_jitter, 1 + color_jitter)
    img_np = np.clip(img_np * factor, 0, 255).astype(np.uint8)

    return Image.fromarray(img_np)

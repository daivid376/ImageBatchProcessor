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
    if getattr(p, 'hflip', False):
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
    
    
    distortion_strength =getattr(p, 'distortion_strength', 5)
    distortion_smoothness =getattr(p, 'distortion_smoothness', 8)
    if distortion_strength > 0:
        img_np = apply_elastic_distortion(img_np, distortion_strength, distortion_smoothness)
    
    scale_x = getattr(p, 'scale_x', 1.0)
    scale_y = getattr(p, 'scale_y', 1.0)
    if scale_x != 1.0 or scale_y != 1.0:
        img_np = scale_and_fill(img_np, scale_x, scale_y, mode='reflect')
    
    opacity = getattr(p, 'opacity', 1.0)
    if opacity < 1.0:
        # 转换为RGBA添加透明度
        if img_np.shape[2] == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2RGBA)
        img_np[..., 3] = (img_np[..., 3].astype(np.float32) * opacity).astype(np.uint8)
    # ✅ 返回 PIL Image
    return Image.fromarray(img_np)

def apply_elastic_distortion(image, distortion_strength=5, distortion_smoothness=8):
    """
    对图像进行弹性形变处理
    :param image: 输入图像 (numpy array)
    :param distortion_strength: 形变强度 (alpha)
    :param distortion_smoothness: 形变平滑度 (sigma)
    :return: 扭曲后的图像
    """
    random_state = np.random.RandomState(None)
    shape = image.shape[:2]

    dx = (random_state.rand(*shape) * 2 - 1) * distortion_strength
    dy = (random_state.rand(*shape) * 2 - 1) * distortion_strength

    dx = cv2.GaussianBlur(dx, (17, 17), distortion_smoothness)
    dy = cv2.GaussianBlur(dy, (17, 17), distortion_smoothness)

    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    map_x = (x + dx).astype(np.float32)
    map_y = (y + dy).astype(np.float32)

    return cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def scale_and_fill(img_np, scale_x=1.0, scale_y=1.0, mode='reflect'):
    h, w = img_np.shape[:2]
    new_w = int(w * scale_x)
    new_h = int(h * scale_y)

    # 缩放图像
    img_resized = cv2.resize(img_np, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    if new_w <= w and new_h <= h:
        # ====== 缩小情况：需要填充 ======
        pad_left = (w - new_w) // 2
        pad_right = w - new_w - pad_left
        pad_top = (h - new_h) // 2
        pad_bottom = h - new_h - pad_top

        if mode == 'reflect':
            canvas = cv2.copyMakeBorder(img_resized, pad_top, pad_bottom, pad_left, pad_right, 
                                        borderType=cv2.BORDER_REFLECT_101)
        elif mode == 'blur':
            bg = cv2.GaussianBlur(img_np, (51, 51), 30)
            canvas = bg
            canvas[pad_top:pad_top+new_h, pad_left:pad_left+new_w] = img_resized
        else:
            canvas = cv2.copyMakeBorder(img_resized, pad_top, pad_bottom, pad_left, pad_right,
                                        borderType=cv2.BORDER_CONSTANT, value=(255,255,255))
    else:
        # ====== 放大情况：裁剪中间部分 ======
        start_x = max((new_w - w) // 2, 0)
        start_y = max((new_h - h) // 2, 0)
        canvas = img_resized[start_y:start_y+h, start_x:start_x+w]

    return canvas
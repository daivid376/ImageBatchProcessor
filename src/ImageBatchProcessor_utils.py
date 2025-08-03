import cv2
import numpy as np
from PIL import Image
import random

def process_image_v5(image_path, flip=True, noise_level=2.0, min_angle=0.5, max_angle=1.5):
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img)

    # Step 1: 水平翻转
    if flip:
        img_np = cv2.flip(img_np, 1)

    # Step 2: 双区间随机旋转
    h, w = img_np.shape[:2]
    center = (w // 2, h // 2)
    if random.random() < 0.5:
        # 负角度区间
        angle = random.uniform(-max_angle, -min_angle)
    else:
        # 正角度区间
        angle = random.uniform(min_angle, max_angle)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    img_np = cv2.warpAffine(img_np, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)

    # Step 3: 轻微透视变化
    shift = random.uniform(-5, 5)
    pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    pts2 = np.float32([[0 + shift, 0], [w + shift, 0], [0, h + shift], [w, h + shift]])
    M_persp = cv2.getPerspectiveTransform(pts1, pts2)
    img_np = cv2.warpPerspective(img_np, M_persp, (w, h), borderMode=cv2.BORDER_REFLECT)

    # Step 4: 加入微量噪点
    noise = np.random.normal(0, noise_level, img_np.shape).astype(np.int16)
    img_np = np.clip(img_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Step 5: 颜色细微扰动
    factor = random.uniform(0.98, 1.02)
    img_np = np.clip(img_np * factor, 0, 255).astype(np.uint8)

    return Image.fromarray(img_np)

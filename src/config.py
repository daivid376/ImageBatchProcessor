# src/config.py
from dataclasses import dataclass

@dataclass
class ImageProcessConfig:
    flip: bool = True
    vflip: bool = False
    noise_level: float = 2.0
    rot_min: float = 0.5
    rot_max: float = 1.5
    persp_min: float = 1.0
    persp_max: float = 5.0
    color_jitter: float = 0.02
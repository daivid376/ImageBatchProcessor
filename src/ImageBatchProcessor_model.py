import os
from src.ImageBatchProcessor_utils import process_image_v5
from src.config import ImageProcessConfig

class ImageBatchModel:
    def __init__(self):
        self.files = []
        self.output_dir = ""

    def set_output_dir(self, path):
        self.output_dir = path

    def add_files(self, paths):
        valid_files = []
        for f in paths:
            f = os.path.abspath(f)
            if os.path.isdir(f):
                for img in os.listdir(f):
                    if img.lower().endswith((".png", ".jpg", ".jpeg")):
                        valid_files.append(os.path.join(f, img))
            elif f.lower().endswith((".png", ".jpg", ".jpeg")):
                valid_files.append(f)
        added_files = []
        for f in valid_files:
            if f not in self.files:
                self.files.append(f)
                added_files.append(f)
        return added_files

    def process_one(self, file, config: ImageProcessConfig):
        """处理单张图片并保存"""
        if not self.output_dir or not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        img_out = process_image_v5(file, config)
        name, _ = os.path.splitext(os.path.basename(file))
        output_path = os.path.join(self.output_dir, f"mod_{name}.png")
        img_out.save(output_path, format="PNG")
        return output_path

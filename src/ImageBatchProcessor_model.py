import os
from ImageBatchProcessor_utils import process_image_v5

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

    def process_all(self, flip, noise, rot_min, rot_max):
        if not self.output_dir or not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        for file in self.files:
            img_out = process_image_v5(file, flip, noise, rot_min, rot_max)
            img_out.save(os.path.join(self.output_dir, "mod_" + os.path.basename(file)), quality=95)


import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageEnhance, ImageFilter, ImageTk
import cv2
import numpy as np
import json
import os
import random

CONFIG_FILE = 'ui_config.json'

def process_image_v5(image_path, flip=True, noise_level=2.0):
    img = Image.open(image_path).convert("RGB")
    w0, h0 = img.size
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    pad_x, pad_y = int(w0*0.25), int(h0*0.25)
    new_w, new_h = w0 + 2*pad_x, h0 + 2*pad_y
    img_ext = Image.new("RGB", (new_w, new_h))
    img_ext.paste(img, (pad_x, pad_y))
    img_ext_np = np.array(img_ext)
    img_ext_np[:pad_y, pad_x:pad_x+w0] = np.flipud(img_ext_np[pad_y:2*pad_y, pad_x:pad_x+w0])
    img_ext_np[pad_y+h0:, pad_x:pad_x+w0] = np.flipud(img_ext_np[h0:pad_y+h0, pad_x:pad_x+w0])
    img_ext_np[:, :pad_x] = np.fliplr(img_ext_np[:, pad_x:2*pad_x])
    img_ext_np[:, pad_x+w0:] = np.fliplr(img_ext_np[:, pad_x+w0-pad_x:pad_x+w0])
    h, w = img_ext_np.shape[:2]
    pts1 = np.float32([[0,0],[w-1,0],[0,h-1],[w-1,h-1]])
    delta = (np.random.uniform(-0.02, 0.02, (4,2))*[w,h]).astype(np.float32)
    pts2 = pts1 + delta
    M = cv2.getPerspectiveTransform(pts1, pts2)
    img_np = cv2.warpPerspective(img_ext_np, M, (w,h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    gradient = np.linspace(np.random.randint(200,255), np.random.randint(200,255), h).astype(np.uint8)
    gradient = np.tile(gradient[:, None], (1,w))
    gradient_img = np.stack([gradient]*3, axis=2)
    alpha = np.random.uniform(0.02,0.06)
    img_np = cv2.addWeighted(img_np, 1, gradient_img, alpha, 0)
    img_out = Image.fromarray(img_np)
    img_out = ImageEnhance.Brightness(img_out).enhance(np.random.uniform(0.96, 1.05))
    img_out = ImageEnhance.Contrast(img_out).enhance(np.random.uniform(0.95, 1.06))
    img_out = ImageEnhance.Color(img_out).enhance(np.random.uniform(0.97, 1.05))
    img_np = np.array(img_out, dtype=np.float32)
    noise = np.random.normal(0, noise_level, img_np.shape)
    img_np = np.clip(img_np + noise, 0, 255).astype(np.uint8)
    img_out = Image.fromarray(img_np)
    img_out = img_out.filter(ImageFilter.GaussianBlur(0.3))
    img_out = img_out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    center_x, center_y = img_np.shape[1]//2, img_np.shape[0]//2
    start_x = max(center_x - w0//2, 0)
    start_y = max(center_y - h0//2, 0)
    img_np = img_np[start_y:start_y+h0, start_x:start_x+w0]
    return Image.fromarray(img_np)

def save_config():
    config = {
        'output_folder': output_entry.get(),
        'flip': flip_var.get(),
        'noise': noise_entry.get()
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            output_entry.insert(0, config.get('output_folder', ''))
            flip_var.set(config.get('flip', True))
            noise_entry.insert(0, config.get('noise', '2.0'))

def drop_files(event):
    files = root.tk.splitlist(event.data)
    input_list.delete(0, tk.END)
    for f in files:
        input_list.insert(tk.END, f)

def select_output_folder():
    folder = filedialog.askdirectory(title="选择输出文件夹")
    output_entry.delete(0, tk.END)
    output_entry.insert(0, folder)

def preview_image():
    files = input_list.get(0, tk.END)
    if not files:
        messagebox.showerror("错误", "请选择至少一张图片预览")
        return
    flip = flip_var.get()
    noise = float(noise_entry.get())
    img_out = process_image_v5(files[0], flip, noise)
    img_preview = ImageTk.PhotoImage(img_out.resize((200,200)))
    preview_label.config(image=img_preview)
    preview_label.image = img_preview

def run_processing():
    files = input_list.get(0, tk.END)
    if not files:
        messagebox.showerror("错误", "请先选择图片")
        return
    output_dir = output_entry.get()
    if not output_dir:
        messagebox.showerror("错误", "请选择输出文件夹")
        return
    os.makedirs(output_dir, exist_ok=True)
    for img_file in files:
        img_out = process_image_v5(img_file, flip_var.get(), float(noise_entry.get()))
        filename = os.path.basename(img_file)
        img_out.save(os.path.join(output_dir, "mod5_"+filename), quality=95)
    save_config()
    messagebox.showinfo("完成", f"处理完成，结果保存在: {output_dir}")

root = TkinterDnD.Tk()
root.title("批量图片处理工具 V5 UI 拖放版")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="拖放图片到下方列表或手动选择:").grid(row=0, column=0, columnspan=2, sticky='w')
input_list = tk.Listbox(frame, selectmode=tk.MULTIPLE, width=50)
input_list.grid(row=1, column=0, columnspan=2, padx=5)
input_list.drop_target_register(DND_FILES)
input_list.dnd_bind('<<Drop>>', drop_files)

tk.Button(frame, text="输出文件夹", command=select_output_folder).grid(row=2, column=0, padx=5)
output_entry = tk.Entry(frame, width=53)
output_entry.grid(row=2, column=1, padx=5)

flip_var = tk.BooleanVar(value=True)
tk.Checkbutton(frame, text="水平翻转", variable=flip_var).grid(row=3, column=0, sticky='w')

tk.Label(frame, text="噪点强度:").grid(row=4, column=0, sticky='e')
noise_entry = tk.Entry(frame, width=10)
noise_entry.insert(0, "2.0")
noise_entry.grid(row=4, column=1, sticky='w')

tk.Button(frame, text="预览效果", command=preview_image, bg="lightgreen").grid(row=5, column=0, pady=10)
tk.Button(frame, text="开始处理", command=run_processing, bg="lightblue").grid(row=5, column=1, pady=10)

preview_label = tk.Label(root)
preview_label.pack(pady=5)

load_config()
root.mainloop()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import ImageTk, Image
import os, json
from ImageBatchProcessor_utils import process_image_v5

CONFIG_FILE = 'ui_config.json'

thumb_cache = {}

# ========================= 配置保存/读取 =========================
def create_ui():
    root = TkinterDnD.Tk()
    root.title("批量图片处理工具 V12")
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10, fill='both', expand=True)

    # Treeview 列定义
    columns = ("path",)
    tk.Label(frame, text="拖放图片或文件夹到下方列表:").grid(row=0, column=0, columnspan=4, sticky='w')
    tree = ttk.Treeview(frame, selectmode='extended', columns=columns)
    tree.heading("#0", text="缩略图")
    tree.heading("path", text="文件路径")
    tree.column("#0", width=60, anchor='center')
    tree.column("path", width=400, anchor='w')
    tree.grid(row=1, column=0, columnspan=4, sticky='nsew')
    ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    xsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscroll=ysb.set, xscroll=xsb.set)
    ysb.grid(row=1, column=4, sticky='ns')
    xsb.grid(row=2, column=0, columnspan=4, sticky='ew')
    tree.drop_target_register(DND_FILES)
    tree.dnd_bind('<<Drop>>', lambda e: drop_files(e, tree))

    # 输出文件夹
    tk.Button(frame, text="输出文件夹", command=lambda: select_output_folder(output_entry)).grid(row=3, column=0)
    output_entry = tk.Entry(frame, width=50)
    output_entry.grid(row=3, column=1, columnspan=3, sticky='we')
    output_entry.drop_target_register(DND_FILES)
    output_entry.dnd_bind('<<Drop>>', lambda e: output_entry.delete(0, tk.END) or output_entry.insert(0, tree.tk.splitlist(e.data)[0]))

    # 参数区域
    flip_var = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="水平翻转", variable=flip_var).grid(row=4, column=0, sticky='w')
    tk.Label(frame, text="噪点强度:").grid(row=4, column=1, sticky='e')
    noise_entry = tk.Entry(frame, width=6)
    noise_entry.insert(0, "2.0")
    noise_entry.grid(row=4, column=2, sticky='w')
    tk.Label(frame, text="旋转最小:").grid(row=5, column=0, sticky='e')
    rot_min_entry = tk.Entry(frame, width=6)
    rot_min_entry.insert(0, "0.5")
    rot_min_entry.grid(row=5, column=1, sticky='w')
    tk.Label(frame, text="旋转最大:").grid(row=5, column=2, sticky='e')
    rot_max_entry = tk.Entry(frame, width=6)
    rot_max_entry.insert(0, "1.5")
    rot_max_entry.grid(row=5, column=3, sticky='w')

    # 手动预览
    show_preview = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="显示缩略图", variable=show_preview).grid(row=6, column=0, sticky='w')
    tk.Button(frame, text="查看预览", command=lambda: preview_image(tree, preview_label, show_preview)).grid(row=6, column=1, sticky='w')

    preview_label = tk.Label(frame)
    preview_label.grid(row=7, column=0, columnspan=4, pady=5)

    # 删除键删除选中项
    tree.bind('<Delete>', lambda e: [tree.delete(i) for i in tree.selection()])

    # 处理按钮
    tk.Button(frame, text="开始处理",
              command=lambda: run_processing(tree, output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry),
              bg='lightblue').grid(row=8, column=0, columnspan=4, pady=10)

    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(1, weight=1)
    load_config(output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry)
    root.mainloop()
    #t
def load_config(output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry):
    # 清空
    for entry, default in [
        (output_entry, ''),
        (noise_entry, '2.0'),
        (rot_min_entry, '0.5'),
        (rot_max_entry, '1.5')
    ]:
        entry.delete(0, tk.END)
        entry.insert(0, default)
    flip_var.set(True)

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                output_entry.delete(0, tk.END)
                output_entry.insert(0, config.get('output_folder', ''))
                flip_var.set(config.get('flip', True))
                noise_entry.delete(0, tk.END)
                noise_entry.insert(0, str(config.get('noise', '2.0')))
                rot_min_entry.delete(0, tk.END)
                rot_min_entry.insert(0, str(config.get('rot_min', '0.5')))
                rot_max_entry.delete(0, tk.END)
                rot_max_entry.insert(0, str(config.get('rot_max', '1.5')))
        except:
            pass

# ========================= TreeView 文件管理 =========================
def get_thumbnail(path):
    if path not in thumb_cache:
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((20, 20))
            thumb_cache[path] = ImageTk.PhotoImage(img)
        except:
            return None
    return thumb_cache[path]

def add_files(tree, files):
    for f in files:
        f = os.path.abspath(f)
        if os.path.isdir(f):
            if not tree.exists(f):
                folder_id = tree.insert('', 'end', iid=f, text=os.path.basename(f), values=(f,))
            else:
                folder_id = f
            # 添加文件
            for img in os.listdir(f):
                full = os.path.join(f, img)
                if full.lower().endswith(('.png', '.jpg', '.jpeg')):
                    if not tree.exists(full):
                        tree.insert(folder_id, 'end', iid=full, text=img, values=(full,), image=get_thumbnail(full))
        else:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not tree.exists(f):
                tree.insert('', 'end', iid=f, text=os.path.basename(f), values=(f,), image=get_thumbnail(f))

def drop_files(event, tree):
    files = tree.tk.splitlist(event.data)
    add_files(tree, files)

def select_output_folder(output_entry):
    folder = filedialog.askdirectory(title="选择输出文件夹")
    if folder:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, folder)

# ========================= 处理功能 =========================
def run_processing(tree, output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry):
    files = []
    for iid in tree.get_children():
        if os.path.isdir(iid):
            for child in tree.get_children(iid):
                files.append(tree.item(child, "values")[0])
        else:
            files.append(tree.item(iid, "values")[0])

    if not files:
        messagebox.showerror("错误", "请选择图片")
        return

    output_dir = output_entry.get()
    if not output_dir:
        messagebox.showerror("错误", "请选择输出文件夹")
        return

    os.makedirs(output_dir, exist_ok=True)
    for img_file in files:
        img_out = process_image_v5(img_file, flip_var.get(),
                                   float(noise_entry.get()), float(rot_min_entry.get()), float(rot_max_entry.get()))
        filename = os.path.basename(img_file)
        img_out.save(os.path.join(output_dir, "mod_" + filename), quality=95)

    save_config(output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry)
    messagebox.showinfo("完成", f"处理完成，结果保存在: {output_dir}")

# ========================= 查看大图 =========================
def show_large_preview(tree):
    sel = tree.selection()
    if not sel:
        return
    path = tree.item(sel[0], "values")[0]
    if not os.path.isfile(path):
        return
    top = tk.Toplevel()
    top.title("图片预览")
    img = Image.open(path).convert("RGB")
    img.thumbnail((800, 800))
    photo = ImageTk.PhotoImage(img)
    lbl = tk.Label(top, image=photo)
    lbl.image = photo
    lbl.pack()

# ========================= UI主界面 =========================
def create_ui():
    root = TkinterDnD.Tk()
    root.title("批量图片处理工具 V13")
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10, fill='both', expand=True)

    # 提示
    tk.Label(frame, text="拖放图片或文件夹到下方列表:").grid(row=0, column=0, columnspan=5, sticky='w')

    # 文件树
    columns = ('fullpath',)
    tree = ttk.Treeview(frame, selectmode='extended', columns=columns, displaycolumns=())
    tree.grid(row=1, column=0, columnspan=5, sticky='nsew')
    ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    xsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscroll=ysb.set, xscroll=xsb.set)
    ysb.grid(row=1, column=5, sticky='ns')
    xsb.grid(row=2, column=0, columnspan=5, sticky='ew')
    tree.drop_target_register(DND_FILES)
    tree.dnd_bind('<<Drop>>', lambda e: drop_files(e, tree))
    # 文件树，增加路径列
    columns = ('fullpath',)
    tree = ttk.Treeview(frame, selectmode='extended', columns=columns, show='headings')
    tree.heading('fullpath', text='文件路径')
    tree.column('fullpath', width=400, anchor='w')
    tree.grid(row=1, column=0, columnspan=5, sticky='nsew')

    # 输出文件夹选择
    tk.Button(frame, text="输出文件夹", command=lambda: select_output_folder(output_entry)).grid(row=3, column=0, padx=5, pady=5)
    output_entry = tk.Entry(frame, width=50)
    output_entry.grid(row=3, column=1, columnspan=4, sticky='we')
    output_entry.drop_target_register(DND_FILES)
    output_entry.dnd_bind('<<Drop>>', lambda e: output_entry.delete(0, tk.END) or output_entry.insert(0, tree.tk.splitlist(e.data)[0]))

    # ===== 参数设置分组框 =====
    param_frame = tk.LabelFrame(frame, text="参数设置", padx=10, pady=5)
    param_frame.grid(row=4, column=0, columnspan=5, pady=10, sticky='we')

    flip_var = tk.BooleanVar(value=True)
    tk.Checkbutton(param_frame, text="水平翻转", variable=flip_var).grid(row=0, column=0, padx=5, pady=5, sticky='w')

    tk.Label(param_frame, text="噪点强度:").grid(row=0, column=1, sticky='e', padx=(10, 2))
    noise_entry = tk.Entry(param_frame, width=8)
    noise_entry.insert(0, "2.0")
    noise_entry.grid(row=0, column=2, padx=5, pady=5)

    tk.Label(param_frame, text="旋转最小:").grid(row=1, column=1, sticky='e', padx=(10, 2))
    rot_min_entry = tk.Entry(param_frame, width=8)
    rot_min_entry.insert(0, "0.5")
    rot_min_entry.grid(row=1, column=2, padx=5, pady=5)

    tk.Label(param_frame, text="旋转最大:").grid(row=1, column=3, sticky='e', padx=(10, 2))
    rot_max_entry = tk.Entry(param_frame, width=8)
    rot_max_entry.insert(0, "1.5")
    rot_max_entry.grid(row=1, column=4, padx=5, pady=5)

    # 预览选项
    show_preview = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="显示缩略图", variable=show_preview).grid(row=5, column=0, sticky='w', padx=5)

    # 缩略图区域 + 查看按钮
    preview_frame = tk.Frame(frame)
    preview_frame.grid(row=6, column=0, columnspan=5, pady=5, sticky='we')
    preview_label = tk.Label(preview_frame)
    preview_label.pack(side='left', padx=5)
    tk.Button(preview_frame, text="查看大图", command=lambda: preview_image(tree, preview_label, show_preview)).pack(side='left', padx=10)

    # 绑定事件
    tree.bind('<<TreeviewSelect>>', lambda e: preview_image(tree, preview_label, show_preview))
    tree.bind('<Delete>', lambda e: [tree.delete(i) for i in tree.selection()])

    # 开始处理按钮
    tk.Button(frame, text="开始处理",
              command=lambda: run_processing(tree, output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry),
              bg='lightblue').grid(row=7, column=0, columnspan=5, pady=10)

    # 布局权重
    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(1, weight=1)

    # 加载配置
    load_config(output_entry, flip_var, noise_entry, rot_min_entry, rot_max_entry)

    root.mainloop()


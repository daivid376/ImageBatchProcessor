import tkinter as tk
from ImageBatchProcessor_ui import create_ui

if __name__ == "__main__":
    # 如果已有窗口实例，先销毁
    if tk._default_root is not None:
        try:
            tk._default_root.destroy()
        except:
            pass

    # 创建新窗口
    create_ui()

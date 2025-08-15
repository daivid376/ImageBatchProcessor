import sys,os  # noqa: E401
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ImageBatchProcessor_model import ImageBatchModel
from src.ImageBatchProcessor_presenter import ImageBatchPresenter
from src.comfyui_api.comfyui_presnter import ComfyUIPresenter
from src.ui.ImageBatchProcessor_view import ImageBatchView
sys.path.append(os.path.dirname(__file__))
from src import __version__ 
from src import get_resource_path
import winreg
def add_proxy_override(new_entry: str):
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    reg_value = "ProxyOverride"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
        current_value, _ = winreg.QueryValueEx(key, reg_value)
        winreg.CloseKey(key)
    except FileNotFoundError:
        current_value = ""

    if current_value and new_entry.lower() in current_value.lower():
        print(f"已存在: {new_entry}，无需添加")
        return

    updated_value = (current_value + ";" + new_entry) if current_value else new_entry

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, reg_value, 0, winreg.REG_SZ, updated_value)
    winreg.CloseKey(key)
    print(f"已追加: {new_entry}")
    
if __name__ == "__main__":
    add_proxy_override("100.83.*")
    app = QApplication(sys.argv)
    app.setApplicationName(f"ImageBatchProcessor v{__version__}")
    base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    icon_path = os.path.join(base_dir, "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    try:
        qss_path = get_resource_path("src/style.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print("QSS 加载失败:", e)
    # 加载 QSS 样式

        
    model = ImageBatchModel()
    view = ImageBatchView()
    main_presenter = ImageBatchPresenter(model, view)
    comfy_view = view.comfy_section

    comfy_presenter = ComfyUIPresenter(model, comfy_view) 
    main_presenter.set_comfy_presenter(comfy_presenter)
    # 让 view 主动发出初始状态
    view.emit_initial_signals()
    view.show()
    sys.exit(app.exec())
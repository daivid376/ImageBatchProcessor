@echo off
chcp 65001 >nul
echo ✅ 正在用 GUI 的 ComfyUI 启动 API 模式...

:: 1. 进入 ComfyUI 根目录
cd /d C:\Users\admin\Documents\ComfyUI

:: 2. 激活 GUI 的 venv
call ".venv\Scripts\activate"

:: 3. 升级 pip
python -m pip install --upgrade pip

:: 4. 安装 ComfyUI 主依赖
if exist requirements.txt (
    echo 📦 安装 ComfyUI 主依赖...
    pip install -r requirements.txt --no-warn-script-location
)

:: 5. 安装 custom_nodes 依赖（只看第一层文件夹）
for /d %%D in (custom_nodes\*) do (
    if exist "%%D\requirements.txt" (
        echo 📦 安装依赖: %%D\requirements.txt
        pip install -r "%%D\requirements.txt" --no-warn-script-location
    )
)

:: 6. 启动 ComfyUI API（可改端口）
python main.py --listen 0.0.0.0 --port 8188

pause

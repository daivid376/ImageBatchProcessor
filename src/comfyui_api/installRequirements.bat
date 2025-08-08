@echo off
chcp 65001 >nul
echo 📦 开始安装 ComfyUI 依赖...

:: 1. 进入 ComfyUI 根目录
cd /d C:\Users\admin\Documents\ComfyUI

:: 2. 激活 venv
call .venv\Scripts\activate

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

echo ✅ 依赖安装完成
pause
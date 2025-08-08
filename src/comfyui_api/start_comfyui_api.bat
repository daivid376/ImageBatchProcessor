@echo off
chcp 65001 >nul
echo 🚀 正在启动 ComfyUI API 模式...

:: 1. 进入 ComfyUI 根目录
cd /d C:\Users\admin\Documents\ComfyUI

:: 2. 激活 venv
call .venv\Scripts\activate

:: 3. 启动 ComfyUI API（可改端口）
python main.py --listen 0.0.0.0 --port 8188

pause
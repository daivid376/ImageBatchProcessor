@echo off
chcp 65001 >nul
REM ==========================================
REM  Build script for ImageBatchProcessor
REM  Author: EleFlyStudio
REM ==========================================

:: 配置变量
set ENTRY_FILE=src\ImageBatchProcessor_main.py
set EXE_NAME=ImageBatchProcessor

echo [1/4] 检查 Python 环境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python 未安装或未加入环境变量。
    pause
    exit /b 1
)

echo [2/4] 检查 PyInstaller...
python -c "import PyInstaller" >nul 2>nul
if %errorlevel% neq 0 (
    echo 未检测到 PyInstaller，正在安装...
    pip install pyinstaller
)

echo [3/4] 清理旧构建文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist %EXE_NAME%.spec del /q %EXE_NAME%.spec

echo [4/4] 开始打包 (单文件模式)...
python -m PyInstaller ^
 --noconfirm ^
 --onefile ^
 --windowed ^
 --name "%EXE_NAME%" ^
 src\\ImageBatchProcessor_main.py

echo.
echo ==========================================
echo  构建完成！
echo  可执行文件路径: dist\%EXE_NAME%.exe
echo ==========================================
pause

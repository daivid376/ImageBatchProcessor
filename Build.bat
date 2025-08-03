@echo off
REM ==============================================
REM   Build Script for Image Batch Processor V5
REM   使用 PyInstaller 打包为单独可执行文件 (.exe)
REM ==============================================

REM 切换到当前脚本所在目录
cd /d %~dp0

REM 清理上一次打包生成的文件
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
del /q *.spec

REM 使用 PyInstaller 打包 (模块名必须大写)
python -m PyInstaller --noconfirm --onefile --windowed "anti_pHash.py"

REM 提示完成
echo.
echo ==============================================
echo 打包完成，文件已生成在 dist 文件夹中
echo ==============================================
pause

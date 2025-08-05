@echo off
setlocal
chcp 65001 >nul

set EXE_NAME=ImageBatchProcessor.exe
set MAIN_SCRIPT=src\ImageBatchProcessor_main.py
set ICON_FILE=src\resources\app_icon.ico
set OUTPUT_DIR=release

REM 删除旧的输出目录，但保留缓存加速打包
rmdir /s /q dist %OUTPUT_DIR% >nul 2>nul

echo === [Step 1] 使用 PyInstaller 打包 ===
pyinstaller ^
 --noconfirm ^
 --onefile ^
 --windowed ^
 --name "%EXE_NAME%" ^
 --icon "%ICON_FILE%" ^
 --add-data "src\style.qss;src" ^
 --add-data "src\resources\app_icon.ico;resources" ^
 "%MAIN_SCRIPT%"

echo === [Step 2] 将 exe 移动到 %OUTPUT_DIR% 目录 ===
mkdir "%OUTPUT_DIR%"
move /y "dist\%EXE_NAME%" "%OUTPUT_DIR%\" >nul

echo ✅ 打包完成: %OUTPUT_DIR%\%EXE_NAME%
pause

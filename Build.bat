@echo off
setlocal
chcp 65001 >nul

set EXE_NAME=ImageBatchProcessor.exe
set MAIN_SCRIPT=src\ImageBatchProcessor_main.py
set ICON_FILE=src\resources\app_icon.ico
set OUTPUT_DIR=release

echo === [Step 1] 使用 PyInstaller 打包 ===
pyinstaller ^
 --noconfirm ^
 --onefile ^
 --windowed ^
 --name "%EXE_NAME%" ^
 --icon "%ICON_FILE%" ^
 --add-data "src\style.qss;src" ^
 --add-data "src\resources;resources" ^
 "%MAIN_SCRIPT%"

echo === [Step 2] 将 exe 复制到 %OUTPUT_DIR% 目录 ===
mkdir "%OUTPUT_DIR%" >nul 2>nul
copy /y "dist\%EXE_NAME%" "%OUTPUT_DIR%\" >nul

echo ✅ 打包完成: %OUTPUT_DIR%\%EXE_NAME%
pause

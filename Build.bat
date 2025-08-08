@echo off
setlocal
chcp 65001 >nul

:: === 读取版本号并清理 ===
for /f "tokens=2 delims== " %%a in ('findstr "__version__" src\__init__.py') do (
    set "version=%%a"
)
set "version=%version:"=%"
set "version=%version: =%"

set "EXE_NAME=ImageBatchProcessor.exe"
set "MAIN_SCRIPT=src\ImageBatchProcessor_main.py"
set "ICON_FILE=src\resources\app_icon.ico"
set "OUTPUT_DIR=dist\v%version%"

REM === 删除旧的输出文件夹 ===
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"

echo === [Step 1] 使用 PyInstaller 打包 ===
pyinstaller ^
 --noconfirm ^
 --onefile ^
 --windowed ^
 --name "%EXE_NAME%" ^
 --icon "%ICON_FILE%" ^
 --add-data "src\style.qss;src" ^
 --add-data "src\resources\app_icon.ico;resources" ^
 --add-data "Changelog.md;." ^
 --add-data "comfyui_assets;comfyui_assets" ^
 "%MAIN_SCRIPT%"

echo === [Step 2] 版本目录移动 ===
mkdir "%OUTPUT_DIR%"
move /y "dist\%EXE_NAME%" "%OUTPUT_DIR%\"

echo ✅ 打包完成: %OUTPUT_DIR%\%EXE_NAME%
pause

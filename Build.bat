@echo off
setlocal
chcp 65001 >nul

:: 读取版本号
for /f "tokens=2 delims==" %%a in ('findstr "__version__" src\__init__.py') do (
    set version=%%~a
)
:: 去掉引号
set version=%version:"=%

set EXE_NAME=ImageBatchProcessor.exe
set MAIN_SCRIPT=src\ImageBatchProcessor_main.py
set ICON_FILE=src\resources\app_icon.ico
set OUTPUT_DIR=dist\v%version%

REM 删除旧的输出文件夹
rmdir /s /q "%OUTPUT_DIR%" >nul 2>nul

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
 "%MAIN_SCRIPT%"

echo === [Step 2] 版本目录移动 ===
mkdir "%OUTPUT_DIR%"
move /y "dist\%EXE_NAME%" "%OUTPUT_DIR%\" >nul

echo ✅ 打包完成: %OUTPUT_DIR%\%EXE_NAME%
pause

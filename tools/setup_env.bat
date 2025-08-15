@echo off
setlocal

:: ===== 配置 =====
set PROJECT_NAME=ImageBatchProcessor
set PROJECT_DIR=%~dp0\..
set VENV_DIR=C:\venvs\%PROJECT_NAME%
set PYTHON_EXE=python

echo [STEP 1] 创建或使用虚拟环境: %VENV_DIR%
if not exist "%VENV_DIR%" (
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
) else (
    echo [INFO] 虚拟环境已存在
)

echo [STEP 2] 激活虚拟环境
call "%VENV_DIR%\Scripts\activate"

echo [STEP 3] 从当前 Python 全局环境导出依赖（只锁定大版本）
%PYTHON_EXE% -m pip list --format=freeze | powershell -Command ^
    "$input | ForEach-Object {if ($_ -match '^(?<name>[^=]+)==(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)$') {'${matches['name']}>=${matches['major']}.${matches['minor']}' } else { $_ }} " > "%PROJECT_DIR%\requirements.txt"

echo [STEP 4] 安装依赖到虚拟环境
pip install -r "%PROJECT_DIR%\requirements.txt"

echo.
echo [NEXT STEP] 在 VSCode 按 Ctrl+Shift+P，选择 Python: Select Interpreter
echo            选择: %VENV_DIR%\Scripts\python.exe
echo.
pause
endlocal

@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "NEW_ENTRY=100.83.*"
set "REG_PATH=HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
set "REG_VALUE=ProxyOverride"

for /f "tokens=2,* skip=2" %%A in ('reg query "%REG_PATH%" /v "%REG_VALUE%" 2^>nul') do (
    set "CURRENT=%%B"
)

if "!CURRENT!"=="" (
    reg add "%REG_PATH%" /v "%REG_VALUE%" /t REG_SZ /d "!NEW_ENTRY!" /f >nul
    echo 已添加: !NEW_ENTRY!
    goto :eof
)

REM ★ 改动1：给两端加分号，避免部分匹配
set "CHECK=;!CURRENT!;"
echo(!CHECK! | find /i ";!NEW_ENTRY!;" >nul
if !errorlevel! == 0 (
    echo 已存在: !NEW_ENTRY! ，无需添加
) else (
    REM 去掉末尾多余分号
    set "TEMP=!CURRENT!"
    if "!TEMP:~-1!"==";" set "TEMP=!TEMP:~0,-1!"
    set "UPDATED=!TEMP!;!NEW_ENTRY!"
    reg add "%REG_PATH%" /v "%REG_VALUE%" /t REG_SZ /d "!UPDATED!" /f >nul
    echo 已追加: !NEW_ENTRY!
)

endlocal

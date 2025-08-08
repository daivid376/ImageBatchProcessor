@echo off
chcp 65001 >nul
echo === 应用 .gitignore 规则，移除已跟踪但应忽略的文件 ===

REM 确保在项目根目录执行
echo 当前目录: %cd%
pause

REM 移除所有已跟踪但被 .gitignore 忽略的文件（仅移除追踪，不删除本地文件）
git rm -r --cached .

REM 重新添加所有需要追踪的文件
git add .

REM 提交更改
git commit -m "Apply updated .gitignore rules"

echo === 完成！.gitignore 规则已生效 ===
pause

@echo off
chcp 65001
title 财务收据系统

echo ==================================================
echo    财务收据自动生成系统
echo ==================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8或以上版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 正在检查依赖包...

:: 安装依赖
echo [2/4] 正在安装依赖包（首次运行需要几分钟）...
python -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，尝试继续...
)

:: 初始化数据库
echo [3/4] 正在初始化数据库...
python init_db.py

:: 启动应用
echo [4/4] 正在启动应用...
echo.
echo ✓ 启动成功！
echo.
echo 请在浏览器中打开: http://localhost:5000
echo 按 Ctrl+C 停止应用
echo.

python app.py

pause

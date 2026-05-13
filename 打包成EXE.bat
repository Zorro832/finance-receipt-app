@echo off
chcp 65001
title 财务收据系统 - Windows打包工具

echo ==================================================
echo    财务收据系统 - 创建独立EXE文件
echo ==================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8或以上版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/5] Python已安装
echo.

:: 安装PyInstaller
echo [2/5] 正在安装PyInstaller...
python -m pip install -q pyinstaller
if %errorlevel% neq 0 (
    echo [错误] PyInstaller安装失败
    pause
    exit /b 1
)

echo [3/5] PyInstaller已安装
echo.

:: 安装依赖
echo [4/5] 正在安装项目依赖...
python -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，尝试继续...
)

echo [5/5] 依赖安装完成
echo.

:: 执行打包
echo 正在创建独立EXE文件...
echo 这可能需要几分钟，请耐心等待...
echo.

pyinstaller --onefile ^
           --noconsole ^
           --name "财务收据系统" ^
           --add-data "templates;templates" ^
           --add-data "static;static" ^
           --hidden-import "xhtml2pdf" ^
           --hidden-import "database" ^
           --hidden-import "pdf_generator" ^
           app.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ==================================================
echo ✓ EXE文件创建成功！
echo.
echo 文件位置: dist\财务收据系统.exe
echo.
echo 你可以把这个EXE文件发给别人：
echo   1. 别人下载后双击就能用
echo   2. 不需要安装Python
echo   3. 不需要安装任何依赖
echo.
echo ==================================================
echo.

pause

@echo off
chcp 65001
title 财务收据系统 - 打包工具

echo ==================================================
echo    财务收据系统 - 创建发布包
echo ==================================================
echo.

:: 设置变量
set APP_NAME=财务收据系统
set VERSION=1.0
set OUTPUT_FILE=%APP_NAME%_v%VERSION%.zip

:: 检查必要文件
echo [1/5] 检查文件...
if not exist "app.py" (
    echo [错误] 未找到 app.py！
    pause
    exit /b 1
)
if not exist "database.py" (
    echo [错误] 未找到 database.py！
    pause
    exit /b 1
)
if not exist "pdf_generator.py" (
    echo [错误] 未找到 pdf_generator.py！
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt！
    pause
    exit /b 1
)
if not exist "templates\" (
    echo [错误] 未找到 templates 文件夹！
    pause
    exit /b 1
)

echo ✓ 文件检查通过
echo.

:: 创建临时文件夹
echo [2/5] 创建发布文件夹...
if exist "dist_temp" rmdir /s /q "dist_temp"
mkdir "dist_temp\%APP_NAME%"

:: 复制文件
echo [3/5] 复制文件...
copy "app.py" "dist_temp\%APP_NAME%\"
copy "database.py" "dist_temp\%APP_NAME%\"
copy "pdf_generator.py" "dist_temp\%APP_NAME%\"
copy "init_db.py" "dist_temp\%APP_NAME%\"
copy "requirements.txt" "dist_temp\%APP_NAME%\"
copy "启动.bat" "dist_temp\%APP_NAME%\"
copy "启动.sh" "dist_temp\%APP_NAME%\"
copy "使用说明.txt" "dist_temp\%APP_NAME%\"
xcopy /E /I "templates" "dist_temp\%APP_NAME%\templates"
if exist "static" xcopy /E /I "static" "dist_temp\%APP_NAME%\static"

:: 创建示例数据文件夹
mkdir "dist_temp\%APP_NAME%\instance"

echo ✓ 文件复制完成
echo.

:: 压缩文件
echo [4/5] 正在压缩文件...
if exist "%OUTPUT_FILE%" del "%OUTPUT_FILE%"

:: 尝试使用PowerShell压缩
powershell -Command "Compress-Archive -Path 'dist_temp\%APP_NAME%' -DestinationPath '%OUTPUT_FILE%'"

if %errorlevel% neq 0 (
    echo [警告] PowerShell压缩失败，尝试使用Python压缩...
    python -c "import zipfile; z = zipfile.ZipFile('%OUTPUT_FILE%', 'w', zipfile.ZIP_DEFLATED); import os; [z.write(os.path.join(r, f) for r, d, fs in os.walk('dist_temp/%APP_NAME%') for f in fs]; z.close()"
)

echo ✓ 压缩完成
echo.

:: 清理临时文件
echo [5/5] 清理临时文件...
rmdir /s /q "dist_temp"

echo.
echo ==================================================
echo ✓ 发布包创建成功！
echo.
echo 文件名: %OUTPUT_FILE%
echo.
echo 你可以把这个文件发给别人：
echo  1. 别人下载后解压缩
echo  2. 双击 "启动.bat"
echo  3. 浏览器打开 http://localhost:5000
echo.
echo ==================================================
echo.

pause

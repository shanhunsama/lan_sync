@echo off
echo LAN同步工具打包脚本
echo ========================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 安装PyInstaller
echo 正在安装PyInstaller...
pip install pyinstaller

REM 运行打包脚本
echo 开始打包程序...
python build.py

echo.
echo 打包完成！
echo 生成的可执行文件在 dist 目录下
echo.
pause
@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 学习监督机器人

echo.
echo ================================
echo   学习监督机器人 v2.0
echo ================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

:: Create data/logs dirs
if not exist data mkdir data
if not exist logs mkdir logs

:: Check .env
if not exist .env (
    echo [WARN] .env not found, using defaults
)

echo [INFO] Python:
python --version 2>&1
echo [INFO] Mode: mock
echo.

echo ================================
echo   [1] 模拟测试模式 (mock)
echo   [2] 网页仪表盘
echo   [3] 文件桥接模式
echo   [4] WeiLink模式 (需扫码)
echo   [0] 退出
echo ================================
echo.
set /p choice="选择模式: "

if "%choice%"=="1" goto mock
if "%choice%"=="2" goto web
if "%choice%"=="3" goto bridge
if "%choice%"=="4" goto weilink
if "%choice%"=="0" goto end
goto end

:mock
echo.
echo 启动模拟测试模式...
echo 按 Ctrl+C 停止
echo.
python main.py
goto end

:web
echo.
echo 启动网页仪表盘: http://localhost:8000/dashboard
echo.
python main.py --web
goto end

:bridge
echo.
echo 启动文件桥接模式...
echo 输入: bridge_in.txt  ^|  输出: bridge_out.txt
echo.
python wechat_gateway/file_bridge.py
goto end

:weilink
echo.
echo 启动 WeiLink 模式...
echo 请准备微信小号扫码
echo.
set WECHAT_GATEWAY_MODE=weilink
python main.py
goto end

:end

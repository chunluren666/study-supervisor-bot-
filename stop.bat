@echo off
chcp 65001 >nul
echo Stopping bot processes...

:: Kill python processes running main.py or the bot
for /f "tokens=1,2" %%a in ('tasklist /fi "IMAGENAME eq python.exe" /fo csv ^| findstr /i "main.py"') do (
    echo Stopping PID: %%b
    taskkill /PID %%b /F >nul 2>&1
)

for /f "tokens=1,2" %%a in ('tasklist /fi "IMAGENAME eq python.exe" /fo csv ^| findstr /i "file_bridge"') do (
    echo Stopping PID: %%b
    taskkill /PID %%b /F >nul 2>&1
)

echo Done.
pause

@echo off
setlocal
chcp 65001 >nul
python "%~dp0initialize-robot.py" %*
set "D1_INIT_EXIT=%errorlevel%"
echo.
if not "%D1_INIT_EXIT%"=="0" echo Initialization did not complete. Read the message above.
pause
exit /b %D1_INIT_EXIT%

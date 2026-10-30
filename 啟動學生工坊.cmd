@echo off
chcp 65001 >nul
setlocal
set "D1_APP=%~dp0output\D1彩色課程套件\學生工具\D1學生工坊\D1學生工坊.exe"
if not exist "%D1_APP%" (
  echo Application missing. Extract the complete delivery package into output first.
  pause
  exit /b 1
)
start "" /D "%~dp0output\D1彩色課程套件\學生工具\D1學生工坊" "%D1_APP%"

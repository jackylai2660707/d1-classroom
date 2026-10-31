@echo off
call "%~dp0scripts\dev-local.cmd" %*
if errorlevel 1 pause
exit /b %errorlevel%

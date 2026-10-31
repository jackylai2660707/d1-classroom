@echo off
call "%~dp0scripts\initialize-robot.cmd" %*
exit /b %errorlevel%

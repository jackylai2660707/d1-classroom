@echo off
setlocal
for %%R in ("%~dp0..") do set "D1_ROOT=%%~fR"
set "D1_NODE=%D1_ROOT%\local\tools\node-v24.18.0-win-x64"
set "D1_PNPM=%D1_ROOT%\local\tools\pnpm\node_modules\pnpm\bin\pnpm.cjs"
if not exist "%D1_NODE%\node.exe" goto missing
if not exist "%D1_PNPM%" goto missing
set "PATH=%D1_NODE%;%D1_ROOT%\local\tools\pnpm\node_modules\.bin;%D1_ROOT%\local\tools\gh\bin;%PATH%"
set "D1_PLAYWRIGHT=%D1_ROOT%\local\test-tools\node_modules\playwright"
set "ELECTRON_RUN_AS_NODE="
cd /d "%D1_ROOT%\d1-classroom"
if "%~1"=="--shell" goto shell
if "%~1"=="--check" goto check
if "%~1"=="--debug" goto debug
if not "%~1"=="" goto usage
node "%D1_PNPM%" run dev
exit /b %errorlevel%
:debug
node "%D1_PNPM%" run dev:debug
exit /b %errorlevel%
:shell
set "PROMPT=[D1 x64] $P$G"
%ComSpec% /k
exit /b %errorlevel%
:check
node -p "process.version + ' ' + process.arch"
if errorlevel 1 exit /b 1
node "%D1_PNPM%" --version
exit /b %errorlevel%
:missing
echo Local x64 tools are missing. See the ARM workstation preparation guide in docs/.
exit /b 1
:usage
echo Usage: scripts\dev-local.cmd [--debug ^| --shell ^| --check]
exit /b 1

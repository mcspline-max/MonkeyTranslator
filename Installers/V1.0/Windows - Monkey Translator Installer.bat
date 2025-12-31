@echo off
setlocal EnableDelayedExpansion

:: =============================================================
:: CONFIGURATION
:: =============================================================
set "GITHUB_URL=https://raw.githubusercontent.com/mcspline-max/MonkeyTranslator/main/installer.py"
:: =============================================================

title MonkeyTranslator Installer
cls

:: -------------------------------------------------------------
:: 1. Check for Administrator Privileges
:: -------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :CHECK_PYTHON
) else (
    echo.
    echo =======================================================
    echo      MonkeyTranslator Web Installer
    echo =======================================================
    echo.
    echo [!] Administrator privileges are required to install
    echo     plugins into the DaVinci Resolve folder.
    echo.
    echo     Requesting permission...
    echo     (Please click 'Yes' in the Windows security pop-up)
    echo.
    
    :: Self-elevate the script using PowerShell
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

:CHECK_PYTHON
cls
echo =======================================================
echo      MonkeyTranslator Web Installer
echo =======================================================
echo.

:: -------------------------------------------------------------
:: 2. Check if Python is installed
:: -------------------------------------------------------------
echo [1/4] Checking for Python...

:: Try 'python' command
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :DOWNLOAD
)

:: Try 'py' launcher (Common on Windows)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :DOWNLOAD
)

:: If we get here, Python is missing
echo.
echo [ERROR] Python is NOT installed or not found in PATH.
echo.
echo Please install Python 3.10+ from python.org before running this installer.
echo (Make sure to check "Add Python to PATH" during installation)
echo.
pause
exit /b

:DOWNLOAD
echo       Found: !PY_CMD!
echo.

:: -------------------------------------------------------------
:: 3. Download the Installer Logic from GitHub
:: -------------------------------------------------------------
echo [2/4] Fetching installer logic from GitHub...
set "TEMP_FILE=%TEMP%\monkey_installer.py"

:: Delete old temp file if it exists
if exist "%TEMP_FILE%" del "%TEMP_FILE%"

:: Use PowerShell to download (Works on Windows 10/11)
powershell -Command "Invoke-WebRequest -Uri '%GITHUB_URL%' -OutFile '%TEMP_FILE%'"

if not exist "%TEMP_FILE%" (
    echo.
    echo [ERROR] Could not download installer. 
    echo Please check your internet connection or firewall.
    pause
    exit /b
)

:: -------------------------------------------------------------
:: 4. Run the Python Installer
:: -------------------------------------------------------------
echo.
echo [3/4] Starting Python Installer...
echo -------------------------------------------------------

:: Run using the detected command (python or py)
!PY_CMD! "%TEMP_FILE%"

:: -------------------------------------------------------------
:: 5. Clean up
:: -------------------------------------------------------------
if exist "%TEMP_FILE%" del "%TEMP_FILE%"

echo.
echo -------------------------------------------------------
echo [4/4] Process finished.
echo.
echo If you saw "INSTALLATION SUCCESSFUL" above, you can close this window.
pause
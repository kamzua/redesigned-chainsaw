@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==========================================
echo AUDITION SWEET DREAMS - Windows EXE Builder
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher "py" not found.
    echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
    echo During installation, enable "Add Python to PATH".
    pause
    exit /b 1
)

py -m pip install --upgrade pip
if errorlevel 1 goto :failed

py -m pip install -r requirements.txt
if errorlevel 1 goto :failed

py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "AuditionSweetDreams" ^
  --collect-all selenium ^
  audition_sweet_dreams.py
if errorlevel 1 goto :failed

echo.
echo BUILD SUCCESSFUL
echo EXE location: %~dp0dist\AuditionSweetDreams.exe
echo.
echo Copy the EXE to a writable folder. Keep the settings/database files
echo created beside it so your configuration and history can persist.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Read the error messages above.
pause
exit /b 1

@echo off
REM Xamlysis - start the Django development server.
REM Usage:  run.bat         (defaults to port 8000)
REM         run.bat 8080    (custom port)

setlocal
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo No virtual environment found at .venv - creating one...
    python -m venv .venv
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install Django djangorestframework Pillow
)

echo Xamlysis - Django development server
echo http://127.0.0.1:%PORT%/   (Ctrl+C to stop)
echo.

"%PY%" manage.py runserver %PORT%
endlocal

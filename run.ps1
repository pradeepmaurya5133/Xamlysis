# Xamlysis - start the Django development server.
# Usage:  .\run.ps1          (defaults to port 8000)
#         .\run.ps1 8080     (custom port)

param([string]$Port = "8000")

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "No virtual environment found at .venv" -ForegroundColor Yellow
    Write-Host "Creating one now..." -ForegroundColor Yellow
    python -m venv .venv
    & $python -m pip install --upgrade pip
    & $python -m pip install Django djangorestframework Pillow
}

Write-Host "Xamlysis - Django development server" -ForegroundColor Cyan
Write-Host "http://127.0.0.1:$Port/   (Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""

& $python manage.py runserver $Port

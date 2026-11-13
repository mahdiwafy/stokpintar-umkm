@echo off
setlocal

cd /d "%~dp0"
set PORT=8090
set HOST=127.0.0.1

echo ======================================================
echo    StokPintar UMKM - Auto Setup & Launch (Windows)
echo ======================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python tidak ditemukan di PATH. Pastikan Python 3.10+ terinstall.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Membuat virtual environment (.venv)...
    python -m venv .venv
)

echo [2/3] Mengaktifkan virtual environment...
call .venv\Scripts\activate.bat

python -c "import fastapi, uvicorn, pydantic, httpx" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [3/3] Menginstall dependensi dari requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo [3/3] Seluruh dependensi sudah siap.
)

echo.
echo ======================================================
echo  Aplikasi Web : http://localhost:%PORT%
echo  Swagger API  : http://localhost:%PORT%/docs
echo  Database     : data\stok_umkm.db (Auto-created & Seeded)
echo ======================================================
echo.

python -m uvicorn app.main:app --host %HOST% --port %PORT% --reload
pause

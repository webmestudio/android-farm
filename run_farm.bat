@echo off
title Phone Farm Dashboard (Zero-Lag)
cd /d "%~dp0"

echo ========================================================
echo             STARTING PHONE FARM DASHBOARD
echo        (Hardware Acceleration Zero-Lag Engine)
echo ========================================================
echo.

python src\main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Gagal menjalankan Phone Farm Dashboard.
    echo Pastikan Python 3 sudah terinstall di sistem Windows Anda.
    echo.
    pause
)

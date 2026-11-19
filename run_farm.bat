@echo off
title Phone Farm Dashboard (Zero-Lag)
cd /d "%~dp0"

echo ========================================================
echo             STARTING PHONE FARM DASHBOARD
echo        (Hardware Acceleration Zero-Lag Engine)
echo ========================================================
echo.

:: 1. Prioritaskan eksekusi Python jika tersedia
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Menjalankan via Python Engine...
    python src\main.py
    if %errorlevel% equ 0 goto :eof
)

:: 2. Fallback ke Portable EXE jika Python tidak ada atau gagal
if exist "dist\PhoneFarmDashboard.exe" (
    echo Menjalankan Portable EXE (dist\PhoneFarmDashboard.exe)...
    start "" "dist\PhoneFarmDashboard.exe"
    goto :eof
)

if exist "PhoneFarmDashboard.exe" (
    echo Menjalankan Portable EXE (PhoneFarmDashboard.exe)...
    start "" "PhoneFarmDashboard.exe"
    goto :eof
)

echo.
echo [ERROR] Gagal menjalankan Phone Farm Dashboard.
echo Silakan pastikan Python 3 terinstall atau jalankan build_exe.bat terlebih dahulu.
echo.
pause

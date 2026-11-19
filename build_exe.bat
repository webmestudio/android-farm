@echo off
title Build Portable EXE - Phone Farm Dashboard
cd /d "%~dp0"

echo ================================================================
echo         BUILD PORTABLE EXE - PHONE FARM DASHBOARD
echo ================================================================
echo.

:: 1. Cek Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem PATH!
    echo Silakan install Python 3 terlebih dahulu.
    echo.
    pause
    exit /b 1
)

:: 2. Cek apakah PhoneFarmDashboard.exe sedang berjalan
tasklist /fi "imagename eq PhoneFarmDashboard.exe" 2>nul | findstr /i "PhoneFarmDashboard.exe" >nul
if %errorlevel% equ 0 (
    echo [PERINGATAN] Aplikasi PhoneFarmDashboard.exe sedang berjalan!
    echo Menutup proses PhoneFarmDashboard.exe yang aktif agar file dist tidak terkunci...
    taskkill /f /im PhoneFarmDashboard.exe >nul 2>nul
    timeout /t 1 /nobreak >nul
)

:: 3. Cek PyInstaller & Pillow
echo [1/4] Memeriksa modul PyInstaller dan Pillow...
python -c "import PyInstaller, PIL" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Menginstall dependensi build: pyinstaller dan pillow...
    python -m pip install pyinstaller pillow
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal menginstall dependensi build!
        pause
        exit /b 1
    )
)

:: 4. Generate icon jika belum ada
echo [2/4] Memeriksa icon aplikasi: app.ico...
if not exist "app.ico" goto :generate_ico
goto :after_ico

:generate_ico
echo [INFO] Mengenerate app.ico dari bin\scrcpy.png...
python -c "from PIL import Image; img = Image.open('bin/scrcpy.png'); img.save('app.ico', format='ICO', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])"

:after_ico
:: 5. Kompilasi dengan PyInstaller
echo [3/4] Mengompilasi PhoneFarmDashboard.exe (Onefile + Standalone Binaries)...
python -m PyInstaller --clean PhoneFarmDashboard.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Kompilasi gagal! Silakan cek log di atas.
    pause
    exit /b 1
)

:: 6. Selesai
echo.
echo ================================================================
echo [SUKSES] Portable EXE berhasil dibuat!
echo Lokasi file: dist\PhoneFarmDashboard.exe
echo ================================================================
echo.
echo Anda dapat menjalankan file dist\PhoneFarmDashboard.exe langsung
echo di komputer Windows mana saja tanpa perlu menginstall Python!
echo.
pause

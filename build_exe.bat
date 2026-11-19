@echo off
title Build Portable EXE - Phone Farm Dashboard
cd /d "%~dp0"

echo ================================================================
echo         BUILD PORTABLE EXE - PHONE FARM DASHBOARD
echo ================================================================
echo.

:: 1. Cek Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di sistem PATH!
    echo Silakan install Python 3 terlebih dahulu.
    echo.
    pause
    exit /b 1
)

:: 2. Cek PyInstaller & Pillow
echo [1/4] Memeriksa modul PyInstaller dan Pillow...
python -c "import PyInstaller, PIL" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Menginstall dependensi build (pyinstaller, pillow)...
    pip install pyinstaller pillow
    if errorlevel 1 (
        echo [ERROR] Gagal menginstall dependensi build!
        pause
        exit /b 1
    )
)

:: 3. Generate icon jika belum ada
echo [2/4] Memeriksa icon aplikasi (app.ico)...
if not exist "app.ico" (
    echo [INFO] Mengenerate app.ico dari bin\scrcpy.png...
    python -c "from PIL import Image; img = Image.open('bin/scrcpy.png'); img.save('app.ico', format='ICO', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])"
)

:: 4. Kompilasi dengan PyInstaller
echo [3/4] Mengompilasi PhoneFarmDashboard.exe (Onefile + Standalone Binaries)...
pyinstaller --clean PhoneFarmDashboard.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Kompilasi gagal! Silakan cek log di atas.
    pause
    exit /b 1
)

:: 5. Selesai
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

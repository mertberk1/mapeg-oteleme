@echo off
chcp 65001 >nul
title MAPEG Oteleme - EXE Olusturucu

echo.
echo  ============================================
echo   MAPEG Oteleme - EXE Olusturucu
echo  ============================================
echo.
echo  Bu dosya tek seferlik calistirilir.
echo  Python yükleyip .exe olusturur.
echo.

REM Check if Python exists
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python bulunamadi!
    echo.
    echo  Python indirmek icin:
    echo  https://www.python.org/downloads/
    echo.
    echo  Kurulumda "Add Python to PATH" secenegini isaretleyin.
    echo.
    pause
    exit /b 1
)

echo  [1/3] PyInstaller yukleniyor...
pip install pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] PyInstaller yuklenemedi!
    pause
    exit /b 1
)
echo        Tamam.

echo  [2/3] EXE olusturuluyor...
echo        (Bu islem 1-2 dakika surebilir)
pyinstaller --onefile --windowed --name "MAPEG_Oteleme" --clean MAPEG_Oteleme.py >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] EXE olusturulamadi!
    pause
    exit /b 1
)
echo        Tamam.

echo  [3/3] Temizleniyor...
rmdir /s /q build >nul 2>&1
rmdir /s /q __pycache__ >nul 2>&1
del MAPEG_Oteleme.spec >nul 2>&1
echo        Tamam.

echo.
echo  ============================================
echo   BASARILI!
echo   dist\MAPEG_Oteleme.exe olusturuldu.
echo  ============================================
echo.
echo  Artik sadece MAPEG_Oteleme.exe dosyasini
echo  kullanabilirsiniz. Python gerekmez.
echo.

REM Move exe to current directory
move dist\MAPEG_Oteleme.exe . >nul 2>&1
rmdir /s /q dist >nul 2>&1

echo  MAPEG_Oteleme.exe bu klasorde hazir.
echo.
pause

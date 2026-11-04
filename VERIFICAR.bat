@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  Verificacion previa (Python, CUDA y datos SFT)
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "training\entrenar_windows.ps1" -CheckOnly %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
    echo La verificacion encontro un problema ^(codigo %RC%^).
) else (
    echo Verificacion completada. Ya se puede ejecutar ENTRENAR.bat
)
echo.
pause
exit /b %RC%

@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  Entrenamiento Qwen2.5-Coder-1.5B + QLoRA
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "training\entrenar_windows.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
    echo El proceso termino con errores ^(codigo %RC%^).
    echo Revisa el mensaje anterior y training\out\train.log
) else (
    echo Proceso terminado correctamente.
)
echo.
pause
exit /b %RC%

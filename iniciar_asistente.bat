@echo off
setlocal
TITLE Asistente Virtual - Logs
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en:
    echo         %cd%\venv
    echo.
    echo Crea uno con:  python -m venv venv
    echo Y luego instala las dependencias del README.
    echo.
    pause
    exit /b 1
)

echo [OK] Activando entorno virtual...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b 1
)

echo [OK] Arrancando main.py ...
echo     DEV=True  -^> esta ventana muestra los logs
echo     DEV=False -^> la ventana se oculta sola ^(cierre por Administrador de tareas^)
echo --------------------------------------------------
echo.

python main.py
set EXITCODE=%ERRORLEVEL%

echo.
echo --------------------------------------------------
echo [Asistente] Proceso finalizado con codigo %EXITCODE%.
if not "%EXITCODE%"=="0" (
    echo Revisa el mensaje de error de arriba.
)
echo.
pause
endlocal
exit /b %EXITCODE%

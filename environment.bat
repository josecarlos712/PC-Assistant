@echo off
TITLE ComfyUI - Ambiente Virtual CUDA 12.4
:: Navega a la carpeta del proyecto
cd /d "D:\JoseCarlos\Programacion\Python\Home Assistant"
cd /d "D:"

:: Verifica si la carpeta venv existe antes de intentar activarla
if exist venv\Scripts\activate.bat (
    echo [OK] Activando entorno virtual...
    call venv\Scripts\activate.bat
    echo.
    echo Entorno activado. Puedes ejecutar ComfyUI con: python main.py
    echo.
) else (
    echo [ERROR] No se encontro la carpeta venv en C:\Programas\ComfyUI
    echo Ejecuta primero: python -m venv venv
    pause
    exit
)

:: Esto mantiene la consola abierta y te devuelve el prompt
cmd /k
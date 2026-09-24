@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
TITLE PC-Assistant - Instalacion
cd /d "%~dp0"

set "PYTHON_MIN_MAJOR=3"
set "PYTHON_MIN_MINOR=10"
set "PYTHON_WANT=3.11"
set "PYTHON_WINGET_ID=Python.Python.3.11"
set "PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\pcassistant-python-3.11.9-amd64.exe"

set "PIPER_ONNX=voices\Dave\es_ES-davefx-medium.onnx"
set "PIPER_JSON=voices\Dave\es_ES-davefx-medium.onnx.json"
set "PIPER_ONNX_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx?download=true"
set "PIPER_JSON_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json?download=true"

echo ============================================================
echo   PC-Assistant — instalacion para Windows
echo ============================================================
echo.
echo Este asistente instalara:
echo   1^) Python %PYTHON_WANT% ^(si no hay 3.10+^)
echo   2^) Entorno virtual y dependencias ^(requirements.txt^)
echo   3^) Modelos Piper ^(voz^) y Whisper ^(reconocimiento^)
echo   4^) Carpetas y archivos basicos de configuracion
echo.
echo Puede tardar varios minutos ^(descargas grandes^).
echo ------------------------------------------------------------
echo.

REM ------------------------------------------------------------------
REM 1) Python
REM ------------------------------------------------------------------
echo [1/4] Comprobando Python...
call :encontrar_python
if defined PYEXE (
    echo [OK] Python encontrado: !PYEXE!
    "!PYEXE!" --version
) else (
    echo [!] No hay Python %PYTHON_MIN_MAJOR%.%PYTHON_MIN_MINOR%+ usable.
    echo     Intentando instalar Python %PYTHON_WANT%...
    call :instalar_python
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar Python automaticamente.
        echo         Descarga e instala a mano desde:
        echo         https://www.python.org/downloads/release/python-3119/
        echo         Marca "Add python.exe to PATH" durante la instalacion.
        goto :fallo
    )
    call :refrescar_path
    call :encontrar_python
    if not defined PYEXE (
        echo [ERROR] Python se instalo, pero esta ventana no lo ve aun.
        echo         Cierra esta ventana, abre una nueva y vuelve a ejecutar setup.bat.
        goto :fallo
    )
    echo [OK] Python listo: !PYEXE!
    "!PYEXE!" --version
)
echo.

REM ------------------------------------------------------------------
REM 2) venv + requirements
REM ------------------------------------------------------------------
echo [2/4] Entorno virtual y dependencias...
if not exist "requirements.txt" (
    echo [ERROR] Falta requirements.txt en la carpeta del proyecto.
    goto :fallo
)

if not exist "venv\Scripts\python.exe" (
    echo [..] Creando entorno virtual en venv\ ...
    "!PYEXE!" -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        goto :fallo
    )
) else (
    echo [OK] Entorno virtual ya existe.
)

set "VENV_PY=%cd%\venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] No se encontro %VENV_PY%
    goto :fallo
)

echo [..] Actualizando pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Fallo al actualizar pip.
    goto :fallo
)

echo [..] Instalando requirements.txt ^(puede tardar^)...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias.
    goto :fallo
)
echo [OK] Dependencias instaladas.
echo.

REM ------------------------------------------------------------------
REM 3) Modelos
REM ------------------------------------------------------------------
echo [3/4] Modelos de voz y reconocimiento...
if not exist "voices\Dave" mkdir "voices\Dave"

if not exist "%PIPER_JSON%" (
    echo [..] Descargando config Piper...
    call :descargar "%PIPER_JSON_URL%" "%PIPER_JSON%"
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar %PIPER_JSON%
        echo         URL: %PIPER_JSON_URL%
        goto :fallo
    )
) else (
    echo [OK] Ya existe %PIPER_JSON%
)

if not exist "%PIPER_ONNX%" (
    echo [..] Descargando modelo Piper ^(~63 MB^)...
    call :descargar "%PIPER_ONNX_URL%" "%PIPER_ONNX%"
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar el modelo Piper ONNX.
        echo         URL intentada:
        echo         %PIPER_ONNX_URL%
        echo.
        echo         Si tienes el archivo, colocalo en:
        echo         %cd%\%PIPER_ONNX%
        echo         y vuelve a ejecutar setup.bat.
        goto :fallo
    )
) else (
    echo [OK] Ya existe %PIPER_ONNX%
)

for %%A in ("%PIPER_ONNX%") do set "PIPER_SIZE=%%~zA"
if defined PIPER_SIZE if !PIPER_SIZE! LSS 1000000 (
    echo [ERROR] El archivo Piper parece incompleto ^(!PIPER_SIZE! bytes^).
    echo         Borra %PIPER_ONNX% y vuelve a ejecutar setup.bat.
    goto :fallo
)

echo [..] Descargando / comprobando modelo Whisper "small" ^(primera vez ~500 MB^)...
"%VENV_PY%" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('[OK] Modelo Whisper small listo.')"
if errorlevel 1 (
    echo [ERROR] No se pudo descargar el modelo Whisper.
    echo         Necesitas conexion a Internet ^(Hugging Face / mirror^).
    goto :fallo
)
echo.

REM ------------------------------------------------------------------
REM 4) Archivos y carpetas basicas
REM ------------------------------------------------------------------
echo [4/4] Carpetas y archivos basicos...
for %%D in (nucleo comandos config datos voices\Dave datos\alarmas datos\capturas datos\notas datos\cache_tts datos\output_tts) do (
    if not exist "%%D" (
        mkdir "%%D"
        echo [OK] Creada carpeta %%D\
    )
)

if not exist "datos\alarmas\registro.json" (
    >"datos\alarmas\registro.json" echo []
    echo [OK] Creado datos\alarmas\registro.json
)

if not exist "datos\input_tts.txt" (
    type nul >"datos\input_tts.txt"
    echo [OK] Creado datos\input_tts.txt
)

REM Plantillas config\*_blank.json → nombre final sin sufijo ^(copia; las plantillas se quedan^)
echo [..] Aplicando plantillas config\*_blank.json...
set "BLANK_OK=0"
for %%F in (config\*_blank.json) do (
    set "BLANK_NAME=%%~nxF"
    set "DEST_NAME=!BLANK_NAME:_blank=!"
    if /I "!DEST_NAME!"=="!BLANK_NAME!" (
        echo [AVISO] No se pudo quitar el sufijo a %%F
    ) else if exist "config\!DEST_NAME!" (
        echo [OK] Ya existe config\!DEST_NAME! — no se sobrescribe
        set "BLANK_OK=1"
    ) else if exist "%%F" (
        copy /Y "%%F" "config\!DEST_NAME!" >nul
        if errorlevel 1 (
            echo [ERROR] No se pudo crear config\!DEST_NAME! desde %%F
        ) else (
            echo [OK] %%F -^> config\!DEST_NAME!  ^(editalo con tus datos^)
            set "BLANK_OK=1"
        )
    )
)
if "!BLANK_OK!"=="0" (
    if not exist "config\apps_blank.json" if not exist "config\carpetas_blank.json" if not exist "config\config_local_blank.json" if not exist "config\cache_registro_blank.json" (
        echo [AVISO] No hay plantillas config\*_blank.json en el proyecto.
    )
)

if not exist "config\cache_registro.json" (
    >"config\cache_registro.json" echo {}
    echo [OK] Creado config\cache_registro.json vacio
)

if not exist "nircmd.exe" (
    echo.
    echo [AVISO] Falta nircmd.exe en la raiz del proyecto.
    echo         Sin el no funcionan volumen, silencio ni apagar monitores.
    echo         Descarga: https://www.nirsoft.net/utils/nircmd.html
    echo         Coloca nircmd.exe junto a main.py / setup.bat
    echo         ^(este instalador NO lo descarga automaticamente^).
)

echo.
echo ============================================================
echo   Instalacion completada
echo ============================================================
echo.
echo Para arrancar el asistente:
echo   iniciar_asistente.bat
echo.
echo Revisa y adapta a tu PC ^(rutas locales^):
echo   - config\apps.json
echo   - config\carpetas.json
echo   - config\config_local.json  ^(ciudad del clima / IA local^)
echo.
pause
endlocal
exit /b 0

:fallo
echo.
echo ============================================================
echo   La instalacion NO se completo
echo ============================================================
echo.
pause
endlocal
exit /b 1


REM ==================================================================
REM Subrutinas
REM ==================================================================

:encontrar_python
set "PYEXE="
REM Preferir py launcher con 3.11 / 3.12 / 3.10
where py >nul 2>&1
if not errorlevel 1 (
    for %%V in (3.11 3.12 3.13 3.10) do (
        if not defined PYEXE (
            py -%%V -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (%PYTHON_MIN_MAJOR%, %PYTHON_MIN_MINOR%) else 1)" >nul 2>&1
            if not errorlevel 1 (
                for /f "delims=" %%P in ('py -%%V -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
            )
        )
    )
)
if defined PYEXE exit /b 0

where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (%PYTHON_MIN_MAJOR%, %PYTHON_MIN_MINOR%) else 1)" >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
        if defined PYEXE exit /b 0
    )
)

where python3 >nul 2>&1
if not errorlevel 1 (
    python3 -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (%PYTHON_MIN_MAJOR%, %PYTHON_MIN_MINOR%) else 1)" >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%P in ('python3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
    )
)
exit /b 0


:instalar_python
where winget >nul 2>&1
if not errorlevel 1 (
    echo [..] Instalando con winget ^(%PYTHON_WINGET_ID%^)...
    winget install -e --id %PYTHON_WINGET_ID% --accept-package-agreements --accept-source-agreements --silent
    if not errorlevel 1 (
        echo [OK] winget termino la instalacion de Python.
        exit /b 0
    )
    echo [!] winget fallo o el paquete no esta disponible. Probando instalador oficial...
)

echo [..] Descargando instalador oficial de Python 3.11.9...
call :descargar "%PYTHON_INSTALLER_URL%" "%PYTHON_INSTALLER%"
if errorlevel 1 (
    echo [ERROR] No se pudo descargar el instalador de Python.
    exit /b 1
)

echo [..] Ejecutando instalador en modo silencioso...
echo     ^(puede pedir permiso de administrador^)
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_pip=1 SimpleInstall=1
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    echo [ERROR] El instalador de Python devolvio codigo !RC!
    exit /b 1
)
echo [OK] Instalador de Python finalizado.
exit /b 0


:refrescar_path
REM Recargar PATH de usuario + maquina en esta sesion
for /f "usebackq tokens=2*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do set "USER_PATH=%%B"
for /f "usebackq tokens=2*" %%A in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul`) do set "SYS_PATH=%%B"
if defined SYS_PATH if defined USER_PATH (
    set "PATH=%SYS_PATH%;%USER_PATH%"
) else if defined SYS_PATH (
    set "PATH=%SYS_PATH%"
) else if defined USER_PATH (
    set "PATH=%USER_PATH%"
)
exit /b 0


:descargar
set "URL=%~1"
set "DEST=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%URL%' -OutFile '%DEST%' -UseBasicParsing; if (-not (Test-Path '%DEST%') -or ((Get-Item '%DEST%').Length -lt 100)) { exit 1 }; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
exit /b %ERRORLEVEL%

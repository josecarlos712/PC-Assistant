"""Rutas absolutas del proyecto (raíz limpia: nucleo / config / datos / voices)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUCLEO = RAIZ / "nucleo"
COMANDOS = RAIZ / "comandos"
CONFIG = RAIZ / "config"
DATOS = RAIZ / "datos"
VOCES = RAIZ / "voices"

APPS_JSON = CONFIG / "apps.json"
CARPETAS_JSON = CONFIG / "carpetas.json"
CONFIG_LOCAL = CONFIG / "config_local.json"
MAPEO_COMANDOS = CONFIG / "mapeo_comandos.json"
CACHE_REGISTRO = CONFIG / "cache_registro.json"

ALARMAS = DATOS / "alarmas"
CACHE_TTS = DATOS / "cache_tts"
CAPTURAS = DATOS / "capturas"
NOTAS = DATOS / "notas"
OUTPUT_TTS = DATOS / "output_tts"
INPUT_TTS = DATOS / "input_tts.txt"

MODELO_PIPER = VOCES / "Dave" / "es_ES-davefx-medium.onnx"
NIRCMD = RAIZ / "nircmd.exe"
READ_FILE = NUCLEO / "read_file.py"
ALARM_SOUND = NUCLEO / "alarm_sound.py"


def asegurar_sys_path() -> None:
    """Permite `import escuchador` / `import hora` desde main y subprocess."""
    import sys

    for ruta in (str(NUCLEO), str(COMANDOS)):
        if ruta not in sys.path:
            sys.path.insert(0, ruta)

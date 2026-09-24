import os
import sys
import json
import re
import subprocess
import importlib.util

import rutas

rutas.asegurar_sys_path()


def ejecutar_salida_tts(texto_respuesta):
    """Escribe en datos/input_tts.txt y ejecuta nucleo/read_file.py."""
    try:
        rutas.DATOS.mkdir(parents=True, exist_ok=True)
        with open(rutas.INPUT_TTS, "w", encoding="utf-8") as f:
            f.write(texto_respuesta)
        subprocess.run(
            [sys.executable, str(rutas.READ_FILE)],
            check=True,
            cwd=str(rutas.RAIZ),
        )
    except Exception as e:
        print(f"\n[Error TTS Bridge]: No se pudo ejecutar el Módulo 1. Detalle: {e}")


def cargar_mapeo():
    """Carga config/mapeo_comandos.json."""
    try:
        with open(rutas.MAPEO_COMANDOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"\n[Error Orquestador]: No se pudo leer mapeo_comandos.json. {e}")
        return {}


def lanzar_comando_dinamico(nombre_script, match):
    """
    Importa el script desde comandos/ y lo ejecuta.
    Reutiliza el mismo módulo en memoria (importante para estado de
    conversación, historial de la IA, etc.).
    """
    ruta_script = rutas.COMANDOS / f"{nombre_script}.py"

    if not ruta_script.is_file():
        return f"Error: El script {nombre_script}.py no existe en la carpeta comandos."

    try:
        if nombre_script in sys.modules:
            modulo = sys.modules[nombre_script]
        else:
            spec = importlib.util.spec_from_file_location(nombre_script, str(ruta_script))
            modulo = importlib.util.module_from_spec(spec)
            sys.modules[nombre_script] = modulo
            spec.loader.exec_module(modulo)

        return modulo.ejecutar(match)
    except Exception as e:
        return f"Error al ejecutar el comando {nombre_script}: {e}"


def evaluar_comando(texto_usuario):
    """Revisa el JSON, busca la coincidencia RegEx y delega al script correspondiente."""
    entrada = texto_usuario.strip().lower()
    if not entrada:
        return

    mapa = cargar_mapeo()

    for nombre_script, patrones in mapa.items():
        for patron in patrones:
            match = re.match(patron, entrada)
            if match:
                respuesta_asistente = lanzar_comando_dinamico(nombre_script, match)
                if respuesta_asistente:
                    print(f"\n[Asistente]: {respuesta_asistente}")
                    ejecutar_salida_tts(respuesta_asistente)
                return

    print(f"\n[Asistente]: (ignorado) '{entrada}'")

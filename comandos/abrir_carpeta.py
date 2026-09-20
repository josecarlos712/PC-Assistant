"""Abre una carpeta por palabra clave definida en carpetas.json."""
import json
import os
import unicodedata

RUTA_MAPEO = os.path.join(os.getcwd(), "carpetas.json")


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _normalizar_clave(texto: str) -> str:
    t = _sin_acentos((texto or "").strip().lower())
    return " ".join(t.split())


def _cargar_carpetas() -> dict:
    try:
        with open(RUTA_MAPEO, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            return {str(k): str(v) for k, v in datos.items()}
    except Exception as e:
        print(f"[Abrir carpeta] No se pudo leer {RUTA_MAPEO}: {e}")
    return {}


def _resolver_ruta(clave: str, mapa: dict):
    buscada = _normalizar_clave(clave)
    if not buscada:
        return None, None

    for palabra, ruta in mapa.items():
        if _normalizar_clave(palabra) == buscada:
            return palabra, os.path.expandvars(ruta)

    # Coincidencia sin espacios: "apepedata" ≈ "a pe pe data"
    compacta = buscada.replace(" ", "")
    for palabra, ruta in mapa.items():
        if _normalizar_clave(palabra).replace(" ", "") == compacta:
            return palabra, os.path.expandvars(ruta)

    return None, None


def ejecutar(match):
    clave = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                clave = g.strip()
                break

    if not clave:
        return "Dime qué carpeta quieres abrir."

    mapa = _cargar_carpetas()
    if not mapa:
        return "No pude leer el archivo de carpetas."

    nombre, ruta = _resolver_ruta(clave, mapa)
    if not ruta:
        return f"No conozco la carpeta {clave}."

    if not os.path.isdir(ruta):
        print(f"[Abrir carpeta] Ruta inexistente: {ruta}")
        return f"La carpeta {nombre} no existe en disco."

    try:
        os.startfile(ruta)
        return f"Abriendo la carpeta {nombre}."
    except Exception as e:
        print(f"[Abrir carpeta] Error al abrir {ruta}: {e}")
        return f"No pude abrir la carpeta {nombre}."

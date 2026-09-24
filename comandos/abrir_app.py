"""
Abre una aplicación definida en apps.json.

Estrategia anti-errores de Whisper:
  - Cada app tiene alias fonéticos (cromo → chrome, espotifai → spotify).
  - Coincidencia exacta, sin espacios, y difusa (SequenceMatcher).
  - escuchador.py también aplica esos alias al limpiar la transcripción.
"""
import json
import os
import shutil
import subprocess
import unicodedata
from difflib import SequenceMatcher

RUTA_MAPEO = None  # se resuelve al importar rutas

try:
    import rutas
    RUTA_MAPEO = str(rutas.APPS_JSON)
except ImportError:
    import os
    RUTA_MAPEO = os.path.join(os.getcwd(), "config", "apps.json")
UMBRAL_DIFUSO = 0.72


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _normalizar(texto: str) -> str:
    t = _sin_acentos((texto or "").strip().lower())
    # Quitar artículos sueltos al inicio
    for art in ("el ", "la ", "los ", "las ", "un ", "una "):
        if t.startswith(art):
            t = t[len(art) :]
            break
    return " ".join(t.split())


def _compacto(texto: str) -> str:
    return _normalizar(texto).replace(" ", "")


def cargar_apps() -> dict:
    """
    Devuelve {clave: {"ruta": str, "alias": [str], "nombres": [todas las formas]}}
    Acepta formato simple "clave": "ruta" o el enriquecido con alias.
    """
    try:
        with open(RUTA_MAPEO, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as e:
        print(f"[Abrir app] No se pudo leer {RUTA_MAPEO}: {e}")
        return {}

    if not isinstance(datos, dict):
        return {}

    apps = {}
    for clave, valor in datos.items():
        clave_s = str(clave).strip()
        if isinstance(valor, str):
            ruta = valor
            alias = []
        elif isinstance(valor, dict):
            ruta = str(valor.get("ruta") or valor.get("path") or "").strip()
            alias = [str(a) for a in (valor.get("alias") or [])]
        else:
            continue
        if not ruta:
            continue
        nombres = [clave_s] + alias
        apps[clave_s] = {"ruta": ruta, "alias": alias, "nombres": nombres}
    return apps


def alias_foneticos() -> dict:
    """Mapa 'alias hablado' → clave canónica (para el escuchador)."""
    mapa = {}
    for clave, meta in cargar_apps().items():
        for nombre in meta["nombres"]:
            n = _normalizar(nombre)
            if n and n != _normalizar(clave):
                mapa[n] = clave
            c = _compacto(nombre)
            if c and c != _compacto(clave):
                mapa[c] = clave
    return mapa


def _resolver_app(pedido: str, apps: dict):
    buscada = _normalizar(pedido)
    if not buscada:
        return None
    compacta = _compacto(pedido)

    # 1) Exacta / compacta
    for clave, meta in apps.items():
        for nombre in meta["nombres"]:
            if _normalizar(nombre) == buscada or _compacto(nombre) == compacta:
                return clave

    # 2) Contención (pedido dentro del alias o al revés)
    candidatas = []
    for clave, meta in apps.items():
        for nombre in meta["nombres"]:
            nn = _normalizar(nombre)
            nc = _compacto(nombre)
            if buscada in nn or nn in buscada or compacta in nc or nc in compacta:
                candidatas.append(clave)
                break
    if len(candidatas) == 1:
        return candidatas[0]

    # 3) Difusa
    mejor_clave = None
    mejor_score = 0.0
    for clave, meta in apps.items():
        for nombre in meta["nombres"]:
            for a, b in (
                (buscada, _normalizar(nombre)),
                (compacta, _compacto(nombre)),
            ):
                if not a or not b:
                    continue
                score = SequenceMatcher(None, a, b).ratio()
                if score > mejor_score:
                    mejor_score = score
                    mejor_clave = clave
    if mejor_clave and mejor_score >= UMBRAL_DIFUSO:
        print(f"[Abrir app] Coincidencia difusa '{pedido}' → '{mejor_clave}' ({mejor_score:.2f})")
        return mejor_clave

    return None


def _lanzar(ruta: str) -> bool:
    ruta = os.path.expandvars(ruta.strip())
    try:
        if os.path.isfile(ruta):
            os.startfile(ruta)
            return True

        # URI / protocolo (spotify:, shell:..., https://...) — no unidad C:\
        es_disco = len(ruta) >= 3 and ruta[1] == ":" and ruta[2] in "\\/"
        if ":" in ruta and not es_disco:
            os.startfile(ruta)
            return True

        # Ejecutable en PATH
        candidato = ruta
        if not candidato.lower().endswith(".exe") and "\\" not in candidato and "/" not in candidato:
            which = shutil.which(candidato) or shutil.which(candidato + ".exe")
            if which:
                subprocess.Popen([which], close_fds=False)
                return True

        if "\\" in ruta or "/" in ruta:
            subprocess.Popen([ruta], close_fds=False)
            return True
        os.startfile(ruta)
        return True
    except Exception as e:
        print(f"[Abrir app] Error al lanzar '{ruta}': {e}")
        return False


def ejecutar(match):
    pedido = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                pedido = g.strip()
                break

    # Quitar "aplicación/app" residuales
    pedido_n = _normalizar(pedido)
    for pref in ("aplicacion ", "aplicación ", "app ", "programa "):
        if pedido_n.startswith(_normalizar(pref)):
            pedido = pedido_n[len(_normalizar(pref)) :].strip()
            break

    if not pedido:
        return "Dime qué aplicación quieres abrir."

    apps = cargar_apps()
    if not apps:
        return "No pude leer el archivo de aplicaciones."

    clave = _resolver_app(pedido, apps)
    if not clave:
        return f"No conozco la aplicación {pedido}."

    ruta = apps[clave]["ruta"]
    if not _lanzar(ruta):
        return f"No pude abrir {clave}. Revisa la ruta en apps.json."

    return f"Abriendo {clave}."

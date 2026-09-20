"""Registro persistente de alarmas programadas (para consultarlas por voz)."""
import json
import os
import uuid
from datetime import datetime

RUTA_REGISTRO = os.path.join(os.getcwd(), "alarmas", "registro.json")


def _cargar() -> list:
    try:
        if not os.path.isfile(RUTA_REGISTRO):
            return []
        with open(RUTA_REGISTRO, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except Exception:
        return []


def _guardar(entradas: list) -> None:
    carpeta = os.path.dirname(RUTA_REGISTRO)
    os.makedirs(carpeta, exist_ok=True)
    with open(RUTA_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(entradas, f, ensure_ascii=False, indent=2)


def _proceso_vivo(pid) -> bool:
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def registrar(pid: int, segundos: int, titulo: str, ruta_wav: str, alarm_id: str = None) -> str:
    """Añade una alarma pendiente. Devuelve el id."""
    ahora = datetime.now()
    dispara = ahora.timestamp() + max(1, int(segundos))
    alarm_id = alarm_id or uuid.uuid4().hex[:12]
    entradas = _cargar()
    entradas.append(
        {
            "id": alarm_id,
            "pid": int(pid),
            "creada": ahora.isoformat(timespec="seconds"),
            "dispara_en": datetime.fromtimestamp(dispara).isoformat(timespec="seconds"),
            "titulo": (titulo or "").strip(),
            "wav": ruta_wav,
        }
    )
    _guardar(entradas)
    return alarm_id


def quitar(alarm_id: str = None, ruta_wav: str = None) -> None:
    entradas = _cargar()
    if not entradas:
        return
    filtradas = []
    for e in entradas:
        if alarm_id and e.get("id") == alarm_id:
            continue
        if ruta_wav and os.path.abspath(e.get("wav") or "") == os.path.abspath(ruta_wav):
            continue
        if alarm_id or ruta_wav:
            filtradas.append(e)
            continue
        filtradas.append(e)
    # Si no se pasó criterio, no tocar
    if not alarm_id and not ruta_wav:
        return
    _guardar(filtradas)


def listar_pendientes() -> list:
    """Alarmas futuras cuyo proceso sigue vivo (o sin pid conocido)."""
    ahora = datetime.now()
    vivas = []
    restantes = []
    for e in _cargar():
        try:
            dispara = datetime.fromisoformat(e.get("dispara_en", ""))
        except ValueError:
            continue
        if dispara <= ahora:
            continue
        pid = e.get("pid")
        if pid and not _proceso_vivo(pid):
            continue
        vivas.append(e)
        restantes.append(e)
    _guardar(restantes)
    vivas.sort(key=lambda x: x.get("dispara_en", ""))
    return vivas

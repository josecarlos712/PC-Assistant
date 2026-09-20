"""
Comando de modos del sistema.

Para añadir un modo nuevo:
  1. Escribe una función `modo_xxx(match) -> str`
  2. Regístrala en el diccionario MODOS con su palabra clave

NOTA — Desbloqueo con PIN:
  Windows ejecuta la pantalla de bloqueo en un "secure desktop" (Winlogon).
  SendInput / teclas simuladas desde una app de usuario NO pueden escribir el PIN.
  Por eso el modo noche NO usa LockWorkStation: apaga los monitores (nircmd).
  El modo día los enciende y extiende la proyección. La sesión sigue abierta.
"""
import ctypes
import os
import subprocess
import sys
import time
import unicodedata

KEYEVENTF_KEYUP = 0x0002
VK_LWIN = 0x5B
VK_D = 0x44
VK_SPACE = 0x20
VK_NUMLOCK = 0x90

TEXT_GEN_WEBUI_BAT = r"C:\Programas\text-generation-webui\start_windows.bat"


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _mostrar_escritorio() -> bool:
    """Equivale a Windows+D."""
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_D, 0, 0, 0)
        user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def _proyeccion_pantalla_principal() -> bool:
    """Proyectar solo en la pantalla principal (DisplaySwitch /internal)."""
    try:
        subprocess.run(
            ["DisplaySwitch.exe", "/internal"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _proyeccion_extender() -> bool:
    """Proyectar en modo extender (varias pantallas)."""
    try:
        subprocess.run(
            ["DisplaySwitch.exe", "/extend"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _ruta_nircmd() -> str:
    return os.path.join(os.getcwd(), "nircmd.exe")


def _monitores_off() -> bool:
    """Apaga los monitores (sesión sigue activa; no es pantalla de bloqueo)."""
    nircmd = _ruta_nircmd()
    if not os.path.isfile(nircmd):
        print("[Modo] Falta nircmd.exe para apagar monitores.")
        return False
    try:
        subprocess.run([nircmd, "monitor", "off"], check=False)
        return True
    except Exception:
        return False


def _despertar_monitores() -> bool:
    """Mueve el ratón / pulsa una tecla para encender pantallas."""
    try:
        user32 = ctypes.windll.user32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        punto = POINT()
        user32.GetCursorPos(ctypes.byref(punto))
        user32.SetCursorPos(punto.x + 1, punto.y + 1)
        time.sleep(0.05)
        user32.SetCursorPos(punto.x, punto.y)
        user32.keybd_event(VK_SPACE, 0, 0, 0)
        user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def _pulsar_tecla(vk: int) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _apagar_numlock_si_activo() -> bool:
    """Si NumLock está encendido, lo apaga con una pulsación."""
    try:
        user32 = ctypes.windll.user32
        # GetKeyState: bit bajo = toggle state (1 = ON)
        estado = user32.GetKeyState(VK_NUMLOCK)
        if estado & 1:
            print("[Modo] NumLock activo → apagando.")
            _pulsar_tecla(VK_NUMLOCK)
            time.sleep(0.15)
        else:
            print("[Modo] NumLock ya estaba apagado.")
        return True
    except Exception as e:
        print(f"[Modo] No se pudo tocar NumLock: {e}")
        return False


def _apagar_luz_teclado_yunzii() -> bool:
    """
    Yunzii QL108: Fn+Backspace apaga el RGB en el firmware del teclado.
    Esa tecla Fn NO genera scancode hacia Windows, así que no se puede
    simular con SendInput. Tampoco hay API pública HID documentada para
    el QL108 (solo software/qmk.top en modo cable).

    Dejamos el gancho por si en el futuro se captura el reporte HID.
    """
    print(
        "[Modo] Luz teclado Yunzii QL108: no automatizable "
        "(Fn es local al teclado; sin protocolo HID público)."
    )
    return False


def _iniciar_text_generation_webui() -> bool:
    """Lanza text-generation-webui en consola propia; no espera a que termine."""
    bat = TEXT_GEN_WEBUI_BAT
    if not os.path.isfile(bat):
        print(f"[Modo] No existe text-generation-webui: {bat}")
        return False
    try:
        cwd = os.path.dirname(bat)
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", bat],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[Modo] Iniciado text-generation-webui: {bat}")
        return True
    except Exception as e:
        print(f"[Modo] No se pudo iniciar text-generation-webui: {e}")
        return False


def _decir(texto: str) -> None:
    try:
        with open("input_tts.txt", "w", encoding="utf-8") as f:
            f.write(texto)
        subprocess.run(
            [sys.executable, os.path.join(os.getcwd(), "read_file.py")],
            check=False,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Definición de modos (palabra clave → función)
# ---------------------------------------------------------------------------

def modo_dia(match):
    """
    1) Despertar monitores
    2) Proyección en modo extender
    """
    ok_wake = _despertar_monitores()
    time.sleep(0.8)
    ok_proy = _proyeccion_extender()
    time.sleep(0.3)

    if ok_wake and ok_proy:
        return "Modo dia activado."
    if ok_proy:
        return "Pantallas en modo extender."
    return "No pude activar el modo dia."


def modo_noche(match):
    """
    1) Mostrar escritorio (Win+D)
    2) Proyectar solo en la pantalla principal
    3) Apagar NumLock si está activo
    4) Iniciar text-generation-webui
    5) Apagar monitores
    """
    ok_desk = _mostrar_escritorio()
    time.sleep(0.5)
    ok_proy = _proyeccion_pantalla_principal()
    time.sleep(0.4)
    _apagar_numlock_si_activo()
    time.sleep(0.2)
    _apagar_luz_teclado_yunzii()
    time.sleep(0.2)
    _iniciar_text_generation_webui()
    time.sleep(0.5)

    if not (ok_desk and ok_proy):
        return "Modo noche incompleto: revisa pantallas o permisos."

    _decir("Modo noche activado.")
    time.sleep(0.3)
    ok_mon = _monitores_off()
    if not ok_mon:
        return (
            "Escritorio y proyección listos, pero no pude apagar los monitores. "
            "¿Está nircmd.exe en la carpeta del proyecto?"
        )
    return ""  # ya habló antes de apagar pantallas


# Registra aquí cada modo nuevo: "clave": funcion
MODOS = {
    "dia": modo_dia,
    "día": modo_dia,
    "noche": modo_noche,
}

# Alias típicos de Whisper / errores de oído → clave real
ALIAS_MODOS = {
    "via": "dia",
    "vía": "dia",
    "vr": "dia",
    "vii": "dia",
    "gear": "dia",
    "tia": "dia",
    "diary": "dia",
    "melodia": "dia",
    "melodía": "dia",
    "moropia": "dia",
    "moropía": "dia",
}


def _resolver_modo(nombre: str):
    """Devuelve la función del modo o None."""
    if not nombre:
        return None

    crudo = nombre.strip().lower()
    clave = _sin_acentos(crudo)
    clave = ALIAS_MODOS.get(crudo, clave)
    clave = ALIAS_MODOS.get(clave, clave)

    funcion = MODOS.get(crudo) or MODOS.get(clave)
    if funcion is not None:
        return funcion

    for k, fn in MODOS.items():
        if _sin_acentos(k) == clave:
            return fn

    canon = ALIAS_MODOS.get(clave)
    if canon:
        return MODOS.get(canon) or MODOS.get(_sin_acentos(canon))
    return None


def ejecutar(match):
    nombre = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                nombre = g.strip().lower()
                break

    if not nombre and match is not None:
        frase = _sin_acentos((match.group(0) or "").lower())
        if "melodia" in frase:
            nombre = "dia"

    if not nombre:
        print("[Modo] Frase de modo sin nombre reconocible; ignorado.")
        return ""

    funcion = _resolver_modo(nombre)
    if funcion is None:
        print(f"[Modo] Alias desconocido '{nombre}'; ignorado.")
        return ""

    return funcion(match)

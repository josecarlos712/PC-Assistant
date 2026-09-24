"""
Punto de entrada del asistente de voz.
La raíz del repo se mantiene limpia: el motor vive en nucleo/, los comandos en comandos/.
"""
import ctypes
import os
import subprocess
import sys

# Resolver imports de nucleo/ y comandos/ aunque se lance desde la raíz
_RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_RAIZ, "nucleo"))
sys.path.insert(0, os.path.join(_RAIZ, "comandos"))

import rutas  # noqa: E402
import orquestador  # noqa: E402
import escuchador  # noqa: E402

# True  → consola visible con logs (desarrollo)
# False → sin ventana; hay que cerrarlo desde el Administrador de tareas
DEV = True

# True  → barras de micrófono, RMS, segmentos Whisper, etc.
# False → solo mensajes útiles para el uso normal
VERVOSE = True


def configurar_visibilidad_consola():
    """Muestra u oculta la consola según DEV (solo Windows)."""
    if sys.platform != "win32":
        return
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if not hwnd:
        return
    # SW_HIDE = 0, SW_SHOW = 5
    ctypes.windll.user32.ShowWindow(hwnd, 5 if DEV else 0)


def _tts(texto: str) -> None:
    """TTS bloqueante (comandos normales fuera de conversación)."""
    if texto:
        print(f"\n[Asistente]: {texto}")
        orquestador.ejecutar_salida_tts(texto)


def _matar_tts(proc: subprocess.Popen) -> None:
    """Corta el proceso de Piper/pygame y su árbol en Windows."""
    if proc.poll() is not None:
        return
    pid = proc.pid
    if sys.platform == "win32" and pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _tts_conversacion(texto: str) -> bool:
    """
    Reproduce la respuesta escuchando a la vez.
    Devuelve True si el usuario dijo «para» / «calla» (respuesta omitida).
    """
    if not texto:
        return False

    import conversacion

    print(f"\n[Asistente]: {texto}")
    try:
        rutas.DATOS.mkdir(parents=True, exist_ok=True)
        with open(rutas.INPUT_TTS, "w", encoding="utf-8") as f:
            f.write(texto)
    except Exception as e:
        print(f"[TTS] No se pudo escribir input_tts.txt: {e}")
        return False

    proc = subprocess.Popen(
        [sys.executable, str(rutas.READ_FILE)],
        cwd=str(rutas.RAIZ),
    )
    print('[Conversación] Escuchando barge-in («para» / «calla»)…')

    micro = escuchador.obtener_microfono()
    while proc.poll() is None:
        frase = micro.capturar_frase(
            segundos_silencio=0.4,
            timeout_sin_habla=0.45,
            etiqueta="Di «para» o «calla» para callar",
            min_segundos_habla=0.5,
        )
        if proc.poll() is not None:
            break
        if not frase:
            continue

        limpio = escuchador.limpiar_fonetica_windows(frase)
        if not limpio:
            continue

        activado, resto = escuchador.extraer_comando_tras_activacion(limpio)
        candidato = resto if (activado and resto) else limpio

        if conversacion.es_orden_callar(candidato) or conversacion.es_orden_callar(limpio):
            print("[Conversación] Interrumpido por el usuario. Cortando audio…")
            _matar_tts(proc)
            return True

        print(f"[Conversación] (durante respuesta, ignorado): '{limpio}'")

    try:
        proc.wait(timeout=5)
    except Exception:
        _matar_tts(proc)
    return False


def _turno_conversacion() -> None:
    """Una frase del usuario → IA → voz. Sin palabra Dave."""
    import conversacion
    import preguntar_ia

    texto = escuchador.esperar_frase_conversacion()
    if not texto:
        return

    print(f"Tú (conversación): {texto}")

    if conversacion.es_fin_conversacion(texto):
        _tts_conversacion(conversacion.terminar())
        return

    if conversacion.es_inicio_conversacion(texto):
        _tts_conversacion("Ya estamos en una conversación.")
        return

    if conversacion.es_orden_callar(texto):
        print("[Conversación] No estoy hablando; sigo escuchando.")
        return

    respuesta = preguntar_ia.preguntar(texto)
    interrumpido = _tts_conversacion(respuesta)
    if interrumpido:
        print("[Conversación] Listo. Dime lo siguiente.")


def bucle_principal():
    escuchador.VERVOSE = VERVOSE
    import conversacion

    print("=== ASISTENTE VIRTUAL INICIADO (Modo Voz) ===")
    if VERVOSE:
        print(
            f"[Modo] DEV={'ON' if DEV else 'OFF'} | "
            f"VERVOSE={'ON' if VERVOSE else 'OFF'} "
            f"(consola {'visible' if DEV else 'oculta'})"
        )
    print(
        f'Di "{escuchador.NOMBRE_ASISTENTE}" o "escucha" para activarlo. '
        "Puedes encadenar el comando: «escucha qué hora es»."
    )
    print(
        'Conversación: «inicia una conversación» → habla libre → '
        "«para»/«calla» corta la respuesta → «fin de la conversación»."
    )
    escuchador.obtener_microfono()

    while True:
        if conversacion.esta_activa():
            _turno_conversacion()
            continue

        texto_usuario = escuchador.esperar_comando_activado()

        if not texto_usuario:
            continue

        print(f"Tú dijiste: {texto_usuario}")
        orquestador.evaluar_comando(texto_usuario)


if __name__ == "__main__":
    os.chdir(rutas.RAIZ)
    configurar_visibilidad_consola()
    try:
        bucle_principal()
    except KeyboardInterrupt:
        if DEV:
            print("\n[Asistente]: Programa finalizado.")

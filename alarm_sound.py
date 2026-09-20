"""
Reproduce el WAV de una alarma por el dispositivo de audio predeterminado de Windows.

Uso:
  python alarm_sound.py ruta\\archivo.wav
  python alarm_sound.py 60 ruta\\archivo.wav [id]
"""
import json
import os
import sys
import time

REPETICIONES = 3
PAUSA_ENTRE_REPETICIONES = 0.45  # segundos entre cada "Alarma. Es la hora."


def _quitar_del_registro(alarm_id: str = None, ruta_wav: str = None) -> None:
    ruta = os.path.join(os.getcwd(), "alarmas", "registro.json")
    try:
        if not os.path.isfile(ruta):
            return
        with open(ruta, "r", encoding="utf-8") as f:
            entradas = json.load(f)
        if not isinstance(entradas, list):
            return
        wav_abs = os.path.abspath(ruta_wav) if ruta_wav else None
        filtradas = []
        for e in entradas:
            if alarm_id and e.get("id") == alarm_id:
                continue
            if wav_abs and os.path.abspath(e.get("wav") or "") == wav_abs:
                continue
            filtradas.append(e)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(filtradas, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Alarma] No se pudo actualizar el registro: {e}")


def _reproducir_windows(ruta_wav: str) -> None:
    """Usa la API nativa de Windows (dispositivo predeterminado del sistema)."""
    import winsound

    winsound.PlaySound(ruta_wav, winsound.SND_FILENAME)


def _reproducir_pygame(ruta_wav: str) -> None:
    """Reserva por si winsound no está disponible."""
    import pygame

    os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.mixer.music.load(ruta_wav)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    time.sleep(0.2)
    pygame.mixer.quit()


def _reproducir_insistente(ruta_wav: str, usar_windows: bool) -> None:
    for i in range(1, REPETICIONES + 1):
        print(f"[Alarma] Tocando {i}/{REPETICIONES}...")
        if usar_windows:
            _reproducir_windows(ruta_wav)
        else:
            _reproducir_pygame(ruta_wav)
        if i < REPETICIONES:
            time.sleep(PAUSA_ENTRE_REPETICIONES)


def main():
    args = sys.argv[1:]
    if not args:
        print("[Alarma] Uso: python alarm_sound.py [segundos] ruta.wav [id]")
        sys.exit(1)

    espera = 0
    alarm_id = ""
    if len(args) >= 2 and args[0].isdigit():
        espera = int(args[0])
        ruta_wav = args[1]
        if len(args) >= 3:
            alarm_id = args[2]
    else:
        ruta_wav = args[0]
        if len(args) >= 2:
            alarm_id = args[1]

    ruta_wav = os.path.abspath(ruta_wav)
    if not os.path.isfile(ruta_wav):
        print(f"[Alarma] No existe el archivo: {ruta_wav}")
        sys.exit(1)

    if espera > 0:
        print(f"[Alarma] Esperando {espera}s antes de sonar...")
        time.sleep(espera)

    _quitar_del_registro(alarm_id=alarm_id or None, ruta_wav=ruta_wav)

    print(f"[Alarma] Reproduciendo x{REPETICIONES} (dispositivo predeterminado): {ruta_wav}")
    try:
        _reproducir_insistente(ruta_wav, usar_windows=(sys.platform == "win32"))
        print("[Alarma] Reproducción finalizada.")
    except Exception as e:
        print(f"[Alarma] Falló winsound ({e}). Probando pygame...")
        try:
            _reproducir_insistente(ruta_wav, usar_windows=False)
            print("[Alarma] Reproducción finalizada (pygame).")
        except Exception as e2:
            print(f"[Alarma] Error de audio: {e2}")
            sys.exit(1)


if __name__ == "__main__":
    main()

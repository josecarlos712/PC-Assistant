"""Programa una alarma con timeout de Windows + reproducción de un WAV TTS."""
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

import alarmas_registro
import uuid

MENSAJE_ALARMA_DEFAULT = "Alarma. Es la hora."
TIMEOUT_MAX_SEGUNDOS = 99999
CARPETA_ALARMAS = "alarmas"

NUMEROS = {
    "cero": 0,
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "dieciséis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintidós": 22,
    "veintitres": 23,
    "veintitrés": 23,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "media": 30,
    "cuarto": 15,
}


def _a_entero(token: str):
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return NUMEROS.get(token)


def _segundos_hasta(hora: int, minuto: int) -> int:
    ahora = datetime.now()
    objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return max(1, int((objetivo - ahora).total_seconds()))


def _quitar_expresiones_de_tiempo(texto: str) -> str:
    """Elimina plazos/horas del texto para dejar solo el título."""
    t = texto
    t = re.sub(
        r"\b(?:en|dentro\s+de)\s+(\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
        r"once|doce|quince|veinte|treinta|cuarenta|cincuenta|media)\s+"
        r"(segundos?|minutos?|horas?)\b",
        " ",
        t,
    )
    t = re.sub(r"\ben\s+media\s+hora\b", " ", t)
    t = re.sub(r"\ben\s+un\s+cuarto\s+de\s+hora\b", " ", t)
    t = re.sub(r"\ba\s+las?\s+\d{1,2}[:\.]\d{2}\b", " ", t)
    t = re.sub(
        r"\ba\s+las?\s+(\d{1,2}|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|"
        r"diez|once|doce|trece|catorce|quince|dieciseis|dieciséis|diecisiete|"
        r"dieciocho|diecinueve|veinte|veintiuno|veintiuna|veintidos|veintidós|"
        r"veintitres|veintitrés)"
        r"(?:\s+y\s+(\d{1,2}|cero|cinco|diez|quince|veinte|media|cuarto))?"
        r"(?:\s+en\s+punto)?\b",
        " ",
        t,
    )
    return " ".join(t.split()).strip(" .,;:")


def _extraer_titulo(texto: str) -> str:
    """
    Título opcional tras 'para' / 'de' / 'llamada'.
    Ej.: 'en un minuto para sacar el pollo' -> 'sacar el pollo'
    """
    t = " ".join(texto.lower().split())

    m = re.search(r"\b(?:para|llamada|titulada|sobre)\s+(.+)$", t)
    if not m:
        m = re.search(r"\bde\s+(.+)$", t)
        if m:
            candidato = m.group(1).strip()
            # Evitar falsos positivos: "cuarto de hora", "de la tarde", etc.
            if re.match(
                r"^(hora|minuto|la\s+tarde|la\s+mañana|la\s+noche|punto)\b",
                candidato,
            ):
                return ""
    if not m:
        return ""

    titulo = _quitar_expresiones_de_tiempo(m.group(1))
    # Si pedía "para alarma" o quedó vacío, no hay título útil
    if not titulo or titulo in {"alarma", "alarme", "alarm"}:
        return ""
    return titulo


def _mensaje_voz_alarma(titulo: str) -> str:
    if not titulo:
        return MENSAJE_ALARMA_DEFAULT
    if titulo.startswith("para "):
        return f"Alarma {titulo}."
    return f"Alarma para {titulo}."


def _parsear_tiempo(texto: str):
    """
    Devuelve (segundos, descripcion_humana) o (None, motivo_error).
    Acepta relativo (en/dentro de X segundos/minutos/horas) o absoluto (a las HH[:MM]).
    """
    t = " ".join(texto.lower().split())

    # --- Relativo (segundos, minutos u horas) ---
    m = re.search(
        r"\b(?:en|dentro\s+de)\s+(\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
        r"once|doce|quince|veinte|treinta|cuarenta|cincuenta|media)\s+"
        r"(segundos?|minutos?|horas?)\b",
        t,
    )
    if m:
        cantidad = _a_entero(m.group(1))
        unidad = m.group(2)
        if cantidad is None:
            return None, "No entendí la cantidad de tiempo."
        if unidad.startswith("segundo"):
            segundos = max(1, cantidad)
            etiqueta = "segundo" if segundos == 1 else "segundos"
            return segundos, f"en {segundos} {etiqueta}"
        if unidad.startswith("hora"):
            if m.group(1) == "media":
                segundos = 30 * 60
                return segundos, "en media hora"
            segundos = cantidad * 3600
            etiqueta = "hora" if cantidad == 1 else "horas"
            return segundos, f"en {cantidad} {etiqueta}"
        segundos = cantidad * 60
        etiqueta = "minuto" if cantidad == 1 else "minutos"
        return segundos, f"en {cantidad} {etiqueta}"

    if re.search(r"\ben\s+media\s+hora\b", t):
        return 30 * 60, "en media hora"
    if re.search(r"\ben\s+un\s+cuarto\s+de\s+hora\b", t):
        return 15 * 60, "en un cuarto de hora"

    # --- Absolute: a las 8:30 / 8.30 / 8 ---
    m = re.search(r"\ba\s+las?\s+(\d{1,2})[:\.](\d{2})\b", t)
    if m:
        hora, minuto = int(m.group(1)), int(m.group(2))
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            return None, "La hora no es válida."
        segundos = _segundos_hasta(hora, minuto)
        return segundos, f"a las {hora:02d}:{minuto:02d}"

    m = re.search(
        r"\ba\s+las?\s+(\d{1,2}|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|"
        r"diez|once|doce|trece|catorce|quince|dieciseis|dieciséis|diecisiete|"
        r"dieciocho|diecinueve|veinte|veintiuno|veintiuna|veintidos|veintidós|"
        r"veintitres|veintitrés)"
        r"(?:\s+y\s+(\d{1,2}|cero|cinco|diez|quince|veinte|media|cuarto))?"
        r"(?:\s+en\s+punto)?\b",
        t,
    )
    if m:
        hora = _a_entero(m.group(1))
        minuto = _a_entero(m.group(2)) if m.group(2) else 0
        if hora is None or minuto is None:
            return None, "No entendí la hora de la alarma."
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            return None, "La hora no es válida."
        segundos = _segundos_hasta(hora, minuto)
        return segundos, f"a las {hora:02d}:{minuto:02d}"

    return None, "Indica una hora, por ejemplo: a las 8:30, en 20 segundos, o en 10 minutos."


def _generar_wav_alarma(ruta_wav: str, texto: str) -> bool:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    modelo = os.path.join(base, "voices", "Dave", "es_ES-davefx-medium.onnx")
    if not os.path.isfile(modelo):
        print(f"[Alarma] No se encuentra el modelo Piper: {modelo}")
        return False

    # Misma normalización que read_file: Dave lee peor las tildes
    _tildes = str.maketrans("áéíóúüÁÉÍÓÚÜ", "aeiouuAEIOUU")
    texto = (texto or "").translate(_tildes)

    os.makedirs(os.path.dirname(ruta_wav), exist_ok=True)
    temp_txt = ruta_wav + ".txt"
    # piper.exe falla en este entorno; el módulo Python es el camino fiable
    comando = [
        sys.executable,
        "-m",
        "piper",
        "--model",
        modelo,
        "--output_file",
        ruta_wav,
    ]
    try:
        with open(temp_txt, "w", encoding="utf-8", errors="replace") as f:
            f.write(texto)
        with open(temp_txt, "r", encoding="utf-8", errors="ignore") as f_in:
            resultado = subprocess.run(
                comando,
                stdin=f_in,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=base,
                text=True,
            )
        if resultado.returncode != 0:
            print(f"[Alarma] Piper exit={resultado.returncode}")
            if resultado.stderr:
                print(f"[Alarma] Piper stderr: {resultado.stderr.strip()[:500]}")
            return False
        return os.path.isfile(ruta_wav) and os.path.getsize(ruta_wav) > 0
    except Exception as e:
        print(f"[Alarma] Error generando WAV: {e}")
        return False
    finally:
        if os.path.exists(temp_txt):
            try:
                os.remove(temp_txt)
            except OSError:
                pass


def _lanzar_timeout(segundos: int, ruta_wav: str, alarm_id: str = ""):
    """
    Lanza un proceso en segundo plano que espera N segundos y reproduce el WAV.
    Usa el mismo intérprete Python (no cmd timeout): así el audio puede abrir
    el dispositivo predeterminado de Windows sin consola interactiva.
    """
    base = os.getcwd()
    alarm_sound = os.path.join(base, "alarm_sound.py")
    python = sys.executable

    flags = 0
    if os.name == "nt":
        # Sin ventana: winsound usa el dispositivo predeterminado del sistema
        # y no necesita consola (a diferencia de pygame en proceso detached).
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    try:
        args = [python, alarm_sound, str(int(segundos)), ruta_wav]
        if alarm_id:
            args.append(alarm_id)
        proc = subprocess.Popen(
            args,
            cwd=base,
            creationflags=flags,
            close_fds=False,
        )
        return proc
    except Exception as e:
        print(f"[Alarma] No se pudo lanzar el proceso de alarma: {e}")
        return None


def ejecutar(match):
    resto = ""
    frase_completa = ""
    if match is not None:
        frase_completa = (match.group(0) or "").strip()
        if match.lastindex:
            resto = (match.group(1) or "").strip()
        if not resto:
            resto = frase_completa

    texto_trabajo = resto or frase_completa
    titulo = _extraer_titulo(texto_trabajo)
    if not titulo and frase_completa:
        titulo = _extraer_titulo(frase_completa)

    # Si el grupo capturado no trae el plazo, buscar en toda la frase
    segundos, detalle = _parsear_tiempo(texto_trabajo)
    if segundos is None and frase_completa and frase_completa != texto_trabajo:
        segundos, detalle = _parsear_tiempo(frase_completa)
    if segundos is None:
        return detalle

    if segundos > TIMEOUT_MAX_SEGUNDOS:
        return (
            "Esa alarma queda demasiado lejos. "
            "Prueba con un plazo menor de unas 27 horas."
        )

    mensaje_wav = _mensaje_voz_alarma(titulo)
    base = os.getcwd()
    carpeta = os.path.join(base, CARPETA_ALARMAS)
    os.makedirs(carpeta, exist_ok=True)
    nombre = datetime.now().strftime("alarma_%Y%m%d_%H%M%S.wav")
    ruta_wav = os.path.join(carpeta, nombre)

    if not _generar_wav_alarma(ruta_wav, mensaje_wav):
        return "No pude preparar el sonido de la alarma."

    alarm_id = uuid.uuid4().hex[:12]
    proc = _lanzar_timeout(segundos, ruta_wav, alarm_id=alarm_id)
    if proc is None:
        return "No pude programar la alarma en el sistema."

    alarmas_registro.registrar(
        pid=proc.pid,
        segundos=segundos,
        titulo=titulo,
        ruta_wav=ruta_wav,
        alarm_id=alarm_id,
    )
    print(f"[Alarma] id={alarm_id} '{mensaje_wav}' en {segundos}s → {ruta_wav}")
    if titulo:
        return f"De acuerdo. Alarma para {titulo} programada {detalle}."
    return f"De acuerdo. Alarma programada {detalle}."

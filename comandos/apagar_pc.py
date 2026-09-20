"""Apaga el PC: al momento, o tras un plazo si se indica."""
import os
import re
import subprocess
import sys

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
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "media": 30,
}


def _a_entero(token: str):
    token = (token or "").strip().lower()
    if token.isdigit():
        return int(token)
    return NUMEROS.get(token)


def _parsear_plazo(texto: str):
    """
    Devuelve (segundos, detalle_humano) o (0, None) si no hay plazo
    (apagado inmediato). Si el plazo es inválido: (None, mensaje_error).
    """
    t = " ".join((texto or "").lower().split())
    if not t:
        return 0, None

    if re.search(r"\ben\s+media\s+hora\b", t):
        return 30 * 60, "en media hora"
    if re.search(r"\ben\s+un\s+cuarto\s+de\s+hora\b", t):
        return 15 * 60, "en un cuarto de hora"

    m = re.search(
        r"\b(?:en|dentro\s+de)\s+(\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
        r"once|doce|quince|veinte|treinta|cuarenta|cincuenta|media)\s+"
        r"(segundos?|minutos?|horas?)\b",
        t,
    )
    if not m:
        # Hay texto extra pero no un plazo reconocible
        return None, "No entendí el plazo. Di por ejemplo: apaga el ordenador en 10 minutos."

    cantidad = _a_entero(m.group(1))
    unidad = m.group(2)
    if cantidad is None:
        return None, "No entendí la cantidad de tiempo."

    if unidad.startswith("segundo"):
        segundos = max(0, cantidad)
        etiqueta = "segundo" if segundos == 1 else "segundos"
        return segundos, f"en {segundos} {etiqueta}"
    if unidad.startswith("hora"):
        if m.group(1) == "media":
            return 30 * 60, "en media hora"
        segundos = cantidad * 3600
        etiqueta = "hora" if cantidad == 1 else "horas"
        return segundos, f"en {cantidad} {etiqueta}"

    segundos = cantidad * 60
    etiqueta = "minuto" if cantidad == 1 else "minutos"
    return segundos, f"en {cantidad} {etiqueta}"


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


def _iniciar_apagado(segundos: int, comentario: str) -> bool:
    try:
        subprocess.run(
            [
                "shutdown",
                "/s",
                "/t",
                str(max(0, int(segundos))),
                "/c",
                comentario,
            ],
            check=True,
        )
        return True
    except Exception:
        return False


def ejecutar(match):
    resto = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                resto = g.strip()
                break

    segundos, detalle = _parsear_plazo(resto)
    if segundos is None:
        return detalle

    if segundos == 0:
        # Hablar antes: /t 0 corta el proceso al instante
        _decir("Apagando el equipo ahora.")
        ok = _iniciar_apagado(
            0,
            "Apagado inmediato solicitado por el asistente.",
        )
        if not ok:
            return "No pude iniciar el apagado del equipo."
        return ""

    ok = _iniciar_apagado(
        segundos,
        f"El asistente apagará el PC {detalle}.",
    )
    if not ok:
        return "No pude iniciar el apagado del equipo."
    return (
        f"Apagando el equipo {detalle}. "
        "Para cancelar, di: cancela el apagado."
    )

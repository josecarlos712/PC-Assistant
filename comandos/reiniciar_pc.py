"""Reinicia el PC: al momento, o tras un plazo si se indica."""
import subprocess

from apagar_pc import _decir, _parsear_plazo


def _iniciar_reinicio(segundos: int, comentario: str) -> bool:
    try:
        subprocess.run(
            [
                "shutdown",
                "/r",
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
        _decir("Reiniciando el equipo ahora.")
        ok = _iniciar_reinicio(
            0,
            "Reinicio inmediato solicitado por el asistente.",
        )
        if not ok:
            return "No pude iniciar el reinicio del equipo."
        return ""

    ok = _iniciar_reinicio(
        segundos,
        f"El asistente reiniciará el PC {detalle}.",
    )
    if not ok:
        return "No pude iniciar el reinicio del equipo."
    return (
        f"Reiniciando el equipo {detalle}. "
        "Para cancelar, di: cancela el apagado."
    )

"""Bloquea la sesión de Windows."""
import subprocess


def ejecutar(match):
    try:
        subprocess.run(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            check=False,
        )
        return "Bloqueando el equipo."
    except Exception:
        return "No pude bloquear el equipo."

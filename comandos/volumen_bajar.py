import subprocess
import os


def _nircmd() -> str:
    try:
        import rutas
        return str(rutas.NIRCMD)
    except ImportError:
        return os.path.join(os.getcwd(), "nircmd.exe")


def ejecutar(match):
    try:
        subprocess.run([_nircmd(), "changesysvolume", "-2000"], check=True)
        return "Bajando el volumen."
    except Exception:
        return "No pude bajar el volumen del sistema."

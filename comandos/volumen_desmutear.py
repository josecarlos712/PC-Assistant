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
        subprocess.run([_nircmd(), "mutesysvolume", "0"], check=True)
        return "Sonido activado."
    except Exception:
        return "No se pudo activar el sonido del sistema."

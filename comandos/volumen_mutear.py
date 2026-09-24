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
        subprocess.run([_nircmd(), "mutesysvolume", "1"], check=True)
        return "Cambiando a estado de silencio."
    except Exception:
        return "No se pudo alterar el silencio del sistema."

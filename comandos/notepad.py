import subprocess

def ejecutar(match):
    try:
        subprocess.Popen(["notepad.exe"], start_new_session=True)
        return "Abriendo el bloc de notas."
    except Exception:
        return "No pude abrir el bloc de notas debido a un error del sistema."
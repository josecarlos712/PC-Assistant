import subprocess
import os

def ejecutar(match):
    try:
        ruta_nircmd = os.path.join(os.getcwd(), "nircmd.exe")
        
        # 'changesysvolume 2000' incrementa el volumen maestro directamente
        subprocess.run([ruta_nircmd, "changesysvolume", "2000"], check=True)
        return "Subiendo el volumen."
    except Exception as e:
        return "No pude subir el volumen del sistema."
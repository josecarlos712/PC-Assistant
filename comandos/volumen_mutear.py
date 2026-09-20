import subprocess
import os

def ejecutar(match):
    try:
        # Buscamos nircmd en la raíz del proyecto de forma relativa
        ruta_nircmd = os.path.join(os.getcwd(), "nircmd.exe")
        
        # 'mutesysvolume 2' alterna entre mutear y desmutear de forma nativa
        subprocess.run([ruta_nircmd, "mutesysvolume", "1"], check=True)
        return "Cambiando a estado de silencio."
    except Exception as e:
        return "No se pudo alterar el silencio del sistema."
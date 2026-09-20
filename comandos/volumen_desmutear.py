import subprocess
import os

def ejecutar(match):
    try:
        # Localizamos el ejecutable nircmd en la raíz del proyecto
        ruta_nircmd = os.path.join(os.getcwd(), "nircmd.exe")
        
        # 'mutesysvolume 0' fuerza a Windows a desactivar el estado de silencio (Mute Off)
        subprocess.run([ruta_nircmd, "mutesysvolume", "0"], check=True)
        return "Sonido activado."
    except Exception as e:
        return "No pude activar el sonido del sistema."
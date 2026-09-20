"""Guarda una captura de pantalla y la copia al portapapeles de Windows."""
import os
import subprocess
from datetime import datetime


def _captura_powershell(ruta_png: str) -> bool:
    """Captura, guarda PNG y pone la imagen en el portapapeles (requiere -STA)."""
    ruta_ps = ruta_png.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('{ruta_ps}')
[System.Windows.Forms.Clipboard]::SetImage($bitmap)
$graphics.Dispose()
$bitmap.Dispose()
"""
    try:
        subprocess.run(
            ["powershell", "-STA", "-NoProfile", "-Command", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return os.path.isfile(ruta_png) and os.path.getsize(ruta_png) > 0
    except Exception:
        return False


def _copiar_png_al_portapapeles(ruta_png: str) -> bool:
    """Copia un PNG ya guardado al portapapeles."""
    ruta_ps = ruta_png.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile('{ruta_ps}')
[System.Windows.Forms.Clipboard]::SetImage($img)
$img.Dispose()
"""
    try:
        subprocess.run(
            ["powershell", "-STA", "-NoProfile", "-Command", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _captura_nircmd(ruta_png: str) -> bool:
    nircmd = os.path.join(os.getcwd(), "nircmd.exe")
    if not os.path.isfile(nircmd):
        return False
    try:
        subprocess.run([nircmd, "savescreenshot", ruta_png], check=True)
        return os.path.isfile(ruta_png) and os.path.getsize(ruta_png) > 0
    except Exception:
        return False


def ejecutar(match):
    carpeta = os.path.join(os.getcwd(), "capturas")
    os.makedirs(carpeta, exist_ok=True)
    nombre = datetime.now().strftime("captura_%Y%m%d_%H%M%S.png")
    ruta = os.path.join(carpeta, nombre)

    if _captura_powershell(ruta):
        return "Captura guardada."

    # Reserva: nircmd guarda el archivo y luego lo mandamos al portapapeles
    if _captura_nircmd(ruta):
        _copiar_png_al_portapapeles(ruta)
        return "Captura guardada."

    return "No pude tomar la captura de pantalla."

"""Guarda una nota rápida en notas/ y la copia al portapapeles."""
import os
import subprocess
from datetime import datetime

CARPETA_NOTAS = "notas"


def _copiar_portapapeles(texto: str) -> bool:
    """Copia texto Unicode al portapapeles de Windows."""
    try:
        # Set-Clipboard maneja bien Unicode y saltos de línea
        completado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Set-Clipboard -Value $input",
            ],
            input=texto,
            text=True,
            encoding="utf-8",
            check=False,
            capture_output=True,
        )
        return completado.returncode == 0
    except Exception as e:
        print(f"[Nota] Portapapeles: {e}")
        return False


def ejecutar(match):
    contenido = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                contenido = g.strip()
                break

    if not contenido:
        return "Dime qué quieres anotar."

    base = os.getcwd()
    carpeta = os.path.join(base, CARPETA_NOTAS)
    os.makedirs(carpeta, exist_ok=True)

    ahora = datetime.now()
    nombre = ahora.strftime("nota_%Y%m%d_%H%M%S.txt")
    ruta = os.path.join(carpeta, nombre)

    cuerpo = (
        f"Fecha: {ahora.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'-' * 40}\n"
        f"{contenido}\n"
    )

    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(cuerpo)
    except Exception as e:
        print(f"[Nota] No se pudo guardar: {e}")
        return "No pude guardar la nota."

    copiado = _copiar_portapapeles(contenido)
    print(f"[Nota] Guardada: {ruta} | portapapeles={'OK' if copiado else 'falló'}")

    if copiado:
        return "Nota guardada y copiada al portapapeles."
    return "Nota guardada, pero no pude copiarla al portapapeles."

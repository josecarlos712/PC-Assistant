import subprocess
import time
import re
import os

import rutas


def procesar_archivo_a_tts(
    archivo_entrada=None,
    modelo_piper=None,
    carpeta_salida=None,
):
    directorio_base = str(rutas.RAIZ)
    archivo_entrada = archivo_entrada or str(rutas.INPUT_TTS)
    modelo_piper = modelo_piper or str(rutas.MODELO_PIPER)
    carpeta_salida = carpeta_salida or str(rutas.OUTPUT_TTS)

    ruta_entrada_absoluta = (
        archivo_entrada
        if os.path.isabs(archivo_entrada)
        else os.path.join(directorio_base, archivo_entrada)
    )
    ruta_salida_absoluta = (
        carpeta_salida
        if os.path.isabs(carpeta_salida)
        else os.path.join(directorio_base, carpeta_salida)
    )
    ruta_modelo_absoluta = (
        modelo_piper
        if os.path.isabs(modelo_piper)
        else os.path.join(directorio_base, modelo_piper)
    )

    if not os.path.exists(ruta_entrada_absoluta):
        print(f"Error crítico: No se encuentra el archivo de entrada en {ruta_entrada_absoluta}")
        return

    try:
        with open(ruta_entrada_absoluta, "r", encoding="utf-8") as f:
            texto = f.read()
    except Exception as e:
        print(f"Error al leer el archivo {archivo_entrada}: {e}")
        return

    if not texto.strip():
        print(f"El archivo '{archivo_entrada}' está vacío.")
        return

    if not os.path.exists(ruta_salida_absoluta):
        os.makedirs(ruta_salida_absoluta)

    if os.name == "nt":
        ruta_piper = os.path.join(directorio_base, "venv", "Scripts", "piper.exe")
    else:
        ruta_piper = os.path.join(directorio_base, "venv", "bin", "piper")

    if not os.path.exists(ruta_piper):
        print(f"Error crítico: No se encontró piper en {ruta_piper}")
        return

    id_lote = time.strftime("%Y%m%d_%H%M%S")
    print(f"Leyendo texto de: '{archivo_entrada}'")
    print(f"Iniciando lote de audios con ID: {id_lote}")

    frases = re.split(r"(?<=\.)\s+", texto.strip())
    contador = 1

    ruta_temporal = str(rutas.DATOS / "temp_frase.txt")
    rutas.DATOS.mkdir(parents=True, exist_ok=True)

    for frase in frases:
        frase_limpia = frase.strip()
        if not frase_limpia:
            continue

        nombre_archivo = f"{id_lote}_parte_{contador:02d}.wav"
        ruta_archivo = os.path.join(ruta_salida_absoluta, nombre_archivo)

        try:
            with open(ruta_temporal, "w", encoding="cp1252", errors="replace") as f_temp:
                f_temp.write(frase_limpia)
        except Exception as e:
            print(f"Error al preparar archivo temporal: {e}")

        comando = [
            ruta_piper,
            "--model",
            ruta_modelo_absoluta,
            "--output_file",
            ruta_archivo,
        ]

        try:
            with open(ruta_temporal, "r", encoding="cp1252", errors="ignore") as f_temp_read:
                subprocess.run(
                    comando,
                    stdin=f_temp_read,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            print(f" -> Generado: {nombre_archivo} (Texto: '{frase_limpia[:40]}...')")

        except subprocess.CalledProcessError as e:
            error_real = e.stderr.decode("utf-8", errors="ignore").strip()
            print(f" [!] Error al generar la parte {contador}.")
            print(f"     Detalle de Piper: {error_real}")

        contador += 1

    if os.path.exists(ruta_temporal):
        os.remove(ruta_temporal)


if __name__ == "__main__":
    procesar_archivo_a_tts()
    print("¡Procesamiento finalizado!")

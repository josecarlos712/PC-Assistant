import subprocess
import time
import re
import os

def procesar_archivo_a_tts(archivo_entrada="input_tts.txt", modelo_piper="voices/Dave/es_ES-davefx-medium.onnx", carpeta_salida="output_tts"):
    directorio_base = os.path.dirname(os.path.abspath(__file__))
    
    ruta_entrada_absoluta = os.path.join(directorio_base, archivo_entrada)
    ruta_salida_absoluta = os.path.join(directorio_base, carpeta_salida)
    ruta_modelo_absoluta = os.path.join(directorio_base, modelo_piper)

    # 1. Comprobar si el archivo de texto de entrada existe
    if not os.path.exists(ruta_entrada_absoluta):
        print(f"Error crítico: No se encuentra el archivo de entrada en {ruta_entrada_absoluta}")
        return

    # 2. Leer el contenido del archivo original (usualmente UTF-8 desde Notepad++)
    try:
        with open(ruta_entrada_absoluta, "r", encoding="utf-8") as f:
            texto = f.read()
    except Exception as e:
        print(f"Error al leer el archivo {archivo_entrada}: {e}")
        return

    if not texto.strip():
        print(f"El archivo '{archivo_entrada}' está vacío.")
        return

    # 3. Crear carpeta de salida si no existe
    if not os.path.exists(ruta_salida_absoluta):
        os.makedirs(ruta_salida_absoluta)

    # 4. Definir la ruta al ejecutable de Piper en el venv
    if os.name == 'nt':  # Windows
        ruta_piper = os.path.join(directorio_base, "venv", "Scripts", "piper.exe")
    else:                # Linux
        ruta_piper = os.path.join(directorio_base, "venv", "bin", "piper")

    if not os.path.exists(ruta_piper):
        print(f"Error crítico: No se encontró piper en {ruta_piper}")
        return

    id_lote = time.strftime("%Y%m%d_%H%M%S")
    print(f"Leyendo texto de: '{archivo_entrada}'")
    print(f"Iniciando lote de audios con ID: {id_lote}")

    # Separar el texto en frases conservando los puntos
    frases = re.split(r'(?<=\.)\s+', texto.strip())
    contador = 1
    
    # Definimos la ruta de un archivo temporal
    ruta_temporal = os.path.join(directorio_base, "temp_frase.txt")
    
    for frase in frases:
        frase_limpia = frase.strip()
        if not frase_limpia:
            continue

        nombre_archivo = f"{id_lote}_parte_{contador:02d}.wav"
        ruta_archivo = os.path.join(ruta_salida_absoluta, nombre_archivo)

        # SOLUCIÓN MAESTRA: Guardamos el archivo temporal usando la codificación 
        # nativa de Windows (cp1252). Al abrirlo en este formato, Windows no tiene 
        # que hacer ninguna conversión interna extraña y Piper recibirá la 'á' 
        # como un único byte válido (0xE1) en lugar de una secuencia rota de UTF-8.
        try:
            with open(ruta_temporal, "w", encoding="cp1252", errors="replace") as f_temp:
                f_temp.write(frase_limpia)
        except Exception as e:
            print(f"Error al preparar archivo temporal: {e}")

        comando = [
            ruta_piper,
            "--model", ruta_modelo_absoluta,
            "--output_file", ruta_archivo
        ]

        try:
            # Le pasamos el archivo temporal codificado en formato nativo de Windows
            with open(ruta_temporal, "r", encoding="cp1252", errors="ignore") as f_temp_read:
                subprocess.run(
                    comando,
                    stdin=f_temp_read,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE 
                )
            print(f" -> Generado: {nombre_archivo} (Texto: '{frase_limpia[:40]}...')")
            
        except subprocess.CalledProcessError as e:
            error_real = e.stderr.decode('utf-8', errors='ignore').strip()
            print(f" [!] Error al generar la parte {contador}.")
            print(f"     Detalle de Piper: {error_real}")
        
        contador += 1

    # Limpieza final del archivo temporal
    if os.path.exists(ruta_temporal):
        os.remove(ruta_temporal)

if __name__ == "__main__":
    procesar_archivo_a_tts()
    print("¡Procesamiento finalizado!")
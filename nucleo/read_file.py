import subprocess
import time
import re
import os
import sys
import threading
import queue
import pygame
import hashlib
import json
import shutil

import rutas

# ==========================================
# CONFIGURACIÓN GENERAL Y RUTAS GLOBALES
# ==========================================
UMBRAL_POPULARIDAD = 3  # Veces que debe repetirse una frase para pasar a caché permanente
HOLGURA_JSON = 50       # Margen dinámico de frases nuevas en el JSON

DIRECTORIO_BASE = str(rutas.RAIZ)
RUTA_ENTRADA_ABSOLUTA = str(rutas.INPUT_TTS)
RUTA_SALIDA_ABSOLUTA = str(rutas.OUTPUT_TTS)
RUTA_MODELO_ABSOLUTA = str(rutas.MODELO_PIPER)
RUTA_CARPETA_CACHE = str(rutas.CACHE_TTS)
RUTA_JSON_REGISTRO = str(rutas.CACHE_REGISTRO)

# Inicializar el mezclador de audio de pygame y la cola de hilos
pygame.mixer.init()
cola_reproduccion = queue.Queue()


# ==========================================
# MÓDULO DE CACHÉ Y LIMPIEZA INTELIGENTE
# ==========================================
def calcular_md5(texto):
    """Genera un hash único de 32 caracteres para una frase."""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def cargar_registro_cache():
    """Lee el archivo JSON de la caché utilizando la ruta global."""
    if os.path.exists(RUTA_JSON_REGISTRO):
        try:
            with open(RUTA_JSON_REGISTRO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def limpiar_registro_json(registro_cache):
    """
    Algoritmo del programador: Recolección de basura dinámica en el JSON.
    Límite máximo = (Frases en caché permanente) + HOLGURA_JSON (50)
    """
    permanentes = [k for k, v in registro_cache.items() if v["en_cache_permanente"]]
    num_permanentes = len(permanentes)
    
    limite_maximo = num_permanentes + HOLGURA_JSON
    total_frases_json = len(registro_cache)
    
    # Si no superamos el techo dinámico, mantenemos todo intacto
    if total_frases_json <= limite_maximo:
        return registro_cache

    print(f"\n[Mantenimiento JSON] El registro tiene {total_frases_json} entradas. Límite dinámico alcanzado ({limite_maximo}).")
    
    # Separamos las frases que aún son temporales y las ordenamos de menos a más usadas
    temporales = [k for k, v in registro_cache.items() if not v["en_cache_permanente"]]
    temporales.sort(key=lambda k: registro_cache[k]["contador"])
    
    # Calculamos cuántas borrar para volver a estar bajo el límite
    cuantas_purgar = total_frases_json - limite_maximo
    print(f"[Mantenimiento JSON] Purgando las {cuantas_purgar} frases temporales menos utilizadas...")
    
    for i in range(min(cuantas_purgar, len(temporales))):
        hash_a_eliminar = temporales[i]
        del registro_cache[hash_a_eliminar]
        
    return registro_cache


def guardar_registro_cache(datos):
    """Aplica la limpieza dinámica y guarda el JSON usando la ruta global."""
    try:
        datos_limpios = limpiar_registro_json(datos)
        with open(RUTA_JSON_REGISTRO, "w", encoding="utf-8") as f:
            json.dump(datos_limpios, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Caché] Error al guardar registro JSON: {e}")


# ==========================================
# MÓDULO DE NORMALIZACIÓN DE TEXTO
# ==========================================
_TILDES = str.maketrans(
    "áéíóúüÁÉÍÓÚÜ",
    "aeiouuAEIOUU",
)


def quitar_tildes(texto: str) -> str:
    """Quita tildes/diéresis para que Piper/Dave las lea mejor. Conserva la ñ."""
    return (texto or "").translate(_TILDES)


def normalizar_simbolos(texto):
    """Busca símbolos domóticos y comunes en el texto y los traduce."""
    diccionario_simbolos = {
        r'°C': ' grados centígrados',
        r'°': ' grados',
        r'kW': ' kilovatios',
        r'W': ' vatios',
        r'%': ' por ciento',
        r'€': ' euros',
        r'\$': ' dólares',
        r'(?<=\d)h\b|\bh\b': ' horas',      
        r'(?<=\d)min\b|\bmin\b': ' minutos',
        r'\/': ' barra ',
        r'&': ' y ',
        r'\+': ' más ',
        r'[“”]': '"',
        r'[‘’]': "'",
    }
    for patron, reemplazo in diccionario_simbolos.items():
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)

    texto = quitar_tildes(texto)

    # Esto elimina emojis, caracteres asiáticos o símbolos extraños que harían que Dave diga "interrogación"
    texto = re.sub(r'[^a-zA-Z0-9ñÑ¡!¿?,.\s"\'\-]', '', texto)

    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


# ==========================================
# NÚCLEO DE EJECUCIÓN: HILOS Y SÍNTESIS
# ==========================================
def hilo_reproductor():
    """Hilo secundario: Monitorea la cola y reproduce el audio en orden."""
    print("[Reproductor] Hilo iniciado y a la espera de audios...")
    while True:
        ruta_audio = cola_reproduccion.get()
        if ruta_audio is None:
            break
            
        print(f"[Reproductor] -> Reproduciendo: {os.path.basename(ruta_audio)}")
        try:
            pygame.mixer.music.load(ruta_audio)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            time.sleep(0.1)  # Pausa entre frases
        except Exception as e:
            print(f"[Reproductor] Error al reproducir {ruta_audio}: {e}")
            
        cola_reproduccion.task_done()
    print("[Reproductor] Hilo finalizado.")
    
    # Limpiar la carpeta de audios antiguos tras terminar la reproducción.
    limpiar_carpeta_output()


def procesar_y_generar_tts():
    """Hilo Principal: Administra la caché, genera con Piper y encola las rutas."""
    if not os.path.exists(RUTA_ENTRADA_ABSOLUTA) or not os.path.exists(RUTA_MODELO_ABSOLUTA):
        print("Error crítico: Faltan archivos base (entrada o modelo).")
        return

    try:
        with open(RUTA_ENTRADA_ABSOLUTA, "r", encoding="utf-8") as f:
            texto = f.read()
    except Exception as e:
        print(f"Error al leer entrada: {e}")
        return

    if not texto.strip():
        return

    # Asegurar la existencia de las carpetas a nivel global
    if not os.path.exists(RUTA_SALIDA_ABSOLUTA): os.makedirs(RUTA_SALIDA_ABSOLUTA)
    if not os.path.exists(RUTA_CARPETA_CACHE): os.makedirs(RUTA_CARPETA_CACHE)

    registro_cache = cargar_registro_cache()

    # piper.exe falla en este entorno; usar el módulo Python del venv
    ruta_piper_cmd = [sys.executable, "-m", "piper"]

    hilo_audio = threading.Thread(target=hilo_reproductor, daemon=True)
    hilo_audio.start()

    id_lote = time.strftime("%Y%m%d_%H%M%S")
    print(f"[Generador] Procesando lote: {id_lote}")

    texto_normalizado = normalizar_simbolos(texto)
    frases = re.split(r'(?<=\.)\s+', texto_normalizado)
    contador = 1
    
    ruta_temporal = str(rutas.DATOS / "temp_frase.txt")
    
    for frase in frases:
        frase_limpia = frase.strip()
        if not frase_limpia:
            continue

        hash_frase = calcular_md5(frase_limpia)
        nombre_archivo = f"{id_lote}_parte_{contador:02d}.wav"
        ruta_archivo_final = os.path.join(RUTA_SALIDA_ABSOLUTA, nombre_archivo)
        
        if hash_frase not in registro_cache:
            registro_cache[hash_frase] = {
                "texto": frase_limpia,
                "contador": 0,
                "en_cache_permanente": False
            }

        ruta_audio_en_cache = os.path.join(RUTA_CARPETA_CACHE, f"{hash_frase}.wav")
        
        if registro_cache[hash_frase]["en_cache_permanente"] and os.path.exists(ruta_audio_en_cache):
            shutil.copy(ruta_audio_en_cache, ruta_archivo_final)
            print(f"[Generador]  [CACHÉ HIT] Recuperado instantáneamente: {nombre_archivo}")
            cola_reproduccion.put(ruta_archivo_final)
        else:
            try:
                with open(ruta_temporal, "w", encoding="utf-8", errors="replace") as f_temp:
                    f_temp.write(frase_limpia)
            except Exception as e:
                print(f"Error temporal: {e}")

            comando = ruta_piper_cmd + [
                "--model", RUTA_MODELO_ABSOLUTA,
                "--output_file", ruta_archivo_final,
            ]

            try:
                with open(ruta_temporal, "r", encoding="utf-8", errors="ignore") as f_temp_read:
                    resultado = subprocess.run(
                        comando,
                        stdin=f_temp_read,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                if resultado.returncode != 0:
                    detalle = (resultado.stderr or "").strip()[:300]
                    print(f"[Generador]  [!] Error Piper en parte {contador}: {detalle}")
                    contador += 1
                    continue
                
                print(f"[Generador]  [PIPER CALC] WAV Creado por CPU/GPU: {nombre_archivo}")
                cola_reproduccion.put(ruta_archivo_final)
                
                registro_cache[hash_frase]["contador"] += 1
                
                if registro_cache[hash_frase]["contador"] >= UMBRAL_POPULARIDAD and not registro_cache[hash_frase]["en_cache_permanente"]:
                    shutil.copy(ruta_archivo_final, ruta_audio_en_cache)
                    registro_cache[hash_frase]["en_cache_permanente"] = True
                    print(f"[Caché]      ¡Frase Promovida! '{frase_limpia[:20]}...' ahora es permanente.")
                    
            except Exception as e:
                print(f"[Generador] Error Piper/caché: {e}")

        contador += 1

    if os.path.exists(ruta_temporal):
        os.remove(ruta_temporal)

    guardar_registro_cache(registro_cache)

    print("[Generador] Esperando reproducción final...")
    cola_reproduccion.join()
    cola_reproduccion.put(None)
    hilo_audio.join()
    
    
def limpiar_carpeta_output(max_archivos=50):
    """Limpia la carpeta efímera utilizando la ruta global."""
    if not os.path.exists(RUTA_SALIDA_ABSOLUTA): return

    archivos = [os.path.join(RUTA_SALIDA_ABSOLUTA, f) for f in os.listdir(RUTA_SALIDA_ABSOLUTA) if f.endswith('.wav')]
    if len(archivos) > max_archivos:
        archivos.sort(key=os.path.getmtime)
        cuantos_borrar = len(archivos) - max_archivos
        print(f"\n[Limpieza] Se detectaron {len(archivos)} audios. Eliminando {cuantos_borrar} antiguos...")
        for i in range(cuantos_borrar):
            try: os.remove(archivos[i])
            except Exception: pass


if __name__ == "__main__":
    procesar_y_generar_tts()   
    print("¡Todo el proceso ha finalizado correctamente!")
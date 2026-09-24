import collections
import json
import os
import queue
import re
import sys
import unicodedata

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# Configuración del modelo (local, rápido y ligero)
MODEL_SIZE = "small"
echo_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

# Se sincroniza desde main.py (VERVOSE). Por defecto off.
VERVOSE = False

# ---------------------------------------------------------------------------
# Palabra de activación
# Di el nombre o "escucha" para que empiece a atender el comando.
# ---------------------------------------------------------------------------
NOMBRE_ASISTENTE = "Dave"
_nombre = NOMBRE_ASISTENTE.strip().lower()
PALABRAS_ACTIVACION = [
    "escucha",
    "escuchame",
    "escuche",
    "escuchar",
    f"oye {_nombre}",
    f"hola {_nombre}",
    f"hey {_nombre}",
    "oye",
    _nombre,
    "deiv",
    "deive",
]

FRECUENCIA = 16000
BLOQUE_MUESTRAS = 1600  # 0.1 s
BLOQUES_POR_SEGUNDO = 10
SEGUNDOS_PRE_ROLL = 0.5
SEGUNDOS_CALIBRACION = 1.5
SEGUNDOS_SILENCIO_ACTIVACION = 0.8
SEGUNDOS_SILENCIO_COMANDO = 1.1
SEGUNDOS_ESPERA_COMANDO = 7.0
MIN_SEGUNDOS_HABLA = 2.0  # Ninguna orden útil dura menos; evita Whisper en ruido/cortes
GANANCIA_MAXIMA = 16.0
NIVEL_OBJETIVO = 0.38

# Umbral de voz: margen sobre el ruido (aire acondicionado, ventilador, etc.)
# Antes se usaba ruido*2.4 y quedaba demasiado alto con ruido constante.
FACTOR_MARGEN_RUIDO = 0.28   # umbral ≈ ruido + 28% del ruido
MARGEN_ABS_MIN = 0.0020      # mínimo por encima del ruido
UMBRAL_MIN = 0.0030
UMBRAL_MAX = 0.0280          # evita que el AC dispare un umbral imposible

_PROMPT_WHISPER = (
    "Dave. Escucha. Activa modo dia. Activa modo noche. Modo dia. Modo noche. "
    "Pasa a modo dia. Abre el bloc de notas. Dime la hora. "
    "Busca en google. Haz una captura. Abre chrome. Abre spotify. "
    "Cancela el apagado. Cancela la ultima alarma. Cancela la alarma mas proxima. "
    "Reinicia el ordenador. Anota comprar leche. "
    "Pregunta a la ia. Pregunta al modelo. "
    "Inicia una conversacion. Fin de la conversacion."
)


def _vlog(*args, **kwargs):
    """Print solo cuando VERVOSE está activo."""
    if VERVOSE:
        print(*args, **kwargs)


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _alias_apps_foneticos() -> dict:
    """
    Carga alias de apps.json para corregir nombres mal oídos
    (ej. 'cromo' → 'chrome', 'espotifai' → 'spotify').
    """
    import rutas

    ruta = str(rutas.APPS_JSON)
    correcciones = {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            return correcciones
        for clave, valor in datos.items():
            clave_n = " ".join(_sin_acentos(str(clave).lower()).split())
            alias = []
            if isinstance(valor, dict):
                alias = [str(a) for a in (valor.get("alias") or [])]
            for a in alias:
                a_n = " ".join(_sin_acentos(a.lower()).split())
                if a_n and a_n != clave_n:
                    correcciones[a_n] = clave_n
                a_c = a_n.replace(" ", "")
                if a_c and a_c != clave_n.replace(" ", ""):
                    correcciones[a_c] = clave_n
    except Exception:
        pass
    return correcciones


def _aplicar_correccion_fonetica(texto: str, error: str, correccion: str) -> str:
    """
    Sustituye 'error' por 'correccion'.
    Si es una sola palabra, exige límites de palabra (evita model→modo dentro de 'modelo').
    """
    if not error:
        return texto
    if " " in error:
        return texto.replace(error, correccion) if error in texto else texto
    # Letra/dígito a ambos lados = interior de otra palabra
    return re.sub(
        rf"(?<![a-záéíóúüñ0-9]){re.escape(error)}(?![a-záéíóúüñ0-9])",
        correccion,
        texto,
        flags=re.IGNORECASE,
    )


def limpiar_fonetica_windows(texto: str) -> str:
    texto = texto.lower()

    signos_puntuacion = [".", ",", "?", "!", "¿", "¡", ";", ":", "…", '"', "'"]
    for signo in signos_puntuacion:
        texto = texto.replace(signo, "")

    texto = " ".join(texto.split())

    lista_negra = [
        "suscríbete", "suscribete", "subscribete",
        "gracias por ver", "thank you for watching",
        "multi-tech", "bye", "subtitles by",
    ]

    if texto in lista_negra or len(texto) <= 2:
        return ""

    errores_comunes = {
        "blotinotas": "bloc de notas",
        "blot de notas": "bloc de notas",
        "blog de notas": "bloc de notas",
        "notepas": "notepad",
        "deiv": "dave",
        "deive": "dave",
        "dei": "dave",
        "day": "dave",
        "de pregunta": "dave pregunta",
        "de abre": "dave abre",
        "de anota": "dave anota",
        "de apunta": "dave apunta",
        "de modo": "dave modo",
        "de activa": "dave activa",
        "de busca": "dave busca",
        "de dime": "dave dime",
        "de pon": "dave pon",
        "de cancela": "dave cancela",
        "de reinicia": "dave reinicia",
        "de apaga": "dave apaga",
        "de bloquea": "dave bloquea",
        "de estado": "dave estado",
        "de ia": "dave ia",
        "de ooba": "dave ooba",
        "pregunta laia": "pregunta a la ia",
        "pregunta la ia": "pregunta a la ia",
        "preguntalaia": "pregunta a la ia",
        "pregunta a laia": "pregunta a la ia",
        "consulta laia": "consulta a la ia",
        "dile a laia": "dile a la ia",
        "a laia": "a la ia",
        "laia": "la ia",
        "un alarme": "una alarma",
        "un alarma": "una alarma",
        "alarme": "alarma",
        "buscan google": "busca en google",
        "busca google": "busca en google",
        "bosque en google": "busca en google",
        "pusk and google": "busca en google",
        "gugel": "google",
        "googlear": "buscar en google",
        "pregunta a la i a": "pregunta a la ia",
        "pregunta ala ia": "pregunta a la ia",
        "pregunta al ia": "pregunta a la ia",
        "dile a la i a": "dile a la ia",
        "consulta a la i a": "consulta a la ia",
        "inicia una conversacion": "inicia una conversación",
        "iniciar una conversacion": "inicia una conversación",
        "iniciar conversacion": "inicia una conversación",
        "empieza una conversacion": "empieza una conversación",
        "fin de la conversacion": "fin de la conversación",
        "termina la conversacion": "termina la conversación",
        "dave para": "dave para",
        "dave calla": "dave calla",
        "dav para": "dave para",
        "dav calla": "dave calla",
        "callate": "callate",
        "pece": "pc",
        # --- Modo día (Whisper lo deforma mucho) ---
        "activa model gear": "activa modo dia",
        "activar model gear": "activa modo dia",
        "activa model dia": "activa modo dia",
        "activa model día": "activa modo dia",
        "activa modo via": "activa modo dia",
        "activa modo vía": "activa modo dia",
        "activa modo vr": "activa modo dia",
        "activa modo vii": "activa modo dia",
        "activa moropia": "activa modo dia",
        "activa moropía": "activa modo dia",
        "activa la melodia": "activa modo dia",
        "activa la melodía": "activa modo dia",
        "activar la melodia": "activa modo dia",
        "activar la melodía": "activa modo dia",
        "pasa a modo via": "pasa a modo dia",
        "pasa a modo vía": "pasa a modo dia",
        "pasa a modo vr": "pasa a modo dia",
        "modo via": "modo dia",
        "modo vía": "modo dia",
        "modo vr": "modo dia",
        "modo vii": "modo dia",
        "model dia": "modo dia",
        "model día": "modo dia",
        "model gear": "modo dia",
        "moropia": "modo dia",
        "moropía": "modo dia",
        "melodia": "modo dia",
        "melodía": "modo dia",
        # --- Modo noche / genéricos ---
        "moro noche": "modo noche",
        "moro dia": "modo dia",
        "moro día": "modo dia",
        "moto noche": "modo noche",
        "moto dia": "modo dia",
        "moto día": "modo dia",
        "modo nohe": "modo noche",
        "modo nochi": "modo noche",
        "modo nochee": "modo noche",
        "activa model": "activa modo",
        "activa moro": "activa modo",
        "activar moro": "activa modo",
        "pasa a moro": "pasa a modo",
        "pasar a moro": "pasa a modo",
        "pasa moro": "pasa a modo",
        "pomelo": "modo noche",
        "pa un modo": "modo noche",
        "moro": "modo",
        "model": "modo",
        "anade": "añade",
        "anado": "añade",
        # --- Alarmas ---
        "cancela la ultima alarma": "cancela la última alarma",
        "cancelar la ultima alarma": "cancela la última alarma",
        "anula la ultima alarma": "anula la última alarma",
        "quita la ultima alarma": "quita la última alarma",
        "borra la ultima alarma": "borra la última alarma",
        "cancela la alarma mas proxima": "cancela la alarma más próxima",
        "cancela la alarma mas cercana": "cancela la alarma más cercana",
        "cancela la proxima alarma": "cancela la próxima alarma",
        "anula la alarma mas proxima": "anula la alarma más próxima",
        "quita la alarma mas proxima": "quita la alarma más próxima",
        # --- Apagado / reinicio ---
        "cancela el apagado": "cancela el apagado",
        "cancelar el apagado": "cancela el apagado",
        "cancelar apagado": "cancela el apagado",
        "anula el apagado": "cancela el apagado",
        "reinicia el ordenador": "reinicia el ordenador",
        "reiniciar el pc": "reinicia el pc",
    }

    # Alias de aplicaciones (apps.json) — fonética Whisper
    errores_comunes.update(_alias_apps_foneticos())

    # Frases largas primero para no pisar reemplazos parciales
    for error, correccion in sorted(
        errores_comunes.items(), key=lambda kv: len(kv[0]), reverse=True
    ):
        texto = _aplicar_correccion_fonetica(texto, error, correccion)

    # Reparar daños previos / Whisper raro
    texto = _aplicar_correccion_fonetica(texto, "modoo", "modelo")

    # "Dave" → "De" al inicio + verbo de comando (Whisper lo confunde mucho)
    _verbos_tras_dave = (
        "pregunta", "abre", "abrir", "anota", "apunta", "modo", "activa",
        "busca", "dime", "pon", "pone", "cancela", "reinicia", "apaga",
        "bloquea", "estado", "ia", "ooba", "consulta", "dile", "lanza",
        "ejecuta", "toma", "haz", "sube", "baja", "silencio",
    )
    partes = texto.split()
    if len(partes) >= 2 and partes[0] in {"de", "day", "dei", "debe"}:
        if partes[1] in _verbos_tras_dave or partes[1].startswith("pregunta"):
            partes[0] = "dave"
            texto = " ".join(partes)

    return texto


def extraer_comando_tras_activacion(texto: str):
    """
    Detecta si la frase contiene la palabra de activación.
    Devuelve (activado, resto_del_comando).
    Permite 'escucha qué hora es' en un solo turno.

    La búsqueda de la palabra de activación ignora acentos, pero el resto
    conserva el texto limpio (p. ej. 'añade' no se convierte en 'anade').
    """
    limpio = limpiar_fonetica_windows(texto)
    if not limpio:
        return False, ""

    tokens_orig = limpio.split()
    tokens_norm = [_sin_acentos(t) for t in tokens_orig]
    frases = sorted(PALABRAS_ACTIVACION, key=len, reverse=True)

    for frase in frases:
        partes = _sin_acentos(frase.lower()).split()
        n = len(partes)
        if n == 0 or n > len(tokens_norm):
            continue
        for i in range(len(tokens_norm) - n + 1):
            if tokens_norm[i : i + n] == partes:
                resto = " ".join(tokens_orig[:i] + tokens_orig[i + n :])
                return True, resto

    return False, ""


def _barra_nivel(rms: float, umbral: float, ancho: int = 28) -> str:
    """Barra ASCII del nivel del micrófono respecto al umbral de voz."""
    escala = max(umbral * 4.0, 0.02)
    llenos = int(min(rms / escala, 1.0) * ancho)
    marca = int(min(umbral / escala, 1.0) * ancho)
    chars = []
    for i in range(ancho):
        if i == marca:
            chars.append("|")
        elif i < llenos:
            chars.append("#")
        else:
            chars.append("-")
    estado = "VOZ" if rms > umbral else "sil"
    return f"[{''.join(chars)}] {estado} rms={rms:.4f} umbral={umbral:.4f}"


def _aplicar_ganancia(audio: np.ndarray) -> np.ndarray:
    """Sube el volumen del recorte si se habló lejos del micrófono."""
    audio = audio.astype(np.float32, copy=False)
    audio = audio - np.mean(audio)
    pico = float(np.max(np.abs(audio))) if audio.size else 0.0
    if pico < 1e-5:
        _vlog("[STT] Aviso: el recorte de audio está vacío o casi en silencio.")
        return audio

    ganancia = min(NIVEL_OBJETIVO / pico, GANANCIA_MAXIMA)
    if ganancia > 1.05:
        audio = np.clip(audio * ganancia, -1.0, 1.0)
        _vlog(f"[STT] Ganancia x{ganancia:.1f} (pico original {pico:.4f})")
    else:
        _vlog(f"[STT] Pico de audio={pico:.4f} (sin ganancia extra)")
    return audio


class Microfono:
    def __init__(self):
        self.cola = queue.Queue()
        self.stream = None
        self.umbral = 0.006
        self.ruido_rms = 0.002
        self.dispositivo = None

    def _calcular_umbral(self, ruido_rms: float) -> float:
        """Umbral justo por encima del ruido ambiente (mejor con AC/ventiladores)."""
        margen = max(MARGEN_ABS_MIN, ruido_rms * FACTOR_MARGEN_RUIDO)
        umbral = ruido_rms + margen
        return float(min(max(umbral, UMBRAL_MIN), UMBRAL_MAX))

    def _callback(self, indata, frames, time, status):
        if status:
            _vlog(f"[STT] Aviso PortAudio: {status}", file=sys.stderr)
        self.cola.put(indata.copy())

    def _mostrar_dispositivo(self):
        try:
            info = sd.query_devices(kind="input")
            self.dispositivo = info.get("name", "desconocido")
            _vlog(f"[STT] Micrófono de entrada: {self.dispositivo}")
            _vlog(
                f"[STT] Canales={info.get('max_input_channels')} | "
                f"sample rate por defecto={info.get('default_samplerate')}"
            )
        except Exception as e:
            print(f"[STT] No se pudo consultar el micrófono: {e}")

    def iniciar(self):
        if self.stream is not None:
            return
        self._mostrar_dispositivo()
        self.stream = sd.InputStream(
            samplerate=FRECUENCIA,
            channels=1,
            dtype="float32",
            callback=self._callback,
            blocksize=BLOQUE_MUESTRAS,
        )
        self.stream.start()
        _vlog("[STT] Stream de micrófono abierto.")
        self.calibrar()

    def detener(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _vaciar_cola(self):
        while True:
            try:
                self.cola.get_nowait()
            except queue.Empty:
                break

    def calibrar(self):
        """Mide el ruido de la sala (incluye AC) y fija un umbral cercano a ese suelo."""
        print("[STT] Calibrando ruido ambiente... (quédate en silencio un momento)")
        self._vaciar_cola()
        muestras_rms = []
        bloques_objetivo = int(SEGUNDOS_CALIBRACION * BLOQUES_POR_SEGUNDO)
        timeouts = 0

        while len(muestras_rms) < bloques_objetivo:
            try:
                data = self.cola.get(timeout=1.0)
                timeouts = 0
            except queue.Empty:
                timeouts += 1
                print(f"[STT] Sin datos del micrófono durante la calibración ({timeouts}s)...")
                if timeouts >= 3:
                    print(
                        "[STT] ERROR: el micrófono no entrega audio. "
                        "Revisa el dispositivo de entrada en Windows."
                    )
                    return
                continue
            rms = float(np.sqrt(np.mean(data ** 2)))
            muestras_rms.append(rms)
            _vlog(
                f"\r[STT] Calibrando {_barra_nivel(rms, 0.01)}",
                end="",
                flush=True,
            )

        if VERVOSE:
            print()
        # Mediana: el AC constante no dispara el umbral tanto como el percentil 75
        self.ruido_rms = float(np.median(muestras_rms))
        self.umbral = self._calcular_umbral(self.ruido_rms)
        if VERVOSE:
            print(
                f"[STT] Calibración OK | ruido RMS={self.ruido_rms:.4f} | "
                f"umbral de voz={self.umbral:.4f}"
            )
            print(
                "[STT] Feedback: la barra '|' marca el umbral. "
                "Al hablar debería pasar a VOZ y llenarse de #."
            )
        else:
            print("[STT] Calibración lista.")

    def capturar_frase(
        self,
        segundos_silencio,
        timeout_sin_habla=None,
        etiqueta="Escuchando",
        min_segundos_habla=None,
    ):
        """
        Graba desde que detecta voz hasta un silencio.
        timeout_sin_habla: si no se empieza a hablar, abandona (None = espera indefinida).
        min_segundos_habla: override del mínimo global (p. ej. barge-in «para»).
        """
        minimo = (
            MIN_SEGUNDOS_HABLA
            if min_segundos_habla is None
            else float(min_segundos_habla)
        )
        self.iniciar()
        limite_silencio = int(segundos_silencio * BLOQUES_POR_SEGUNDO)
        pre_roll = collections.deque(maxlen=int(SEGUNDOS_PRE_ROLL * BLOQUES_POR_SEGUNDO))
        audio_bloques = []
        hablando = False
        silencio_bloques = 0
        bloques_espera = 0
        bloques_sin_datos = 0
        pico_visto = 0.0
        limite_espera = (
            int(timeout_sin_habla * BLOQUES_POR_SEGUNDO) if timeout_sin_habla else None
        )

        if VERVOSE:
            print(f"\n[STT] {etiqueta}... (umbral={self.umbral:.4f})")
        else:
            print(f"\n[STT] {etiqueta}...")

        while True:
            try:
                data = self.cola.get(timeout=1.0)
                bloques_sin_datos = 0
            except queue.Empty:
                bloques_sin_datos += 1
                _vlog(
                    f"\r[STT] Sin paquetes de audio del micrófono ({bloques_sin_datos}s)   ",
                    end="",
                    flush=True,
                )
                if bloques_sin_datos >= 3:
                    print(
                        "\n[STT] ERROR: no llega audio. "
                        "¿Micrófono silenciado o dispositivo incorrecto?"
                    )
                    return ""
                continue

            rms = float(np.sqrt(np.mean(data ** 2)))
            pico_visto = max(pico_visto, rms)

            # Mientras espera, adapta el suelo de ruido al AC (lento)
            if not hablando and rms < self.umbral:
                self.ruido_rms = (0.92 * self.ruido_rms) + (0.08 * rms)
                self.umbral = self._calcular_umbral(self.ruido_rms)

            es_voz = rms > self.umbral
            _vlog(f"\r[STT] {_barra_nivel(rms, self.umbral)}", end="", flush=True)

            if not hablando:
                pre_roll.append(data)
                if limite_espera is not None:
                    bloques_espera += 1
                    if bloques_espera > limite_espera:
                        _vlog(
                            f"\n[STT] Timeout: no se detectó voz. "
                            f"Pico máximo oído={pico_visto:.4f} (umbral={self.umbral:.4f})."
                        )
                        if pico_visto < self.umbral:
                            _vlog(
                                "[STT] Pista: el micrófono recibe señal débil o el umbral "
                                "está alto. Habla más cerca o revisa el volumen de entrada."
                            )
                        return ""
                if es_voz:
                    hablando = True
                    audio_bloques.extend(pre_roll)
                    silencio_bloques = 0
                    _vlog(f"\n[STT] >> Voz detectada (rms={rms:.4f}). Grabando...")
            else:
                audio_bloques.append(data)
                if es_voz:
                    silencio_bloques = 0
                else:
                    silencio_bloques += 1
                    if silencio_bloques > limite_silencio:
                        if VERVOSE:
                            print()  # corta la barra de nivel en su línea
                        _vlog(
                            f"[STT] << Fin de frase por silencio "
                            f"({segundos_silencio:.1f}s). "
                            f"Pico durante la captura={pico_visto:.4f}"
                        )
                        break

        if not audio_bloques:
            _vlog("[STT] No hay bloques de audio que procesar.")
            return ""

        duracion = len(audio_bloques) / BLOQUES_POR_SEGUNDO
        if duracion < minimo:
            if VERVOSE:
                print()
            _vlog(
                f"[STT] Descartado sin Whisper: demasiado corto "
                f"({duracion:.2f}s < {minimo:.1f}s)."
            )
            return ""

        _vlog(f"[STT] Audio capturado: {duracion:.2f}s ({len(audio_bloques)} bloques)")
        audio_fp32 = _aplicar_ganancia(np.concatenate(audio_bloques).flatten())
        return self._transcribir(audio_fp32)

    def _transcribir(self, audio_fp32: np.ndarray) -> str:
        print("[STT] Procesando voz...")
        # El recorte ya está hecho por energía; el VAD de Whisper recortaba
        # voces lejanas y se desactiva a propósito.
        segmentos, info = echo_model.transcribe(
            audio_fp32,
            beam_size=5,
            language="es",
            initial_prompt=_PROMPT_WHISPER,
            vad_filter=False,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.75,
        )

        partes = []
        for segmento in segmentos:
            partes.append(segmento.text)
            _vlog(
                f"[STT] Segmento [{segmento.start:.1f}-{segmento.end:.1f}s]: "
                f"'{segmento.text.strip()}'"
            )

        texto_sucio = " ".join(partes)
        if not texto_sucio.strip():
            _vlog(
                f"[STT] Whisper no devolvió texto "
                f"(prob. habla={getattr(info, 'language_probability', '?')})."
            )
            return ""

        texto_limpio = limpiar_fonetica_windows(texto_sucio)
        if not texto_limpio:
            _vlog(f"[STT] Texto descartado por limpieza: '{texto_sucio.strip()}'")
            return ""

        _vlog(f"[STT] Transcripción limpia: '{texto_limpio}'")
        return texto_limpio


_microfono = None


def obtener_microfono() -> Microfono:
    global _microfono
    if _microfono is None:
        _microfono = Microfono()
        _microfono.iniciar()
    return _microfono


def capturar_y_transcribir():
    """Compatibilidad: graba la siguiente frase que se hable."""
    micro = obtener_microfono()
    return micro.capturar_frase(
        segundos_silencio=SEGUNDOS_SILENCIO_COMANDO,
        etiqueta="Escuchando",
    )


def esperar_frase_conversacion():
    """
    Escucha la siguiente frase sin exigir palabra de activación
    (modo conversación continua con la IA).
    """
    micro = obtener_microfono()
    print('[STT] Conversación activa. Habla (di "fin de la conversación" para salir).')

    while True:
        frase = micro.capturar_frase(
            segundos_silencio=SEGUNDOS_SILENCIO_COMANDO,
            etiqueta="Conversación",
        )
        if not frase:
            _vlog("[STT] Sin texto en conversación. Sigo escuchando...")
            continue

        limpio = limpiar_fonetica_windows(frase)
        if not limpio:
            continue

        # Si dice Dave/escucha por costumbre, quedarnos con el resto
        activado, resto = extraer_comando_tras_activacion(limpio)
        if activado:
            if not resto:
                _vlog("[STT] Solo activación en conversación; ignoro.")
                continue
            limpio = resto

        print(f"[STT] Conversación oído: '{limpio}'")
        return limpio


def esperar_comando_activado():
    """
    Espera la palabra de activación y, si hace falta, una segunda frase con el comando.
    Devuelve el texto del comando o '' si se cancela por tiempo.
    """
    micro = obtener_microfono()
    nombre = NOMBRE_ASISTENTE
    print(f'[STT] En espera. Di "{nombre}" o "escucha" y después el comando.')

    while True:
        frase = micro.capturar_frase(
            segundos_silencio=SEGUNDOS_SILENCIO_ACTIVACION,
            etiqueta=f'Esperando "{nombre}" / "escucha"',
        )
        if not frase:
            _vlog("[STT] Sin texto útil en esta captura. Sigo escuchando...")
            continue

        print(f"[STT] Oído: '{frase}'")
        activado, resto = extraer_comando_tras_activacion(frase)
        if not activado:
            _vlog(f'[STT] No hay palabra de activación. Di "{nombre}" o "escucha".')
            continue

        _vlog(f"[STT] Activación detectada. Resto='{resto or '(vacío)'}'")
        if resto:
            return resto

        print(f"[STT] {nombre} te escucha. Di el comando.")
        comando = micro.capturar_frase(
            segundos_silencio=SEGUNDOS_SILENCIO_COMANDO,
            timeout_sin_habla=SEGUNDOS_ESPERA_COMANDO,
            etiqueta="Comando",
        )
        if not comando:
            print("[STT] Volviendo a espera de activación.")
            continue
        return comando


if __name__ == "__main__":
    VERVOSE = True
    try:
        while True:
            resultado = esperar_comando_activado()
            if resultado:
                print(f"Comando reconocido: '{resultado}'")
    except KeyboardInterrupt:
        if _microfono is not None:
            _microfono.detener()
        print("\nPrueba finalizada.")

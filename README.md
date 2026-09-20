# Asistente virtual local (Home Assistant)

Asistente de voz **offline** para Windows. Escucha por el micrófono, reconoce el español en el propio PC, ejecuta comandos y responde en voz alta. No envía audio ni texto a servicios en la nube (excepto el clima, que consulta [Open-Meteo](https://open-meteo.com/) al pedir el tiempo).

No es el software [Home Assistant](https://www.home-assistant.io/); es un asistente personal de escritorio pensado para el hogar. Licencia [GPL-3.0](LICENSE).

## Cómo funciona

```
Micrófono → escuchador (Whisper) → orquestador (regex) → comandos/*.py → Piper TTS → altavoces
```

1. **STT** (`escuchador.py`): calibra el ruido ambiente, espera la palabra de activación (**Dave**, **escucha**, **oye**, etc.), captura el comando y transcribe con [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`small`, CPU, `int8`, idioma `es`). Corrige errores fonéticos habituales y conserva tildes/ñ en el comando tras la activación.
2. **Orquestador** (`orquestador.py`): compara la frase con patrones de `mapeo_comandos.json` y carga el script de `comandos/` que corresponda. Si no hay coincidencia, **ignora en silencio** (sin TTS).
3. **TTS** (`read_file.py`): sintetiza la respuesta con [Piper](https://github.com/rhasspy/piper) invocando `python -m piper` (voz Dave, `es_ES-davefx-medium`) y la reproduce con pygame. Antes de sintetizar **normaliza símbolos** (°C, %, €…) y **quita las tildes** (conserva la ñ). Las frases repetidas se guardan en caché permanente.

## Requisitos

- Windows 10/11
- Python 3.10 o superior (recomendado 3.11+)
- Micrófono
- [`nircmd.exe`](https://www.nirsoft.net/utils/nircmd.html) en la **raíz del proyecto** (volumen, silencio, captura de reserva y apagado de monitores). El repositorio ya lo incluye.
- Modelo Piper **ONNX** en `voices/Dave/es_ES-davefx-medium.onnx` (el `.json` sí está en git; el `.onnx` no, porque pesa ~63 MB)

## Instalación

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si falta `nircmd.exe`, colócalo junto a `main.py`.

Descarga la voz Piper y déjala junto al JSON que ya hay en el repo:

```
voices/Dave/es_ES-davefx-medium.onnx
voices/Dave/es_ES-davefx-medium.onnx.json
```

Modelo oficial: [rhasspy/piper-voices — es_ES davefx medium](https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx).

Opcional — `config_local.json` (no se sube a git):

```json
{
  "ciudad_tiempo": "Los Palacios y Villafranca",
  "llm": {
    "url": "http://127.0.0.1:5000/v1",
    "api_key": "",
    "timeout": 180,
    "max_tokens": 220,
    "temperature": 0.6,
    "model": "",
    "system_prompt": "Eres Dave, un asistente de voz. Responde en 2 a 4 frases en español, listas para leer en voz alta."
  }
}
```

La URL del log de oobabooga (`0.0.0.0:5000`) es la dirección de escucha; desde Dave usa siempre `127.0.0.1:5000`.

Edita `carpetas.json` y `apps.json` con las rutas de **tu** PC (ahora apuntan a rutas locales de ejemplo).

## Uso

**Arranque rápido** (activa el venv y lanza `main.py`):

```powershell
.\iniciar_asistente.bat
```

O a mano, con el entorno virtual activado, desde la raíz del repositorio:

```powershell
python main.py
```

Al arrancar, quédate en silencio un segundo y medio (calibra el ruido). Luego activa el asistente:

- `Dave, qué hora es`
- `escucha` … (pausa) … `sube el volumen`
- `oye Dave, abre el bloc de notas`

**Modo consola** (texto, útil para probar comandos sin STT):

```powershell
python main_console.py
```

Para salir del modo consola escribe `salir`, `exit` o `apagar`. En modo voz usa `Ctrl+C`.

### Flags en `main.py`

| Variable | Efecto |
|----------|--------|
| `DEV` | `True`: consola visible con logs. `False`: oculta la ventana (cerrar desde el Administrador de tareas). |
| `VERVOSE` | `True`: barras de micrófono, RMS, segmentos Whisper, etc. `False`: solo mensajes útiles. |

### Inicio con Windows

Se puede crear un acceso directo a `iniciar_asistente.bat` en la carpeta de inicio:

```
shell:startup
```

Pruebas aisladas:

```powershell
python escuchador.py          # solo transcripción
python read_file.py           # lee input_tts.txt y lo dice en voz alta
```

## Comandos actuales

| Intención | Ejemplos de frase | Script |
|-----------|-------------------|--------|
| Hora | *qué hora es*, *dime la hora* | `comandos/hora.py` |
| Fecha | *qué día es hoy*, *dime la fecha* | `comandos/fecha.py` |
| Bloc de notas | *abre el bloc de notas*, *notepad* | `comandos/notepad.py` |
| Subir volumen | *sube el volumen*, *más volumen* | `comandos/volumen_subir.py` |
| Bajar volumen | *baja el volumen*, *menos volumen* | `comandos/volumen_bajar.py` |
| Silencio | *silencio*, *mutear* | `comandos/volumen_mutear.py` |
| Quitar silencio | *desmutear*, *activa el sonido* | `comandos/volumen_desmutear.py` |
| Alarma | *pon una alarma en 5 minutos*, *añade una alarma en 10 minutos para sacar las papas* | `comandos/alarma.py` |
| Buscar en Google | *busca en google recetas de pollo* | `comandos/buscar_google.py` |
| Preguntar a la IA local | *pregunta a la ia qué es la fotosíntesis*, *ia cuéntame un chiste*, *olvida la conversación* | `comandos/preguntar_ia.py` |
| Conversación continua | *inicia una conversación* → habla sin Dave → *fin de la conversación* | `comandos/conversacion.py` |
| Captura de pantalla | *haz una captura*, *screenshot* | `comandos/captura.py` |
| Bloquear PC | *bloquea el pc*, *lock* | `comandos/bloquear_pc.py` |
| Apagar PC | *apaga el ordenador* (ya); *apaga el ordenador en 10 minutos* | `comandos/apagar_pc.py` |
| Cancelar apagado | *cancela el apagado*, *anula el reinicio* | `comandos/cancelar_apagado.py` |
| Reiniciar PC | *reinicia el ordenador*; *reinicia el pc en 5 minutos* | `comandos/reiniciar_pc.py` |
| Nota rápida | *anota comprar leche*, *apunta llamar al dentista* | `comandos/nota.py` |
| Modo día / noche | *modo noche*, *activa modo día*, *pasa a modo noche* | `comandos/modo.py` |
| Abrir carpeta | *abre la carpeta peliculas*, *abrir carpeta proyecto* | `comandos/abrir_carpeta.py` |
| Abrir app | *abre chrome*, *abre spotify*, *lanza la calculadora* | `comandos/abrir_app.py` |
| Estado | *estado tiempo*, *qué tiempo hace*, *estado alarmas*, *qué alarmas hay* | `comandos/estado.py` |

### Alarmas

- Plazos: *en N segundos/minutos/horas*, *a las 8:30*, *en media hora*, etc.
- Título opcional tras *para* / *llamada*: *alarma en un minuto para sacar el pollo*.
- Se genera un WAV con Piper, Windows espera en segundo plano (`timeout` + `alarm_sound.py`) y el sonido se reproduce 3 veces (`winsound`).
- Quedan registradas en `alarmas/registro.json` para poder consultarlas con **estado alarmas**.

### Modos día y noche

**Modo noche**

1. Mostrar escritorio (Win+D)
2. Proyección solo en pantalla principal
3. Apagar NumLock si está activo
4. Iniciar `C:\Programas\text-generation-webui\start_windows.bat`
5. Apagar monitores con nircmd (sesión sigue abierta; no es bloqueo con PIN)

**Modo día**

1. Despertar monitores
2. Proyección en modo extender

> La luz RGB del teclado (p. ej. Yunzii QL108 con Fn+Backspace) **no** se puede apagar por software: Fn la gestiona el firmware.

### Carpetas (`carpetas.json`)

Palabra clave → ruta. Ejemplos actuales: `peliculas`, `musica`, `programas`, `proyecto`, `appdata` / `a pe pe data`.

```json
"descargas": "D:\\Descargas"
```

### Aplicaciones (`apps.json`)

Para abrir programas por voz sin pelearte con Whisper. Cada entrada tiene:

- **ruta**: ejecutable en PATH (`chrome`), `.exe` con ruta completa, o URI (`spotify:`)
- **alias**: formas alternativas / fonéticas que suele inventar el micrófono

```json
"chrome": {
  "ruta": "chrome",
  "alias": ["crom", "cromo", "google chrome"]
}
```

El escuchador aplica esos alias al transcribir; `abrir_app` además hace coincidencia exacta, sin espacios y difusa. Si Whisper deforma un nombre, añade un alias nuevo en el JSON.

### Notas rápidas

*anota …* / *apunta …* guarda un `.txt` con marca de tiempo en `notas/` y copia el texto al portapapeles.

### Capturas

*haz una captura* guarda un PNG en `capturas/` (PowerShell; si falla, nircmd) y lo deja también en el portapapeles.

### Estado

| Consulta | Frases |
|----------|--------|
| Hora | *estado hora* (también *qué hora es*) |
| Día | *estado día* / *estado fecha* |
| Tiempo | *estado tiempo*, *qué tiempo hace*, *dime el tiempo* |
| Alarmas | *estado alarmas*, *qué alarmas hay*, *dime las alarmas* |

Ciudad del clima: `ciudad_tiempo` en `config_local.json` (si falta, usa el valor por defecto de `comandos/estado.py`).

### IA local (text-generation-webui)

Requiere oobabooga con API OpenAI activa (`--api`, puerto 5000). Frases:

- *pregunta a la ia …* / *pregunta al modelo …* / *dile a la ia …* / *ia …*
- *olvida la conversación* (borra el historial de la sesión con el modelo)
- **Conversación continua:** *inicia una conversación* → a partir de ahí no hace falta decir Dave; cada frase va a la IA y Dave lee la respuesta → *para* / *calla* / *silencio* / *basta* (o *Dave, para*) corta la respuesta al instante → *fin de la conversación* para volver al modo normal

La respuesta se limpia de markdown/razonamiento y se acorta para Piper. Ajustes en `config_local.json` → `llm`.

## Añadir un comando

1. Crea `comandos/mi_comando.py` con una función `ejecutar(match)` que devuelva un `str` (el texto que se dirá), o `""` si no debe hablar:

```python
def ejecutar(match):
    return "Hecho."
```

`match` es el objeto de `re.match` sobre la frase del usuario.

2. Añade la clave en `mapeo_comandos.json`. El nombre de la clave debe coincidir con el archivo (sin `.py`):

```json
"mi_comando": [
  "^(haz esto|hazlo)$"
]
```

Los patrones se evalúan en minúsculas, de arriba abajo; gana la primera coincidencia.

Para **modos** o **estados** nuevos, registra la función en el diccionario de `comandos/modo.py` o `comandos/estado.py`.

## Estructura

```
.
├── main.py                 # Bucle principal (voz); flags DEV / VERVOSE
├── main_console.py         # Bucle principal (teclado)
├── iniciar_asistente.bat   # Arranque con venv
├── escuchador.py           # Captura de micrófono y transcripción
├── orquestador.py          # Enrutado de comandos
├── read_file.py            # Síntesis y reproducción TTS + caché + quitar tildes
├── alarm_sound.py          # Espera y reproduce WAV de alarma
├── mapeo_comandos.json     # Frases → scripts
├── carpetas.json           # Palabras clave → rutas de carpetas
├── apps.json               # Apps + alias fonéticos para Whisper
├── config_local.json       # Ajustes locales (gitignored): ciudad_tiempo, llm
├── requirements.txt
├── LICENSE                 # GPL-3.0
├── nircmd.exe              # Utilidad Windows (incluida en el repo)
├── input_tts.txt           # Texto que Piper debe leer (gitignored)
├── cache_registro.json     # Índice de frases cacheadas (gitignored)
├── alarmas/                # WAV y registro.json de alarmas pendientes
├── capturas/               # Capturas de pantalla
├── notas/                  # Notas rápidas por voz
├── comandos/               # Un script por comando
│   ├── alarma.py
│   ├── alarmas_registro.py
│   ├── abrir_carpeta.py
│   ├── abrir_app.py
│   ├── cancelar_apagado.py
│   ├── reiniciar_pc.py
│   ├── nota.py
│   ├── estado.py
│   ├── modo.py
│   └── ...
├── voices/Dave/            # JSON de Piper en git; el .onnx hay que descargarlo
├── cache_tts/              # WAV permanentes (frases frecuentes)
└── output_tts/             # WAV temporales de reproducción
```

`desbloquear_pin.py` es solo una nota de investigación: Windows no deja escribir el PIN en la pantalla de bloqueo desde un script de usuario.

## Palabra de activación y micrófono

En `escuchador.py`:

- `NOMBRE_ASISTENTE` y `PALABRAS_ACTIVACION`: cómo se le llama. Por defecto **Dave**, **escucha**, **oye**, **hola Dave**, **hey Dave** y variantes fonéticas (*deiv*, *deive*).
- El umbral de voz se **calibra al iniciar** (~1,5 s).
- `GANANCIA_MAXIMA`: tope de amplificación por software si el recorte llega bajo de volumen.
- `SEGUNDOS_ESPERA_COMANDO`: tiempo, tras la activación, para decir el comando (7 s).
- `MIN_SEGUNDOS_HABLA`: duración mínima de la captura de voz.

Si transcribe ruido de fondo, sube un poco el factor del umbral en `Microfono.calibrar`. Si sigue sin oírte, baja ese factor o revisa en Windows que el micrófono no esté en un volumen muy bajo.

## Caché de voz

Cada frase se identifica por MD5 (sobre el texto ya normalizado, sin tildes). Tras **3** repeticiones se copia a `cache_tts/` y se reutiliza sin volver a llamar a Piper. El registro (`cache_registro.json`) se recorta cuando crece demasiado: se conservan las frases permanentes más un margen de 50 temporales.

## Limitaciones

- Pensado para Windows (Notepad, NirCmd, DisplaySwitch, rutas de Piper).
- El reconocimiento es por expresiones regulares, no por un modelo de lenguaje: las frases deben parecerse a las del JSON.
- La primera ejecución de Whisper descarga el modelo `small` y puede tardar.
- Hay que descargar a mano el `.onnx` de Piper; sin él no hay voz.
- No se puede escribir el PIN en la pantalla de bloqueo de Windows desde una app de usuario (secure desktop); el modo noche apaga monitores en su lugar.
- Fn del teclado no es simulable; la luz RGB de teclados como el Yunzii QL108 no se controla por software con la API pública.
- El clima necesita red; el resto del asistente funciona offline.
- `carpetas.json`, `apps.json` y la ruta de text-generation-webui en `modo.py` son específicos de cada máquina.

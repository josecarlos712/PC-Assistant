# Asistente virtual local (Home Assistant)

Asistente de voz **offline** para Windows. Escucha por el micrófono, reconoce el español en el propio PC, ejecuta comandos y responde en voz alta. No envía audio ni texto a servicios en la nube (excepto el clima, que consulta [Open-Meteo](https://open-meteo.com/) al pedir el tiempo).

No es el software [Home Assistant](https://www.home-assistant.io/); es un asistente personal de escritorio pensado para el hogar. Licencia [GPL-3.0](LICENSE).

## Cómo funciona

```
Micrófono → nucleo/escuchador (Whisper) → nucleo/orquestador (regex) → comandos/*.py → Piper TTS → altavoces
```

1. **STT** (`nucleo/escuchador.py`): calibra el ruido ambiente, espera la palabra de activación (**Dave**, **escucha**, **oye**, etc.), captura el comando y transcribe con [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`small`, CPU, `int8`, idioma `es`). Corrige errores fonéticos habituales y conserva tildes/ñ tras la activación.
2. **Orquestador** (`nucleo/orquestador.py`): compara la frase con patrones de `config/mapeo_comandos.json` y carga el script de `comandos/` que corresponda. Si no hay coincidencia, **ignora en silencio** (sin TTS).
3. **TTS** (`nucleo/read_file.py`): sintetiza con [Piper](https://github.com/rhasspy/piper) (`python -m piper`, voz Dave `es_ES-davefx-medium`) y reproduce con pygame. Normaliza símbolos (°C, %, €…) y **quita las tildes** (conserva la ñ). Las frases repetidas se cachean.

Las rutas del proyecto están centralizadas en `nucleo/rutas.py`.

## Requisitos

- Windows 10/11
- Python 3.10 o superior (recomendado 3.11+)
- Micrófono
- [`nircmd.exe`](https://www.nirsoft.net/utils/nircmd.html) en la **raíz** (volumen, silencio, captura de reserva y apagar monitores). El repo ya lo incluye.
- Modelo Piper ONNX en `voices/Dave/es_ES-davefx-medium.onnx` (~63 MB; el `.json` sí está en git)

## Instalación

### Opción rápida (recomendada)

Doble clic o desde PowerShell en la raíz del repo:

```powershell
.\setup.bat
```

`setup.bat` instala Python 3.11 si hace falta, crea el `venv`, instala `requirements.txt`, descarga Piper y Whisper, crea carpetas en `datos/` y copia las plantillas `config/*_blank.json` a los JSON locales (sin sobrescribir los que ya existan).

<details>
<summary><strong>Opción manual</strong> (avanzado)</summary>

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Descarga la voz Piper:

```
voices/Dave/es_ES-davefx-medium.onnx
voices/Dave/es_ES-davefx-medium.onnx.json
```

Modelo: [rhasspy/piper-voices — es_ES davefx medium](https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx).

Copia las plantillas de configuración (o deja que lo haga `setup.bat`):

| Plantilla (en git) | Archivo local (gitignored) |
|--------------------|----------------------------|
| `config/apps_blank.json` | `config/apps.json` |
| `config/carpetas_blank.json` | `config/carpetas.json` |
| `config/config_local_blank.json` | `config/config_local.json` |
| `config/cache_registro_blank.json` | `config/cache_registro.json` |

Ejemplo de `config/config_local.json`:

```json
{
  "ciudad_tiempo": "TuCiudad",
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

La URL del log de oobabooga (`0.0.0.0:5000`) es solo la escucha; desde Dave usa siempre `127.0.0.1:5000`.

</details>

## Uso

**Arranque rápido:**

```powershell
.\iniciar_asistente.bat
```

O a mano, con el venv activado, desde la raíz:

```powershell
python main.py
```

Al arrancar, quédate en silencio ~1,5 s (calibra el ruido). Luego:

- `Dave, qué hora es`
- `escucha` … (pausa) … `sube el volumen`
- `oye Dave, abre el bloc de notas`

**Modo consola** (texto, sin micrófono):

```powershell
python nucleo\main_console.py
```

Salir del modo consola: `salir`, `exit` o `apagar`. En modo voz: `Ctrl+C`.

### Flags en `main.py`

| Variable | Efecto |
|----------|--------|
| `DEV` | `True`: consola visible. `False`: oculta la ventana (cerrar desde el Administrador de tareas). |
| `VERVOSE` | `True`: barras de micrófono, RMS, segmentos Whisper. `False`: solo mensajes útiles. |

### Inicio con Windows

Acceso directo a `iniciar_asistente.bat` en:

```
shell:startup
```

Pruebas aisladas:

```powershell
python nucleo\escuchador.py   # solo transcripción
python nucleo\read_file.py    # lee datos\input_tts.txt y lo dice en voz alta
```

## Comandos actuales

<details>
<summary><strong>Lista de comandos</strong> (frase → script)</summary>

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
| Cancelar alarma | *cancela la última alarma*, *cancela la alarma más próxima* | `comandos/cancelar_alarma.py` |
| Buscar en Google | *busca en google recetas de pollo* | `comandos/buscar_google.py` |
| Preguntar a la IA local | *pregunta a la ia qué es la fotosíntesis*, *ia cuéntame un chiste*, *olvida la conversación* | `comandos/preguntar_ia.py` |
| Conversación continua | *inicia una conversación* → habla sin Dave → *fin de la conversación* | `comandos/conversacion.py` |
| Captura de pantalla | *haz una captura*, *screenshot* | `comandos/captura.py` |
| Bloquear PC | *bloquea el pc*, *lock* | `comandos/bloquear_pc.py` |
| Apagar PC | *apaga el ordenador*; *apaga el ordenador en 10 minutos* | `comandos/apagar_pc.py` |
| Cancelar apagado | *cancela el apagado*, *anula el reinicio* | `comandos/cancelar_apagado.py` |
| Reiniciar PC | *reinicia el ordenador*; *reinicia el pc en 5 minutos* | `comandos/reiniciar_pc.py` |
| Nota rápida | *anota comprar leche*, *apunta llamar al dentista* | `comandos/nota.py` |
| Modo día / noche | *modo noche*, *activa modo día*, *pasa a modo noche* | `comandos/modo.py` |
| Abrir carpeta | *abre la carpeta descargas*, *abrir carpeta escritorio* | `comandos/abrir_carpeta.py` |
| Abrir app | *abre chrome*, *abre spotify*, *lanza la calculadora* | `comandos/abrir_app.py` |
| Estado | *estado tiempo*, *qué tiempo hace*, *estado alarmas*, *qué alarmas hay* | `comandos/estado.py` |

</details>

### Alarmas

- Plazos: *en N segundos/minutos/horas*, *a las 8:30*, *en media hora*, etc.
- Título opcional tras *para* / *llamada*: *alarma en un minuto para sacar el pollo*.
- Se genera un WAV con Piper; `nucleo/alarm_sound.py` espera y suena 3 veces (`winsound`).
- Registro en `datos/alarmas/registro.json` (**estado alarmas**).
- Cancelar: *cancela la última alarma* (la que acabas de poner); *cancela la alarma más próxima* (la que suena antes). Sin matiz, *cancela la alarma* anula la última.

### Modos día y noche

**Modo noche:** escritorio (Win+D) → proyección pantalla principal → apagar NumLock → iniciar text-generation-webui → apagar monitores con nircmd (la sesión sigue abierta; no es bloqueo con PIN).

**Modo día:** despertar monitores → proyección extender.

> La luz RGB del teclado (p. ej. Yunzii QL108 con Fn+Backspace) **no** se puede apagar por software.

La ruta de text-generation-webui está fijada en `comandos/modo.py` (`C:\Programas\text-generation-webui\...`); ajústala a tu máquina.

### Carpetas (`config/carpetas.json`)

Palabra clave → ruta. Partiendo de la plantilla: `descargas`, `documentos`, `escritorio`, `musica`, `videos`, `appdata`, etc.

```json
"descargas": "%USERPROFILE%\\Downloads"
```

### Aplicaciones (`config/apps.json`)

- **ruta**: ejecutable en PATH (`chrome`), `.exe` completo, o URI (`spotify:`)
- **alias**: formas fonéticas que suele inventar Whisper

```json
"chrome": {
  "ruta": "chrome",
  "alias": ["crom", "cromo", "google chrome"]
}
```

El escuchador aplica esos alias al transcribir; `abrir_app` hace coincidencia exacta, sin espacios y difusa.

### Notas y capturas

- *anota …* / *apunta …* → `datos/notas/` + portapapeles
- *haz una captura* → `datos/capturas/` (PowerShell; reserva nircmd) + portapapeles

### Estado

| Consulta | Frases |
|----------|--------|
| Hora | *estado hora* (también *qué hora es*) |
| Día | *estado día* / *estado fecha* |
| Tiempo | *estado tiempo*, *qué tiempo hace*, *dime el tiempo* |
| Alarmas | *estado alarmas*, *qué alarmas hay*, *dime las alarmas* |

Ciudad del clima: `ciudad_tiempo` en `config/config_local.json`.

### IA local (text-generation-webui)

Requiere oobabooga con API OpenAI (`--api`, puerto 5000):

- *pregunta a la ia …* / *ia …* / *olvida la conversación*
- **Conversación continua:** *inicia una conversación* → habla sin Dave → *para* / *calla* / *silencio* / *basta* corta la respuesta → *fin de la conversación*

Ajustes en `config/config_local.json` → `llm`.

## Añadir funcionalidades (regla de organización)

| Qué añades | Dónde |
|------------|--------|
| Comando de voz nuevo | `comandos/mi_comando.py` + clave en `config/mapeo_comandos.json` |
| Motor (STT, TTS, orquestación, utilidades) | `nucleo/` |
| Configuración / plantillas | `config/` (JSON personal → gitignored; plantilla → `*_blank.json` en git) |
| Archivos generados al usar el asistente | `datos/` |
| Modelos de voz | `voices/` |
| Entrada, instalador, licencia, nircmd | **raíz** (mantenerla limpia) |

### Nuevo comando de voz

1. Crea `comandos/mi_comando.py`:

```python
def ejecutar(match):
    return "Hecho."
```

2. Regístralo en `config/mapeo_comandos.json` (la clave = nombre del archivo sin `.py`):

```json
"mi_comando": [
  "^(haz esto|hazlo)$"
]
```

Los patrones van en minúsculas, de arriba abajo; gana la primera coincidencia.

Para **modos** o **estados** nuevos, registra la función en `comandos/modo.py` o `comandos/estado.py`.

## Estructura
```
.
├── main.py                 # Entrada (voz); flags DEV / VERVOSE
├── setup.bat               # Instalador (Python, deps, modelos, plantillas)
├── iniciar_asistente.bat   # Arranque con venv
├── environment.bat
├── requirements.txt
├── LICENSE                 # GPL-3.0
├── nircmd.exe
├── nucleo/                 # Motor
│   ├── rutas.py            # Rutas absolutas (config/, datos/, voices/…)
│   ├── escuchador.py
│   ├── orquestador.py
│   ├── read_file.py
│   ├── alarm_sound.py
│   ├── main_console.py
│   ├── strip_pipe.py
│   └── desbloquear_pin.py  # Solo referencia (PIN de Windows no automatizable)
├── comandos/               # Un script por intención de voz
├── config/                 # Config + plantillas *_blank.json
│   ├── mapeo_comandos.json
│   ├── apps_blank.json
│   ├── carpetas_blank.json
│   ├── config_local_blank.json
│   └── cache_registro_blank.json
├── datos/                  # Generado en ejecución (gitignored)
│   ├── alarmas/
│   ├── capturas/
│   ├── notas/
│   ├── cache_tts/
│   ├── output_tts/
│   └── input_tts.txt
└── voices/Dave/            # Piper (.json en git; .onnx a descargar)
```

## Palabra de activación y micrófono

En `nucleo/escuchador.py`:

- `NOMBRE_ASISTENTE` / `PALABRAS_ACTIVACION`: por defecto **Dave**, **escucha**, **oye**, **hola Dave**, **hey Dave** y variantes (*deiv*, *deive*).
- Calibración al iniciar (~1,5 s).
- `GANANCIA_MAXIMA`, `SEGUNDOS_ESPERA_COMANDO` (7 s), `MIN_SEGUNDOS_HABLA`.

Si transcribe ruido de fondo, sube el margen del umbral en `Microfono.calibrar`. Si no te oye, bájalo o revisa el volumen del micrófono en Windows.

## Caché de voz

Cada frase se identifica por MD5 (texto normalizado, sin tildes). Tras **3** repeticiones se copia a `datos/cache_tts/`. El índice está en `config/cache_registro.json` (permanentes + margen de 50 temporales).

## Limitaciones

- Pensado para Windows (Notepad, NirCmd, DisplaySwitch, Piper).
- Reconocimiento por regex, no por LLM: las frases deben parecerse a las del JSON.
- La primera ejecución de Whisper descarga el modelo `small` y puede tardar.
- Sin el `.onnx` de Piper no hay voz (lo descarga `setup.bat` o hay que colocarlo a mano).
- No se puede escribir el PIN en la pantalla de bloqueo desde una app de usuario; el modo noche apaga monitores.
- Fn del teclado no es simulable (RGB Yunzii QL108, etc.).
- El clima necesita red; el resto funciona offline.
- `config/apps.json`, `config/carpetas.json` y la ruta de text-generation-webui en `modo.py` son específicos de cada PC (no subir datos personales a git).

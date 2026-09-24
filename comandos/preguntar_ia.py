"""
Consulta al modelo local de text-generation-webui (oobabooga).

API OpenAI-compatible: http://127.0.0.1:5000/v1/chat/completions
(Arranca el webui con --api; el 0.0.0.0 del log es la escucha, el cliente usa 127.0.0.1)
"""
import json
import os
import re
import socket
import traceback
import urllib.error
import urllib.request

try:
    import rutas
    CONFIG_LOCAL = str(rutas.CONFIG_LOCAL)
except ImportError:
    CONFIG_LOCAL = os.path.join(os.getcwd(), "config", "config_local.json")

LLM_URL_DEFAULT = "http://127.0.0.1:5000/v1"
LLM_TIMEOUT_DEFAULT = 180
LLM_MAX_TOKENS_DEFAULT = 220
LLM_TEMPERATURE_DEFAULT = 0.6
SYSTEM_PROMPT_DEFAULT = (
    "Eres Dave, un asistente de voz. "
    "Tu única salida debe ser 2 a 4 frases en español que respondan al usuario, "
    "listas para leer en voz alta. "
    "Empieza directamente por la respuesta. "
    "No escribas pensamiento, análisis, borradores, pasos numerados ni comprobaciones "
    "(ni en inglés ni en español). Sin markdown y sin listas."
)

_historial = []
_MAX_TURNOS = 8

_PALABRAS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "que", "qué", "es", "son", "en", "se", "no", "si", "sí", "por", "para",
    "con", "como", "más", "pero", "sus", "su", "le", "ya", "o", "u", "y", "e",
    "fue", "ser", "está", "esta", "este", "esto", "hay", "muy", "sin", "sobre",
    "también", "cuando", "donde", "dónde", "quien", "desde", "todo", "todos",
    "nada", "algo", "entre", "hacia", "hasta", "durante", "después", "antes",
    "puede", "pueden", "forma", "forma", "zona", "espacio", "gravedad", "luz",
    "estrella", "agujero", "negro", "porque", "aunque", "así", "solo", "sólo",
}


def _cargar_config_llm() -> dict:
    cfg = {
        "url": LLM_URL_DEFAULT,
        "api_key": "",
        "timeout": LLM_TIMEOUT_DEFAULT,
        "max_tokens": LLM_MAX_TOKENS_DEFAULT,
        "temperature": LLM_TEMPERATURE_DEFAULT,
        "system_prompt": SYSTEM_PROMPT_DEFAULT,
        "model": "",
    }
    try:
        with open(CONFIG_LOCAL, "r", encoding="utf-8") as f:
            datos = json.load(f)
        bloque = datos.get("llm") or {}
        if isinstance(bloque, dict):
            for k in cfg:
                if k in bloque and bloque[k] not in (None, ""):
                    cfg[k] = bloque[k]
        if datos.get("llm_url"):
            cfg["url"] = datos["llm_url"]
        if datos.get("llm_api_key"):
            cfg["api_key"] = datos["llm_api_key"]
    except Exception:
        pass

    url = str(cfg["url"]).rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    # 0.0.0.0 no es reachable como cliente
    url = url.replace("://0.0.0.0:", "://127.0.0.1:")
    url = url.replace("://localhost:", "://127.0.0.1:")
    cfg["url"] = url
    return cfg


def _extraer_texto_contenido(contenido) -> str:
    """Acepta string OpenAI clásico o lista de partes (APIs compatibles)."""
    if contenido is None:
        return ""
    if isinstance(contenido, str):
        return contenido.strip()
    if isinstance(contenido, list):
        partes = []
        for p in contenido:
            if isinstance(p, str):
                partes.append(p)
            elif isinstance(p, dict):
                partes.append(
                    str(
                        p.get("text")
                        or p.get("content")
                        or p.get("value")
                        or ""
                    )
                )
        return " ".join(partes).strip()
    return str(contenido).strip()


def _ratio_espanol(texto: str) -> float:
    palabras = re.findall(r"[a-záéíóúüñ]+", (texto or "").lower(), flags=re.I)
    if not palabras:
        return 0.0
    hits = 0
    for p in palabras:
        if p in _PALABRAS_ES or any(c in "áéíóúüñ" for c in p):
            hits += 1
    return hits / len(palabras)


def _cortar_cola_meta(texto: str) -> str:
    """Elimina comprobaciones / pasos en inglés que van después de la respuesta."""
    t = texto or ""
    # "4. Check Constraints", "Let's count", etc.
    t = re.split(
        r"(?i)\s*(?:"
        r"\d+\.\s*(?:check|verify|confirm|review|identify|analyze|draft|constraints?)\b"
        r"|check\s+constraints?"
        r"|let'?s\s+count"
        r"|only\s+final\s+answer\s*\?"
        r"|in\s+spanish\s*\?"
        r"|here'?s\s+a\s+thinking"
        r"|thinking\s+process\s*:"
        r").*",
        t,
        maxsplit=1,
    )[0]
    return t.strip(" -\n\t")


def _frase_meta(f: str) -> bool:
    """True si la frase es meta-comentario del modelo, no respuesta al usuario."""
    return bool(
        re.search(
            r"(?i)\b("
            r"yes\.?|good\.?|constraints?|thinking process|analyze user|"
            r"only final|in spanish\?|let'?s count|sentences\?|draft\b|"
            r"check constraints|respond only|prohibited|key concepts"
            r")\b",
            f,
        )
    )


def _extraer_respuesta_final(texto: str) -> str:
    """
    Quita el 'thinking process' de modelos reasoning y deja la respuesta hablable.
    """
    t = (texto or "").strip()
    if not t:
        return ""

    t = re.sub(r"<think>[\s\S]*?</think>", " ", t, flags=re.I)
    t = re.sub(r"<thinking>[\s\S]*?</thinking>", " ", t, flags=re.I)
    t = re.sub(r"<reason(?:ing)?>[\s\S]*?</reason(?:ing)?>", " ", t, flags=re.I)

    # Tras marcadores de borrador / respuesta final
    for patron in (
        r"(?is)draft\s*\([^)]*spanish[^)]*\)\s*:\s*(.+)$",
        r"(?is)(?:final\s+answer|respuesta\s+final)\s*:\s*(.+)$",
        r"(?is)draft[^:\n]*:\s*(.+)$",
    ):
        m = re.search(patron, t)
        if m:
            cand = _cortar_cola_meta(m.group(1))
            if len(cand) > 30 and _ratio_espanol(cand) >= 0.25:
                return cand

    # Thinking dump: quedarnos solo con frases en español (no meta)
    if re.search(
        r"(?i)thinking process|analyze user input|check constraints|mental refinement|draft\s*\(",
        t,
    ):
        frases = re.findall(r"[^.!?]+[.!?]+", t)
        buenas = []
        for f in frases:
            f = f.strip(" -\n\t*")
            if len(f) < 40 or _frase_meta(f):
                continue
            if _ratio_espanol(f) >= 0.35:
                buenas.append(f)
        if buenas:
            # Tomar el bloque continuo de español al final (antes del check)
            return _cortar_cola_meta(" ".join(buenas[-4:]))

        lineas = [ln.strip(" -•\t*") for ln in t.splitlines() if ln.strip()]
        buenas_ln = [
            ln
            for ln in lineas
            if len(ln) > 40 and _ratio_espanol(ln) >= 0.4 and not _frase_meta(ln)
        ]
        if buenas_ln:
            return _cortar_cola_meta(" ".join(buenas_ln[-2:]))

    return _cortar_cola_meta(t)


def _limpiar_para_voz(texto: str) -> str:
    t = _extraer_respuesta_final(texto)
    if not t:
        return ""
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"[*_#~>]+", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = _cortar_cola_meta(t)
    t = re.sub(r"\s+", " ", t).strip()

    # Solo frases en español; descarta cola en inglés pegada al final
    frases = re.findall(r"[^.!?]+[.!?]*", t)
    limpias = []
    for f in frases:
        f = f.strip()
        if not f or _frase_meta(f):
            continue
        # Restos tipo "4." / "3" del thinking (Check Constraints)
        if re.fullmatch(r"\d+\.?", f):
            continue
        if _ratio_espanol(f) < 0.28 and len(f) > 20:
            break
        limpias.append(f if f.endswith((".", "!", "?")) else f + ".")
    if limpias:
        t = " ".join(limpias[:4])

    # Cola suelta: "… pareció. 4." o "… pareció 4."
    t = re.sub(r"(?<=[.!?])\s*\d+\.?\s*$", "", t)
    t = re.sub(r"\s+\d+\.\s*$", "", t)
    t = t.strip()

    if len(t) > 450:
        corte = t[:450]
        punto = corte.rfind(".")
        if punto > 100:
            corte = corte[: punto + 1]
        t = corte
    return t.strip()


def _chat(pregunta: str, cfg: dict) -> str:
    global _historial

    messages = [{"role": "system", "content": cfg["system_prompt"]}]
    messages.extend(_historial[-(_MAX_TURNOS * 2) :])
    messages.append({"role": "user", "content": pregunta})

    payload = {
        "messages": messages,
        "temperature": float(cfg["temperature"]),
        "max_tokens": int(cfg["max_tokens"]),
        "top_p": 0.95,
        "stream": False,
    }
    if cfg.get("model"):
        payload["model"] = cfg["model"]

    body = json.dumps(payload).encode("utf-8")
    endpoint = cfg["url"] + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DaveAsistente/1.0",
        "Connection": "close",
    }
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    print(f"[IA] POST {endpoint} (timeout={cfg['timeout']}s, max_tokens={cfg['max_tokens']})")
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=float(cfg["timeout"])) as resp:
        raw = resp.read()
        status = getattr(resp, "status", None) or resp.getcode()
        print(f"[IA] HTTP {status}, {len(raw)} bytes")

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        preview = raw[:300].decode("utf-8", errors="replace")
        raise RuntimeError(f"JSON inválido de la API: {e}. Inicio: {preview}") from e

    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        if isinstance(err, dict):
            raise RuntimeError(err.get("message") or str(err))
        raise RuntimeError(str(err))

    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        raise RuntimeError(f"Sin choices en la respuesta. Claves: {list(data) if isinstance(data, dict) else type(data)}")

    choice0 = choices[0] if isinstance(choices[0], dict) else {}
    msg = choice0.get("message") or {}
    if not isinstance(msg, dict):
        msg = {}

    contenido = _extraer_texto_contenido(msg.get("content"))
    if not contenido:
        # Modelos "reasoning" (R1, QwQ, etc.): a veces solo rellenan reasoning_content
        contenido = _extraer_texto_contenido(msg.get("reasoning_content"))
    if not contenido:
        contenido = _extraer_texto_contenido(msg.get("refusal"))
    if not contenido:
        contenido = _extraer_texto_contenido(choice0.get("text"))
    if not contenido:
        delta = choice0.get("delta") or {}
        if isinstance(delta, dict):
            contenido = _extraer_texto_contenido(delta.get("content"))
            if not contenido:
                contenido = _extraer_texto_contenido(delta.get("reasoning_content"))
    if not contenido:
        raise RuntimeError(
            f"Respuesta vacía. choice keys={list(choice0)} "
            f"message keys={list(msg)}"
        )

    # Si hay content y reasoning, preferir content; si content vacío ya usamos reasoning
    _historial.append({"role": "user", "content": pregunta})
    _historial.append({"role": "assistant", "content": contenido})
    return contenido


def _olvidar() -> str:
    global _historial
    _historial = []
    return "He olvidado la conversación con el modelo."


def preguntar(pregunta: str) -> str:
    """API simple para otros módulos (p. ej. modo conversación)."""
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return "No te he oído bien."

    cfg = _cargar_config_llm()
    print(f"[IA] Pregunta: {pregunta[:160]}")

    try:
        bruto = _chat(pregunta, cfg)
        print(f"[IA] Respuesta: {bruto[:400]}{'…' if len(bruto) > 400 else ''}")
        limpio = _limpiar_para_voz(bruto)
        return limpio or "El modelo no dijo nada útil."
    except urllib.error.HTTPError as e:
        detalle = ""
        try:
            detalle = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        print(f"[IA] HTTP {e.code}: {detalle}")
        if e.code == 401:
            return "El modelo rechazó la clave API. Revisa llm.api_key en config_local.json."
        return f"El modelo respondió con error {e.code}."
    except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
        print(f"[IA] Conexión/timeout: {e}")
        traceback.print_exc()
        return (
            "No pude conectar con el modelo en el puerto 5000 "
            "o tardó demasiado. ¿Está text-generation-webui con la API activa?"
        )
    except Exception as e:
        print(f"[IA] Error: {type(e).__name__}: {e}")
        traceback.print_exc()
        breve = str(e).split("\n")[0][:120]
        return f"Error al consultar el modelo: {breve}"


def ejecutar(match):
    pregunta = ""
    frase = ""
    if match is not None:
        frase = (match.group(0) or "").strip().lower()
        if match.lastindex:
            for i in range(1, match.lastindex + 1):
                g = match.group(i)
                if g:
                    pregunta = g.strip()
                    break

    if re.search(r"olvid(a|ar)|reinicia(?:r)?(?: la)? conversaci[oó]n|nueva conversaci[oó]n", frase):
        if not pregunta or pregunta in {
            "la conversacion",
            "la conversación",
            "conversacion",
            "conversación",
        }:
            return _olvidar()

    if not pregunta:
        return "Dime qué quieres preguntarle al modelo."

    if re.match(r"^(?:olvida(?:r)?(?: la)? conversaci[oó]n|nueva conversaci[oó]n)\b", pregunta, re.I):
        _olvidar()
        pregunta = re.sub(
            r"^(?:olvida(?:r)?(?: la)? conversaci[oó]n|nueva conversaci[oó]n)\s*(?:y\s+)?",
            "",
            pregunta,
            flags=re.I,
        ).strip()
        if not pregunta:
            return "He olvidado la conversación con el modelo."

    return preguntar(pregunta)

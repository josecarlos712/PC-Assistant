"""
Modo conversación continua con la IA local.

- Inicio: «inicia una conversación» (con Dave/escucha)
- Durante: cada frase va a la IA sin palabra de activación
- Fin: «fin de la conversación»
"""
import re
import unicodedata

_activa = False


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def esta_activa() -> bool:
    return _activa


def es_fin_conversacion(texto: str) -> bool:
    t = _sin_acentos((texto or "").strip().lower())
    t = " ".join(t.split())
    return bool(
        re.search(
            r"\b(?:"
            r"fin de la conversacion"
            r"|termina(?:r)?(?: la)? conversacion"
            r"|acaba(?:r)?(?: la)? conversacion"
            r"|salir de la conversacion"
            r"|cierra(?:r)?(?: la)? conversacion"
            r")\b",
            t,
        )
    )


def es_inicio_conversacion(texto: str) -> bool:
    t = _sin_acentos((texto or "").strip().lower())
    t = " ".join(t.split())
    return bool(
        re.search(
            r"\b(?:"
            r"inicia(?:r)?(?: una| la)? conversacion"
            r"|empieza(?:r)?(?: una| la)? conversacion"
            r"|abre(?:r)?(?: una| la)? conversacion"
            r"|modo conversacion"
            r")\b",
            t,
        )
    )


def es_orden_callar(texto: str) -> bool:
    """«para», «calla», «dave calla», etc. — interrumpir TTS en conversación."""
    t = _sin_acentos((texto or "").strip().lower())
    t = " ".join(t.split())
    # Quitar activación suelta al inicio
    t = re.sub(r"^(?:dave|dav|deiv|deive|day|de|escucha|oye)\s+", "", t)
    t = t.strip()
    if not t:
        return False
    return bool(
        re.match(
            r"^(?:"
            r"para"
            r"|para\s+ya"
            r"|calla"
            r"|callate"
            r"|callate\s+ya"
            r"|silencio"
            r"|basta"
            r"|stop"
            r"|enough"
            r")$",
            t,
        )
    )


def iniciar() -> str:
    global _activa
    _activa = True
    try:
        import preguntar_ia

        preguntar_ia._olvidar()
    except Exception:
        pass
    print("[Conversación] MODO ACTIVO — sin palabra de activación.")
    return (
        "Conversación iniciada. Puedes hablarme sin decir Dave. "
        "Si quieres que me calle, di para o calla. "
        "Cuando quieras terminar, di fin de la conversación."
    )


def terminar() -> str:
    global _activa
    _activa = False
    print("[Conversación] Modo desactivado.")
    return "Conversación terminada. Vuelvo a esperar la palabra Dave."


def ejecutar(match):
    frase = ""
    if match is not None:
        frase = (match.group(0) or "").strip()

    if es_fin_conversacion(frase):
        if not _activa:
            return "No había ninguna conversación activa."
        return terminar()

    if es_inicio_conversacion(frase):
        if _activa:
            return "Ya estamos en una conversación. Di fin de la conversación para salir."
        return iniciar()

    return ""

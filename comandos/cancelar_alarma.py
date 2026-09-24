"""Cancela por voz la última alarma añadida o la más próxima a disparar."""
import re
import unicodedata
from datetime import datetime

import alarmas_registro


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _hora_hablada(iso_txt: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_txt)
    except (TypeError, ValueError):
        return ""
    return f"las {dt.strftime('%H')} y {dt.strftime('%M')}"


def _describir(entrada: dict) -> str:
    titulo = (entrada.get("titulo") or "").strip()
    cuando = _hora_hablada(entrada.get("dispara_en", ""))
    partes = []
    if titulo:
        partes.append(f"para {titulo}")
    if cuando:
        partes.append(f"a {cuando}")
    return ", ".join(partes)


def _intencion(frase: str) -> str:
    """'proxima' o 'ultima'. Sin matiz, se cancela la última añadida (deshacer)."""
    t = _sin_acentos(frase.lower())
    t = " ".join(t.split())
    if re.search(
        r"\b(?:proxima|proximo|cercana|cercano|siguiente|inminente)\b",
        t,
    ):
        return "proxima"
    if re.search(r"mas\s+(?:proxima|cerca|cercana)|que suena\s+(?:antes|primero|ya|pronto)", t):
        return "proxima"
    return "ultima"


def _frase_completa(match) -> str:
    if match is None:
        return ""
    return (match.group(0) or "").strip()


def ejecutar(match):
    frase = _frase_completa(match)
    cual = _intencion(frase)

    if cual == "proxima":
        entrada = alarmas_registro.mas_proxima()
        etiqueta = "la alarma más próxima"
        vacio = "No hay ninguna alarma programada."
    else:
        entrada = alarmas_registro.ultima_anadida()
        etiqueta = "la última alarma"
        vacio = "No hay ninguna alarma programada."

    if not entrada:
        return vacio

    detalle = _describir(entrada)
    if not alarmas_registro.cancelar(entrada):
        print(f"[Cancelar alarma] Falló al matar pid={entrada.get('pid')} id={entrada.get('id')}")
        return "No pude cancelar la alarma."

    print(f"[Cancelar alarma] Cancelada ({cual}) id={entrada.get('id')}")
    if detalle:
        return f"He cancelado {etiqueta}, {detalle}."
    return f"He cancelado {etiqueta}."

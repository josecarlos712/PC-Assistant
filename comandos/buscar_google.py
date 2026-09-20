"""Abre una búsqueda en Google en el navegador predeterminado."""
import urllib.parse
import webbrowser


def ejecutar(match):
    consulta = ""
    if match is not None and match.lastindex:
        consulta = (match.group(1) or "").strip()

    if not consulta:
        return "Dime qué quieres buscar en Google."

    url = "https://www.google.com/search?q=" + urllib.parse.quote(consulta)
    try:
        webbrowser.open(url, new=2)
        return f"Buscando en Google: {consulta}."
    except Exception:
        return "No pude abrir el navegador para buscar en Google."

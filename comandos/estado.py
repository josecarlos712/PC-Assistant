"""
Comando de estado: hora, día, tiempo (clima) y alarmas programadas.

Para añadir un estado nuevo:
  1. Escribe una función `estado_xxx(match) -> str`
  2. Regístrala en ESTADOS y, si hace falta, en ALIAS_ESTADOS
"""
import json
import os
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import alarmas_registro

# Ciudad por defecto si falta config_local.json → "ciudad_tiempo"
CIUDAD_TIEMPO_DEFAULT = "Los Palacios y Villafranca"

CODIGOS_WMO = {
    0: "cielo despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "cubierto",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna ligera",
    53: "llovizna",
    55: "llovizna intensa",
    56: "llovizna helada",
    57: "llovizna helada intensa",
    61: "lluvia ligera",
    63: "lluvia",
    65: "lluvia intensa",
    66: "lluvia helada",
    67: "lluvia helada intensa",
    71: "nieve ligera",
    73: "nieve",
    75: "nieve intensa",
    77: "granizo menudo",
    80: "chubascos ligeros",
    81: "chubascos",
    82: "chubascos fuertes",
    85: "chubascos de nieve",
    86: "chubascos de nieve fuertes",
    95: "tormenta",
    96: "tormenta con granizo",
    99: "tormenta con granizo fuerte",
}


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _ciudad_configurada() -> str:
    try:
        import rutas
        ruta = str(rutas.CONFIG_LOCAL)
    except ImportError:
        ruta = os.path.join(os.getcwd(), "config", "config_local.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        ciudad = (datos.get("ciudad_tiempo") or "").strip()
        if ciudad:
            return ciudad
    except Exception:
        pass
    return CIUDAD_TIEMPO_DEFAULT


def _http_json(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "DaveAsistente/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def estado_hora(match):
    ahora = datetime.now()
    return f"Son las {ahora.strftime('%H')} y {ahora.strftime('%M')} minutos."


def estado_dia(match):
    dias = [
        "lunes", "martes", "miércoles", "jueves",
        "viernes", "sábado", "domingo",
    ]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    ahora = datetime.now()
    return (
        f"Hoy es {dias[ahora.weekday()]}, "
        f"{ahora.day} de {meses[ahora.month - 1]}."
    )


def estado_tiempo(match):
    ciudad = _ciudad_configurada()
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode(
                {"name": ciudad, "count": 1, "language": "es", "format": "json"}
            )
        )
        geo = _http_json(geo_url)
        resultados = geo.get("results") or []
        if not resultados:
            return f"No encontré la ciudad {ciudad} para consultar el tiempo."

        lugar = resultados[0]
        lat = lugar["latitude"]
        lon = lugar["longitude"]
        nombre = lugar.get("name") or ciudad
        admin = lugar.get("admin1") or ""

        meteo_url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "timezone": "auto",
                    "wind_speed_unit": "kmh",
                }
            )
        )
        meteo = _http_json(meteo_url)
        actual = meteo.get("current") or {}
        temp = actual.get("temperature_2m")
        sensacion = actual.get("apparent_temperature")
        codigo = actual.get("weather_code")
        viento = actual.get("wind_speed_10m")
        descripcion = CODIGOS_WMO.get(int(codigo), "condiciones variables") if codigo is not None else "sin datos"

        donde = nombre if not admin else f"{nombre}, {admin}"
        partes = [f"En {donde} hay {descripcion}"]
        if temp is not None:
            partes.append(f"con {temp:.0f} grados")
        if sensacion is not None and temp is not None and abs(sensacion - temp) >= 2:
            partes.append(f"sensación térmica de {sensacion:.0f}")
        if viento is not None:
            partes.append(f"viento a {viento:.0f} kilómetros por hora")
        return ", ".join(partes) + "."
    except urllib.error.URLError:
        return "No pude consultar el tiempo: sin conexión o el servicio no responde."
    except Exception as e:
        print(f"[Estado] Error clima: {e}")
        return "No pude obtener el estado del tiempo."


def _formatear_hora_alarma(iso_txt: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_txt)
    except ValueError:
        return iso_txt
    return f"las {dt.strftime('%H')} y {dt.strftime('%M')}"


def estado_alarmas(match):
    pendientes = alarmas_registro.listar_pendientes()
    if not pendientes:
        return "No hay alarmas programadas."

    if len(pendientes) == 1:
        e = pendientes[0]
        cuando = _formatear_hora_alarma(e.get("dispara_en", ""))
        titulo = (e.get("titulo") or "").strip()
        if titulo:
            return f"Tienes una alarma a {cuando} para {titulo}."
        return f"Tienes una alarma a {cuando}."

    partes = []
    for e in pendientes[:5]:
        cuando = _formatear_hora_alarma(e.get("dispara_en", ""))
        titulo = (e.get("titulo") or "").strip()
        if titulo:
            partes.append(f"a {cuando} para {titulo}")
        else:
            partes.append(f"a {cuando}")
    texto = "; ".join(partes)
    extra = ""
    if len(pendientes) > 5:
        extra = f" Y {len(pendientes) - 5} más."
    return f"Tienes {len(pendientes)} alarmas: {texto}.{extra}"


ESTADOS = {
    "hora": estado_hora,
    "dia": estado_dia,
    "día": estado_dia,
    "fecha": estado_dia,
    "tiempo": estado_tiempo,
    "clima": estado_tiempo,
    "alarmas": estado_alarmas,
    "alarma": estado_alarmas,
}

ALIAS_ESTADOS = {
    "la hora": "hora",
    "el dia": "dia",
    "el día": "dia",
    "la fecha": "fecha",
    "el tiempo": "tiempo",
    "del tiempo": "tiempo",
    "la meteorologia": "tiempo",
    "la meteorología": "tiempo",
    "el clima": "clima",
    "las alarmas": "alarmas",
    "mis alarmas": "alarmas",
    "alarmas programadas": "alarmas",
}


def _resolver_estado(nombre: str):
    if not nombre:
        return None

    crudo = " ".join(nombre.strip().lower().split())
    if not crudo:
        return None

    if crudo in ALIAS_ESTADOS:
        crudo = ALIAS_ESTADOS[crudo]

    clave = _sin_acentos(crudo)
    if clave in ALIAS_ESTADOS:
        crudo = ALIAS_ESTADOS[clave]
        clave = _sin_acentos(crudo)

    fn = ESTADOS.get(crudo) or ESTADOS.get(clave)
    if fn:
        return fn

    for k, fn in ESTADOS.items():
        if _sin_acentos(k) == clave:
            return fn

    # Prefijo: "del tiempo en madrid" → tiempo
    for k, fn in ESTADOS.items():
        kn = _sin_acentos(k)
        if clave.startswith(kn + " ") or clave.startswith("el " + kn) or clave.startswith("la " + kn):
            return fn
        if clave.startswith("las " + kn) or clave.startswith("mis " + kn):
            return fn

    return None


def ejecutar(match):
    nombre = ""
    if match is not None and match.lastindex:
        for i in range(1, match.lastindex + 1):
            g = match.group(i)
            if g:
                nombre = g.strip().lower()
                break

    # Frases naturales sin grupo (p. ej. "qué tiempo hace")
    if not nombre and match is not None:
        frase = _sin_acentos((match.group(0) or "").lower())
        if "alarm" in frase:
            nombre = "alarmas"
        elif "tiempo" in frase or "clima" in frase:
            nombre = "tiempo"
        elif "hora" in frase:
            nombre = "hora"
        elif "dia" in frase or "fecha" in frase:
            nombre = "dia"

    if not nombre:
        return (
            "Puedo decirte la hora, el día, el tiempo o las alarmas. "
            "Di por ejemplo: estado tiempo."
        )

    funcion = _resolver_estado(nombre)
    if funcion is None:
        print(f"[Estado] Desconocido: '{nombre}'")
        return (
            "No conozco ese estado. Prueba hora, día, tiempo o alarmas."
        )

    return funcion(match)

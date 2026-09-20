from datetime import datetime

def ejecutar(match):
    # Diccionarios para traducir el tiempo a lenguaje natural
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", 
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    ahora = datetime.now()
    dia_semana = dias[ahora.weekday()]
    dia_mes = ahora.day
    mes = meses[ahora.month - 1]
    
    return f"Hoy es {dia_semana}, {dia_mes} de {mes}."
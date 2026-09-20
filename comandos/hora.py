from datetime import datetime

def ejecutar(match):
    ahora = datetime.now()
    hora_texto = ahora.strftime("%H y %M")
    return f"Son las {hora_texto} minutos."
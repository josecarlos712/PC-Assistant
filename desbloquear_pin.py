"""
INTENTO de escribir el PIN en la pantalla de bloqueo de Windows.

RESULTADO (documentado tras investigación):
  NO funciona desde una aplicación normal. La pantalla de bloqueo corre en el
  "secure desktop" (Winlogon). SendInput / teclas simuladas no llegan ahí
  (medida de seguridad de Microsoft). La vía soportada sería un Credential
  Provider (DLL del sistema), no un script Python.

Este archivo se deja solo como referencia. El asistente usa en su lugar:
  modo noche → apagar monitores (nircmd)
  modo día   → despertar monitores + extender proyección
"""
print(
    "desbloquear_pin.py: Windows no permite escribir el PIN en la pantalla "
    "de bloqueo desde un script. Usa modo noche/día con monitores on/off."
)
raise SystemExit(1)

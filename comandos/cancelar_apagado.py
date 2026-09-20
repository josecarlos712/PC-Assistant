"""Cancela un apagado o reinicio programado de Windows (shutdown /a)."""
import subprocess


def ejecutar(match):
    try:
        resultado = subprocess.run(
            ["shutdown", "/a"],
            check=False,
            capture_output=True,
            text=True,
        )
        # 1116 = no había apagado pendiente (Windows)
        if resultado.returncode == 0:
            return "Apagado cancelado."
        err = (resultado.stderr or resultado.stdout or "").lower()
        if "1116" in err or "no se está" in err or "not in the process" in err:
            return "No había ningún apagado programado."
        print(f"[Cancelar apagado] exit={resultado.returncode} {resultado.stderr}")
        return "No pude cancelar el apagado."
    except Exception as e:
        print(f"[Cancelar apagado] {e}")
        return "No pude cancelar el apagado."

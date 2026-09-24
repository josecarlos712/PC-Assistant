import os
import sys

import rutas

rutas.asegurar_sys_path()
os.chdir(rutas.RAIZ)

from orquestador import evaluar_comando


def bucle_principal():
    print("====================================================")
    print(" ASISTENTE VIRTUAL LOCAL - MÓDULO 2: ORQUESTADOR")
    print(" Escribe tu comando (o escribe 'salir' para terminar)")
    print("====================================================\n")

    while True:
        try:
            usuario_input = input("Tú ──► ")

            if usuario_input.strip().lower() in ["salir", "exit", "apagar"]:
                print("\n[Asistente]: Cerrando sistemas. ¡Hasta pronto!")
                break

            evaluar_comando(usuario_input)
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n\n[Asistente]: Programa finalizado forzosamente.")
            sys.exit(0)


if __name__ == "__main__":
    bucle_principal()

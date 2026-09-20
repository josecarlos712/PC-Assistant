import sys
from orquestador import evaluar_comando

def bucle_principal():
    print("====================================================")
    print(" ASISTENTE VIRTUAL LOCAL - MÓDULO 2: ORQUESTADOR")
    print(" Escribe tu comando (o escribe 'salir' para terminar)")
    print("====================================================\n")
    
    while True:
        try:
            # Captura la orden directamente desde la consola
            usuario_input = input("Tú ──► ")
            
            # Condición de salida del programa
            if usuario_input.strip().lower() in ["salir", "exit", "apagar"]:
                print("\n[Asistente]: Cerrando sistemas. ¡Hasta pronto!")
                break
                
            # Procesar la orden a través del orquestador
            evaluar_comando(usuario_input)
            print("-" * 50)
            
        except KeyboardInterrupt:
            # Permite cerrar limpiamente con Ctrl+C
            print("\n\n[Asistente]: Programa finalizado forzosamente.")
            sys.exit(0)

if __name__ == "__main__":
    bucle_principal()
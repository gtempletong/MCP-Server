import csv

FILENAME = 'market_data.csv'
NUM_LINES_TO_CHECK = 15 # Vamos a revisar las primeras 15 líneas

print(f"--- Iniciando diagnóstico del archivo: {FILENAME} ---")

try:
    with open(FILENAME, mode='r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= NUM_LINES_TO_CHECK:
                break

            # Imprimimos el número de línea y la línea de texto cruda
            print(f"\nLínea {i+1} (cruda):")
            print(line.strip())

            # Imprimimos la representación de la línea para ver caracteres invisibles
            # como \t (tabulador)
            print(f"Línea {i+1} (representación):")
            print(repr(line.strip()))

    print("\n--- Diagnóstico finalizado ---")
    print("\nPor favor, copia y pega todo este output para analizarlo.")
    print("Fíjate en la sección '(representación)'. Si ves '\\t', significa que el separador es un Tabulador.")

except FileNotFoundError:
    print(f"❌ ERROR: No se pudo encontrar el archivo '{FILENAME}'.")
except Exception as e:
    print(f"❌ Ocurrió un error inesperado: {e}")
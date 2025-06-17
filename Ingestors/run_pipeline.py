# Este script importa y ejecuta los otros dos en secuencia.

# 1. Importar las funciones 'main' de nuestros otros scripts
#    y les damos nombres más descriptivos.
from excel_to_sheets import main as run_file_conversion
from ingest_data import main as run_supabase_ingestion
import time

def run_full_pipeline():
    """
    Ejecuta el pipeline completo de datos:
    1. Convierte el Excel a una Hoja de Google estandarizada.
    2. Ingesta los datos de esa hoja en Supabase.
    """
    print("====== INICIANDO PIPELINE DE DATOS COMPLETO ======")
    print("=" * 50)

    # --- ETAPA 1: CONVERTIR EXCEL Y POBLAR HOJA PUENTE ---
    print("\n>>> [ETAPA 1/2] Ejecutando conversión de Excel a Google Sheet...")
    try:
        run_file_conversion()
        print(">>> [ETAPA 1/2] Conversión finalizada con éxito.")
    except Exception as e:
        print(f"❌ ERROR FATAL en la etapa de conversión de archivos: {e}")
        print("====== PIPELINE DETENIDO ======")
        return # Detiene todo si el primer script falla

    # Pequeña pausa para asegurar que Google procese los cambios
    print("\nEsperando 5 segundos para la propagación de datos en Google...")
    time.sleep(5)

    # --- ETAPA 2: LEER HOJA PUENTE E INGESTAR DATOS EN SUPABASE ---
    print("\n>>> [ETAPA 2/2] Ejecutando ingesta de datos a Supabase...")
    try:
        run_supabase_ingestion()
        print(">>> [ETAPA 2/2] Ingesta finalizada con éxito.")
    except Exception as e:
        print(f"❌ ERROR FATAL en la etapa de ingesta a Supabase: {e}")
        print("====== PIPELINE DETENIDO ======")
        return # Detiene todo si el segundo script falla

    print("\n" + "=" * 50)
    print("✅✅✅====== PIPELINE FINALIZADO CON ÉXITO TOTAL ======")

if __name__ == "__main__":
    run_full_pipeline()
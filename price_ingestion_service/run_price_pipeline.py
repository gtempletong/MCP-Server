# Ingestors/run_pipeline.py (Versión Robusta con Manejo de Errores)
from excel_to_sheets import main as run_file_conversion
from ingest_data import main as run_supabase_ingestion
import time

def run_full_pipeline():
    print("====== INICIANDO PIPELINE DE DATOS COMPLETO ======")
    print("=" * 50)

    print("\n>>> [ETAPA 1/2] Ejecutando conversión de Excel a Google Sheet...")
    success_stage_1 = run_file_conversion()
    
    if not success_stage_1:
        print("\n❌ ERROR FATAL en la Etapa 1. Pipeline detenido.")
        print("=" * 50)
        return

    print(">>> [ETAPA 1/2] Conversión finalizada con éxito.")
    print("\nEsperando 5 segundos para la propagación de datos en Google...")
    time.sleep(5)

    print("\n>>> [ETAPA 2/2] Ejecutando ingesta de datos a Supabase...")
    success_stage_2 = run_supabase_ingestion()

    if not success_stage_2:
        print("\n❌ ERROR FATAL en la Etapa 2. Pipeline detenido.")
        print("=" * 50)
        return

    print("\n" + "=" * 50)
    print("✅✅✅====== PIPELINE FINALIZADO CON ÉXITO REAL Y TOTAL ======")

if __name__ == "__main__":
    run_full_pipeline()
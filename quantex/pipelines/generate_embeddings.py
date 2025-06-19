# data_workers/generate_embeddings.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

def generate_and_store_embeddings():
    """
    Lee las series de la base de datos, genera sus embeddings
    y los guarda de vuelta en Supabase, preservando los datos existentes.
    """
    print("--- Iniciando proceso de generación de embeddings ---")
    
    # --- Conexión y Carga de Modelos ---
    try:
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=dotenv_path)
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Conexión a Supabase exitosa.")

        # Cargamos un modelo de embeddings multilingüe y eficiente
        print("Cargando modelo de embeddings (esto puede tardar un momento la primera vez)...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Modelo de embeddings cargado.")

    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")
        return

    # --- Procesamiento de Series ---
    try:
        # 1. Obtenemos TODA la información de las series que aún no tienen un embedding
        response = supabase.table('series_definitions').select('*').filter('embedding', 'is', 'null').execute()
        
        if not response.data:
            print("\n✅ ¡Excelente! Todas las series ya tienen su embedding. No hay nada que hacer.")
            return

        series_to_process = response.data
        print(f"\nSe encontraron {len(series_to_process)} series para procesar.")

        # 2. Generamos los embeddings para cada series_name
        names_to_embed = [series['series_name'] for series in series_to_process]
        print("Generando vectores de embeddings...")
        embeddings = model.encode(names_to_embed)
        print(f"✅ Se generaron {len(embeddings)} vectores.")

        # 3. Preparamos los datos para la actualización
        updates = []
        for i, series in enumerate(series_to_process):
            # Tomamos TODOS los datos existentes de la serie
            updated_series = series
            # Y añadimos el nuevo embedding
            updated_series['embedding'] = embeddings[i].tolist()
            updates.append(updated_series)

        # 4. Actualizamos la base de datos con los registros completos
        print("Actualizando la base de datos con los nuevos embeddings...")
        if updates:
            supabase.table('series_definitions').upsert(updates).execute()
        
        print(f"\n✅ ¡Proceso completado! Se actualizaron {len(updates)} series.")

    except Exception as e:
        print(f"❌ Ocurrió un error durante el procesamiento: {e}")

if __name__ == "__main__":
    generate_and_store_embeddings()
# data_workers/semantic_search_provider.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# --- INICIALIZACIÓN DE CLIENTES Y MODELOS ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

try:
    print("[SEMANTIC_SEARCH] Cargando modelo de embeddings...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[SEMANTIC_SEARCH] ✅ Modelo cargado.")
except Exception as e:
    print(f"[SEMANTIC_SEARCH] ❌ No se pudo cargar el modelo de embeddings: {e}")
    embedding_model = None

# --- FUNCIÓN PRINCIPAL DE BÚSQUEDA ---
def find_relevant_series(user_query: str, match_count: int = 3, match_threshold: float = 0.5) -> list[dict]:
    if not embedding_model:
        print("  -> ❌ Búsqueda semántica deshabilitada, modelo no cargado.")
        return []

    print(f"[SEMANTIC_SEARCH] Buscando series relevantes para: '{user_query}'")
    try:
        query_embedding = embedding_model.encode(user_query).tolist()
        params = {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': match_count
        }
        response = supabase.rpc('match_series_by_name', params).execute()

        if response.data:
            print(f"  -> Se encontraron {len(response.data)} series relevantes.")
            return response.data 
        else:
            print("  -> No se encontraron series relevantes por encima del umbral.")
            return []
            
    except Exception as e:
        print(f"  -> ❌ Error durante la búsqueda semántica: {e}")
        return []
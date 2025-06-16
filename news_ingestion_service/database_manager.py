# news_ingestion_service/database_manager.py

from supabase import create_client, Client
from datetime import datetime
import config

# Inicializa el cliente de Supabase una sola vez
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def get_active_topics() -> list[str]:
    """Obtiene la lista de temas activos desde la tabla news_topics."""
    try:
        response = supabase.table('news_topics').select('topic_name').eq('is_active', True).execute()
        if response.data:
            return [item['topic_name'] for item in response.data]
        return []
    except Exception as e:
        print(f"Error al obtener temas activos: {e}")
        return []

def get_existing_links_for_topic(topic: str) -> set[str]:
    """Obtiene los URLs de artículos que ya existen para un tema específico."""
    try:
        response = supabase.table('news_articles').select('source_url').eq('topic', topic).execute()
        if response.data:
            return {item['source_url'] for item in response.data}
        return set()
    except Exception as e:
        print(f"Error al obtener enlaces para el tema {topic}: {e}")
        return set()

def insert_article(article_data: dict):
    """Inserta un nuevo artículo procesado en la tabla news_articles."""
    try:
        supabase.table('news_articles').insert(article_data).execute()
        print(f"✅ Artículo '{article_data['title']}' insertado.")
    except Exception as e:
        print(f"❌ Error al insertar artículo: {e}")

def update_topic_fetch_time(topic: str):
    """Actualiza la fecha de la última búsqueda para un tema."""
    try:
        now = datetime.now().isoformat()
        supabase.table('news_topics').update({'last_fetched': now}).eq('topic_name', topic).execute()
    except Exception as e:
        print(f"Error al actualizar la fecha para el tema {topic}: {e}")
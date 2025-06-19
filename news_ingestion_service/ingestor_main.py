# news_ingestion_service/ingestor_main.py (VERSIÓN ACTUALIZADA)

import database_manager as db
import processing_utils as proc
from datetime import datetime, timezone

def main():
    """Función principal que orquesta el pipeline de ingesta de noticias."""
    print("🚀 Iniciando servicio de ingesta de noticias...")
    
    # 1. Obtener la lista de temas a procesar desde la DB (ahora viene con alias)
    topics_to_process = db.get_active_topics()
    if not topics_to_process:
        print("No hay temas activos para procesar. Finalizando.")
        return
        
    print(f"Temas a procesar: {[t['topic_name'] for t in topics_to_process]}")
    
    # 2. Obtener todos los artículos del feed RSS
    rss_articles = proc.fetch_articles_from_rss()
    print(f"Se encontraron {len(rss_articles)} artículos en el feed.")

    # 3. Procesar cada tema individualmente
    for topic_data in topics_to_process:
        # --- LÓGICA DE ALIAS ---
        canonical_name = topic_data['topic_name'] # Ej: "Cobre"
        aliases = topic_data.get('aliases') or [] # Ej: ["copper"]

        print(f"\n--- Procesando Tema Estándar: {canonical_name.upper()} ---")

        # Combinamos el nombre principal y sus alias para la búsqueda.
        # Convertimos todo a minúsculas para una comparación robusta.
        search_terms = [canonical_name.lower()] + [alias.lower() for alias in aliases]
        print(f"Buscando con los términos: {search_terms}")
        # --- FIN LÓGICA DE ALIAS ---
        
        # Usamos el nombre canónico para consultar los links existentes
        existing_links = db.get_existing_links_for_topic(canonical_name)
        print(f"Se encontraron {len(existing_links)} artículos existentes para '{canonical_name}'.")
        
        # Filtra usando la nueva lista de términos de búsqueda
        new_articles_for_topic = [
            art for art in rss_articles
            # Comprueba si alguno de los términos de búsqueda está en el título
            if any(term in art['title'].lower() for term in search_terms) and art['link'] not in existing_links
        ]
        
        if not new_articles_for_topic:
            print(f"No hay artículos nuevos para '{canonical_name}'.")
            db.update_topic_fetch_time(canonical_name) # Actualizamos la fecha aunque no haya nuevos
            continue
            
        print(f"Procesando {len(new_articles_for_topic)} artículo(s) nuevo(s) para '{canonical_name}':")
        
        for article in new_articles_for_topic:
            content = proc.scrape_article_with_firecrawl(article['link'])
            if not content:
                continue
            
            summary = proc.summarize_text_with_claude(content, canonical_name)
            
            article_to_insert = {
                'published_at': article['published'],
                'source_url': article['link'],
                'topic': canonical_name, # <-- Usamos SIEMPRE el nombre canónico
                'title': article['title'],
                'summary': summary
            }
            
            db.insert_article(article_to_insert)

        # Actualizar la fecha de la última búsqueda para el tema
        db.update_topic_fetch_time(canonical_name)
        
    print("\n✅ Proceso de ingesta finalizado.")

if __name__ == "__main__":
    main()
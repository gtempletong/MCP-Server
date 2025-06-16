# news_ingestion_service/ingestor_main.py

import database_manager as db
import processing_utils as proc
from datetime import datetime, timezone

def main():
    """Función principal que orquesta el pipeline de ingesta de noticias."""
    print("🚀 Iniciando servicio de ingesta de noticias...")
    
    # 1. Obtener la lista de temas a procesar desde la DB
    topics_to_process = db.get_active_topics()
    if not topics_to_process:
        print("No hay temas activos para procesar. Finalizando.")
        return
        
    print(f"Temas a procesar: {', '.join(topics_to_process)}")
    
    # 2. Obtener todos los artículos del feed RSS (se hace una sola vez)
    rss_articles = proc.fetch_articles_from_rss()
    print(f"Se encontraron {len(rss_articles)} artículos en el feed.")

    # 3. Procesar cada tema individualmente
    for topic in topics_to_process:
        print(f"\n--- Procesando Tema: {topic.upper()} ---")
        
        # Obtiene los enlaces ya existentes para este tema para evitar duplicados
        existing_links = db.get_existing_links_for_topic(topic)
        print(f"Se encontraron {len(existing_links)} artículos existentes para '{topic}'.")
        
        # Filtra los artículos del feed que son relevantes y nuevos
        new_articles_for_topic = [
            art for art in rss_articles 
            if topic.lower() in art['title'].lower() and art['link'] not in existing_links
        ]
        
        if not new_articles_for_topic:
            print(f"No hay artículos nuevos para '{topic}'.")
            continue
            
        print(f"Procesando {len(new_articles_for_topic)} artículo(s) nuevo(s) para '{topic}':")
        
        for article in new_articles_for_topic:
            # 4. Scrapear el contenido completo
            content = proc.scrape_article_with_firecrawl(article['link'])
            if not content:
                continue # Si el scrapeo falla, pasar al siguiente artículo
            
            # 5. Generar el resumen con IA
            summary = proc.summarize_text_with_claude(content, topic)
            
            # 6. Preparar los datos para la inserción
            article_to_insert = {
                'published_at': article['published'],
                'source_url': article['link'],
                'topic': topic,
                'title': article['title'],
                'summary': summary
            }
            
            # 7. Insertar en la base de datos
            db.insert_article(article_to_insert)

        # 8. Actualizar la fecha de la última búsqueda para el tema
        db.update_topic_fetch_time(topic)
        
    print("\n✅ Proceso de ingesta finalizado.")

if __name__ == "__main__":
    main()
# news_ingestion_service/processing_utils.py (Versión con fecha simplificada)

import feedparser
import requests
from datetime import datetime 
from anthropic import Anthropic
import config
import time # Importamos time para el parsing de fechas

# ... (inicialización de anthropic_client sin cambios) ...

RSS_FEED_URL = "https://rss.metal.com/news/the_latest.xml"

def fetch_articles_from_rss() -> list[dict]:
    """Obtiene y parsea artículos desde un feed RSS, formateando la fecha a AAAA-MM-DD."""
    print(f"Obteniendo artículos desde {RSS_FEED_URL}...")
    feed = feedparser.parse(RSS_FEED_URL)
    
    articles = []
    for entry in feed.entries:
        # --- LÓGICA DE FECHA MEJORADA ---
        published_date = datetime.now().strftime('%Y-%m-%d') # Un valor por defecto
        if 'published_parsed' in entry and entry.published_parsed is not None:
            # feedparser nos da la fecha ya parseada, la formateamos a nuestro gusto
            published_date = time.strftime('%Y-%m-%d', entry.published_parsed)
        elif 'published' in entry:
            # Si no, intentamos parsear el string, pero es menos fiable
            try:
                # Intentamos varios formatos comunes
                dt_obj = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                published_date = dt_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass # Si falla, usamos el valor por defecto (la fecha de hoy)
        
        articles.append({
            'title': entry.get('title', 'Sin Título'),
            'link': entry.get('link', ''),
            'published': published_date # Ahora siempre es AAAA-MM-DD
        })
    return articles

# ... (El resto de tus funciones scrape_with_firecrawl y summarize_text_with_claude se mantienen igual) ...
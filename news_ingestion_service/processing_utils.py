# news_ingestion_service/processing_utils.py

import feedparser
import requests
from datetime import datetime 
from anthropic import Anthropic
import config

# Inicializa el cliente de Anthropic
anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

RSS_FEED_URL = "https://rss.metal.com/news/the_latest.xml"

def fetch_articles_from_rss() -> list[dict]:
    """Obtiene y parsea artículos desde un feed RSS."""
    print(f"Obteniendo artículos desde {RSS_FEED_URL}...")
    feed = feedparser.parse(RSS_FEED_URL)
    
    articles = []
    for entry in feed.entries:
        articles.append({
            'title': entry.get('title', 'Sin Título'),
            'link': entry.get('link', ''),
            'published': entry.get('published', datetime.now().isoformat())
        })
    return articles

def scrape_article_with_firecrawl(url: str) -> str | None:
    """Usa Firecrawl para extraer el contenido principal de un artículo."""
    print(f"   Scrapeando URL: {url}")
    headers = {
        "Authorization": f"Bearer {config.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"url": url, "pageOptions": {"onlyMainContent": True}}
    
    try:
        response = requests.post("https://api.firecrawl.dev/v0/scrape", json=payload, headers=headers)
        response.raise_for_status() # Lanza un error si la petición falla
        return response.json().get('data', {}).get('markdown', '')
    except requests.RequestException as e:
        print(f"   ❌ Error en Firecrawl: {e}")
        return None

def summarize_text_with_claude(text: str, topic: str) -> str:
    """Genera un resumen conciso usando Claude 3 Haiku."""
    print("      Resumiendo con Claude Haiku...")
    
    # Un prompt robusto para obtener resúmenes de calidad
    prompt = f"""
    Eres un analista de mercado experto en el sector de metales y commodities.
    Tu tarea es leer el siguiente artículo de noticias sobre '{topic}' y escribir un resumen ejecutivo conciso de 2 a 3 párrafos.
    El resumen debe ser objetivo, informativo y centrarse en los datos y hechos clave relevantes para un análisis de mercado.
    No incluyas opiniones personales ni frases como "El artículo dice" o "Según el autor". Ve directo a los hechos.

    Artículo:
    {text}

    Resumen Ejecutivo:
    """
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompt}
            ]
        ).content[0].text
        return message
    except Exception as e:
        print(f"      ❌ Error en Claude: {e}")
        return "No se pudo generar el resumen."
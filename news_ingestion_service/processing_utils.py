# news_ingestion_service/processing_utils.py

import feedparser
import requests
from datetime import datetime
from anthropic import Anthropic
import time
import config # Importamos nuestro archivo de configuración

# --- INICIALIZACIÓN DE CLIENTES ---
try:
    anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    print("✅ Cliente de Anthropic inicializado en processing_utils.")
except Exception as e:
    print(f"❌ Error al inicializar cliente de Anthropic: {e}")
    anthropic_client = None

# --- FUNCIONES DE PROCESAMIENTO ---

def fetch_articles_from_rss() -> list[dict]:
    """
    Obtiene y parsea artículos desde un feed RSS, formateando la fecha a AAAA-MM-DD.
    """
    print(f"Obteniendo artículos desde {config.RSS_FEED_URL}...")
    feed = feedparser.parse(config.RSS_FEED_URL)
    
    articles = []
    for entry in feed.entries:
        # Lógica robusta para parsear la fecha y formatearla
        published_date_str = datetime.now().strftime('%Y-%m-%d') # Valor por defecto: hoy
        if hasattr(entry, 'published_parsed') and entry.published_parsed is not None:
            # feedparser a menudo nos da la fecha ya parseada en una tupla de tiempo
            published_date_str = time.strftime('%Y-%m-%d', entry.published_parsed)
        elif hasattr(entry, 'published'):
            # Si no, intentamos parsear el string de fecha
            try:
                # Intentamos con un formato común de RSS (ej: 'Tue, 18 Jun 2025 12:00:00 +0000')
                dt_obj = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                published_date_str = dt_obj.strftime('%Y-%m-%d')
            except ValueError:
                # Si falla, intentamos otros formatos o lo dejamos como hoy
                print(f"  -> ADVERTENCIA: No se pudo parsear la fecha '{entry.published}'. Usando fecha actual.")
        
        articles.append({
            'title': entry.get('title', 'Sin Título'),
            'link': entry.get('link', ''),
            'published': published_date_str # La fecha siempre estará en formato AAAA-MM-DD
        })
    return articles

def scrape_article_with_firecrawl(url: str) -> str | None:
    """Usa Firecrawl para extraer el contenido principal de un artículo como Markdown."""
    print(f"  -> [Firecrawl] Scrapeando URL: {url[:50]}...")
    if not config.FIRECRAWL_API_KEY:
        print("  -> ❌ Error: La clave de API para Firecrawl no está configurada.")
        return None

    headers = {
        "Authorization": f"Bearer {config.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"url": url, "pageOptions": {"onlyMainContent": True}}
    
    try:
        response = requests.post("https://api.firecrawl.dev/v0/scrape", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('success') and 'markdown' in data.get('data', {}):
             print("  -> ✅ Contenido extraído con Firecrawl.")
             return data['data']['markdown']
        else:
            print(f"  -> ❌ Firecrawl no devolvió contenido exitosamente: {data.get('error')}")
            return None
    except requests.RequestException as e:
        print(f"  -> ❌ Error de red en Firecrawl: {e}")
        return None

def summarize_text_with_claude(text: str, topic: str) -> str:
    """Genera un resumen conciso usando Claude 3 Haiku."""
    if not anthropic_client:
        return "Error: Cliente de Anthropic no inicializado."
        
    print("    -> [Claude] Generando resumen...")
    
    prompt = f"""
    Eres un analista de mercado experto en el sector de metales y commodities.
    Tu tarea es leer el siguiente artículo de noticias sobre '{topic}' y escribir un resumen ejecutivo conciso de 2 a 3 párrafos en español.
    El resumen debe ser objetivo, informativo y centrarse en los datos y hechos clave relevantes para un análisis de mercado.
    No incluyas opiniones personales ni frases como "El artículo dice". Ve directo a los hechos.

    Artículo:
    {text}

    Resumen Ejecutivo:
    """
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        print("    -> ✅ Resumen generado con Claude.")
        return message
    except Exception as e:
        print(f"    -> ❌ Error en Claude: {e}")
        return "No se pudo generar el resumen debido a un error."
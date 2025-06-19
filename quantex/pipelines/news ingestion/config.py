# news_ingestion_service/config.py

import os
from dotenv import load_dotenv

# --- Lógica para encontrar el archivo .env en la raíz del proyecto ---

# 1. Obtenemos la ruta absoluta de la carpeta donde está este archivo (news_ingestion_service)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Subimos un nivel para llegar a la raíz del proyecto (mcp-server)
project_root = os.path.dirname(current_dir)

# 3. Construimos la ruta completa al archivo .env
dotenv_path = os.path.join(project_root, '.env')

# 4. Cargamos las variables de ese archivo .env
load_dotenv(dotenv_path=dotenv_path)

# --- Definición de las Variables de Configuración ---

# Leemos las claves específicas que este servicio necesita desde las variables de entorno ya cargadas
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


# También definimos la URL del RSS aquí para que sea fácil de cambiar en el futuro
RSS_FEED_URL = "https://rss.metal.com/news/the_latest.xml"

print("✅ Configuración de news_ingestion_service cargada.")
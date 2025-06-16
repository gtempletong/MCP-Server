# news_ingestion_service/config.py

import os
from dotenv import load_dotenv

# Carga las variables desde el archivo .env en la raíz del proyecto
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Credenciales de Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# --- Claves de API de Servicios ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# --- Validaciones ---
if not all([SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY, FIRECRAWL_API_KEY]):
    raise ValueError("Una o más variables de entorno requeridas no están configuradas. Revisa tu archivo .env")
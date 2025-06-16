# Proyecto MCP-Server v2.0

Este es el manual de referencia y la documentación central del proyecto.

## 1. Arquitectura del Sistema

- **Interfaz de Chat:** Slack (`slack_bolt`)
- **Cerebro IA:** Claude 3 Haiku (`anthropic`)
- **Base de Datos Estructurada:** Supabase (PostgreSQL)
- **Memoria Vectorial (Largo Plazo):** Pinecone
- **Motor de Embeddings:** Google AI (`generative-ai`)
- **Fuente de Datos Primaria:** Google Sheets (`gspread`, `pandas`)
- **Herramientas Externas:** Google Custom Search API

## 2. Configuración de Entorno (`.env`)

El archivo `.env` requiere las siguientes claves:
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `ANTHROPIC_API_KEY`
- `PINECONE_API_KEY`
- `GOOGLE_API_KEY`
- `Google Search_API_KEY`
- `SEARCH_ENGINE_ID`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GOOGLE_CREDENTIALS_PATH`

## 3. Estructura de la Base de Datos (Supabase)

- **`series_definitions`**: Define cada serie de datos (nombre, fuente, unidad, etc.).
- **`time_series_data`**: Almacena los puntos de datos numéricos (valor y timestamp).
    - **Vista `v_time_series_readable`**: Vista combinada para fácil lectura humana.
- **`news_articles`**: Almacena resúmenes de noticias.
- **`chat_history`**: (Actualmente no utilizada, se reemplazó por Pinecone).

## 4. Scripts Principales

- **`main.py`**: El orquestador principal. Inicia el bot, maneja los eventos de Slack y usa las herramientas.
- **`ingest_data.py`**: El motor de ingesta de datos. Se conecta a Google Sheets, procesa los datos y los carga en Supabase.

---
# Chat_Interface/app.py (Versión de Producción Final - Verificada)

import os
import sys
import re
import json
from flask import Flask, render_template, request, jsonify
import anthropic
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- INICIO DE LA CORRECCIÓN DE RUTA DE IMPORTACIÓN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
# --- FIN DE LA CORRECCIÓN ---

# --- IMPORTACIÓN DE HERRAMIENTAS ---
try:
    from data_workers.query_reformulator_agent import reformulate_query
    from data_workers.tool_router_agent import decide_tool_to_use
    # from data_workers.market_data_provider import get_comparative_data # Descomenta cuando lo necesites
    print("✅ Módulos de data_workers importados.")
except ImportError as e:
    print(f"❌ ERROR al importar data_workers: {e}")
    # Definimos funciones falsas para que la app pueda arrancar y mostrar el error
    def reformulate_query(query): return query
    def decide_tool_to_use(query): return {"tool_name": "error", "argument": "Módulos no encontrados."}

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CHILE_TZ = pytz.timezone('America/Santiago')

try:
    from supabase import create_client, Client
    from googleapiclient.discovery import build
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
    print("✅ Clientes de API inicializados.")
except Exception as e:
    print(f"❌ Error al inicializar clientes: {e}")

# --- DEFINICIÓN DE HERRAMIENTAS (AGENTES DE TAREAS) ---

def get_news_articles(topic: str, date_filter: str = None) -> str:
    """Busca noticias por tema en Supabase, con un filtro de fecha opcional."""
    print(f"🛠️ [Herramienta Noticias] Ejecutando para tema: '{topic}', Filtro de Fecha: '{date_filter}'")
    try:
        query = supabase.table('news_articles').select('title, summary, published_at').ilike('topic', f'%{topic}%')
        if date_filter:
            query = query.eq('published_at', date_filter)
        
        response = query.order('published_at', desc=True).limit(20).execute()

        if not response.data:
            return f"No se encontraron noticias para el tema '{topic}'" + (f" en la fecha {date_filter}." if date_filter else ".")
        
        formatted_news = [f"- ({a['published_at']}) **{a['title']}**: {a['summary']}" for a in response.data]
        return "\n".join(formatted_news)
    except Exception as e: 
        print(f"  -> ❌ Error técnico en la herramienta de noticias: {e}")
        return f"Error técnico al buscar noticias: {e}"

# Mapea los nombres de las herramientas a las funciones reales de Python
TOOL_MAPPING = {
    "get_news_articles": get_news_articles,
    # "get_market_data": get_market_data, # Puedes añadir más herramientas aquí
}


# --- RUTA PRINCIPAL (ORQUESTADOR) ---
@app.route("/")
def home(): return render_template("index.html")

@app.route("/chat", methods=['POST'])
def chat():
    user_message = request.json.get("message")
    if not user_message: return jsonify({"error": "No se recibió ningún mensaje."})
    
    print(f"💬 [Orquestador] Petición recibida: '{user_message}'")
    try:
        # ETAPA 0: REFORMULACIÓN
        clean_query = reformulate_query(user_message)
        
        # ETAPA 1: PLANIFICACIÓN
        action_plan = decide_tool_to_use(clean_query)
        
        # ETAPA 2: EJECUCIÓN
        tool_output = "El planificador decidió que no se requería ninguna herramienta."
        if action_plan and action_plan.get('tool_name') in TOOL_MAPPING:
            tool_name = action_plan['tool_name']
            argument = action_plan.get('argument')
            date_filter = action_plan.get('date_filter')
            
            print(f"  -> [Orquestador] Ejecutando plan: Herramienta='{tool_name}', Argumento='{argument}', Filtro de Fecha='{date_filter}'")
            
            tool_to_run = TOOL_MAPPING[tool_name]
            
            # Pasamos los argumentos correctos a la herramienta correcta
            tool_output = tool_to_run(topic=argument, date_filter=date_filter)
        
        # ETAPA 3: SÍNTESIS
        print("  -> [Orquestador] Enviando evidencia al Sintetizador (Quantex)...")
        prompt_path = os.path.join(project_root, 'Prompts', 'prompt_quantex.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            synthesis_system_prompt = f.read()

        final_prompt_for_llm = f"Contexto Recolectado:\n---\n{tool_output}\n---\nPregunta Original del Usuario: {user_message}\n\nRespuesta Experta y Concisa:"
        
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2048,
            system=synthesis_system_prompt,
            messages=[{"role": "user", "content": final_prompt_for_llm}]
        )
        final_response = response.content[0].text
        
        return jsonify({"text_response": final_response})

    except Exception as e:
        print(f"❌ Ocurrió un error en el Orquestador: {e}")
        return jsonify({"text_response": "Lo siento, ocurrió un error grave."})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
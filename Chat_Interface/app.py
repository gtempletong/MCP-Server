import os
import re
import time
from flask import Flask, render_template, request, jsonify
import anthropic
import openai
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from googleapiclient.discovery import build

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)

try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
    print("✅ Todos los clientes de API inicializados.")
except Exception as e:
    print(f"❌ Error al inicializar clientes: {e}")

conversation_histories = {}
print("✅ Memoria de corto plazo para conversaciones lista.")


# --- FUNCIONES DE RECOLECCIÓN DE DATOS ---
def get_all_series_names() -> str:
    print("🧠 Obteniendo catálogo de series de datos de Supabase...")
    try:
        response = supabase.table('series_definitions').select('series_name').execute()
        if response.data:
            names = [item['series_name'] for item in response.data]
            return ", ".join(names)
        return "No se encontraron series."
    except Exception as e:
        print(f"Error obteniendo nombres de series: {e}")
        return "Error al obtener catálogo."

def get_market_data(series_name: str, days_ago: int = 7) -> str:
    print(f"🛠️  Usando herramienta: Buscando datos para '{series_name}' en Supabase.")
    try:
        date_filter = datetime.now(timezone.utc) - timedelta(days=days_ago)
        series_def_response = supabase.table('series_definitions').select('id').ilike('series_name', series_name).single().execute()
        if not series_def_response.data: return f"No se encontró una definición exacta para la serie '{series_name}'."
        series_id = series_def_response.data['id']
        response = supabase.table('time_series_data').select('timestamp', 'value').eq('series_id', series_id).gte('timestamp', date_filter.isoformat()).order('timestamp', desc=True).limit(10).execute()
        if not response.data: return f"No se encontraron datos para la serie '{series_name}' en el rango de fechas."
        return "\n".join([f"Fecha: {d['timestamp']}, Valor: {d['value']}" for d in response.data])
    except Exception as e: return f"Error al buscar datos de mercado: {e}"

def get_news_articles(topic: str, days_ago: int = 7) -> str:
    print(f"🛠️  Usando herramienta: get_news_articles(topic='{topic}') en Supabase.")
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
        response = supabase.table('news_articles').select('summary', 'published_at').eq('topic', topic).gte('published_at', cutoff_date.isoformat()).order('published_at', desc=True).limit(15).execute()
        if not response.data: return f"No se encontraron noticias para '{topic}' en los últimos {days_ago} días."
        return "\n".join([f"- Noticia del {article['published_at'][:10]}: {article['summary']}" for article in response.data])
    except Exception as e: return f"Error al consultar noticias: {str(e)}"

def Google_Search(query: str) -> str:
    print(f"🛠️ Usando herramienta: Google_Search con la consulta '{query}'")
    try:
        service = build("customsearch", "v1", developerKey=os.environ["Google_Search_API_KEY"])
        result = service.cse().list(q=query, cx=os.environ["SEARCH_ENGINE_ID"], num=3).execute()
        snippets = [f"Fuente: {item.get('link')}\nContenido: {item.get('snippet', '')}" for item in result.get('items', [])]
        return "\n\n---\n\n".join(snippets) if snippets else "No se encontraron resultados en la web."
    except Exception as e: return f"Error al buscar en Google: {e}"

# --- LISTA DE HERRAMIENTAS (SCHEMA PARA LA IA) ---
tools = [
    { "name": "get_market_data", "description": "Busca en la base de datos interna (Supabase) datos NUMÉRICOS de SERIES DE TIEMPO.", "input_schema": {"type": "object", "properties": {"series_name": {"type": "string", "description": "Nombre exacto de la serie del catálogo, ej: 'Precio Cobre LME'."}, "days_ago": {"type": "integer", "description": "Número de días hacia atrás a buscar."}},"required": ["series_name"]}},
    { "name": "get_news_articles", "description": "Busca en la base de datos interna (Supabase) RESÚMENES DE NOTICIAS sobre un tema.", "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "description": "El tema en inglés, ej: 'copper'."},"days_ago": {"type": "integer", "description": "Número de días hacia atrás a buscar."}},"required": ["topic", "days_ago"]}},
    { "name": "Google_Search", "description": "Busca información pública en la web. Usar como 'plan B' si los datos no se encuentran en la base de datos.", "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "La consulta de búsqueda."}}, "required": ["query"]}}
]

# --- LÓGICA DE INFORMES Y ARTEFACTOS ---
def generate_content_with_any_model(model_config: dict, system_prompt: str, messages: list) -> str:
    provider = model_config.get("provider")
    model_name = model_config.get("model_name")
    if not provider or not model_name: return "<h1>Error</h1><p>Configuración de modelo inválida.</p>"
    print(f"⚡️ Usando IA de '{provider}' con el modelo '{model_name}'...")
    try:
        if provider == "anthropic":
            response = claude_client.messages.create(model=model_name, max_tokens=4096, system=system_prompt, messages=messages)
            return response.content[0].text
        elif provider == "google":
            gemini_model = genai.GenerativeModel(model_name)
            response = gemini_model.generate_content(f"{system_prompt}\n\nHistorial de Conversación:\n{messages}")
            return response.text
        elif provider == "openai":
            response = openai_client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": system_prompt}] + messages)
            return response.choices[0].message.content
        else: return f"<h1>Error</h1><p>Proveedor de IA '{provider}' no soportado.</p>"
    except Exception as e:
        print(f"❌ Error con la API de '{provider}': {e}")
        return f"<h1>Error</h1><p>Ocurrió un error al contactar al modelo '{provider}': {e}</p>"

def get_report_config(report_keyword: str) -> dict | None:
    print(f"🧠 Buscando configuración para el informe: '{report_keyword}'")
    try:
        response = supabase.table('report_definitions').select('*').eq('report_keyword', report_keyword).eq('is_active', True).single().execute()
        return response.data if response.data else None
    except Exception as e: return None

def generate_report_html(report_config: dict, user_prompt: str, messages: list) -> dict:
    print(f"🤖 Iniciando flujo de GENERACIÓN para: '{report_config['display_title']}'")
    try:
        base_path = os.path.join(os.path.dirname(__file__), '..')
        with open(os.path.join(base_path, report_config['prompt_file']), "r", encoding="utf-8") as f: report_instructions = f.read()
        with open(os.path.join(base_path, report_config['example_file']), "r", encoding="utf-8") as f: report_example = f.read()
        market_data_for_prompt, market_data_for_snapshot = [], {}
        for series in report_config['market_data_series']:
            data = get_market_data(series_name=series, days_ago=8)
            market_data_for_prompt.append(f"DATOS PARA '{series}':\n{data}\n")
            market_data_for_snapshot[series] = data
        news_data = get_news_articles(topic=report_config['news_topic'], days_ago=7)
        
        system_prompt_for_report = f"""{report_instructions}\n\n--- DATOS RECOLECTADOS ---\n{''.join(market_data_for_prompt)}\nNOTICIAS RECIENTES (TEMA: {report_config['news_topic']}):\n{news_data}\n--- FIN DE LOS DATOS ---\n\n--- EJEMPLO DE FORMATO HTML ESPERADO ---\n{report_example}\n--- FIN DEL EJEMPLO ---\n\nTu tarea principal es generar el {report_config['display_title']} para el día de hoy ({datetime.now().strftime('%d de %B de %Y')}). Ten en cuenta la conversación reciente para cualquier aclaración. Responde únicamente con el código HTML del informe."""
        
        model_config = report_config.get('model_config')
        generated_html = generate_content_with_any_model(model_config, system_prompt_for_report, messages)
        
        print("   - Guardando el artefacto generado...")
        source_data_snapshot = {"market_data": market_data_for_snapshot, "news_data": news_data}
        data_to_insert = {"artifact_type": report_config['report_keyword'], "version": 1, "full_content": generated_html, "source_data": source_data_snapshot, "user_prompt": user_prompt}
        insert_response = supabase.table('generated_artifacts').insert(data_to_insert).execute()
        new_artifact_id = insert_response.data[0]['id']
        print(f"   -> Artefacto guardado. ID: {new_artifact_id}")
        return {"html": generated_html, "id": new_artifact_id}
    except Exception as e:
        print(f"❌ Error durante la generación del informe: {e}")
        return {"html": f"<h1>Error</h1><p>Ocurrió un error: {e}</p>", "id": None}

def get_latest_artifact(artifact_type: str) -> dict | None:
    print(f"🧠 Buscando el último artefacto del tipo: '{artifact_type}'")
    try:
        response = supabase.table('generated_artifacts').select('*').eq('artifact_type', artifact_type).order('version', desc=True).limit(1).single().execute()
        if response.data:
            print(f"  -> Encontrado artefacto ID: {response.data['id']}, Versión: {response.data['version']}")
            return response.data
        return None
    except Exception as e: return None

def edit_report_html(last_artifact: dict, user_edit_prompt: str, messages: list) -> dict:
    print(f"🔄 Iniciando flujo de EDICIÓN para artefacto ID: {last_artifact['id']}")
    try:
        edit_system_prompt = f"""Eres un editor experto de documentos HTML. A continuación, te proporciono el código HTML de un informe que generaste previamente. Tu tarea es aplicar la modificación que te pide el usuario y devolver únicamente el código HTML completo y actualizado. Mantén la estructura y los estilos existentes a menos que la modificación pida cambiarlos.\n\n--- HTML DEL INFORME ANTERIOR (VERSIÓN {last_artifact['version']}) ---\n{last_artifact['full_content']}\n--- FIN DEL HTML ANTERIOR ---"""
        report_config = get_report_config(last_artifact['artifact_type'])
        model_config = report_config.get('model_config') if report_config else None
        if not model_config: return {"html": "<h1>Error</h1><p>No se pudo encontrar la configuración del modelo original.</p>", "id": None}
        
        edited_html = generate_content_with_any_model(model_config, edit_system_prompt, messages)
        
        print("   - Guardando la nueva versión del artefacto...")
        new_version_number = last_artifact['version'] + 1
        data_to_insert = {"artifact_type": last_artifact['artifact_type'], "version": new_version_number, "full_content": edited_html, "source_data": last_artifact['source_data'], "user_prompt": user_edit_prompt, "parent_artifact_id": last_artifact['id']}
        insert_response = supabase.table('generated_artifacts').insert(data_to_insert).execute()
        new_artifact_id = insert_response.data[0]['id']
        print(f"   -> Nueva versión {new_version_number} guardada. ID: {new_artifact_id}")
        return {"html": edited_html, "id": new_artifact_id}
    except Exception as e:
        print(f"❌ Error durante la edición del informe: {e}")
        return {"html": f"<h1>Error</h1><p>Lo siento, ocurrió un error al editar: {e}</p>", "id": None}

# --- RUTAS DE LA APLICACIÓN FLASK ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    if not user_message: return jsonify({"error": "No se recibió ningún mensaje."}), 400

    session_id = "webapp_session"
    if session_id not in conversation_histories:
        available_series = get_all_series_names()
        conversation_histories[session_id] = {"messages": [], "series_catalog": available_series}
    conversation_histories[session_id]["messages"].append({"role": "user", "content": user_message})
    
    prompt_lower = user_message.lower()
    edit_keywords = ["modifica", "cambia", "ajusta", "itera", "edita"]
    report_keywords = ["informe", "reporte"]

    if any(keyword in prompt_lower for keyword in edit_keywords):
        print("💡 Detectada intención de EDICIÓN.")
        available_report_keys_res = supabase.table('report_definitions').select('report_keyword').execute()
        available_report_keys = [item['report_keyword'] for item in available_report_keys_res.data]
        found_keyword = next((keyword for keyword in available_report_keys if keyword in prompt_lower), None)
        if found_keyword:
            latest_artifact = get_latest_artifact(found_keyword)
            if latest_artifact:
                messages_history = conversation_histories[session_id]["messages"]
                edit_result = edit_report_html(latest_artifact, user_message, messages_history)
                return jsonify({"html_report": edit_result["html"], "artifact_id": edit_result["id"]})
            else:
                return jsonify({"text_response": f"Pediste modificar un informe sobre '{found_keyword}', pero no encontré uno para editar. Primero genera uno."})
        else:
            return jsonify({"text_response": "Quieres modificar algo, pero no especificaste un tema que yo conozca."})
    
    elif any(keyword in prompt_lower for keyword in report_keywords):
        print("💡 Detectada intención de INFORME.")
        available_report_keys_res = supabase.table('report_definitions').select('report_keyword').execute()
        available_report_keys = [item['report_keyword'] for item in available_report_keys_res.data]
        found_keyword = next((keyword for keyword in available_report_keys if keyword in prompt_lower), None)
        if found_keyword:
            report_config = get_report_config(found_keyword)
            if report_config:
                messages_history = conversation_histories[session_id]["messages"]
                report_result = generate_report_html(report_config, user_message, messages_history)
                return jsonify({"html_report": report_result["html"], "artifact_id": report_result["id"]})
        return jsonify({"text_response": f"Quieres un informe, pero no especificaste un tema válido. Disponibles: {', '.join(available_report_keys)}."})
    
    else:
        # Lógica para una conversación estándar
        print(f"💬  Recibida pregunta estándar: '{user_message}'")
        try:
            series_catalog = conversation_histories[session_id].get("series_catalog", "No disponible")
            base_path = os.path.join(os.path.dirname(__file__), '..')
            with open(os.path.join(base_path, "prompts", "system_prompt_conversacional.txt"), "r", encoding="utf-8") as f:
                prompt_template = f.read()
            system_prompt = prompt_template.format(series_catalog=series_catalog)

            response = claude_client.messages.create(model="claude-3-haiku-20240307", max_tokens=2048, system=system_prompt, messages=conversation_histories[session_id]["messages"], tools=tools, tool_choice={"type": "auto"})
            
            while response.stop_reason == "tool_use":
                tool_calls = [block for block in response.content if block.type == "tool_use"]
                conversation_histories[session_id]["messages"].append({"role": "assistant", "content": response.content})
                tool_outputs = []
                for tool_call in tool_calls:
                    tool_name, tool_input, tool_use_id = tool_call.name, tool_call.input, tool_call.id
                    if tool_name == "get_market_data": tool_result = get_market_data(series_name=tool_input.get("series_name"), days_ago=tool_input.get("days_ago", 7))
                    elif tool_name == "get_news_articles": tool_result = get_news_articles(topic=tool_input.get("topic"), days_ago=tool_input.get("days_ago", 7))
                    elif tool_name == "Google_Search": tool_result = Google_Search(query=tool_input.get("query"))
                    else: tool_result = f"Herramienta desconocida: {tool_name}"
                    tool_outputs.append({"type": "tool_result", "tool_use_id": tool_use_id, "content": str(tool_result)})
                
                conversation_histories[session_id]["messages"].append({"role": "user", "content": tool_outputs})
                response = claude_client.messages.create(model="claude-3-haiku-20240307", max_tokens=2048, system=system_prompt, messages=conversation_histories[session_id]["messages"], tools=tools)
            
            ai_text = response.content[0].text
            conversation_histories[session_id]["messages"].append({"role": "assistant", "content": ai_text})
            return jsonify({"text_response": ai_text})
        except Exception as e:
            print(f"Ocurrió un error en la conversación: {e}")
            return jsonify({"text_response": "Lo siento, ocurrió un error."})

# --- PUNTO DE ENTRADA DE LA APLICACIÓN ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
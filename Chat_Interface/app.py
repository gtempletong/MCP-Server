# Chat_Interface/app.py - VERSIÓN FINAL (ITERACIONES + PARSEO HTML ROBUSTO)

import os
import sys
import json
from flask import Flask, render_template, request, jsonify
import anthropic
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE RUTAS E IMPORTACIONES ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

try:
    from data_workers.query_reformulator_agent import reformulate_query
    from data_workers.tool_router_agent import decide_tool_to_use
    print("✅ Módulos de data_workers importados.")
except ImportError as e:
    print(f"❌ ERROR al importar data_workers: {e}")
    def reformulate_query(query): return query
    def decide_tool_to_use(query): return {"tool_name": "error", "argument": "Módulos no encontrados."}

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CHILE_TZ = pytz.timezone('America/Santiago')

try:
    from supabase import create_client, Client
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))
    print("✅ Clientes de API inicializados.")
except Exception as e:
    print(f"❌ Error al inicializar clientes: {e}")

# --- DEFINICIÓN DE HERRAMIENTAS ---
def get_news_articles(topic: str = None, date_filter: str = None, days_ago: int = None) -> str:
    print(f"🛠️ [Herramienta Noticias] Ejecutando para Tema: '{topic}', Filtro Fecha: '{date_filter}', Días Atrás: {days_ago}")
    try:
        query = supabase.table('news_articles').select('title, summary, published_at')
        if topic: query = query.ilike('topic', f'%{topic}%')
        if days_ago:
            try:
                num_days = int(days_ago)
                if num_days > 0:
                    end_date = datetime.now(CHILE_TZ)
                    start_date = end_date - timedelta(days=num_days)
                    query = query.gte('published_at', start_date.strftime('%Y-%m-%d')).lte('published_at', end_date.strftime('%Y-%m-%d'))
            except (ValueError, TypeError): print(f"  -> ⚠️ 'days_ago' no es un entero válido: {days_ago}")
        elif date_filter:
            query = query.gte('published_at', date_filter).lte('published_at', date_filter)
        response = query.order('published_at', desc=True).limit(20).execute()
        if not response.data:
            message = "No se encontraron noticias"
            if topic: message += f" para el tema '{topic}'"
            if date_filter: message += f" en la fecha {date_filter}"
            if days_ago: message += f" en los últimos {days_ago} días"
            return message + "."
        return "\n".join([f"- ({datetime.strptime(a['published_at'], '%Y-%m-%d').strftime('%d-%m-%Y')}) **{a['title']}**: {a['summary']}" for a in response.data])
    except Exception as e: return f"Error técnico al buscar noticias: {e}"

def get_market_data(series_name: str, date_filter: str = None, days_ago: int = None) -> str:
    print(f"🛠️ [Herramienta Mercado] Ejecutando para Serie: '{series_name}', Filtro Fecha: '{date_filter}', Días Atrás: {days_ago}")
    try:
        series_info_res = supabase.table('series_definitions').select('id, unit').eq('series_name', series_name).single().execute()
        if not series_info_res.data: return f"Error: La serie '{series_name}' no fue encontrada."
        series_id, series_unit = series_info_res.data['id'], series_info_res.data.get('unit', '')
        query = supabase.table('time_series_data').select('timestamp, value').eq('series_id', series_id)
        if days_ago:
            try:
                num_days = int(days_ago)
                if num_days > 0:
                    end_date = datetime.now(CHILE_TZ)
                    start_date = end_date - timedelta(days=num_days)
                    query = query.gte('timestamp', start_date.isoformat()).lte('timestamp', end_date.isoformat())
            except (ValueError, TypeError): print(f"  -> ⚠️ 'days_ago' no es un entero válido: {days_ago}")
        elif date_filter:
            start_of_day = datetime.strptime(date_filter, '%Y-%m-%d').isoformat()
            end_of_day = (datetime.strptime(date_filter, '%Y-%m-%d') + timedelta(days=1, seconds=-1)).isoformat()
            query = query.gte('timestamp', start_of_day).lte('timestamp', end_of_day)
        response = query.order('timestamp', desc=True).limit(365).execute()
        if not response.data: return f"No se encontraron datos para la serie '{series_name}' en el período solicitado."
        header = f"Datos para la serie '{series_name}':\n"
        return header + "\n".join([f"- {datetime.fromisoformat(row['timestamp']).strftime('%d-%m-%Y')}: {row['value']} {series_unit}".strip() for row in response.data])
    except Exception as e: return f"Error técnico al buscar datos de mercado para '{series_name}': {e}"

TOOL_MAPPING = { "get_news_articles": get_news_articles, "get_market_data": get_market_data, }

@app.route("/")
def home(): return render_template("index.html")

@app.route("/chat", methods=['POST'])
def chat():
    json_data = request.get_json()
    user_message = json_data.get("message")
    context_id = json_data.get("context_id")
    if not user_message: return jsonify({"error": "No se recibió ningún mensaje."})
    
    print(f"💬 [Orquestador] Petición recibida: '{user_message}'")
    if context_id: print(f"   -> En el contexto del artefacto: {context_id}")

    try:
        synthesis_system_prompt = ""
        source_data_for_saving = ""
        prev_artifact = None

        if context_id:
            print("   -> [Orquestador] Iniciando flujo de edición...")
            artifact_res = supabase.table('generated_artifacts').select('*').eq('id', context_id).single().execute()
            if not artifact_res.data: return jsonify({"text_response": "Error: No se encontró el artefacto original para editar."})
            
            prev_artifact = artifact_res.data
            prompt_file_name = f"prompt_{prev_artifact['artifact_type']}.txt"
            with open(os.path.join(project_root, 'Prompts', prompt_file_name), 'r', encoding='utf-8') as f:
                synthesis_system_prompt = f.read()

            final_prompt_for_llm = f"""DATOS ORIGINALES (NO CAMBIAN):
---
{prev_artifact['source_data']}
---

VERSIÓN ANTERIOR DEL INFORME HTML:
---
{prev_artifact['full_content']}
---

NUEVA INSTRUCCIÓN DEL USUARIO:
'{user_message}'

Tu tarea es generar una NUEVA versión del informe HTML completo, usando los DATOS ORIGINALES, pero aplicando la NUEVA INSTRUCCIÓN DEL USUARIO a la VERSIÓN ANTERIOR DEL INFORME.
"""
            print(f"   -> Usando prompt de edición: {prompt_file_name}")

        else:
            print("   -> [Orquestador] Iniciando flujo de creación...")
            clean_query = reformulate_query(user_message)
            action_plan = decide_tool_to_use(clean_query)
            
            tool_output = "El planificador decidió que no se requería ninguna herramienta."
            evidence_dossier = []
            action_list = action_plan if isinstance(action_plan, list) else [action_plan]

            for action in action_list:
                if action and action.get('tool_name') in TOOL_MAPPING:
                    tool_name, argument, date_filter, days_ago = action.get('tool_name'), action.get('argument'), action.get('date_filter'), action.get('days_ago')
                    print(f"   -> [Orquestador] Ejecutando sub-tarea: {tool_name}('{argument}')...")
                    tool_to_run = TOOL_MAPPING[tool_name]
                    if tool_name == "get_news_articles": single_result = tool_to_run(topic=argument, date_filter=date_filter, days_ago=days_ago)
                    elif tool_name == "get_market_data": single_result = tool_to_run(series_name=argument, date_filter=date_filter, days_ago=days_ago)
                    else: single_result = "Herramienta desconocida."
                    evidence_dossier.append(single_result)

            if evidence_dossier: tool_output = "\n\n---\n\n".join(evidence_dossier)
            source_data_for_saving = tool_output
            
            if "informe del cobre" in user_message.lower():
                prompt_file_name = 'prompt_cobre.txt'
                with open(os.path.join(project_root, 'examples', 'ejemplo_cobre.html'), 'r', encoding='utf-8') as f: html_example = f.read()
                with open(os.path.join(project_root, 'Prompts', prompt_file_name), 'r', encoding='utf-8') as f: synthesis_system_prompt = f.read() + "\n\n### EJEMPLO DE FORMATO DE SALIDA HTML ###\n" + html_example
            else:
                prompt_file_name = 'prompt_quantex.txt'
                with open(os.path.join(project_root, 'Prompts', prompt_file_name), 'r', encoding='utf-8') as f: synthesis_system_prompt = f.read()
            
            print(f"   -> Usando prompt: {prompt_file_name}")
            final_prompt_for_llm = f"DATOS RECOLECTADOS:\n---\n{source_data_for_saving}\n---\n\nCon base en los datos anteriores, y siguiendo estrictamente tus instrucciones y formato, responde a la siguiente petición original del usuario: {user_message}"
        
        response = claude_client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=4096, system=synthesis_system_prompt, messages=[{"role": "user", "content": final_prompt_for_llm}])
        final_response_text = response.content[0].text
        
        html_start_tag = "<!DOCTYPE html"
        html_start_index = final_response_text.find(html_start_tag)

        if html_start_index != -1:
            html_content = final_response_text[html_start_index:]
            print("   -> [Orquestador] Detectado informe HTML. Guardando en 'generated_artifacts'...")
            try:
                if context_id:
                    new_version = prev_artifact['version'] + 1
                    parent_id = context_id
                    source_data_to_save = prev_artifact['source_data']
                    artifact_type = prev_artifact['artifact_type']
                else:
                    new_version = 1
                    parent_id = None
                    # source_data_for_saving fue definida en el flujo de creación
                    artifact_type = 'cobre' # TODO: Hacer esto dinámico

                artifact_payload = {'artifact_type': artifact_type, 'version': new_version, 'source_data': source_data_to_save, 'full_content': html_content, 'user_prompt': user_message, 'parent_artifact_id': parent_id}
                insert_res = supabase.table('generated_artifacts').insert(artifact_payload).execute()
                
                if insert_res.data:
                    new_artifact_id = insert_res.data[0]['id']
                    print(f"   -> ✅ Artefacto guardado con éxito. Nuevo ID: {new_artifact_id} (Versión {new_version})")
                    return jsonify({"html_report": html_content, "artifact_id": new_artifact_id})
                else:
                    raise Exception("La inserción en Supabase no devolvió los datos.")
            except Exception as e:
                print(f"   -> ❌ Error al guardar el artefacto: {e}")
                return jsonify({"html_report": html_content, "error_saving": str(e)})
        else:
             return jsonify({"text_response": final_response_text})

    except Exception as e:
        print(f"❌ Ocurrió un error en el Orquestador: {e}")
        return jsonify({"text_response": "Lo siento, ocurrió un error grave."})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
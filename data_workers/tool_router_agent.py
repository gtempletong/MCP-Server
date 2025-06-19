# data_workers/tool_router_agent.py (VERSIÓN FINAL CON PARSEO ROBUSTO)

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

# --- INICIALIZACIÓN ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
claude_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_planner_prompt():
    """Carga el prompt para el agente planificador."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(project_root, 'Prompts', 'prompt_jefe_de_herramientas.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: 
        print(f"❌ Error cargando prompt del planificador: {e}")
        return "Error"

def decide_tool_to_use(clean_query: str, max_retries: int = 3) -> dict | list:
    """
    Analiza la consulta y devuelve un plan de acción, que puede ser un
    único objeto dict o una lista de dicts para planes multi-paso.
    """
    print(f"🧠 [Sub-Agente Planificador] Planificando para: '{clean_query}'")
    system_prompt = get_planner_prompt()
    if system_prompt == "Error":
        return {"tool_name": "error", "argument": "No se pudo cargar el prompt del planificador."}

    for attempt in range(max_retries):
        try:
            response = claude_client.messages.create(
                model="claude-3-haiku-20240307", 
                max_tokens=2048, # Aumentamos tokens para planes largos
                system=system_prompt,
                messages=[{"role": "user", "content": clean_query}]
            )
            
            json_text = response.content[0].text

            # --- LÓGICA DE PARSEO MEJORADA ---
            # Busca el inicio del JSON, sea una lista '[' o un objeto '{'
            start_bracket = json_text.find('[')
            start_brace = json_text.find('{')
            
            # Determina el verdadero inicio del JSON
            if start_bracket != -1 and (start_bracket < start_brace or start_brace == -1):
                start_index = start_bracket
                end_char = ']'
            else:
                start_index = start_brace
                end_char = '}'
            
            if start_index == -1:
                raise ValueError("No se encontró JSON en la respuesta del LLM.")

            # Busca el final correspondiente
            end_index = json_text.rfind(end_char)
            if end_index == -1:
                raise ValueError("JSON malformado en la respuesta del LLM.")

            # Extrae y parsea el string JSON
            json_str = json_text[start_index : end_index + 1]
            decision = json.loads(json_str)
            # --- FIN DE LA LÓGICA MEJORADA ---

            print(f"   -> Plan de Acción Generado: {decision}")
            return decision

        except Exception as e:
            print(f"   -> ❌ Error en el Planificador (Intento {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1: 
                time.sleep(2**attempt)
            else:
                # Si es el último intento, devolvemos un plan de error
                return {"tool_name": "error", "argument": f"Todos los reintentos fallaron. Último error: {e}"}
    
    # Fallback por si el bucle termina inesperadamente
    return {"tool_name": "error", "argument": "Fallo inesperado en el planificador."}
import os, json, time
from dotenv import load_dotenv
from anthropic import Anthropic

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
claude_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_planner_prompt():
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(project_root, 'Prompts', 'prompt_jefe_de_herramientas.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return f"Error cargando prompt: {e}"

def decide_tool_to_use(clean_query: str, max_retries: int = 3) -> dict:
    print(f"🧠 [Sub-Agente Planificador] Planificando para: '{clean_query}'")
    system_prompt = get_planner_prompt()
    for attempt in range(max_retries):
        try:
            response = claude_client.messages.create(
                model="claude-3-haiku-20240307", max_tokens=250, system=system_prompt,
                messages=[{"role": "user", "content": clean_query}]
            )
            json_text = response.content[0].text
            json_str = json_text[json_text.find('{'):json_text.rfind('}')+1]
            decision = json.loads(json_str)
            print(f"  -> Plan de Acción Generado: {decision}")
            return decision
        except Exception as e:
            print(f"  -> ❌ Error en el Planificador (Intento {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1: time.sleep(2**attempt)
    return {"tool_name": "error", "argument": "Todos los reintentos a la API fallaron."}
# data_workers/query_reformulator_agent.py (Versión con import corregido)

import os
import time
from dotenv import load_dotenv
import anthropic # <--- LA LÍNEA QUE FALTABA

# --- INICIALIZACIÓN ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except Exception as e:
    print(f"❌ [Query Reformulator] Error al inicializar cliente de Anthropic: {e}")
    claude_client = None

def get_reformulator_prompt():
    """Carga las instrucciones para este sub-agente."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(project_root, 'Prompts', 'prompt_reformulator.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ ERROR: No se pudo cargar 'prompt_reformulator.txt': {e}")
        return None

def reformulate_query(user_query: str, max_retries: int = 3) -> str:
    """Toma una pregunta de usuario y la reformula para que sea clara y precisa."""
    if not claude_client:
        print("-> [Query Reformulator] Cliente de Anthropic no disponible. Devolviendo query original.")
        return user_query

    print(f"🧠 [Sub-Agente Reformulador] Analizando: '{user_query}'")
    
    system_prompt = get_reformulator_prompt()
    if not system_prompt: 
        print("-> [Query Reformulator] No se pudo cargar el prompt. Devolviendo query original.")
        return user_query

    for attempt in range(max_retries):
        try:
            response = claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_query}]
            )
            reformulated_query = response.content[0].text.strip()
            print(f"  -> Consulta Limpia: '{reformulated_query}'")
            return reformulated_query
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  -> ⚠️ API sobrecargada. Reintentando en {wait_time} segundo(s)...")
                time.sleep(wait_time)
            else:
                print(f"  -> ❌ Error final en el Reformulador (API): {e}")
                return user_query
        except Exception as e:
            print(f"  -> ❌ Error general en el Reformulador: {e}")
            return user_query
    return user_query
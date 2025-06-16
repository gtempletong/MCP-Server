import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import pprint
import time

# --- FUNCIONES ESPECIALISTAS DE SCRAPING ---

def scrape_with_selector(url: str, selector: str) -> str:
    """
    Función especialista que extrae un dato usando un selector de data-test.
    """
    print(f"    scraping {url} para el dato con selector '{selector}'...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    element = soup.find(attrs={'data-test': selector})
    
    if element:
        print(f"      -> Dato encontrado: {element.text.strip()}")
        return element.text.strip()
            
    raise ValueError(f"No se pudo encontrar el dato con el selector '{selector}' en la página.")

def clean_and_convert_to_float(value: str) -> float:
    """Limpia un string y lo convierte a un número flotante."""
    if isinstance(value, (int, float)):
        return float(value)
    # Quita comas, símbolos de porcentaje, y cualquier otro carácter no numérico excepto el punto.
    cleaned_str = re.sub(r'[^\d.]', '', value)
    return float(cleaned_str)

def save_timeseries_data(supabase_client: Client, series_name: str, value: float):
    """Busca el ID de una serie y guarda el nuevo dato en la tabla time_series_data."""
    print(f"   - Guardando en Supabase: '{series_name}' = {value}")
    metric_response = supabase_client.table('series_definitions').select('id').eq('series_name', series_name).single().execute()
    if not metric_response.data:
        raise Exception(f"La métrica '{series_name}' no fue encontrada en 'series_definitions'.")
    series_id = metric_response.data['id']

    data_to_insert = {
        'series_id': series_id,
        'timestamp': datetime.now().isoformat(),
        'value': value
    }
    
    # Usamos 'upsert' para que si ya existe un valor para esa métrica y esa fecha, lo actualice
    supabase_client.table('time_series_data').upsert(data_to_insert, on_conflict="series_id, timestamp").execute()
    print("     ✅ Dato guardado/actualizado con éxito.")


# --- FUNCIÓN PRINCIPAL Y ORQUESTADOR ---

def get_active_scraping_targets(supabase_client: Client) -> list:
    """Consulta la tabla 'scraping_targets' y devuelve las tareas activas."""
    print("🧠 Consultando la lista de tareas de scraping activas...")
    try:
        response = supabase_client.table('scraping_targets').select('*').eq('is_active', True).execute()
        if response.data:
            print(f"✅ Se encontraron {len(response.data)} tareas activas.")
            return response.data
        else:
            print("⚠️ No se encontraron tareas de scraping activas.")
            return []
    except Exception as e:
        print(f"❌ Error al consultar las tareas de scraping: {e}")
        return []

def main():
    """Función principal que orquesta todo el proceso."""
    print("\n--- Iniciando el Orquestador de Scrapers ---")
    try:
        # Cargamos las variables de entorno desde la carpeta raíz del proyecto
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=dotenv_path)
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Cliente de Supabase inicializado.")
    except Exception as e:
        print(f"❌ Error fatal durante la inicialización: {e}")
        return

    targets = get_active_scraping_targets(supabase)
    
    if targets:
        print("\n--- Procesando Tareas: ---")
        for target in targets:
            print(f"\n▶️  Ejecutando tarea: '{target['target_name']}'")
            try:
                # La lógica ahora llama a nuestra nueva función de scraping genérica
                # NOTA: La columna en Supabase ahora debería contener el selector CSS
                css_selector = target.get('data_label_on_page') 
                
                if not css_selector:
                    print(f"   ⚠️  La tarea '{target['target_name']}' no tiene un selector CSS definido. Tarea omitida.")
                    continue

                scraped_value_str = scrape_with_selector(target['source_url'], css_selector)

                value_float = clean_and_convert_to_float(scraped_value_str)
                save_timeseries_data(supabase, target['destination_series_name'], value_float)

            except Exception as e:
                print(f"   ❌ ERROR al procesar la tarea '{target['target_name']}': {e}")
                continue # Continuamos con la siguiente tarea

    print("\n--- Proceso finalizado ---")

if __name__ == "__main__":
    main()
# data_workers/market_data_provider.py (Versión con lógica de fecha robusta)

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- INICIALIZACIÓN DEL CLIENTE DE SUPABASE ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- FUNCIÓN PRINCIPAL DE RECOLECCIÓN DE DATOS ---

def get_comparative_data(series_name: str) -> dict:
    """
    Busca en Supabase el último dato para una serie y luego busca los datos
    del día y la semana anteriores a esa fecha.
    """
    print(f"\n[DATA_WORKER] Buscando datos comparativos para '{series_name}'...")
    
    results = {
        "latest_date": None,
        "latest_value": None,
        "previous_day_value": None,
        "previous_week_value": None
    }
    
    try:
        # 1. Obtener el ID de la serie
        series_id_res = supabase.table('series_definitions').select('id').eq('series_name', series_name).single().execute()
        if not series_id_res.data:
            print(f"  -> No se encontró definición para la serie '{series_name}'.")
            return results
        series_id = series_id_res.data['id']
        print(f"  -> ID de la serie '{series_name}' encontrado.")

        # === LÓGICA MEJORADA DE 2 PASOS ===
        # PASO A: Encontrar el último dato disponible
        latest_data_res = supabase.table('time_series_data').select('timestamp, value').eq('series_id', series_id).order('timestamp', desc=True).limit(1).single().execute()
        
        if not latest_data_res.data:
            print(f"  -> No se encontró ningún dato para la serie '{series_name}'.")
            return results

        latest_timestamp_str = latest_data_res.data['timestamp']
        # Convertimos el string ISO de UTC a un objeto datetime
        latest_date_obj = datetime.fromisoformat(latest_timestamp_str)

        results['latest_date'] = latest_date_obj.strftime('%Y-%m-%d')
        results['latest_value'] = latest_data_res.data['value']
        print(f"  -> Último dato encontrado: {results['latest_value']} en la fecha {results['latest_date']} (UTC)")

        # PASO B: Usar esa fecha como referencia para buscar las anteriores
        start_of_latest_day = latest_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Rango para el día anterior
        start_of_previous_day = start_of_latest_day - timedelta(days=1)
        
        # Rango para la semana anterior
        start_of_last_week_day = start_of_latest_day - timedelta(days=7)
        end_of_last_week_day = start_of_last_week_day + timedelta(days=1)
        
        # Realizar las 2 consultas históricas
        prev_day_res = supabase.table('time_series_data').select('value').eq('series_id', series_id).gte('timestamp', start_of_previous_day.isoformat()).lt('timestamp', start_of_latest_day.isoformat()).order('timestamp', desc=True).limit(1).execute()
        if prev_day_res.data:
            results['previous_day_value'] = prev_day_res.data[0]['value']
        
        last_week_res = supabase.table('time_series_data').select('value').eq('series_id', series_id).gte('timestamp', start_of_last_week_day.isoformat()).lt('timestamp', end_of_last_week_day.isoformat()).order('timestamp', desc=True).limit(1).execute()
        if last_week_res.data:
            results['previous_week_value'] = last_week_res.data[0]['value']
            
        return results

    except Exception as e:
        print(f"  -> ❌ Error al obtener datos para '{series_name}': {e}")
        return results

# --- BLOQUE DE PRUEBA INDEPENDIENTE ---
if __name__ == "__main__":
    print("--- Probando el 'market_data_provider' (versión robusta) ---")
    
    serie_de_ejemplo = "Precio Cobre LME" 
    datos = get_comparative_data(serie_de_ejemplo)
    
    print("\n--- Resultados de la prueba ---")
    if datos.get("latest_value") is not None:
        print(f"✅ Valor más reciente para '{serie_de_ejemplo}' (fecha {datos['latest_date']}): {datos['latest_value']}")
    else:
        print(f"❌ No se encontró valor reciente para '{serie_de_ejemplo}'.")
        
    if datos.get("previous_day_value") is not None:
        print(f"✅ Valor del día anterior: {datos['previous_day_value']}")
    else:
        print(f"❌ No se encontró valor del día anterior.")

    if datos.get("previous_week_value") is not None:
        print(f"✅ Valor de la semana anterior: {datos['previous_week_value']}")
    else:
        print(f"❌ No se encontró valor de la semana anterior.")
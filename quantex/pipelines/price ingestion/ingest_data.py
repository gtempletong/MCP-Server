# ingest_data.py (Versión final con manejo de NaN y exclusión de fecha)

import os
import gspread
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import pytz
import math # Importamos math para chequear por NaN

def load_metadata_mapping():
    """Carga el mapa de metadata desde el archivo CSV, manejando valores vacíos."""
    try:
        mapping_path = os.path.join(os.path.dirname(__file__), 'metadata_mapping.csv')
        # CAMBIO: na_filter=False le dice a pandas que lea las celdas vacías como strings vacíos ('') en lugar de NaN.
        df_map = pd.read_csv(mapping_path, na_filter=False)
        mapping_dict = df_map.set_index('sheet_header').to_dict('index')
        print(f"✅ Mapa de metadata cargado con {len(mapping_dict)} definiciones.")
        return mapping_dict
    except Exception as e:
        print(f"❌ ERROR al cargar el mapa de metadata: {e}")
        return None

def main():
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    print("✅ Variables de entorno cargadas.")
    
    metadata_map = load_metadata_mapping()
    if not metadata_map: return False

    try:
        # ... (código de inicialización de clientes sin cambios)
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Cliente de Supabase inicializado.")
        credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        gc = gspread.service_account(filename=credentials_path)
        spreadsheet = gc.open("Datos para Supabase Google Sheet")
        worksheet = spreadsheet.sheet1
        print("✅ Conexión a google_sheets exitosa.")
    except Exception as e:
        print(f"❌ Error durante la inicialización de servicios: {e}")
        return False
    
    print("\n--- Fase 1: Leyendo datos de la hoja puente ---")
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) < 2: raise ValueError("La hoja puente está vacía.")
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        print(f"✅ Se leyeron {len(df)} filas.")
    except Exception as e:
        print(f"❌ Error leyendo la hoja: {e}")
        return False

    print("\n--- Fase 2: Asegurando definiciones en Supabase ---")
    definitions_map = {} 
    try:
        # CAMBIO: Nos aseguramos de no procesar la columna de fecha como una serie
        date_column_header = df.columns[0]
        headers_in_map = [h for h in df.columns if h in metadata_map and h != date_column_header]
        
        for header in headers_in_map:
            series_info = metadata_map[header]
            # Nos aseguramos de que no haya valores NaN antes de enviar a Supabase
            definition_payload = {k: (v if not pd.isna(v) else None) for k, v in series_info.items() if k != 'sheet_header'}
            supabase.table('series_definitions').upsert(definition_payload, on_conflict='series_name').execute()
            
            series_id_res = supabase.table('series_definitions').select('id').eq('series_name', series_info['series_name']).single().execute()
            definitions_map[header] = series_id_res.data['id']
        print(f"✅ Definiciones para {len(definitions_map)} series aseguradas y mapa de IDs creado.")
    except Exception as e:
        print(f"❌ Error procesando definiciones: {e}")
        return False

    print("\n--- Fase 3: Preparando lote de datos para Supabase ---")
    data_to_insert = []
    headers_to_process = headers_in_map # Usamos la misma lista de encabezados válidos

    for index, row in df.iterrows():
        try:
            timestamp_str = str(row[date_column_header])
            if not timestamp_str: continue
            timestamp_obj_naive = datetime.strptime(timestamp_str, '%Y/%m/%d')
            timestamp_iso = pytz.utc.localize(timestamp_obj_naive).isoformat()
        except (ValueError, TypeError):
            continue

        for header in headers_to_process:
            if header in row and str(row[header]).strip() != '':
                try:
                    value_str = str(row[header]).replace(',', '')
                    if value_str:
                        value = float(value_str)
                        series_id_to_insert = definitions_map.get(header)
                        if series_id_to_insert:
                            data_to_insert.append({'series_id': series_id_to_insert, 'timestamp': timestamp_iso, 'value': value})
                except (ValueError, TypeError):
                    pass
    
    print(f"✅ Se prepararon {len(data_to_insert)} puntos de datos para la ingesta.")

    print(f"\n--- Fase 4: Insertando datos en 'time_series_data' ---")
    if data_to_insert:
        batch_size = 5000
        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i + batch_size]
            print(f"  -> Enviando lote de {len(batch)} registros...")
            try:
                supabase.table('time_series_data').upsert(batch, on_conflict="series_id, timestamp").execute()
            except Exception as e:
                print(f"❌ Error al insertar lote: {e}")
                return False
        print(f"\n✅ ¡PROCESO DE INGESTA COMPLETADO!")
    else:
        print("ℹ️ No se encontraron nuevos datos para insertar.")
    
    return True

if __name__ == "__main__":
    if main():
        print("\nEjecución de ingesta completada con éxito.")
    else:
        print("\nEjecución de ingesta falló.")   
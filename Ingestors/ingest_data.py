import os
import gspread
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
print("✅ Variables de entorno cargadas.")

try:
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
    exit()


def clean_and_convert_to_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned_str = value.replace(',', '')
        return float(cleaned_str)
    raise ValueError("El valor no es un número convertible.")

def main():
    # --- FASE 1: LEER DATOS Y GENERAR DEFINICIONES DINÁMICAMENTE ---
    print("\n--- Fase 1: Leyendo datos de google_sheets ---")
    try:
        sheet_data = pd.DataFrame(worksheet.get_all_records())
        print(f"✅ Se leyeron {len(sheet_data)} filas de google_sheets.")

        all_headers = sheet_data.columns.tolist()
        date_column_header = all_headers[0]
        series_headers = all_headers[1:]
        print(f"✅ Se detectaron {len(series_headers)} columnas de datos para procesar.")
        
        SERIES_TO_INGEST = []
        for header in series_headers:
            SERIES_TO_INGEST.append({
                'sheet_header': header, 'series_name': header,
                'source': 'Bloomberg', 'category': 'auto-detected', 'unit': 'unknown'
            })

    except Exception as e:
        print(f"❌ Error leyendo o procesando los encabezados de google_sheets: {e}")
        return

    # --- FASE 2: POBLAR LA TABLA DE DEFINICIONES ---
    print("\n--- Fase 2: Poblando 'series_definitions' ---")
    definitions_map = {}
    for series in SERIES_TO_INGEST:
        try:
            supabase.table('series_definitions').upsert({
                'series_name': series['series_name'], 'source': series['source'],
                'category': series['category'], 'unit': series['unit']
            }, on_conflict='series_name').execute()
            
            series_id_response = supabase.table('series_definitions').select('id').eq('series_name', series['series_name']).single().execute()
            definitions_map[series['sheet_header']] = series_id_response.data['id']
            print(f"✅ Definición para '{series['series_name']}' asegurada.")
        except Exception as e:
            print(f"❌ Error procesando definición para '{series['series_name']}': {e}")
            
    # --- FASE 3: PREPARAR LOTE DE DATOS DE SERIE DE TIEMPO ---
    print("\n--- Fase 3: Preparando lote de datos para Supabase ---")
    data_to_insert = []
    for index, row in sheet_data.iterrows():
        try:
            timestamp_str = row[date_column_header]
            if not timestamp_str: continue
            timestamp = datetime.strptime(timestamp_str, '%Y/%m/%d').isoformat()
        except (ValueError, TypeError):
            print(f"⚠️ Fila omitida en la hoja {index+2}. Formato de fecha inválido: '{row[date_column_header]}'")
            continue

        for series_info in SERIES_TO_INGEST:
            header = series_info['sheet_header']
            if header in row and str(row[header]).strip() != '':
                try:
                    value = clean_and_convert_to_float(row[header])
                    data_to_insert.append({
                        'series_id': definitions_map[header],
                        'timestamp': timestamp, 'value': value
                    })
                except (ValueError, TypeError):
                    print(f"⚠️ Valor omitido para '{header}' en fecha '{timestamp_str}'. No es un número válido: '{row[header]}'")
                    continue

    # --- FASE 4: INSERTAR DATOS EN SUPABASE POR LOTES ---
    print(f"\n--- Fase 4: Insertando {len(data_to_insert)} puntos de datos en 'time_series_data' ---")
    if data_to_insert:
        batch_size = 5000  # Definimos un tamaño de lote más manejable
        total_inserted = 0
        
        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i + batch_size]
            print(f"  -> Enviando lote de {len(batch)} registros...")
            try:
                supabase.table('time_series_data').upsert(batch, on_conflict="series_id, timestamp").execute()
                total_inserted += len(batch)
            except Exception as e:
                print(f"❌ Error al insertar un lote de datos de series de tiempo: {e}")
                print("El proceso se detendrá. Es posible que algunos lotes anteriores se hayan insertado.")
                return # Detener el proceso si un lote falla

        print(f"\n✅ ¡PROCESO COMPLETADO! Se insertaron un total de {total_inserted} registros en Supabase.")
    else:
        print("ℹ️ No se encontraron nuevos datos para insertar.")

if __name__ == "__main__":
    ingest_data()
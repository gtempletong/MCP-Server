import os
import gspread
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
load_dotenv()
print("✅ Variables de entorno cargadas.")

try:
    # Conexión a Supabase
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Cliente de Supabase inicializado.")

    # Conexión a google_sheets
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    if not credentials_path:
        raise ValueError("La variable de entorno GOOGLE_CREDENTIALS_PATH no está definida.")
    
    gc = gspread.service_account(filename=credentials_path)
    spreadsheet = gc.open("Copper Bloomberg Data") # Asegúrate que el nombre sea exacto
    worksheet = spreadsheet.sheet1
    print("✅ Conexión a google_sheets exitosa.")

except Exception as e:
    print(f"❌ Error durante la inicialización de servicios: {e}")
    exit()

# --- DEFINICIÓN DE NUESTRAS SERIES DE DATOS ---
SERIES_TO_INGEST = [
    {'sheet_header': 'COMEX', 'series_name': 'Precio Cobre COMEX', 'source': 'COMEX', 'category': 'precio', 'unit': 'USD/lb'},
    {'sheet_header': 'LME', 'series_name': 'Precio Cobre LME', 'source': 'LME', 'category': 'precio', 'unit': 'USD/tonne'},
    {'sheet_header': 'SHFE', 'series_name': 'Precio Cobre SHFE', 'source': 'SHFE', 'category': 'precio', 'unit': 'CNY/tonne'},
    {'sheet_header': 'Inventarios SHFE', 'series_name': 'Inventarios Cobre SHFE', 'source': 'SHFE', 'category': 'inventario', 'unit': 'tonnes'},
    {'sheet_header': 'Inventarios COMEX', 'series_name': 'Inventarios Cobre COMEX', 'source': 'COMEX', 'category': 'inventario', 'unit': 'tonnes'},
    {'sheet_header': 'Inventarios LME', 'series_name': 'Inventarios Cobre LME', 'source': 'LME', 'category': 'inventario', 'unit': 'tonnes'},
    {'sheet_header': 'Inventarios Totales', 'series_name': 'Inventarios Cobre Totales', 'source': 'Consolidado', 'category': 'inventario', 'unit': 'tonnes'},
    {'sheet_header': 'DXY Curncy', 'series_name': 'Índice Dólar DXY', 'source': 'ICE', 'category': 'moneda', 'unit': 'puntos'},
    {'sheet_header': 'CNY Curncy', 'series_name': 'Tipo de Cambio USD/CNY', 'source': 'Mercado', 'category': 'moneda', 'unit': 'CNY'},
    {'sheet_header': 'CLP Curncy', 'series_name': 'Tipo de Cambio USD/CLP', 'source': 'Mercado', 'category': 'moneda', 'unit': 'CLP'}
]

# FUNCIÓN DE LIMPIEZA DE NÚMEROS - VERSIÓN FINAL Y SIMPLIFICADA
def clean_and_convert_to_float(value) -> float:
    # Si el valor ya es un número (int o float), lo devolvemos tal cual.
    if isinstance(value, (int, float)):
        return float(value)

    # Si es un texto, ahora asumimos el formato estándar "1,234.56"
    if isinstance(value, str):
        # Lo único que necesitamos hacer es quitar las comas de los miles.
        # El punto decimal lo entiende Python de forma nativa.
        cleaned_str = value.replace(',', '')
        return float(cleaned_str)

    # Si no es ni número ni texto, no es convertible.
    raise ValueError("El valor no es un número convertible.")

def ingest_data():
    # 1. Poblar la tabla de definiciones
    print("\n--- Fase 1: Poblando 'series_definitions' ---")
    definitions_map = {}
    for series in SERIES_TO_INGEST:
        try:
            supabase.table('series_definitions').upsert({
                'series_name': series['series_name'], 'source': series['source'],
                'category': series['category'], 'unit': series['unit']
            }, on_conflict='series_name').execute()
            
            series_id = supabase.table('series_definitions').select('id').eq('series_name', series['series_name']).single().execute().data['id']
            definitions_map[series['sheet_header']] = series_id
            print(f"✅ Definición para '{series['series_name']}' asegurada.")
        except Exception as e:
            print(f"❌ Error procesando definición para '{series['series_name']}': {e}")
            
    # 2. Leer datos de google_sheets y preparar el lote
    print("\n--- Fase 2: Leyendo datos de google_sheets y preparando lote ---")
    data_to_insert = []
    try:
        sheet_data = pd.DataFrame(worksheet.get_all_records())
        print(f"✅ Se leyeron {len(sheet_data)} filas de google_sheets.")

        date_column_header = sheet_data.columns[0] # El nombre de la primera columna
        
        for index, row in sheet_data.iterrows():
            try:
                timestamp_str = row[date_column_header]
                if not timestamp_str: continue
                timestamp = datetime.strptime(timestamp_str, '%d/%m/%Y').isoformat()
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
                            'timestamp': timestamp,
                            'value': value
                        })
                    except (ValueError, TypeError):
                        print(f"⚠️ Valor omitido para '{header}' en fecha '{timestamp_str}'. No es un número válido: '{row[header]}'")
                        continue
    except Exception as e:
        print(f"❌ Error leyendo o procesando los datos de google_sheets: {e}")
        return

    # 3. Insertar datos en Supabase
    print(f"\n--- Fase 3: Insertando {len(data_to_insert)} puntos de datos en 'time_series_data' ---")
    if data_to_insert:
        try:
            supabase.table('time_series_data').upsert(data_to_insert, on_conflict="series_id, timestamp").execute()
            print("✅ ¡Datos de series de tiempo insertados con éxito!")
        except Exception as e:
            print(f"❌ Error al insertar datos de series de tiempo: {e}")

if __name__ == "__main__":
    ingest_data()
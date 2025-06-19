import os
import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURACIÓN ---
SOURCE_EXCEL_NAME = "Bloomberg Supabase Data.xlsx"
TARGET_SHEET_NAME = "Bloomberg Supabase Data"
DESTINATION_BRIDGE_SHEET_NAME = "Datos para Supabase Google Sheet"
SOURCE_TAB_NAME = "Supabase" # Asegúrate que coincida (distingue mayúsculas)
# ---------------------

def get_google_services():
    print("--- PASO 1: CONECTANDO CON GOOGLE ---")
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=dotenv_path)
        credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        if not os.path.isabs(credentials_path):
            credentials_path = os.path.join(os.path.dirname(__file__), '..', credentials_path)

        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=creds)
        gspread_client = gspread.Client(auth=creds)
        print("✅ ¡ÉXITO! Conexión a Google Drive y Google Sheets establecida.")
        return drive_service, gspread_client, creds
    except Exception as e:
        print(f"❌ ERROR en get_google_services: {e}")
        return None, None, None

def find_file_by_name(service, file_name, mime_type=None):
    query = f"name = '{file_name}' and trashed = false"
    if mime_type:
        query += f" and mimeType = '{mime_type}'"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    return response.get('files', [])

def convert_excel_to_sheet(service, excel_file_id, target_name, creds):
    print(f"Convirtiendo '{SOURCE_EXCEL_NAME}' a formato Google Sheet...")
    try:
        file_metadata = {'name': target_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
        existing_sheets = find_file_by_name(service, target_name, 'application/vnd.google-apps.spreadsheet')
        for sheet in existing_sheets:
            print(f"Borrando versión antigua de la Hoja de Google convertida...")
            service.files().delete(fileId=sheet['id']).execute()
        
        new_sheet = service.files().copy(fileId=excel_file_id, body=file_metadata).execute()
        print(f"✅ ¡ÉXITO! Se creó la Hoja de Google '{target_name}'.")
        
        permission = {'type': 'user', 'role': 'writer', 'emailAddress': creds.service_account_email}
        service.permissions().create(fileId=new_sheet['id'], body=permission).execute()
        print(f"✅ Permisos de edición otorgados.")
        return new_sheet['id']
    except HttpError as error:
        print(f"❌ Error durante la conversión: {error}")
        return None

def main():
    drive_service, gspread_client, creds = get_google_services()
    if not drive_service:
        print("Pipeline detenido debido a un error en la conexión.")
        return False # Devolvemos False para indicar fallo

    print(f"\n--- PASO 2: BUSCANDO ARCHIVO FUENTE '{SOURCE_EXCEL_NAME}' ---")
    excel_files = find_file_by_name(drive_service, SOURCE_EXCEL_NAME)
    if not excel_files:
        print(f"❌ ERROR CRÍTICO: No se encontró el archivo '{SOURCE_EXCEL_NAME}'.")
        return False

    print(f"✅ Se encontró el archivo Excel fuente.")
    excel_file_id = excel_files[0]['id']
    
    new_sheet_id = convert_excel_to_sheet(drive_service, excel_file_id, TARGET_SHEET_NAME, creds)
    if not new_sheet_id:
        print("Pipeline detenido debido a un error en la conversión.")
        return False

    print(f"\n--- PASO 3: LEYENDO DATOS DE LA PESTAÑA '{SOURCE_TAB_NAME}' ---")
    try:
        spreadsheet = gspread_client.open_by_key(new_sheet_id)
        worksheet = spreadsheet.worksheet(SOURCE_TAB_NAME)
        
        all_values = worksheet.get_all_values()
        if len(all_values) < 2:
            raise ValueError("La hoja no tiene suficientes filas para procesar.")
        
        headers = all_values[0]
        data_rows = all_values[1:]
        df = pd.DataFrame(data_rows, columns=headers)
        
        print(f"  -> Columnas originales encontradas: {df.columns.tolist()}")
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.loc[:, df.columns != '']
        print(f"  -> Columnas después de la limpieza: {len(df.columns)} columnas válidas.")
        print(f"✅ ¡ÉXITO! Se procesaron {len(df)} filas de datos.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ ERROR: No se encontró una pestaña con el nombre '{SOURCE_TAB_NAME}'. Revisa la configuración.")
        return False
    except Exception as e:
        print(f"❌ Ocurrió un error al leer o estructurar los datos: {e}")
        return False
        
    print(f"\n--- PASO 4: ESCRIBIENDO DATOS EN LA HOJA PUENTE '{DESTINATION_BRIDGE_SHEET_NAME}' ---")
    try:
        dest_spreadsheet = gspread_client.open(DESTINATION_BRIDGE_SHEET_NAME)
        dest_worksheet = dest_spreadsheet.sheet1
        
        dest_worksheet.clear()
        dest_worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"✅ ¡ÉXITO FINAL! Se transfirieron {len(df)} filas a '{DESTINATION_BRIDGE_SHEET_NAME}'.")
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ ERROR: No se encontró la hoja de destino '{DESTINATION_BRIDGE_SHEET_NAME}'.")
        return False
    except Exception as e:
        print(f"❌ Ocurrió un error al escribir en la hoja de destino: {e}")
        return False

    return True # Devolvemos True al final si todo fue exitoso

if __name__ == '__main__':
    if main():
        print("\nEjecución de excel_to_sheets completada con éxito.")
    else:
        print("\nEjecución de excel_to_sheets falló.")
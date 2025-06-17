# -*- coding: utf-8 -*-
"""
Script final que localiza un archivo Excel, lo convierte a Google Sheet,
lee sus datos y los escribe en una hoja "Puente" estandarizada.
"""
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
SOURCE_TAB_NAME = 'supabase'

# El nombre de la hoja "Puente" que leerá el siguiente script
DESTINATION_SHEET_NAME = "Datos para Supabase Google Sheet"
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
        if not os.path.exists(credentials_path):
            print(f"❌ ERROR: No se encuentra el archivo de credenciales en '{credentials_path}'.")
            return None, None
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service_gspread = gspread.Client(auth=creds)
        print("✅ ¡ÉXITO! Conexión a Google Drive y Google Sheets establecida.")
        return drive_service, sheets_service_gspread
    except Exception as e:
        print(f"❌ ERROR INESPERADO DURANTE LA CONEXIÓN: {e}")
        return None, None

def find_file_by_name(service, file_name, mime_type=None):
    query = f"name = '{file_name}' and trashed = false"
    if mime_type:
        query += f" and mimeType = '{mime_type}'"
    try:
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        return response.get('files', [])
    except HttpError as error:
        print(f"❌ Ocurrió un error al buscar el archivo: {error}")
        return []

def convert_excel_to_sheet(service, excel_file_id, target_name):
    print(f"Convirtiendo '{SOURCE_EXCEL_NAME}' a formato Google Sheet...")
    try:
        file_metadata = {'name': target_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
        new_sheet = service.files().copy(fileId=excel_file_id, body=file_metadata).execute()
        print(f"✅ ¡ÉXITO! Se creó la Hoja de Google '{target_name}' (ID: {new_sheet['id']}).")
        # Es crucial compartir la nueva hoja con la propia cuenta de servicio para que gspread pueda acceder a ella
        permission = {'type': 'user', 'role': 'writer', 'emailAddress': service.credentials.service_account_email}
        service.permissions().create(fileId=new_sheet['id'], body=permission).execute()
        return new_sheet['id']
    except HttpError as error:
        print(f"❌ Ocurrió un error durante la conversión: {error}")
        return None

def main():
    drive_service, gspread_client = get_google_services()
    if not drive_service or not gspread_client:
        return

    print(f"\n--- PASO 2: BUSCANDO ARCHIVOS Y VALIDANDO FORMATO ---")
    google_sheet_files = find_file_by_name(drive_service, TARGET_SHEET_NAME, 'application/vnd.google-apps.spreadsheet')
    sheet_to_open = None
    if google_sheet_files:
        sheet_to_open = google_sheet_files[0]
        print(f"✅ Se encontró una Hoja de Google existente: '{sheet_to_open['name']}'.")
    else:
        print(f"No se encontró una Hoja de Google. Buscando el archivo Excel '{SOURCE_EXCEL_NAME}' para convertir.")
        excel_files = find_file_by_name(drive_service, SOURCE_EXCEL_NAME)
        if not excel_files:
            print(f"❌ ERROR CRÍTICO: No se encontró el archivo '{SOURCE_EXCEL_NAME}'. Sube el archivo a Google Drive.")
            return
        excel_file_id = excel_files[0]['id']
        new_sheet_id = convert_excel_to_sheet(drive_service, excel_file_id, TARGET_SHEET_NAME)
        if not new_sheet_id:
            return
        sheet_to_open = {'id': new_sheet_id, 'name': TARGET_SHEET_NAME}

    print(f"\n--- PASO 3: LEYENDO DATOS DE '{sheet_to_open['name']}' ---")
    try:
        spreadsheet = gspread_client.open_by_key(sheet_to_open['id'])
        worksheet = spreadsheet.worksheet(SOURCE_TAB_NAME)
        df = pd.DataFrame(worksheet.get_all_records())
        print(f"✅ ¡ÉXITO! Se leyeron {len(df)} filas de la pestaña '{SOURCE_TAB_NAME}'.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ ERROR: La hoja '{sheet_to_open['name']}' no tiene una pestaña llamada '{SOURCE_TAB_NAME}'.")
        return
    except Exception as e:
        print(f"❌ Ocurrió un error al leer los datos: {e}")
        return
        
    print(f"\n--- PASO 4: ESCRIBIENDO DATOS EN LA HOJA PUENTE '{DESTINATION_SHEET_NAME}' ---")
    try:
        dest_spreadsheet = gspread_client.open(DESTINATION_SHEET_NAME)
        dest_worksheet = dest_spreadsheet.sheet1
        
        dest_worksheet.clear()
        # Escribir el DataFrame completo en la hoja de destino
        dest_worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"✅ ¡ÉXITO FINAL! Se transfirieron {len(df)} filas a '{DESTINATION_SHEET_NAME}'.")
        print("\nEl Proceso 1 ha terminado. Ya puedes ejecutar el Proceso 2 (ingest_data.py).")
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ ERROR: No se encontró la hoja de destino '{DESTINATION_SHEET_NAME}'.")
        print("   Asegúrate de que exista y esté compartida con tu cuenta de servicio.")
    except Exception as e:
        print(f"❌ Ocurrió un error al escribir en la hoja de destino: {e}")

if __name__ == '__main__':
    main()
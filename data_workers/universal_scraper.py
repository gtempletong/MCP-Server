import os
import requests
import re
import json
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import time
from urllib.parse import urljoin

# Imports para Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# --- FUNCIONES ESPECIALISTAS DE SCRAPING ---
# ==============================================================================

def scrape_cochilco_rueda(base_url: str) -> dict:
    """
    [VERSIÓN DEFINITIVA CON SELENIUM]
    Función especialista para "La Rueda Diaria" de Cochilco.
    Usa Selenium para manejar la carga de JS, encuentra el último informe y extrae los datos.
    """
    print(f"   (Método: Cochilco Rueda con Selenium) Iniciando scraping en {base_url}...")
    data = {}
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--log-level=3")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1920, 1200)

        # --- Paso 1: Encontrar el enlace al último informe usando Selenium ---
        print("     (Cochilco Rueda) Buscando el último informe...")
        driver.get(base_url)
        
        # Espera explícita a que el enlace aparezca (el corazón de la solución)
        wait = WebDriverWait(driver, 20)
        latest_report_link_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.item-normal h3 a'))
        )
        
        report_url = latest_report_link_element.get_attribute('href')
        print(f"     (Cochilco Rueda) Informe encontrado: {report_url}")

        # --- Paso 2: Scrapear la página del informe ---
        # Ahora que tenemos la URL, podemos usar requests para más velocidad, o seguir con selenium.
        # Para simplicidad y robustez, seguiremos con el driver que ya está abierto.
        driver.get(report_url)
        soup_report = BeautifulSoup(driver.page_source, 'html.parser')

        # --- Paso 3: Extraer las tablas de datos (esta lógica no cambia) ---
        all_tables = soup_report.find_all('table')
        
        for table in all_tables:
            if 'PRECIOS DE COMPRA Y VENTA DE CONTADO' in table.text:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 1 and 'Cobre' in cells[0].text:
                        bolsa_name = cells[0].text
                        price = cells[1].text.strip()
                        if 'LME' in bolsa_name:
                            data['precio_cobre_lme'] = price
                            print(f"     -> Precio Cobre LME encontrado: {price}")
                        elif 'COMEX' in bolsa_name:
                            data['precio_cobre_comex'] = price
                            print(f"     -> Precio Cobre COMEX encontrado: {price}")

        for table in all_tables:
            if 'INVENTARIOS EN BODEGAS DE LAS BOLSAS DE METALES' in table.text:
                 for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        bolsa = cells[0].text.strip().upper()
                        inventario = cells[1].text.strip()
                        if 'LME' in bolsa:
                            data['inventario_cobre_lme'] = inventario
                            print(f"     -> Inventario LME encontrado: {inventario}")
                        elif 'COMEX' in bolsa:
                            data['inventario_cobre_comex'] = inventario
                            print(f"     -> Inventario COMEX encontrado: {inventario}")
                        elif 'SHANGAI' in bolsa or 'SHANGHAI' in bolsa:
                            data['inventario_cobre_shfe'] = inventario
                            print(f"     -> Inventario SHFE encontrado: {inventario}")
        
        if not data:
            raise ValueError("No se pudo extraer ningún dato de precio o inventario de la página del informe.")
        
        print("     (Cochilco Rueda) ✅ Extracción de datos completa.")
        return data

    except Exception as e:
        print(f"     (Cochilco Rueda) ❌ Error inesperado: {e}")
        if driver:
            # Guardamos una captura si algo sale mal
            screenshot_path = f"debug_cochilco_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"   📸 Se ha guardado una captura de pantalla para depuración en: {os.path.abspath(screenshot_path)}")
        raise
    finally:
        if driver:
            driver.quit()

def scrape_with_hybrid_api(symbol: str) -> float:
    """
    [MÉTODO DEFINITIVO PARA YAHOO]
    Usa Selenium para obtener el crumb, y luego Requests para llamar a la API.
    """
    print(f"   (Método: Híbrido API) Obteniendo datos para '{symbol}'...")
    driver = None
    try:
        print("     (Híbrido) Paso 1: Iniciando Selenium para obtener el ticket (crumb)...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        crumb_url = f"https://finance.yahoo.com/quote/{symbol}"
        driver.get(crumb_url)
        time.sleep(5) 
        page_source = driver.page_source
        
        crumb_regex = r'"CrumbStore":{"crumb":"(.*?)"}'
        match = re.search(crumb_regex, page_source)
        if not match:
            raise ValueError("No se pudo encontrar el crumb en la página renderizada por Selenium.")
        
        crumb = match.group(1).replace('\\u002F', '/')
        print("     (Híbrido) ✅ Ticket (crumb) obtenido con éxito vía Selenium.")

    finally:
        if driver:
            driver.quit()

    print("     (Híbrido) Paso 2: Pidiendo los datos a la API con el ticket...")
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        session.headers.update(headers)
        
        api_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {'modules': 'summaryDetail,price', 'crumb': crumb}
        
        api_response = session.get(api_url, params=params, timeout=10)
        api_response.raise_for_status()
        data = api_response.json()
        print("     (Híbrido) ✅ Datos JSON recibidos con éxito.")
        
        pe_ratio = data['quoteSummary']['result'][0]['summaryDetail']['trailingPE']['raw']
        return float(pe_ratio)

    except Exception as e:
        print(f"     (Híbrido) ❌ Error al llamar o procesar la API: {e}")
        raise

def scrape_with_selector(url: str, selector: str) -> str:
    """Función especialista para sitios SIMPLES (carga de servidor)."""
    print(f"   (Método: requests) Raspando {url} para el dato con selector '{selector}'...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    element = soup.find(attrs={'data-test': selector})
    if element:
        return element.text.strip()
    raise ValueError(f"No se pudo encontrar el dato con el selector '{selector}' (método requests).")

# ==============================================================================
# --- FUNCIONES DE UTILIDAD Y BASE DE DATOS ---
# ==============================================================================

def clean_and_convert_to_float(value: str) -> float:
    """Limpia un string y lo convierte a un número flotante."""
    if isinstance(value, (int, float)):
        return float(value)
    # Quita comas y cualquier otro carácter no numérico excepto el punto decimal
    cleaned_str = re.sub(r'[^\d.]', '', str(value))
    return float(cleaned_str)

def save_timeseries_data(supabase_client: Client, series_name: str, value: float):
    """Busca el ID de una serie y guarda el nuevo dato en la tabla time_series_data."""
    print(f"   - Guardando en Supabase: '{series_name}' = {value}")
    try:
        metric_response = supabase_client.table('series_definitions').select('id').eq('series_name', series_name).single().execute()
        if not metric_response.data:
            raise Exception(f"La métrica '{series_name}' no fue encontrada en 'series_definitions'.")
        series_id = metric_response.data['id']

        data_to_insert = {
            'series_id': series_id,
            'timestamp': datetime.now().isoformat(),
            'value': value
        }
        supabase_client.table('time_series_data').insert(data_to_insert).execute()
        print("     ✅ Dato guardado con éxito.")
    except Exception as e:
        print(f"     ❌ Error al guardar en Supabase: {e}")
        raise

# ==============================================================================
# --- ORQUESTADOR PRINCIPAL ---
# ==============================================================================

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
    print("\n--- Iniciando el Orquestador de Scrapers Universal ---")
    try:
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
        cochilco_rueda_data = None # Caché para los datos de "La Rueda Diaria"

        for target in targets:
            print(f"\n▶️  Ejecutando tarea: '{target['target_name']}'")
            try:
                function_name = target.get('scraper_function')
                value_float = None

                # --- LÓGICA DE DECISIÓN DE SCRAPER ---
                if function_name == 'scrape_cochilco_rueda':
                    if cochilco_rueda_data is None:
                        cochilco_rueda_data = scrape_cochilco_rueda(target['source_url'])
                    
                    data_key = target.get('data_label_on_page')
                    if data_key in cochilco_rueda_data:
                        scraped_value_str = cochilco_rueda_data[data_key]
                        value_float = clean_and_convert_to_float(scraped_value_str)
                    else:
                        print(f"   ⚠️ La clave '{data_key}' no se encontró en los datos de Cochilco Rueda.")
                        continue

                elif function_name == 'scrape_with_hybrid_api':
                    ticker = target['source_url'].split('/')[-1]
                    value_float = scrape_with_hybrid_api(ticker)
                
                elif function_name == 'scrape_with_selector':
                    css_selector = target.get('data_label_on_page')
                    if not css_selector:
                        print(f"   ⚠️ La tarea '{target['target_name']}' no tiene un selector CSS definido. Omitida.")
                        continue
                    scraped_value_str = scrape_with_selector(target['source_url'], css_selector)
                    value_float = clean_and_convert_to_float(scraped_value_str)
                
                else:
                    print(f"   ⚠️ Función de scraper desconocida o no definida: '{function_name}'. Tarea omitida.")
                    continue

                if value_float is not None:
                    print(f"     ✅ -> Valor final extraído: {value_float}")
                    save_timeseries_data(supabase, target['destination_series_name'], value_float)
                else:
                    print("     ⚠️ No se pudo extraer un valor final.")

            except Exception as e:
                print(f"   ❌ ERROR al procesar la tarea '{target['target_name']}': {e}")
                continue
    
    # --- CÁLCULO DE TOTALES (al final de todas las tareas) ---
    print("\n--- Calculando Series Derivadas (Totales) ---")
    try:
        # Aquí iría la lógica para calcular el total de inventarios si decides hacerlo en Python.
        # Por ahora, lo dejamos pendiente ya que lo resolvimos con un trigger en la base de datos.
        print("✅ Lógica de totales completada (manejada por triggers en la base de datos).")
    except Exception as e:
        print(f"❌ Error al calcular series derivadas: {e}")


    print("\n--- Proceso finalizado ---")

if __name__ == "__main__":
    main()
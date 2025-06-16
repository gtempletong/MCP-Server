import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar las variables de entorno de nuestro archivo .env
load_dotenv()

print("Iniciando prueba de conexión con Supabase...")

try:
    # Usamos las mismas credenciales de tu .env
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    # Verificamos que las credenciales se cargaron
    if not supabase_url or not supabase_key:
        raise ValueError("Credenciales de Supabase no encontradas en el .env. Revisa el archivo.")

    # Creamos el cliente
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Cliente de Supabase creado.")

    # Hacemos una consulta para leer el título y tema de los primeros 3 artículos
    print("🔎 Realizando consulta a la tabla 'news_articles'...")
    # Usamos count='exact' para que nos diga el total de filas
    response = supabase.table('news_articles').select('title, topic', count='exact').limit(3).execute()

    print(f"✅ Consulta exitosa. Se encontraron {response.count} artículos en total en la tabla.")

    # Imprimimos los resultados para verificar
    print("\n--- PRIMEROS 3 ARTÍCULOS ENCONTRADOS ---")
    if response.data:
        for article in response.data:
            print(f"- Título: {article['title']}, Tema: {article['topic']}")
    else:
        print("No se encontraron datos. ¿La tabla 'news_articles' tiene datos?")
    print("--------------------------------------")

except Exception as e:
    print(f"❌ Ocurrió un error: {e}")
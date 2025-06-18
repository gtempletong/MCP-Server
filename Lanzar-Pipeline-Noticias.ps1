# Lanza el pipeline de NOTICIAS

Write-Host "Iniciando el Pipeline de Noticias..." -ForegroundColor Cyan

# Apunta a la carpeta del servicio de noticias
Set-Location -Path "C:\mcp-server\news_ingestion_service"

# Activa el venv que está en la raíz
.\..\.venv\Scripts\Activate.ps1

# Ejecuta el script de Python que está DENTRO de la carpeta de noticias
python ingestor_main.py

Read-Host -Prompt "Proceso finalizado. Presiona Enter."
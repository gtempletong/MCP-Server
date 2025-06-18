# Script de PowerShell para lanzar el pipeline de NOTICIAS

Write-Host "Iniciando el Pipeline de Noticias de MCP-SERVER..." -ForegroundColor Cyan

# 1. Navega a la carpeta del ingestor de noticias
Set-Location -Path "C:\mcp-server\news_ingestion_service"

# 2. Activa el entorno virtual
Write-Host "Activando entorno virtual..."
.\..\.venv\Scripts\Activate.ps1

# 3. Ejecuta el script principal del pipeline de noticias
Write-Host "Ejecutando ingestor_main.py..."
python ingestor_main.py

# 4. Mantiene la ventana abierta al final
Write-Host "Proceso de noticias finalizado." -ForegroundColor Cyan
Read-Host -Prompt "Presiona Enter para cerrar esta ventana."
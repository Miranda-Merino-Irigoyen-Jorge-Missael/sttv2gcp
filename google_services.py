# google_services.py
import google.auth
from googleapiclient.discovery import build
from google.cloud import secretmanager

# Alcances necesarios para Drive y Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def obtener_servicios_google():
    """
    Autentica automáticamente usando la Identidad de la instancia (Cloud Run).
    No requiere archivos token.json ni intervención del navegador.
    """
    # google.auth.default() detecta automáticamente la Service Account en GCP
    creds, project_id = google.auth.default(scopes=SCOPES)
    
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return sheets_service, drive_service

def acceder_secreto(secret_id, version_id="latest"):
    """
    Obtiene valores sensibles (API Keys) de Secret Manager.
    """
    _, project_id = google.auth.default()
    client = secretmanager.SecretManagerServiceClient()
    nombre_secreto = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    respuesta = client.access_secret_version(request={"name": nombre_secreto})
    return respuesta.payload.data.decode("UTF-8")
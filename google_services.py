import os
import google.auth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import secretmanager

# Alcances necesarios para Drive y Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def obtener_servicios_google():
    """
    Autentica usando el token.json de usuario en lugar de la Service Account.
    Esto permite acceder a archivos del Workspace restringidos al dominio.
    """
    creds = None
    
    # 1. Intentamos cargar el token local (para cuando pruebas en tu computadora)
    if os.path.exists('token.json'):
        print("Cargando credenciales de usuario desde token.json...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        # 2. Si no está el archivo físico (estaremos en Cloud Run), 
        # lo leeremos desde una variable de entorno alimentada por Secret Manager.
        # (Implementaremos esto en el siguiente paso).
        token_string = os.getenv("WORKSPACE_TOKEN_JSON")
        if token_string:
            print("Cargando credenciales de usuario desde Secret Manager...")
            # Reconstruimos las credenciales desde el string JSON
            import json
            token_dict = json.loads(token_string)
            creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
        else:
            raise FileNotFoundError("No se encontró token.json ni el secreto en Cloud Run.")

    # Construimos los servicios de Drive y Sheets con tu cuenta real
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
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Definimos los alcances (scopes) necesarios para leer/escribir en Sheets y Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def obtener_servicios_google(client_secret_file='credentials.json'):
    """
    Autentica y devuelve los clientes de Sheets y Drive usando tu cuenta personal.
    Abre el navegador la primera vez para autorizar.
    """
    creds = None
    # El archivo token.json almacena los tokens de acceso y actualización del usuario.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # Si no hay credenciales válidas, pedimos al usuario que inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            # Esto abrirá el navegador para que inicies sesión
            creds = flow.run_local_server(port=0)
            
        # Guardamos las credenciales para la próxima ejecución
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return sheets_service, drive_service

def obtener_filas_pendientes(spreadsheet_id, sheets_service, range_name='SYSTEM AI RFE!A:D'):
    """
    Lee la hoja y filtra las filas con status 'PENDING'.
    """
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    filas_pendientes = []
    if not values:
        return filas_pendientes

    for index, row in enumerate(values):
        if index == 0:
            continue
        
        if len(row) >= 3:
            nombre_cliente = row[0]
            status = row[1]
            link_drive = row[2]
            
            if status.strip().upper() == 'PENDING':
                filas_pendientes.append({
                    'fila_excel': index + 1, 
                    'cliente': nombre_cliente,
                    'status': status,
                    'link': link_drive
                })
                
    return filas_pendientes

def actualizar_status_y_link(sheets_service, spreadsheet_id, fila, nuevo_status, link_resultado=""):
    """
    Actualiza el status (Columna B) y el link de transcripción final (Columna D) de una fila.
    """
    sheet = sheets_service.spreadsheets()
    
    # Actualizar Status (Columna B)
    sheet.values().update(
        spreadsheetId=spreadsheet_id, 
        range=f'SYSTEM AI RFE!B{fila}',
        valueInputOption='USER_ENTERED', 
        body={'values': [[nuevo_status]]}
    ).execute()

    # Actualizar Link (Columna D) si existe
    if link_resultado:
        sheet.values().update(
            spreadsheetId=spreadsheet_id, 
            range=f'SYSTEM AI RFE!D{fila}',
            valueInputOption='USER_ENTERED', 
            body={'values': [[link_resultado]]}
        ).execute()
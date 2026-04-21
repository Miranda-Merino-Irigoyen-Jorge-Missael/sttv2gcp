import os
import re
import io
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

def extraer_id_drive(url):
    """
    Analiza un link de Google Drive y extrae su ID, 
    además de identificar si es una 'carpeta' (folder) o un 'archivo' (file).
    """
    # Buscar formato de carpeta (/folders/ID)
    match_folder = re.search(r'/folders/([a-zA-Z0-9-_]+)', url)
    if match_folder:
        return match_folder.group(1), 'folder'
    
    # Buscar formato de archivo (/file/d/ID)
    match_file = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match_file:
        return match_file.group(1), 'file'
        
    # Buscar formato alternativo de ID (?id=ID)
    match_id = re.search(r'id=([a-zA-Z0-9-_]+)', url)
    if match_id:
        return match_id.group(1), 'file'
        
    return None, None

def validar_dominio_workspace(drive_service, file_id, dominio_firma):
    """
    Verifica que el propietario del archivo pertenezca al dominio del Workspace de la firma.
    """
    try:
        # Pedimos específicamente los campos de dueños y si es un Shared Drive
        # supportsAllDrives=True es crucial por si usan "Unidades Compartidas" en el Workspace
        meta = drive_service.files().get(
            fileId=file_id, 
            fields="owners, driveId",
            supportsAllDrives=True
        ).execute()

        owners = meta.get('owners', [])
        
        # 1. Si el archivo está en "Mi Unidad" de un usuario
        if owners:
            correo_propietario = owners[0].get('emailAddress', '')
            if correo_propietario.endswith(f"@{dominio_firma}"):
                return True
            else:
                print(f"Bloqueado: El archivo pertenece a {correo_propietario}")
                return False
                
        # 2. Si el archivo está en una "Unidad Compartida" (Shared Drive) del Workspace
        elif meta.get('driveId'):
            # Los Shared Drives no tienen 'owners' individuales, pertenecen a la organización.
            return True
            
        return False
        
    except Exception as e:
        print(f"Error al validar los metadatos en Drive: {e}")
        return False

def descargar_archivo_drive(drive_service, file_id, nombre_archivo, carpeta_destino):
    """Descarga un archivo individual desde Google Drive a tu máquina local."""
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)
        
    ruta_completa = os.path.join(carpeta_destino, nombre_archivo)
    # Soporte para Unidades Compartidas en la descarga
    request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.FileIO(ruta_completa, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    print(f"Descargando audio: {nombre_archivo}...")
    while done is False:
        status, done = downloader.next_chunk()
    
    return ruta_completa

def procesar_link_entrada(drive_service, link, carpeta_descarga_local, dominio_firma="supportmendoza.com"):
    """
    Decide qué hacer basado en el link:
    Si es un archivo, lo descarga y devuelve su ruta en una lista.
    Si es una carpeta, lista todo su contenido, lo descarga y devuelve la lista de rutas.
    Incluye validación estricta del dominio de la firma.
    """
    drive_id, tipo = extraer_id_drive(link)
    if not drive_id:
        raise ValueError(f"No se pudo extraer un ID válido del enlace: {link}")

    if not validar_dominio_workspace(drive_service, drive_id, dominio_firma):
        raise PermissionError(f"ACCESO DENEGADO: El audio/carpeta no pertenece al dominio @{dominio_firma}.")

    rutas_descargadas = []

    if tipo == 'file':
        # Obtenemos el nombre real del archivo
        meta = drive_service.files().get(fileId=drive_id, fields="name", supportsAllDrives=True).execute()
        ruta = descargar_archivo_drive(drive_service, drive_id, meta['name'], carpeta_descarga_local)
        rutas_descargadas.append(ruta)

    elif tipo == 'folder':
        # Listamos todos los archivos dentro de la carpeta
        resultados = drive_service.files().list(
            q=f"'{drive_id}' in parents and trashed=false",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        archivos = resultados.get('files', [])
        print(f"Se detectó una carpeta con {len(archivos)} archivos.")
        
        for archivo in archivos:
            ruta = descargar_archivo_drive(drive_service, archivo['id'], archivo['name'], carpeta_descarga_local)
            rutas_descargadas.append(ruta)
            
    return rutas_descargadas, tipo

def crear_carpeta_drive(drive_service, nombre_carpeta, folder_padre_id):
    """Crea una subcarpeta en Google Drive (útil si procesamos múltiples audios)."""
    file_metadata = {
        'name': nombre_carpeta,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [folder_padre_id]
    }
    folder = drive_service.files().create(body=file_metadata, fields='id, webViewLink', supportsAllDrives=True).execute()
    
    # Hacer pública la carpeta (opcional, para que el equipo pueda abrirla sin problemas de permisos)
    try:
        drive_service.permissions().create(
            fileId=folder.get('id'), 
            body={'type': 'anyone', 'role': 'reader'}, 
            supportsAllDrives=True
        ).execute()
    except Exception:
        pass
        
    return folder.get('id'), folder.get('webViewLink')

def subir_archivo_drive(drive_service, ruta_local, folder_destino_id):
    """Sube la transcripción final (.txt) a Google Drive y devuelve el link."""
    nombre_archivo = os.path.basename(ruta_local)
    
    file_metadata = {
        'name': nombre_archivo,
        'parents': [folder_destino_id]
    }
    media = MediaFileUpload(ruta_local, mimetype='text/plain', resumable=True)
    
    print(f"Subiendo transcripción a Drive: {nombre_archivo}...")
    archivo_subido = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    
    # Dar permisos de lectura general al archivo
    try:
        drive_service.permissions().create(
            fileId=archivo_subido.get('id'),
            body={'type': 'anyone', 'role': 'reader'},
            supportsAllDrives=True
        ).execute()
    except Exception:
        pass

    return archivo_subido.get('webViewLink')
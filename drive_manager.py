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

def descargar_archivo_drive(drive_service, file_id, nombre_archivo, carpeta_destino):
    """Descarga un archivo individual desde Google Drive a tu máquina local."""
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)
        
    ruta_completa = os.path.join(carpeta_destino, nombre_archivo)
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(ruta_completa, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    print(f"Descargando audio: {nombre_archivo}...")
    while done is False:
        status, done = downloader.next_chunk()
    
    return ruta_completa

def procesar_link_entrada(drive_service, link, carpeta_descarga_local):
    """
    Decide qué hacer basado en el link:
    Si es un archivo, lo descarga y devuelve su ruta en una lista.
    Si es una carpeta, lista todo su contenido, lo descarga y devuelve la lista de rutas.
    """
    drive_id, tipo = extraer_id_drive(link)
    if not drive_id:
        raise ValueError(f"No se pudo extraer un ID válido del enlace: {link}")

    rutas_descargadas = []

    if tipo == 'file':
        # Obtenemos el nombre real del archivo
        meta = drive_service.files().get(fileId=drive_id, fields="name").execute()
        ruta = descargar_archivo_drive(drive_service, drive_id, meta['name'], carpeta_descarga_local)
        rutas_descargadas.append(ruta)

    elif tipo == 'folder':
        # Listamos todos los archivos dentro de la carpeta
        resultados = drive_service.files().list(
            q=f"'{drive_id}' in parents and trashed=false",
            fields="files(id, name)"
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
    folder = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
    
    # Hacer pública la carpeta (opcional, para que el equipo pueda abrirla sin problemas de permisos)
    try:
        drive_service.permissions().create(fileId=folder.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
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
        fields='id, webViewLink'
    ).execute()
    
    # Dar permisos de lectura general al archivo
    try:
        drive_service.permissions().create(
            fileId=archivo_subido.get('id'),
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
    except Exception:
        pass

    return archivo_subido.get('webViewLink')
# gcs_manager.py
import os
from google.cloud import storage

def subir_archivo_gcs(ruta_local, bucket_name, carpeta_destino="transcripts"):
    """
    Sube un archivo local a un bucket de Google Cloud Storage.
    La autenticación se maneja automáticamente si la variable de entorno 
    GOOGLE_APPLICATION_CREDENTIALS está configurada.
    """
    if not bucket_name:
        raise ValueError("El nombre del bucket no está configurado.")

    nombre_archivo = os.path.basename(ruta_local)
    # Definimos la ruta dentro del bucket (ej. transcripts/archivo.txt)
    ruta_blob = f"{carpeta_destino}/{nombre_archivo}"

    # Inicializa el cliente. Automáticamente buscará GOOGLE_APPLICATION_CREDENTIALS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(ruta_blob)

    print(f"Subiendo transcripción a GCS (Bucket: {bucket_name}): {nombre_archivo}...")
    
    # Subir el archivo
    blob.upload_from_filename(ruta_local)

    # Construir y retornar la URI gs://
    gcs_uri = f"gs://{bucket_name}/{ruta_blob}"
    print(f"   [OK] Archivo disponible en GCS: {gcs_uri}")
    
    return gcs_uri
import os
import logging
import datetime
from google.cloud import storage
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

def obtener_url_firmada_gcs(gcs_uri):
    """
    Genera una URL firmada delegando la firma a la identidad de Cloud Run
    usando el access_token activo, sin necesidad de clave privada.
    """
    try:
        # 1. Obtenemos las credenciales y las refrescamos para tener un token vigente
        credentials, project_id = google.auth.default()
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)  # <-- ESTO es lo que faltaba

        client = storage.Client(credentials=credentials, project=project_id)
        
        # 2. SA autorizada con roles/iam.serviceAccountTokenCreator
        service_account_email = "907757756276-compute@developer.gserviceaccount.com"

        # 3. Procesamos el URI de entrada
        sin_prefijo = gcs_uri.replace("gs://", "")
        partes = sin_prefijo.split("/", 1)
        bucket = client.bucket(partes[0])
        blob = bucket.blob(partes[1])

        logger.info(f"Delegando firma IAM para: {service_account_email}")
        
        # 4. Generamos la URL con el access_token activo para firmar via IAM
        url_firmada = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET",
            service_account_email=service_account_email,
            access_token=credentials.token  # <-- ESTO es lo que habilita la firma sin clave privada
        )
        
        return url_firmada
        
    except Exception as e:
        logger.error(f"Error al generar URL firmada de GCS: {str(e)}")
        raise RuntimeError(f"No se pudo autorizar el streaming: {str(e)}")


def subir_archivo_gcs(ruta_local, bucket_name, carpeta_destino="transcripts"):
    """Sube el resultado final (.txt) al bucket configurado."""
    client = storage.Client()
    nombre_archivo = os.path.basename(ruta_local)
    ruta_blob = f"{carpeta_destino}/{nombre_archivo}"
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(ruta_blob)
    blob.upload_from_filename(ruta_local)
    return f"gs://{bucket_name}/{ruta_blob}"
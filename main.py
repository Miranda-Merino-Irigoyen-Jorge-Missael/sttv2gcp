from fastapi import FastAPI, BackgroundTasks, HTTPException
import os
import shutil
import logging

# Importacion de modulos internos del proyecto
import preprocesar_audio
import assembly_test
import fusion_assembly_gemini
from gcs_manager import subir_archivo_gcs, obtener_url_firmada_gcs

# Configuracion de logging profesional para monitoreo en Google Cloud
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="API de Transcripcion VAWA/RFE - The Mendoza Law Firm")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def tarea_procesamiento_fondo(ruta_entrada: str, cliente_id: str):
    """
    Orquestador del proceso de transcripcion.
    Optimizado para usar URLs firmadas y evitar descargas lentas en la instancia.
    """
    # Directorio temporal en /tmp para los segmentos de salida
    carpeta_trabajo = os.path.join("/tmp", f"temp_{cliente_id}")
    carpeta_segmentos = os.path.join(carpeta_trabajo, "segmentos")
    
    try:
        os.makedirs(carpeta_segmentos, exist_ok=True)
        logger.info(f"Iniciando flujo de procesamiento para el cliente: {cliente_id}")

        # GESTION DE ENTRADA: Streaming vs Archivo Local
        if ruta_entrada.startswith("gs://"):
            # Obtenemos acceso temporal para que FFmpeg lea directamente de la nube
            logger.info(f"Generando acceso de streaming para: {ruta_entrada}")
            ruta_audio_ffmpeg = obtener_url_firmada_gcs(ruta_entrada)
        else:
            ruta_audio_ffmpeg = ruta_entrada

        # 1. Preprocesamiento: Estandarizacion y segmentacion (FFMPEG lee la URL directamente)
        rutas_segmentos = preprocesar_audio.preprocesar_con_ffmpeg(
            ruta_audio_ffmpeg, 
            carpeta_segmentos, 
            duracion_segmento_segundos=3000
        )
        
        # 2. Analisis Acustico: Diarizacion de voces con AssemblyAI
        assembly_test.generar_mapas_desde_segmentos(rutas_segmentos, carpeta_segmentos)
        
        # 3. Refinamiento por IA: Reconstruccion de dialogo con Gemini
        archivo_txt_final = os.path.join(carpeta_trabajo, f"Transcripcion_{cliente_id}.txt")
        # Capturamos la nueva ruta del archivo JSON que devuelve la función
        archivo_json_final = fusion_assembly_gemini.ensamblar_transcripcion_final(carpeta_segmentos, archivo_txt_final)
        
        # 4. Persistencia: Almacenamiento del resultado final en GCS
        carpeta_gcs = f"transcripciones_{cliente_id}"
        # Subimos el archivo JSON en lugar del TXT
        uri_final = subir_archivo_gcs(archivo_json_final, GCS_BUCKET_NAME, carpeta_gcs)
        
        logger.info(f"Proceso finalizado. Archivo disponible en: {uri_final}")
        
    except Exception as e:
        logger.error(f"Error critico en el procesamiento del caso {cliente_id}: {str(e)}")
    finally:
        # Limpieza de archivos temporales (segmentos y logs)
        if os.path.exists(carpeta_trabajo):
            shutil.rmtree(carpeta_trabajo, ignore_errors=True)
            logger.info(f"Limpieza de recursos completada para el cliente: {cliente_id}")

@app.post("/iniciar-transcripcion")
async def iniciar_transcripcion(payload: dict, background_tasks: BackgroundTasks):
    """
    Endpoint para recibir solicitudes de transcripcion desde la plataforma legal.
    """
    ruta_audio = payload.get("ruta_local_o_gcs")
    cliente_id = payload.get("cliente_id")
    
    if not ruta_audio or not cliente_id:
        logger.warning("Solicitud incompleta: Faltan parametros obligatorios.")
        raise HTTPException(
            status_code=400, 
            detail="Faltan datos requeridos: 'ruta_local_o_gcs' o 'cliente_id'"
        )

    # Iniciar la tarea pesada en segundo plano
    background_tasks.add_task(tarea_procesamiento_fondo, ruta_audio, cliente_id)
    
    return {
        "status": "procesamiento_iniciado", 
        "cliente": cliente_id,
        "mensaje": "La transcripcion se esta procesando mediante streaming de alta velocidad."
    }
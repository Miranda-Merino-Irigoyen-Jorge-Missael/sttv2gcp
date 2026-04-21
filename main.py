from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
import os
import shutil
import logging

# Importación de módulos internos del proyecto
import preprocesar_audio
import assembly_test
import fusion_assembly_gemini
from gcs_manager import subir_archivo_gcs, obtener_url_firmada_gcs

# Configuración de logging profesional para monitoreo en Google Cloud
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="API de Transcripción VAWA/RFE - The Mendoza Law Firm")

# 1. Configuración de CORS para permitir la conexión desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, se debe restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialización del cliente de Firestore
db = firestore.Client()
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def tarea_procesamiento_fondo(ruta_entrada: str, cliente_id: str):
    """
    Orquestador del proceso de transcripción con persistencia de estado en Firestore.
    """
    carpeta_trabajo = os.path.join("/tmp", f"temp_{cliente_id}")
    carpeta_segmentos = os.path.join(carpeta_trabajo, "segmentos")
    
    # Referencia al documento de seguimiento en Firestore
    doc_ref = db.collection('trabajos_transcripcion').document(cliente_id)
    
    try:
        os.makedirs(carpeta_segmentos, exist_ok=True)
        logger.info(f"Iniciando flujo de procesamiento para el cliente: {cliente_id}")

        # GESTIÓN DE ENTRADA: Streaming vs Archivo Local
        if ruta_entrada.startswith("gs://"):
            logger.info(f"Generando acceso de streaming para: {ruta_entrada}")
            ruta_audio_ffmpeg = obtener_url_firmada_gcs(ruta_entrada)
        else:
            ruta_audio_ffmpeg = ruta_entrada

        # 1. Preprocesamiento: Estandarización y segmentación
        rutas_segmentos = preprocesar_audio.preprocesar_con_ffmpeg(
            ruta_audio_ffmpeg, 
            carpeta_segmentos, 
            duracion_segmento_segundos=3000
        )
        
        # 2. Análisis Acústico: Diarización de voces con AssemblyAI
        assembly_test.generar_mapas_desde_segmentos(rutas_segmentos, carpeta_segmentos)
        
        # 3. Refinamiento por IA: Reconstrucción de diálogo con Gemini
        archivo_txt_final = os.path.join(carpeta_trabajo, f"Transcripcion_{cliente_id}.txt")
        archivo_json_final = fusion_assembly_gemini.ensamblar_transcripcion_final(carpeta_segmentos, archivo_txt_final)
        
        # 4. Persistencia: Almacenamiento del resultado final en GCS
        carpeta_gcs = f"transcripciones_{cliente_id}"
        uri_final = subir_archivo_gcs(archivo_json_final, GCS_BUCKET_NAME, carpeta_gcs)
        
        # Actualización de éxito en Firestore para el frontend
        doc_ref.update({
            'status': 'completado',
            'resultado_url': uri_final,
            'completado_en': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Proceso finalizado. Archivo disponible en: {uri_final}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error crítico en el procesamiento del caso {cliente_id}: {error_msg}")
        
        # Notificación de error en Firestore para evitar esperas infinitas en el UI
        doc_ref.update({
            'status': 'error',
            'error_mensaje': error_msg,
            'completado_en': firestore.SERVER_TIMESTAMP
        })
        
    finally:
        # Limpieza de recursos temporales
        if os.path.exists(carpeta_trabajo):
            shutil.rmtree(carpeta_trabajo, ignore_errors=True)
            logger.info(f"Limpieza de recursos completada para el cliente: {cliente_id}")

@app.post("/iniciar-transcripcion")
async def iniciar_transcripcion(payload: dict, background_tasks: BackgroundTasks):
    """
    Endpoint principal que registra el inicio del trabajo en la base de datos.
    """
    ruta_audio = payload.get("ruta_local_o_gcs")
    cliente_id = payload.get("cliente_id")
    
    if not ruta_audio or not cliente_id:
        logger.warning("Solicitud incompleta: Faltan parámetros obligatorios.")
        raise HTTPException(
            status_code=400, 
            detail="Faltan datos requeridos: 'ruta_local_o_gcs' o 'cliente_id'"
        )

    # Crear el registro inicial en Firestore antes de lanzar la tarea asíncrona
    doc_ref = db.collection('trabajos_transcripcion').document(cliente_id)
    doc_ref.set({
        'status': 'procesando',
        'cliente_id': cliente_id,
        'creado_en': firestore.SERVER_TIMESTAMP,
        'resultado_url': None,
        'error_mensaje': None
    })

    # Iniciar la tarea pesada en segundo plano
    background_tasks.add_task(tarea_procesamiento_fondo, ruta_audio, cliente_id)
    
    return {
        "status": "procesamiento_iniciado", 
        "cliente": cliente_id,
        "mensaje": "La transcripción se está procesando. El frontend puede monitorear Firestore para actualizaciones."
    }
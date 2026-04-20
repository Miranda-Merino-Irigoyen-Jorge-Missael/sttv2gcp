# SCRIPT PARA OBTENER MAPA DE VOCES CON ASSEMBLYAI
import assemblyai as aai
import json
import os
import logging
from dotenv import load_dotenv

# Configuracion de logging y variables de entorno
load_dotenv()
logger = logging.getLogger(__name__)
ASSEMBLY_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_KEY

def generar_mapas_desde_segmentos(rutas_segmentos, carpeta_segmentos):
    """
    Procesa individualmente cada segmento de audio generado para obtener la diarizacion
    de hablantes. Crea un archivo JSON por cada segmento con las etiquetas de voz.
    """
    logger.info("Iniciando analisis acustico con AssemblyAI.")
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="es",
        speech_models=["universal-3-pro", "universal-2"] 
    )
    
    transcriber = aai.Transcriber()

    for ruta_audio in rutas_segmentos:
        nombre_archivo = os.path.basename(ruta_audio)
        logger.info(f"Enviando segmento a AssemblyAI: {nombre_archivo}")
        
        try:
            # Transcripcion y diarizacion del segmento
            transcript = transcriber.transcribe(ruta_audio, config)

            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Error en AssemblyAI para {nombre_archivo}: {transcript.error}")
                continue
                
            # Estructuracion de los datos de hablantes para este fragmento
            datos_segmento = {"utterances": []}
            for u in transcript.utterances:
                datos_segmento["utterances"].append({
                    "speaker": u.speaker,
                    "start": u.start, # Tiempo relativo al inicio del segmento flac
                    "text": u.text
                })
            
            # Generacion del archivo JSON correspondiente al segmento
            nombre_json = nombre_archivo.replace(".flac", ".json")
            ruta_json = os.path.join(carpeta_segmentos, nombre_json)
            
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos_segmento, f, ensure_ascii=False, indent=4)
                
            logger.info(f"Mapa acustico guardado exitosamente: {nombre_json}")
            
        except Exception as e:
            logger.error(f"Fallo inesperado al procesar el segmento {nombre_archivo}: {str(e)}")

    return True
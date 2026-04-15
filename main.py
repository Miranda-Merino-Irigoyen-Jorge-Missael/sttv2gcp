from fastapi import FastAPI, BackgroundTasks, HTTPException
import os
import shutil

# Importación de modulos
import preprocesar_audio
import assembly_test
import fusion_assembly_gemini
from gcs_manager import subir_archivo_gcs

app = FastAPI(title="API de Transcripción VAWA/RFE")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def tarea_procesamiento_fondo(ruta_audio_local: str, cliente_id: str):
    """Proceso de transcripción completo que se ejecuta sin bloquear el sistema."""
    carpeta_trabajo = f"temp_{cliente_id}"
    os.makedirs(carpeta_trabajo, exist_ok=True)
    
    try:
        # 1. Preprocesar
        carpeta_segmentos = os.path.join(carpeta_trabajo, "segmentos")
        rutas_masters, limites_masters, limites_segmentos = preprocesar_audio.procesar_flujo_completo(ruta_audio_local, carpeta_segmentos, 50 * 60 * 1000)
        
        # 2. AssemblyAI
        assembly_test.generar_mapas_segmentados(rutas_masters, limites_masters, limites_segmentos, carpeta_segmentos)
        
        # 3. Gemini
        archivo_txt_final = os.path.join(carpeta_trabajo, f"Transcripcion_{cliente_id}.txt")
        fusion_assembly_gemini.ensamblar_transcripcion_final(carpeta_segmentos, archivo_txt_final, limites_segmentos)
        
        # 4. Subir a GCS (La plataforma de tu compañero leerá este archivo desde el bucket)
        carpeta_gcs = f"transcripciones_{cliente_id}"
        uri_final = subir_archivo_gcs(archivo_txt_final, GCS_BUCKET_NAME, carpeta_gcs)
        
        print(f"Proceso finalizado con éxito. Archivo disponible en: {uri_final}")
        
    except Exception as e:
        print(f"Error crítico procesando el caso {cliente_id}: {e}")
    finally:
        # Limpieza de archivos temporales ignorando bloqueos de Windows
        if os.path.exists(carpeta_trabajo):
            import shutil # asegúrate de que shutil esté importado arriba
            shutil.rmtree(carpeta_trabajo, ignore_errors=True)

@app.post("/iniciar-transcripcion")
async def iniciar_transcripcion(payload: dict, background_tasks: BackgroundTasks):
    """
    Endpoint principal. La plataforma de la empresa hará un POST aquí.
    """
    ruta_audio = payload.get("ruta_local_o_gcs")
    cliente_id = payload.get("cliente_id")
    
    if not ruta_audio or not cliente_id:
        raise HTTPException(status_code=400, detail="Faltan datos requeridos: 'ruta_local_o_gcs' o 'cliente_id'")

    # Enviar el procesamiento pesado a segundo plano
    background_tasks.add_task(tarea_procesamiento_fondo, ruta_audio, cliente_id)
    
    return {
        "status": "Procesamiento iniciado", 
        "cliente": cliente_id,
        "mensaje": "La transcripción se está generando y se enviará a GCS."
    }
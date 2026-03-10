#SCRIPT PARA 

import assemblyai as aai
import json
import os
from dotenv import load_dotenv

load_dotenv()
ASSEMBLY_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_KEY

def generar_mapas_segmentados(ruta_master, carpeta_segmentos, ms_por_segmento=50 * 60 * 1000):
    print(f"1. Enviando MASTER a AssemblyAI: {ruta_master}")
    print("   (Esto tomará unos minutos debido a la duración del audio...)")
    
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="es",
        speech_models=['universal-3-pro'] # El modelo más avanzado para español
    )
    
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(ruta_master, config)

    if transcript.status == aai.TranscriptStatus.error:
        print(f"[ERROR] AssemblyAI: {transcript.error}")
        return False

    print("2. Análisis acústico completo. Generando JSONs individuales...")

    # Buscamos los segmentos .flac para saber cuántos JSON crear
    segmentos = sorted([f for f in os.listdir(carpeta_segmentos) if f.startswith("segmento_") and f.endswith(".flac")])

    for i, nombre_flac in enumerate(segmentos):
        inicio_ventana = i * ms_por_segmento
        fin_ventana = (i + 1) * ms_por_segmento
        
        datos_segmento = {"utterances": []}
        
        # Filtramos las frases del MASTER que caen en este segmento
        for u in transcript.utterances:
            if inicio_ventana <= u.start < fin_ventana:
                datos_segmento["utterances"].append({
                    "speaker": u.speaker,
                    "start": u.start - inicio_ventana, # Tiempo relativo al inicio del fragmento
                    "text": u.text
                })
        
        # Guardamos el JSON con el mismo nombre que el segmento
        nombre_json = nombre_flac.replace(".flac", ".json")
        ruta_json = os.path.join(carpeta_segmentos, nombre_json)
        
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(datos_segmento, f, ensure_ascii=False, indent=4)
            
        print(f"   [OK] Creado: {nombre_json} ({len(datos_segmento['utterances'])} frases)")
        
    return True
#SCRIPT PARA OBTENER MAPA DE VOCES CON ASSEMBLYAI

import assemblyai as aai
import json
import os
from dotenv import load_dotenv

load_dotenv()
ASSEMBLY_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_KEY

def generar_mapas_segmentados(rutas_masters, limites_reales_masters, limites_reales_segmentos, carpeta_segmentos):
    print("\n--- INICIANDO PROCESO DE ASSEMBLYAI ---")
    
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="es",
        speech_models=['universal-3-pro'] # El modelo más avanzado para español
    )
    
    transcriber = aai.Transcriber()
    
    # 1. La "Memoria" global donde guardaremos todas las frases con su tiempo matemático real
    todas_las_frases_globales = []
    
    # 2. Procesar cada Macro-Master uno por uno
    for i, ruta_master in enumerate(rutas_masters):
        inicio_global_master = limites_reales_masters[i][0]
        print(f"-> Mandando a AssemblyAI: {os.path.basename(ruta_master)} (Esperando resultados...)")
        
        transcript = transcriber.transcribe(ruta_master, config)

        if transcript.status == aai.TranscriptStatus.error:
            print(f"[ERROR] AssemblyAI falló en {ruta_master}: {transcript.error}")
            return False
            
        # 3. Sumar el tiempo de offset (inicio_global_master) a cada frase y guardarla en la memoria
        for u in transcript.utterances:
            tiempo_real_global = u.start + inicio_global_master
            todas_las_frases_globales.append({
                "speaker": u.speaker,
                "start_global": tiempo_real_global,
                "text": u.text
            })
            
    print(f"-> ¡Análisis acústico completo! Se guardaron {len(todas_las_frases_globales)} frases totales en la memoria.")
    print("-> Distribuyendo frases a los segmentos de 50 minutos...")

    # 4. Repartir la memoria global en los JSON correspondientes a cada segmento
    for segmento_info in limites_reales_segmentos:
        nombre_flac = segmento_info['archivo']
        inicio_seg = segmento_info['inicio_ms']
        fin_seg = segmento_info['fin_ms']
        
        datos_segmento = {"utterances": []}
        
        # Filtramos las frases de la memoria que caen en este bloque de 50 min
        for frase in todas_las_frases_globales:
            if inicio_seg <= frase["start_global"] < fin_seg:
                datos_segmento["utterances"].append({
                    "speaker": frase["speaker"],
                    "start": frase["start_global"] - inicio_seg, # Tiempo relativo al inicio de ESTE segmento
                    "text": frase["text"]
                })
        
        # Guardamos el JSON con el mismo nombre que el segmento .flac
        nombre_json = nombre_flac.replace(".flac", ".json")
        ruta_json = os.path.join(carpeta_segmentos, nombre_json)
        
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(datos_segmento, f, ensure_ascii=False, indent=4)
            
        print(f"   [OK] Creado: {nombre_json} ({len(datos_segmento['utterances'])} frases mapeadas)")
        
    return True
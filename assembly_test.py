import assemblyai as aai
import json
import os
from dotenv import load_dotenv

# 1. Cargamos la llave de forma segura
load_dotenv()
ASSEMBLY_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLY_KEY:
    raise ValueError("¡Error! Falta ASSEMBLYAI_API_KEY en tu archivo .env")

aai.settings.api_key = ASSEMBLY_KEY

def crear_json_de_tiempos(ruta_audio, archivo_salida="resultado_assembly.json"):
    print(f"1. Conectando con AssemblyAI y subiendo: {ruta_audio}")
    print("   (Esto puede tomar un par de minutos dependiendo de tu internet y el tamaño del audio...)")
    
    # Configuramos el modelo usando la palabra exacta que acepta la librería local
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="es",
        speech_models=['universal-3-pro']
    )
    
    transcriber = aai.Transcriber()
    
    try:
        # Aquí ocurre la magia de la transcripción acústica
        transcript = transcriber.transcribe(ruta_audio, config)
    except Exception as e:
        print(f"[ERROR] Hubo un problema al comunicarse con AssemblyAI: {e}")
        return

    if transcript.status == aai.TranscriptStatus.error:
        print(f"[ERROR] AssemblyAI falló: {transcript.error}")
        return

    print("2. ¡Transcripción acústica terminada! Estructurando los tiempos...")
    
    # Preparamos la estructura del JSON que Gemini va a leer después
    datos_json = {"utterances": []}
    
    # Extraemos solo lo que nos importa: quién habla, cuándo empieza y qué dijo
    for utterance in transcript.utterances:
        datos_json["utterances"].append({
            "speaker": utterance.speaker, # Ej. "A" o "B"
            "start": utterance.start,     # Milisegundos exactos
            "text": utterance.text        # El texto crudo
        })
        
    # Guardamos todo en el archivo local
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)
        
    print(f"\n[{archivo_salida}] generado con éxito.")
    print("¡Tu 'Mapa de Tiempos' ya está listo para pasárselo a Gemini!")

if __name__ == "__main__":
    ARCHIVO_AUDIO = "RAMONA PADILLA ALTAMIRANO 2 (normalizado).flac"
    ARCHIVO_JSON = "resultado_assembly.json"
    
    if os.path.exists(ARCHIVO_AUDIO):
        crear_json_de_tiempos(ARCHIVO_AUDIO, ARCHIVO_JSON)
    else:
        print(f"No se encontró el archivo de audio: {ARCHIVO_AUDIO}")
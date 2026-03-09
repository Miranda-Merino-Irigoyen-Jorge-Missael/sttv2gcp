import json
import time
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def preparar_guia_acustica(ruta_json):
    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)
    guia = "--- GUÍA ACÚSTICA DE HABLANTES ---\n"
    for u in datos.get("utterances", []):
        guia += f"[Tiempo: {u.get('start')} ms | Voz: {u.get('speaker')}] -> {u.get('text')}\n"
    return guia

def transcribir_segmento(ruta_audio, ruta_json, num_segmento):
    guia_acustica = preparar_guia_acustica(ruta_json)
    
    print(f"\n[PROCESANDO] Subiendo segmento {num_segmento}: {os.path.basename(ruta_audio)}...")
    audio_subido = client.files.upload(file=ruta_audio)
    
    while audio_subido.state.name == 'PROCESSING':
        time.sleep(4)
        audio_subido = client.files.get(name=audio_subido.name)

    prompt_maestro = f"""
    Eres un perito legal experto en transcripciones de casos de inmigración (VAWA/Visa T).
    
    GUÍA ACÚSTICA (Usa esto para identificar quién habla):
    {guia_acustica}

    INSTRUCCIONES:
    1. ROLES: Identifica quién es el 'Abogado' (quien dirige/pregunta) y quién el 'Cliente' (quien da testimonio). Mantén esta lógica en todo el fragmento.
    2. FIDELIDAD: Usa el audio para corregir nombres propios, lugares y fechas que la guía acústica pudo escribir mal.
    3. FORMATO: Devuelve EXCLUSIVAMENTE un arreglo JSON con este formato:
    [
      {{"tiempo_ms": 1000, "hablante": "Abogado", "texto": "Texto corregido..."}},
      {{"tiempo_ms": 5000, "hablante": "Cliente", "texto": "Texto corregido..."}}
    ]
    """

    try:
        respuesta = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=[audio_subido, prompt_maestro],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(respuesta.text)
    finally:
        client.files.delete(name=audio_subido.name)

def ensamblar_transcripcion_final(carpeta, archivo_final):
    segmentos_audio = sorted([f for f in os.listdir(carpeta) if f.startswith("segmento_") and f.endswith(".flac")])
    transcripcion_completa = ""
    offset_ms = 0
    DURACION_SEGMENTO_MS = 50 * 60 * 1000

    for i, nombre_audio in enumerate(segmentos_audio):
        ruta_audio = os.path.join(carpeta, nombre_audio)
        ruta_json = ruta_audio.replace(".flac", ".json")
        
        if os.path.exists(ruta_json):
            bloques = transcribir_segmento(ruta_audio, ruta_json, i+1)
            
            for b in bloques:
                # Ajustamos el tiempo para que el documento final sea continuo (0 a 4 horas)
                ms_reales = int(b['tiempo_ms']) + (i * DURACION_SEGMENTO_MS)
                minutos = ms_reales // 60000
                segundos = (ms_reales % 60000) // 1000
                transcripcion_completa += f"{b['hablante']} [{minutos:02d}:{segundos:02d}]: {b['texto']}\n\n"
        
        print(f"   [OK] Segmento {i+1} integrado.")

    with open(archivo_final, "w", encoding="utf-8") as f:
        f.write(transcripcion_completa)
    print(f"\n[ÉXITO TOTAL] Transcripción completa guardada en: {archivo_final}")

if __name__ == "__main__":
    CARPETA_TRABAJO = "audio_segmentado_DRAFT 2 ERNESTO GÓMEZ LEAL" # Asegúrate que sea tu carpeta real
    NOMBRE_SALIDA = "TRANSCRIPCION_FINAL_DRAFT 2 ERNESTO GÓMEZ LEAL.txt"
    
    ensamblar_transcripcion_final(CARPETA_TRABAJO, NOMBRE_SALIDA)
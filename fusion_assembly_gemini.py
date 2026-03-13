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
    
    print(f"\n[PROCESANDO] Subiendo segmento {num_segmento}: {os.path.basename(ruta_audio)} a Gemini...")
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
        # Desactivamos los filtros de seguridad explícitamente para análisis legal
        configuracion_segura = types.GenerateContentConfig(
            response_mime_type="application/json",
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        )

        respuesta = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=[audio_subido, prompt_maestro],
            config=configuracion_segura
        )
        
        # Validación extra: Si por algún error de conexión el texto viene vacío, lanzamos una excepción controlada
        if not respuesta.text:
            raise ValueError("Gemini devolvió una respuesta vacía (posible bloqueo interno o caída de red).")
            
        return json.loads(respuesta.text)
        
    except Exception as e:
        print(f"[ERROR] Problema al procesar el segmento {num_segmento} con Gemini: {e}")
        return []
        
    finally:
        # Siempre intentamos borrar el archivo subido para no saturar el almacenamiento de Gemini
        try:
            client.files.delete(name=audio_subido.name)
        except Exception:
            pass

def ensamblar_transcripcion_final(carpeta, archivo_final, limites_segmentos):
    segmentos_audio = sorted([f for f in os.listdir(carpeta) if f.startswith("segmento_") and f.endswith(".flac")])
    transcripcion_completa = ""

    for i, nombre_audio in enumerate(segmentos_audio):
        ruta_audio = os.path.join(carpeta, nombre_audio)
        ruta_json = ruta_audio.replace(".flac", ".json")
        
        # Buscar el tiempo de inicio real exacto para este segmento en particular
        inicio_ms_real = 0
        for limite in limites_segmentos:
            if limite['archivo'] == nombre_audio:
                inicio_ms_real = limite['inicio_ms']
                break
        
        if os.path.exists(ruta_json):
            bloques = transcribir_segmento(ruta_audio, ruta_json, i+1)
            
            for b in bloques:
                # Ajustamos el tiempo usando el inicio matemático real y exacto
                ms_reales = int(b.get('tiempo_ms', 0)) + inicio_ms_real
                minutos = ms_reales // 60000
                segundos = (ms_reales % 60000) // 1000
                hablante = b.get('hablante', 'Desconocido')
                texto = b.get('texto', '')
                transcripcion_completa += f"{hablante} [{minutos:02d}:{segundos:02d}]: {texto}\n\n"
        
        print(f"   [OK] Segmento {i+1} integrado.")

    with open(archivo_final, "w", encoding="utf-8") as f:
        f.write(transcripcion_completa)
        
    print(f"\n[ÉXITO TOTAL] Transcripción completa guardada en: {archivo_final}")
    return archivo_final
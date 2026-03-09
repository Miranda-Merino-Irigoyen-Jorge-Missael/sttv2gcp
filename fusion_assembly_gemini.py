import json
import time
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Falta GEMINI_API_KEY en tu archivo .env")

client = genai.Client(api_key=API_KEY)

def preparar_guia_acustica(ruta_json):
    """Filtra el JSON crudo para darle a Gemini una guía clara de quién es quién acústicamente."""
    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)
        
    guia = "--- GUÍA ACÚSTICA DE HABLANTES ---\n"
    for u in datos.get("utterances", []):
        start = u.get("start", 0)
        speaker = u.get("speaker", "X") 
        text = u.get("text", "")
        guia += f"[Tiempo: {start} ms | Voz Detectada: {speaker}] -> {text}\n"
    return guia

def formatear_a_texto(json_de_gemini, archivo_salida):
    try:
        texto_limpio = json_de_gemini.strip("`").replace("json\n", "")
        datos = json.loads(texto_limpio)
        
        texto_final = ""
        for bloque in datos:
            ms = int(bloque.get("tiempo_ms", 0))
            minutos = ms // 60000
            segundos = (ms % 60000) // 1000
            hablante = bloque.get("hablante", "Desconocido")
            texto = bloque.get("texto", "")
            
            texto_final += f"{hablante} [{minutos:02d}:{segundos:02d}]: {texto}\n\n"
            
        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(texto_final)
        print(f"\n[ÉXITO] Documento formateado guardado en: {archivo_salida}")
        
    except Exception as e:
        print(f"[ERROR] Falló el formateo de Python. La IA no devolvió un JSON limpio: {e}")
        print("Respuesta cruda de Gemini fue:\n", json_de_gemini)

def transcribir_poder_total(ruta_audio, ruta_json):
    guia_acustica = preparar_guia_acustica(ruta_json)
    
    print(f"1. Subiendo '{ruta_audio}' a Gemini...")
    audio_subido = client.files.upload(file=ruta_audio)
    
    print("2. Esperando a que el archivo esté listo...")
    while audio_subido.state.name == 'PROCESSING':
        print(".", end="", flush=True)
        time.sleep(5)
        audio_subido = client.files.get(name=audio_subido.name)

    print("\n3. Iniciando Fusión (JSON Estricto + Anclaje Acústico)...")
    
    # PROMPT OPTIMIZADO PARA EVITAR INVERSIÓN DE HABLANTES
    prompt_maestro = f"""
    Eres un perito legal experto en transcripciones de casos de inmigración (procesos tipo VAWA o Visa T).
    A continuación te proporciono una 'Guía Acústica' generada por un sistema especializado que ya diferenció las firmas de voz (A, B, etc.).

    {guia_acustica}

    TU MISIÓN:
    1. REGLA DE ROLES: Escucha atentamente la dinámica. La voz que hace las preguntas formales y dirige la entrevista es SIEMPRE el 'Intervencionista'. La voz que responde contando su testimonio es SIEMPRE el 'Cliente'.
    2. CONFÍA CIEGAMENTE EN LA GUÍA ACÚSTICA. Una vez que determines si la Voz A es el Intervencionista o el Cliente, mantén esa lógica estricta. Si la guía marca que cambió a la Voz B, tú debes cambiar de personaje. No intentes adivinar por contexto en contra de la guía.
    3. Usa el audio SOLO para redactar con precisión, corregir ortografía y darle sentido legal a la narrativa cruda del JSON. Transcribe fielmente fechas, lugares y parentescos.
    4. RESPETA el valor 'Tiempo' (milisegundos) de la guía.
    5. Tu respuesta debe ser EXCLUSIVAMENTE un arreglo JSON válido:
    [
      {{"tiempo_ms": 135000, "hablante": "Intervencionista", "texto": "Hola Ramona, buen día."}},
      {{"tiempo_ms": 138000, "hablante": "Cliente", "texto": "Buenos días."}}
    ]
    NO incluyas explicaciones ni texto fuera del JSON.
    """

    try:
        respuesta = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[audio_subido, prompt_maestro],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        print("¡Respuesta JSON generada por la IA! Procesando con Python...")
        formatear_a_texto(respuesta.text, "Transcripcion_Nivel_Dios_Corregida.txt")
        
    except Exception as e:
        print(f"[ERROR] Falló la API: {e}")
        
    finally:
        print("4. Limpiando la nube...")
        client.files.delete(name=audio_subido.name)

if __name__ == "__main__":
    ARCHIVO_AUDIO = "RAMONA PADILLA ALTAMIRANO 2 (normalizado).flac"
    ARCHIVO_JSON = "resultado_assembly.json" 
    
    if os.path.exists(ARCHIVO_AUDIO) and os.path.exists(ARCHIVO_JSON):
        transcribir_poder_total(ARCHIVO_AUDIO, ARCHIVO_JSON)
    else:
        print("Revisa que los archivos estén en la misma carpeta.")
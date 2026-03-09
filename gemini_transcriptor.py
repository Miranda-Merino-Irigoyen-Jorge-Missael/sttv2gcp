import os
import time
from pydub import AudioSegment
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Cargar la llave de forma segura desde tu archivo .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("¡Error! No se encontró la GEMINI_API_KEY. Asegúrate de tener tu archivo .env en esta carpeta.")

genai.configure(api_key=API_KEY)

def transcribir_por_bloques(ruta_audio, duracion_minutos=45):
    print(f"1. Cargando el audio original: {ruta_audio} (Esto tomará unos segundos)...")
    
    try:
        audio_completo = AudioSegment.from_file(ruta_audio)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el audio con Pydub: {e}")
        return
        
    # Calculamos en cuántos pedazos se va a partir
    chunk_length_ms = duracion_minutos * 60 * 1000
    total_chunks = len(audio_completo) // chunk_length_ms + (1 if len(audio_completo) % chunk_length_ms > 0 else 0)
    
    print(f"El audio de {len(audio_completo)/1000/60:.2f} minutos se dividirá en {total_chunks} bloque(s) de máximo {duracion_minutos} minutos.")
    
    # Cargamos el modelo
    modelo = genai.GenerativeModel('models/gemini-3-flash-preview')
    transcripcion_completa = ""

    # El súper prompt estructurado y contextualizado para tus casos
    prompt_base = """
    Eres un perito transcriptor experto. Tu tarea es generar una transcripción completa, exacta y literal del siguiente segmento de audio.
    El contexto es una declaración legal de inmigración (procesos tipo VAWA o Visa T), por lo que la precisión en fechas, parentescos y narrativa es crítica.
    
    REGLAS ESTRICTAS:
    1. Diarización Intuitiva: Separa a los hablantes lógicamente (ej. Entrevistador, Declarante).
    2. Marcas de tiempo: Pon la marca de tiempo [MM:SS] al inicio de cada intervención. 
       *Nota: Este es un fragmento de un audio más largo, haz tu mejor esfuerzo con los tiempos relativos al fragmento.*
    3. Puntuación: Aplica puntuación ortográfica perfecta (comas, puntos, signos de interrogación).
    4. Literalidad: No resumas, omitas ni alteres las palabras originales. Transcribe todo.
    5. Necesito que por favor respetes las marcas de tiempo al cien por ciento.
    
    FORMATO DE SALIDA ESPERADO:
    Entrevistador [00:00]: [Texto de su pregunta o comentario]
    Declarante [00:15]: [Texto de la respuesta completa]
    """

    for i in range(total_chunks):
        start_ms = i * chunk_length_ms
        end_ms = start_ms + chunk_length_ms
        
        print(f"\n{'-'*50}")
        print(f"--- PROCESANDO BLOQUE {i+1} DE {total_chunks} ---")
        print(f"{'-'*50}")
        
        # Cortamos el fragmento de audio en la memoria
        chunk = audio_completo[start_ms:end_ms]
        nombre_temp = f"temp_chunk_{i+1}.flac"
        
        print("A) Exportando fragmento localmente...")
        chunk.export(nombre_temp, format="flac")
        
        print("B) Subiendo a los servidores seguros de Gemini...")
        archivo_subido = genai.upload_file(path=nombre_temp)
        
        print("C) Esperando a que el archivo esté activo en la nube...")
        while archivo_subido.state.name == 'PROCESSING':
            print(".", end="", flush=True)
            time.sleep(5)
            archivo_subido = genai.get_file(archivo_subido.name)
            
        if archivo_subido.state.name == 'FAILED':
            print(f"\n[ERROR] Falló el procesamiento del bloque {i+1} en Gemini. Saltando al siguiente...")
            continue
            
        print("\nD) Generando transcripción con Gemini 3 flash preview...")
        try:
            # Mandamos el archivo y las instrucciones
            respuesta = modelo.generate_content([archivo_subido, prompt_base])
            texto_bloque = respuesta.text
            print("¡Fragmento transcrito con éxito!")
            
            # Anexamos el texto al acumulado final
            transcripcion_completa += f"\n\n{'='*20} INICIO BLOQUE {i+1} {'='*20}\n\n"
            transcripcion_completa += texto_bloque
        except Exception as e:
            print(f"[ERROR] Hubo un problema al generar el texto de este bloque: {e}")
            
        print("E) Limpiando archivos temporales (Nube y Local)...")
        genai.delete_file(archivo_subido.name) # Borramos de Google AI
        os.remove(nombre_temp)                 # Borramos de tu PC

    # Guardamos todo en un archivo .txt plano
    archivo_salida = "Transcripcion_Gemini_Final.txt"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(transcripcion_completa)
        
    print(f"\n{'*'*50}")
    print(f"¡PROCESO TOTAL TERMINADO! Revisa el archivo: {archivo_salida}")
    print(f"{'*'*50}")

if __name__ == "__main__":
    # El archivo de entrada
    ARCHIVO = "RAMONA PADILLA ALTAMIRANO 2 (normalizado).flac"
    
    if os.path.exists(ARCHIVO):
        # Arrancamos la máquina
        transcribir_por_bloques(ARCHIVO, duracion_minutos=45)
    else:
        print(f"No se encontró el archivo: {ARCHIVO}. Asegúrate de que esté en la misma carpeta que este script.")
import os
import json
from google.cloud import storage
import docx

# Define la ruta al archivo JSON de credenciales
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "woven-operative-419903-3d469fdaeb1c.json"

def formatear_tiempo(tiempo_str: str) -> str:
    """Convierte el formato '1.500s' de GCP a un formato legible MM:SS."""
    try:
        # Se remueve la 's' final y se convierte a flotante
        segundos_totales = float(tiempo_str.replace('s', ''))
        minutos = int(segundos_totales // 60)
        segundos = int(segundos_totales % 60)
        return f"{minutos:02d}:{segundos:02d}"
    except (ValueError, TypeError):
        return "00:00"

def procesar_json_a_word(bucket_name: str, blob_name: str, output_word_file: str):
    """
    Descarga el JSON de STT V1 y genera un documento Word estructurado.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    print(f"Descargando resultados de: gs://{bucket_name}/{blob_name}")
    json_data_string = blob.download_as_text()
    datos = json.loads(json_data_string)

    doc = docx.Document()
    doc.add_heading('Transcripción Estructurada (Diarización)', 0)

    # En la API V1, la diarización consolidada se encuentra en el último resultado
    resultados = datos.get('results', [])
    if not resultados:
        print("[ERROR] El JSON no contiene resultados de transcripción.")
        return

    ultimo_resultado = resultados[-1]
    alternativas = ultimo_resultado.get('alternatives', [])
    
    if not alternativas or 'words' not in alternativas[0]:
        print("[ERROR] No se encontraron datos de palabras con etiquetas de hablante en el JSON.")
        return

    palabras = alternativas[0].get('words', [])

    hablante_actual = None
    frase_actual = []
    tiempo_inicio = ""

    print("Procesando estructura de hablantes y tiempos...")

    for metadato_palabra in palabras:
        # En la API V1, el identificador numérico del hablante es 'speakerTag'
        hablante = metadato_palabra.get('speakerTag', 0)
        texto_palabra = metadato_palabra.get('word', '')
        tiempo_palabra = metadato_palabra.get('startTime', '0s')

        if hablante != hablante_actual:
            # Si el hablante cambia, se escribe el bloque acumulado en el documento
            if frase_actual:
                parrafo = f"Hablante {hablante_actual} [{tiempo_inicio}]: {' '.join(frase_actual)}"
                doc.add_paragraph(parrafo)
            
            # Se reinician los valores para el nuevo hablante
            hablante_actual = hablante
            frase_actual = [texto_palabra]
            tiempo_inicio = formatear_tiempo(tiempo_palabra)
        else:
            # Se acumula el texto correspondiente al mismo hablante
            frase_actual.append(texto_palabra)

    # Inserción del último bloque procesado
    if frase_actual:
        parrafo = f"Hablante {hablante_actual} [{tiempo_inicio}]: {' '.join(frase_actual)}"
        doc.add_paragraph(parrafo)

    doc.save(output_word_file)
    print("-" * 50)
    print(f"[ÉXITO] Documento Word generado correctamente: {output_word_file}")

if __name__ == "__main__":
    NOMBRE_BUCKET = "sttgcp"
    # La ruta exacta del archivo que definimos en el script de envío
    ARCHIVO_JSON_EN_BUCKET = "transcripts/resultado_carlos_soto.json" 
    ARCHIVO_SALIDA_WORD = "transcripcion_carlos_soto.docx"
    
    procesar_json_a_word(NOMBRE_BUCKET, ARCHIVO_JSON_EN_BUCKET, ARCHIVO_SALIDA_WORD)
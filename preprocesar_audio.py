import os
from pydub import AudioSegment

def procesar_flujo_completo(ruta_entrada, carpeta_salida, target_dbfs=-20.0):
    print(f"1. Cargando audio original: {ruta_entrada}...")
    audio = AudioSegment.from_file(ruta_entrada)
    
    # ESTANDARIZACIÓN (Punto clave para que coincida con el futuro JSON)
    print("2. Estandarizando formato (Mono, 44100Hz)...")
    audio = audio.set_frame_rate(44100).set_channels(1)

    # NORMALIZACIÓN GLOBAL
    print("3. Aplicando normalización de volumen...")
    cambio_en_dbfs = target_dbfs - audio.dBFS
    audio = audio.apply_gain(cambio_en_dbfs)

    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    # EXPORTAR MASTER (Para AssemblyAI)
    ruta_master = os.path.join(carpeta_salida, "MASTER_NORMALIZADO.flac")
    print(f"4. Exportando archivo MASTER para mapeo: {ruta_master}")
    audio.export(ruta_master, format="flac")

    # SEGMENTACIÓN
    print("5. Iniciando segmentación en bloques de 50 minutos...")
    CHUNK_LENGTH_MS = 50 * 60 * 1000 
    total_ms = len(audio)
    inicio = 0
    contador = 1

    while inicio < total_ms:
        fin = min(inicio + CHUNK_LENGTH_MS, total_ms)
        chunk = audio[inicio:fin]
        
        nombre_chunk = f"segmento_{contador:02d}.flac"
        ruta_chunk = os.path.join(carpeta_salida, nombre_chunk)
        
        chunk.export(ruta_chunk, format="flac")
        print(f"   [OK] Fragmento guardado: {nombre_chunk}")
        
        inicio = fin
        contador += 1

    print(f"\n¡Proceso terminado! Tienes el MASTER y {contador-1} segmentos en '{carpeta_salida}'.")
    return ruta_master

if __name__ == "__main__":
    # Coloca aquí el nombre de tu archivo de 3h 39min
    ARCHIVO_ENTRADA = "DRAFT 2 ERNESTO GÓMEZ LEAL.mp3" 
    CARPETA_DESTINO = "audio_segmentado_DRAFT 2 ERNESTO GÓMEZ LEAL"
    
    if os.path.exists(ARCHIVO_ENTRADA):
        procesar_flujo_completo(ARCHIVO_ENTRADA, CARPETA_DESTINO)
    else:
        print(f"No se encuentra el archivo: {ARCHIVO_ENTRADA}")
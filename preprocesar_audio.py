#SCRIPT PARA NORMALIZAR Y SEGMENTAR AUDIO

import os
from pydub import AudioSegment

def procesar_flujo_completo(ruta_entrada, carpeta_salida, chunk_ms, target_dbfs=-20.0):
    print(f"1. Cargando audio original: {ruta_entrada}...")
    audio = AudioSegment.from_file(ruta_entrada)
    
    # ESTANDARIZACIÓN
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
    total_ms = len(audio)
    inicio = 0
    contador = 1

    while inicio < total_ms:
        fin = min(inicio + chunk_ms, total_ms)
        chunk = audio[inicio:fin]
        
        nombre_chunk = f"segmento_{contador:02d}.flac"
        ruta_chunk = os.path.join(carpeta_salida, nombre_chunk)
        
        chunk.export(ruta_chunk, format="flac")
        print(f"   [OK] Fragmento guardado: {nombre_chunk}")
        
        inicio = fin
        contador += 1

    print(f"\n¡Proceso terminado! Tienes el MASTER y {contador-1} segmentos en '{carpeta_salida}'.")
    return ruta_master
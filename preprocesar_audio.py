import os
from pydub import AudioSegment

def normalizar_y_convertir_a_flac(ruta_entrada, ruta_salida, target_dbfs=-20.0):
    print(f"1. Cargando y decodificando: {ruta_entrada}...")
    audio = AudioSegment.from_file(ruta_entrada)
    
    print("2. Estandarizando a 44100 Hz y 2 canales...")
    audio_estandar = audio.set_frame_rate(44100).set_channels(2)
    
    print("3. Aplicando normalización de volumen (RMS)...")
    # Subimos o bajamos el volumen para que quede en el nivel ideal (-20 dBFS)
    cambio_en_dbfs = target_dbfs - audio_estandar.dBFS
    audio_normalizado = audio_estandar.apply_gain(cambio_en_dbfs)
    
    # Sistema de seguridad: si al subir el volumen general hay un grito que satura, lo bajamos un poco
    if audio_normalizado.max_dBFS > -1.0:
        reduccion = audio_normalizado.max_dBFS - (-1.0)
        audio_normalizado = audio_normalizado.apply_gain(-reduccion)
        
    print(f"4. Exportando audio comprimido sin pérdida a: {ruta_salida}...")
    # Aquí está la clave: exportamos en FLAC en lugar de WAV
    audio_normalizado.export(ruta_salida, format="flac")
    print("¡Proceso completado con éxito!\n")

if __name__ == "__main__":
    # Vamos a usar el mismo archivo largo con el que estabas haciendo pruebas
    ENTRADA = "RAMONA PADILLA ALTAMIRANO 2.mp3"
    SALIDA = "RAMONA PADILLA ALTAMIRANO 2 (normalizado).flac"
    
    if os.path.exists(ENTRADA):
        normalizar_y_convertir_a_flac(ENTRADA, SALIDA)
        
        # Un pequeño extra para que veas cuánto pesa el resultado final
        peso_mb = os.path.getsize(SALIDA) / (1024 * 1024)
        print(f"Peso del archivo FLAC resultante: {peso_mb:.2f} MB")
    else:
        print("No se encontró el archivo de entrada.")
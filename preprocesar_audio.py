import os
import subprocess
import logging

# Configuracion de logging profesional
logger = logging.getLogger(__name__)

def preprocesar_con_ffmpeg(ruta_entrada: str, carpeta_salida: str, duracion_segmento_segundos: int = 3000) -> list:
    """
    Estandariza, normaliza y segmenta un archivo de audio utilizando FFMPEG.
    Optimizado para entornos serverless (Cloud Run) mediante procesamiento en streaming
    para evitar el desbordamiento de memoria RAM (OOM).
    
    Parametros:
        ruta_entrada (str): Ruta del archivo original a procesar.
        carpeta_salida (str): Directorio donde se guardaran los segmentos.
        duracion_segmento_segundos (int): Duracion maxima de cada segmento en segundos (por defecto 50 min).
        
    Retorna:
        list: Lista de rutas absolutas de los segmentos .flac generados.
    """
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida, exist_ok=True)
        
    patron_salida = os.path.join(carpeta_salida, "segmento_%03d.flac")
    
    # Configuracion del comando FFMPEG
    # -af loudnorm: Normalizacion profesional de volumen (Target: -20 LUFS)
    # -ar 44100: Sample rate estandar para transcripciones
    # -ac 1: Forzar canal mono
    comando = [
        "ffmpeg", 
        "-y",                 
        "-i", ruta_entrada,   
        "-af", "loudnorm=I=-20:LRA=11:TP=-1.5", 
        "-ar", "44100",       
        "-ac", "1",           
        "-c:a", "flac",       
        "-f", "segment",      
        "-segment_time", str(duracion_segmento_segundos), 
        "-reset_timestamps", "1",
        patron_salida
    ]
    
    logger.info(f"Iniciando procesamiento acustico via FFMPEG para: {ruta_entrada}")
    
    try:
        # Ejecucion del subproceso capturando salidas para depuracion
        resultado = subprocess.run(
            comando, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("Estandarizacion y segmentacion completadas exitosamente.")
        
        # Recoleccion y validacion de los archivos generados
        archivos_generados = sorted([f for f in os.listdir(carpeta_salida) if f.endswith(".flac")])
        rutas_segmentos = [os.path.join(carpeta_salida, f) for f in archivos_generados]
        
        if not rutas_segmentos:
            raise RuntimeError("FFMPEG finalizo correctamente pero no genero archivos de salida.")
            
        return rutas_segmentos
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Falla interna en FFMPEG: {e.stderr}")
        raise RuntimeError("El procesamiento del audio fue interrumpido debido a un error de decodificacion.")
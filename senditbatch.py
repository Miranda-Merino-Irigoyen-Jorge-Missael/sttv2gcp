import os
import time
from google.cloud import speech_v1 as speech

# Define la ruta al archivo JSON de credenciales
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "woven-operative-419903-3d469fdaeb1c.json"

def enviar_batch_v1(gcs_audio_uri: str, gcs_output_uri: str):
    """
    Envía un trabajo de transcripción asíncrona a STT V1 con diarización y puntuación.
    """
    client = speech.SpeechClient()


    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=44100,
        audio_channel_count=2,
        language_code="es-US",
        model="latest_long",
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        # Nivel de Diarización Estricto
        diarization_config=speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2, # Mínimo 2
            max_speaker_count=2, # MÁXIMO 2
        )
    )

    audio = speech.RecognitionAudio(uri=gcs_audio_uri)
    
    output_config = speech.TranscriptOutputConfig(
        gcs_uri=gcs_output_uri
    )

    request = speech.LongRunningRecognizeRequest(
        config=config,
        audio=audio,
        output_config=output_config
    )

    hora_inicio = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{hora_inicio}] Enviando solicitud a Google Cloud usando API V1...")
    
    operation = client.long_running_recognize(request=request)

    print("\nTrabajo enviado exitosamente.")
    print("-" * 50)
    print(f"ID DE OPERACIÓN: {operation.operation.name}")
    print("-" * 50)

if __name__ == "__main__":
    AUDIO_URI = "gs://sttgcp/test/DRAFT_normalizado.flac" 
    
    # IMPORTANTE: Te sugiero cambiar el nombre del archivo de salida para no sobreescribir el anterior
    OUTPUT_URI = "gs://sttgcp/transcripts/resultado_draft_ernesto_puntuado2.json" 
    
    enviar_batch_v1(AUDIO_URI, OUTPUT_URI)
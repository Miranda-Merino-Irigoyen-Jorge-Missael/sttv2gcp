import os
from google.cloud import speech_v1 as speech

# Define la ruta al archivo JSON de credenciales de la cuenta de servicio
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "woven-operative-419903-3d469fdaeb1c.json"

def revisar_estado_v1(operation_name: str):
    """
    Consulta el estado de una operación de transcripción asíncrona en STT V1.
    """
    client = speech.SpeechClient()
    
    # En V1, el cliente de operaciones se accede a través del transporte
    operation = client.transport.operations_client.get_operation(operation_name)
    
    print(f"Revisando operación: {operation_name}")
    print("-" * 50)
    
    if operation.done:
        if operation.HasField("error"):
            print(f"[ERROR] Ocurrió un fallo en la transcripción: {operation.error.message}")
        else:
            print("[ÉXITO] La transcripción ha finalizado.")
            print("El archivo JSON con la diarización está disponible en tu bucket de salida.")
    else:
        print("[EN PROCESO] El trabajo sigue procesándose en la nube.")
        print("Tratándose de un modelo de larga duración, ejecute este script más tarde para verificar.")

if __name__ == "__main__":
    # ID de operación generado por la API V1
    OPERATION_ID = "4096715389190313198"
    
    revisar_estado_v1(OPERATION_ID)
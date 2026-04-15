# STT-VAWA-API: Documentación Técnica del Microservicio

Este repositorio contiene el microservicio de transcripción automatizada diseñado para The Mendoza Law Firm. El sistema implementa un pipeline de procesamiento de lenguaje natural y audio orientado a la transcripción pericial de casos legales (VAWA, Visa T, RFE).

## 1. Descripción General

El sistema procesa archivos de audio de gran longitud mediante una arquitectura de microservicios serverless. Utiliza un enfoque de procesamiento asíncrono que combina el análisis acústico de AssemblyAI con la capacidad de razonamiento lingüístico de los modelos Gemini de Google para corregir terminología legal y nombres propios.

## 2. Características Técnicas

* **Procesamiento Asíncrono**: Implementado mediante FastAPI (Background Tasks) para manejar cargas pesadas sin interrumpir la disponibilidad de la API.
* **Normalización y Segmentación**: Estandarización de audio a formato .flac (Mono, 44100Hz) y división en bloques de 50 minutos con detección de silencios para mantener la integridad del contexto.
* **Diarización de Hablantes**: Mapeo acústico para identificar roles de "Abogado" y "Cliente" de forma automática.
* **Refinamiento por LLM**: Uso de Gemini para la corrección de errores de transcripción basados en una guía acústica generada previamente.
* **Gestión de Secretos**: Integración nativa con Google Cloud Secret Manager para la gestión de API Keys.

## 3. Arquitectura del Sistema

El flujo de datos sigue el siguiente orden lógico:

1.  **Ingesta**: Recepción de solicitud vía HTTP POST con la ruta del archivo (Local o GCS).
2.  **Preprocesamiento**: El audio se normaliza a -20.0 dBFS y se segmenta si excede los límites de procesamiento de los modelos.
3.  **Mapa de Voces**: AssemblyAI genera un archivo JSON con las marcas de tiempo y etiquetas de hablantes.
4.  **Ensamble IA**: Se envían los segmentos de audio y sus respectivos mapas a Gemini. El modelo devuelve una estructura JSON corregida.
5.  **Persistencia**: Se consolida la transcripción final en un archivo .txt y se almacena en Google Cloud Storage.

## 4. Estructura del Proyecto

* `main.py`: Punto de entrada de la API y orquestador de tareas en segundo plano.
* `preprocesar_audio.py`: Lógica de estandarización, normalización y segmentación de audio.
* `assembly_test.py`: Interfaz con el SDK de AssemblyAI para diarización.
* `fusion_assembly_gemini.py`: Lógica de interacción con Google GenAI y reconstrucción de diálogos.
* `gcs_manager.py`: Gestión de subida de resultados a Cloud Storage.
* `google_services.py`: Configuración de autenticación (ADC) y acceso a Secret Manager.
* `Dockerfile`: Configuración del contenedor para despliegue en Cloud Run.

## 5. Configuración y Despliegue

### Requisitos Previos
* Python 3.10+
* FFmpeg (Instalado en el sistema o contenedor)
* Cuenta de Servicio en GCP con roles de Storage Admin y Secret Manager Accessor.

### Variables de Entorno y Secretos
El servicio requiere las siguientes variables inyectadas:
* `GCS_BUCKET_NAME`: Nombre del bucket de destino.
* `GEMINI_API_KEY`: Gestionado vía Secret Manager.
* `ASSEMBLYAI_API_KEY`: Gestionado vía Secret Manager.

### Comandos de Despliegue (Cloud Run)
```bash
# Construcción de la imagen
gcloud builds submit --tag gcr.io/[PROJECT_ID]/transcriptor-mendoza

# Despliegue del servicio
gcloud run deploy transcriptor-mendoza \
  --image gcr.io/[PROJECT_ID]/transcriptor-mendoza \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=[BUCKET_NAME] \
  --set-secrets="GEMINI_API_KEY=gemini-key:latest,ASSEMBLYAI_API_KEY=assembly-key:latest"

## 6. Referencia de la API

### Iniciar Transcripción
* **Endpoint**: `POST /iniciar-transcripcion`
* **Payload**:
```json
{
  "ruta_local_o_gcs": "gs://bucket/audio.mp3",
  "cliente_id": "IDENTIFICADOR_CLIENTE"
}

Aquí tienes el bloque exacto en Markdown, listo para copiar y pegar directamente al final de tu README:

Markdown
## 6. Referencia de la API

### Iniciar Transcripción
* **Endpoint**: `POST /iniciar-transcripcion`
* **Payload**:
```json
{
  "ruta_local_o_gcs": "gs://bucket/audio.mp3",
  "cliente_id": "IDENTIFICADOR_CLIENTE"
}

Nota Legal: Este software es propiedad de The Mendoza Law Firm y está diseñado para uso exclusivo interno en entornos controlados y seguros.

Referencias: La arquitectura y los comandos de despliegue se basan en la configuración de Google Cloud SDK y las especificaciones de FastAPI utilizadas en el desarrollo de este proyecto.

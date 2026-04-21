# Documentación Técnica: Microservicio de Transcripción

Este repositorio contiene la lógica del microservicio de transcripción automatizada diseñado para procesar audios de larga duración. El sistema transforma archivos de audio en datos estructurados mediante un pipeline que combina procesamiento acústico, diarización de hablantes y refinamiento lingüístico por inteligencia artificial.

## 1. Descripción del Sistema

El servicio opera bajo una arquitectura asíncrona sobre Google Cloud Platform. Su propósito principal es recibir archivos de audio (locales o desde Google Cloud Storage), normalizarlos para garantizar la fidelidad del reconocimiento y generar una transcripción estructurada que identifique roles específicos.

### Componentes Core
* **Procesamiento de Audio**: Utiliza FFmpeg para estandarizar archivos a formato .flac (Mono, 44100Hz) y normalizar el volumen a -20 LUFS, eliminando picos que puedan distorsionar la interpretación del modelo.
* **Diarización**: AssemblyAI genera el mapa acústico inicial, identificando los cambios de turno entre voces.
* **Refinamiento GenAI (Vertex AI)**: Modelos fundacionales a través de Vertex AI reconstruyen el diálogo final, corrigiendo terminología legal y nombres propios basándose en el contexto del audio y la guía acústica.

## 2. Especificación para Frontend

Esta sección es fundamental para la integración con la interfaz web. El sistema utiliza un modelo asíncrono con sincronización en tiempo real vía Firebase/Firestore para evitar bloqueos por *timeout* en el navegador.

### Endpoints
* **Producción (Cloud Run):** `https://transcriptor-mendoza-907757756276.us-central1.run.app`
* **Ruta de inicio:** `/iniciar-transcripcion` (Método: POST)

### Flujo de Interacción
1. **Petición Inicial**: El frontend hace un `POST /iniciar-transcripcion` enviando el `ruta_local_o_gcs` y un `cliente_id` único.
2. **Respuesta Rápida**: La API devuelve un código 200 inmediatamente confirmando el inicio del proceso.
3. **Suscripción (Real-time)**: El frontend debe utilizar el SDK de Firebase para suscribirse (usando `onSnapshot`) a la colección `trabajos_transcripcion` en el documento correspondiente al `cliente_id`.

### Estructura del Documento en Firestore
El documento cambiará de estado automáticamente. La interfaz debe reaccionar a estos cambios:

* **Estado Inicial**: `{ "status": "procesando", "cliente_id": "...", "resultado_url": null }`
* **Estado Éxito**: `{ "status": "completado", "resultado_url": "gs://bucket/archivo.json", ... }` -> *Aquí el frontend descarga y renderiza el JSON final.*
* **Estado Error**: `{ "status": "error", "error_mensaje": "Descripción del fallo" }` -> *Mostrar alerta visual al usuario.*

### Estructura del Resultado (JSON)
El archivo final descargado desde el bucket es un arreglo de objetos:

```json
[
  {
    "tiempo_ms": 65000,
    "tiempo_formato": "01:05",
    "hablante": "Abogado",
    "texto": "Texto refinado por la IA..."
  },
  {
    "error": true,
    "segmento": 2,
    "mensaje": "No se pudo transcribir el segmento."
  }
]
```

### Notas de Implementación para el Frontend
1. **Sincronización con Audio**: El campo `tiempo_ms` representa el milisegundo exacto de inicio del bloque. Úsalo para implementar una función de salto en el reproductor web al hacer clic en un párrafo.
2. **Visualización de Hablantes**: El campo `hablante` permite aplicar estilos diferenciados (colores o alineación) para separar visualmente las intervenciones del Abogado de las del Cliente.

## 3. Arquitectura y Flujo de Datos

1. **Ingesta**: El servicio recibe la solicitud y genera una URL firmada de Google Cloud Storage para procesar el audio mediante streaming, evitando el desbordamiento de memoria RAM en la instancia de Cloud Run.
2. **Segmentación**: Si el audio es extenso, se divide en bloques de 50 minutos para optimizar el procesamiento paralelo.
3. **Persistencia y Estado**: Se actualiza el documento en Firestore y el resultado final se guarda en GCS con codificación UTF-8 para garantizar la correcta visualización de caracteres especiales en cualquier navegador.

## 4. Configuración del Entorno y Despliegue

### Variables y Permisos Necesarios
El servicio utiliza la Identidad de Cloud Run (Service Account) para autenticarse nativamente con Vertex AI y Firestore. Se requiere configurar:
* **Secretos en Secret Manager**:
  * `ASSEMBLYAI_API_KEY`: Credencial para el motor de diarización.
* **Roles IAM (Service Account)**:
  * `roles/datastore.user` (Para escribir en Firestore)
  * `roles/aiplatform.user` (Para invocar modelos en Vertex AI)
  * `roles/iam.serviceAccountTokenCreator` (Para firmar URLs de Storage)

### Comando de Despliegue
Para actualizar el servicio en Cloud Run con la configuración óptima (sin throttling de CPU), utilice el siguiente comando en la terminal:

```bash
gcloud run deploy transcriptor-mendoza --image gcr.io/[PROJECT_ID]/transcriptor-mendoza --platform managed --region us-central1 --allow-unauthenticated --no-cpu-throttling --timeout=3600 --set-env-vars GCS_BUCKET_NAME=[NOMBRE_DEL_BUCKET] --set-secrets="ASSEMBLYAI_API_KEY=assembly-ai-api-key-transcriptor-mendoza:latest"
```

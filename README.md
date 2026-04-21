# Documentación Técnica: Microservicio de Transcripción

Este repositorio contiene la lógica del microservicio de transcripción automatizada diseñado para procesar audios de larga duración. El sistema transforma archivos de audio en datos estructurados mediante un pipeline que combina procesamiento acústico, diarización de hablantes y refinamiento lingüístico por inteligencia artificial.

## 1. Descripción del Sistema

El servicio opera bajo una arquitectura asíncrona sobre Google Cloud Platform. Su propósito principal es recibir archivos de audio (locales o desde Google Cloud Storage), normalizarlos para garantizar la fidelidad del reconocimiento y generar una transcripción estructurada que identifique roles específicos.

### Componentes Core
* **Procesamiento de Audio**: Utiliza FFmpeg para estandarizar archivos a formato .flac (Mono, 44100Hz) y normalizar el volumen a -20 LUFS, eliminando picos que puedan distorsionar la interpretación del modelo.
* **Diarización**: AssemblyAI genera el mapa acústico inicial, identificando los cambios de turno entre voces.
* **Refinamiento GenAI**: Modelos Gemini de Google reconstruyen el diálogo final, corrigiendo terminología legal y nombres propios basándose en el contexto del audio y la guía acústica.

## 2. Especificación para Frontend

Esta sección es fundamental para la integración con la interfaz web. El servicio no devuelve texto plano, sino una estructura de datos diseñada para crear interfaces interactivas.

### Interacción con la API
El endpoint principal es asíncrono. Al realizar la petición, el servicio valida los datos e inicia el proceso en segundo plano para evitar el timeout del navegador en audios largos.

* **Endpoint**: `POST /iniciar-transcripcion`
* **Cuerpo de la petición (JSON)**:
  * `ruta_local_o_gcs`: Ubicación del archivo de audio.
  * `cliente_id`: Identificador único para la gestión de archivos y carpetas de salida.

### Estructura del Resultado (JSON)
El archivo final generado en el bucket de salida es un arreglo de objetos. Cada objeto representa un bloque de diálogo con la siguiente anatomía:

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
1. **Sincronización con Audio**: El campo `tiempo_ms` representa el milisegundo exacto de inicio del bloque respecto al inicio total del audio original. Se recomienda usar este valor para implementar una función de salto en el reproductor web al hacer clic en un párrafo.
2. **Visualización de Hablantes**: El campo `hablante` permite aplicar estilos diferenciados (colores o alineación) para separar visualmente las intervenciones del Abogado de las del Cliente.
3. **Manejo de Errores**: Si un objeto contiene la llave `"error": true`, la interfaz debe manejarlo como un aviso visual en lugar de un bloque de texto.

## 3. Arquitectura y Flujo de Datos

1. **Ingesta**: El servicio recibe la solicitud y genera una URL firmada de Google Cloud Storage para procesar el audio mediante streaming, evitando el desbordamiento de memoria RAM en la instancia de Cloud Run.
2. **Segmentación**: Si el audio es extenso, se divide en bloques de 50 minutos para optimizar el procesamiento paralelo.
3. **Persistencia**: El resultado final se guarda con codificación UTF-8 para garantizar la correcta visualización de caracteres especiales (acentos y eñes) en cualquier navegador.

## 4. Configuración del Entorno

### Variables Necesarias
El servicio requiere la configuración de las siguientes variables y secretos en Google Cloud Secret Manager:
* `GEMINI_API_KEY`: Credencial para el acceso a modelos generativos de Google.
* `ASSEMBLYAI_API_KEY`: Credencial para el motor de diarización.
* `GCS_BUCKET_NAME`: Nombre del contenedor donde se alojarán los resultados finales.

### Comandos de Despliegue
Para actualizar el servicio en Cloud Run, utilice los siguientes comandos en la terminal:

```bash
# Construcción de imagen
gcloud builds submit --tag gcr.io/[PROJECT_ID]/transcriptor-mendoza

# Despliegue de revisión
gcloud run deploy transcriptor-mendoza \
  --image gcr.io/[PROJECT_ID]/transcriptor-mendoza \
  --platform managed \
  --region us-central1 \
  --set-env-vars GCS_BUCKET_NAME=[NOMBRE_DEL_BUCKET] \
  --set-secrets="GEMINI_API_KEY=gemini-key:latest,ASSEMBLYAI_API_KEY=assembly-key:latest"
```

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

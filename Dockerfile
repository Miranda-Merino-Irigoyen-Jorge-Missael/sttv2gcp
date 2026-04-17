# Usar una imagen ligera de Python
FROM python:3.10-slim

# INSTALACIÓN CRÍTICA: ffmpeg es necesario para pydub
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar requerimientos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Exponer el puerto usando la variable de entorno de Cloud Run
ENV PORT="8080"
EXPOSE $PORT

# Ejecutar con shell (sh -c) para que evalúe la variable $PORT correctamente
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
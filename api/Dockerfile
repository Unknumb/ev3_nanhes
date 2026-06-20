# API de serving. Se construye desde la RAIZ del repo:
#   docker build -f api/Dockerfile -t ev3-api .
FROM python:3.11-slim

WORKDIR /app

# Deps primero para cachear capas.
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Codigo de la API + contrato compartido.
COPY api ./api
COPY feature_schema.json ./feature_schema.json

# Los modelos bendecidos (data/09_serving) se montan como volumen en runtime:
#   docker run -v "$PWD/data:/app/data" -p 8000:8000 ev3-api
ENV EV3_ROOT=/app
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

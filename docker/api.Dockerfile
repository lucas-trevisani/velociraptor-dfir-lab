FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt
COPY api /app/api
COPY launcher /app/launcher
RUN mkdir -p /app/storage/hunts /app/storage/results /app/secrets
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "18443"]

FROM python:3.12-slim

WORKDIR /app

COPY src/batch/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/shared/ /app/shared/
COPY src/batch/ /app/batch/

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "batch.main"]

FROM python:3.12-slim

WORKDIR /app

COPY src/webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/shared/ /app/shared/
COPY src/webhook/ /app/webhook/

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "30", "webhook.main:create_app()"]

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/drive-scanner/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/drive-scanner/src/ /app/
COPY services/metadata-loader/src/metadata_loader/ /app/metadata_loader/

EXPOSE 8080

CMD ["python", "app.py"]

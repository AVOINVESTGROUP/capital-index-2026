FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY services/entity-extractor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/entity-extractor/src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["python", "src/app.py"]

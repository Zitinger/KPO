FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY file_storing_service /app/file_storing_service

CMD ["uvicorn", "file_storing_service.app:app", "--host", "0.0.0.0", "--port", "8000"]

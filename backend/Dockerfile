# NS-S6-01 — production-style image (API only)
# Pin platform so App Runner (linux/amd64) and M1/Apple Silicon `docker build` both produce a runnable image.
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

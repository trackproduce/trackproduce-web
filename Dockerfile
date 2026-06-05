FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_DEBUG=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 7015

# Production WSGI server (Werkzeug's dev server is not for production).
CMD ["gunicorn", "--bind", "0.0.0.0:7015", "--workers", "2", "--threads", "4", "run:app"]

# Local development image (docker-compose.yml). The deployed site runs on Vercel,
# which builds from requirements.txt and serves wsgi.py itself — see docs/DEPLOY.md.
# Python 3.12 to match the runtime Vercel pins in .python-version.
FROM python:3.12-slim

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

# Werkzeug's dev server is not for serving, even locally behind compose.
CMD ["gunicorn", "--bind", "0.0.0.0:7015", "--workers", "2", "--threads", "4", "wsgi:app"]

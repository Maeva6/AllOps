FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

    # Mise à jour de pip
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Création du dossier pour la base SQLite
RUN mkdir -p instance

RUN mkdir -p instance

EXPOSE 5000

CMD ["python", "run.py"]

# Base image
FROM python:3.11-slim

# Imposta cartella di lavoro
WORKDIR /app

# Copia requirements e installa dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice del bot
COPY . .

# Imposta variabili d'ambiente opzionali (se vuoi sovrascrivere quelle in .env)
ENV PYTHONUNBUFFERED=1

# Avvia il bot
CMD ["python", "-u", "bot.py"]

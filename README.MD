# Telegram Task Bot

Un semplice bot Telegram per gestire le proprie task personali. Permette di aggiungere task con urgenza e data di scadenza, memorizzandole in un database SQLite.

---

## Funzionalità

- `/start` – Avvia il bot e mostra un messaggio di benvenuto.
- `/help` – Mostra i comandi disponibili.
- `/addtask` – Aggiunge una nuova task con descrizione, urgenza e data di scadenza.
- `/cancel` – Annulla l'inserimento di una task.

> ⚠️ Attualmente non è presente la logica per notifiche o gestione di task completate, ma è prevista come futura implementazione.

---

## Tecnologie

- Python 3.11
- Telegram Bot API (`python-telegram-bot`)
- SQLite per la gestione delle task
- Docker & Docker Compose per eseguire il bot in container

---

## Come avviare il progetto

1. Clonare il repository:

```bash
git clone <URL_DEL_REPO>
cd <NOME_CARTELLA>
```
2. Creare un bot su Telegram tramite il [BotFather](https://core.telegram.org/bots#6-botfather) e ottenere la chiave API.

Crea un file .env nella root con la chiave API del bot:
```env
BOT_TOKEN=la_tua_chiave_api
```

3. Costruire ed eseguire il container Docker:

```bash
docker-compose up --build -d
```
import os
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ------------------- CONFIGURAZIONE LOGGING -------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------- CARICAMENTO ENV -------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN non trovato. Controlla il file .env")
    exit(1)

# ------------------- STATI DELLA CONVERSAZIONE -------------------
TASK_TEXT, URGENCY, DUE_DATE, DONE_TASK_ID = range(4)

# ------------------- DATABASE -------------------
DB_FILE = "tasks.db"

def init_db():
    """Crea la tabella tasks se non esiste ancora"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            urgency TEXT NOT NULL,
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            done INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database inizializzato e tabella tasks pronta.")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------- COMANDI BASE -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"{user.first_name} ({user.id}) ha usato /start")
    await update.message.reply_text(
        "Ciao! Sono il tuo bot delle tasks. Usa /help per vedere i comandi disponibili."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"{user.first_name} ({user.id}) ha usato /help")
    await update.message.reply_text(
        "/start - avvia il bot\n"
        "/help - mostra questo messaggio\n"
        "/addtask - aggiungi una nuova task\n"
        "/tasks - mostra le task ancora da fare\n"
        "/donetask - segna una task come completata"
    )

# ------------------- CONVERSAZIONE ADD TASK -------------------
async def addtask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scrivi la descrizione della task:")
    return TASK_TEXT

async def addtask_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['task_text'] = update.message.text
    await update.message.reply_text("Qual è l'urgenza? (bassa / media / alta)")
    return URGENCY

async def addtask_urgency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urgency = update.message.text.strip().lower()
    if urgency not in ['bassa', 'media', 'alta']:
        await update.message.reply_text("Devi scrivere bassa, media o alta.")
        return URGENCY
    context.user_data['urgency'] = urgency
    await update.message.reply_text("Quando deve essere completata? (YYYY-MM-DD HH:MM)")
    return DUE_DATE

async def addtask_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    due_date = update.message.text.strip()
    try:
        datetime.strptime(due_date, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Formato errato. Usa YYYY-MM-DD HH:MM")
        return DUE_DATE

    context.user_data['due_date'] = due_date

    # Salvataggio nel DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, task_text, urgency, due_date) VALUES (?, ?, ?, ?)",
        (update.effective_user.id, context.user_data['task_text'], context.user_data['urgency'], due_date)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("Task aggiunta! Ti terrò aggiornato man mano che si avvicina la scadenza.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Aggiunta task annullata.")
    return ConversationHandler.END

# ------------------- VISUALIZZAZIONE TASK -------------------
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_text, urgency, due_date FROM tasks WHERE user_id=? AND done=0 ORDER BY due_date", (update.effective_user.id,))
    tasks = cursor.fetchall()
    conn.close()
    if not tasks:
        await update.message.reply_text("Non ci sono task da completare.")
    else:
        msg = "📋 Task da completare:\n"
        for task in tasks:
            msg += f"{task['id']}. {task['task_text']} - urgenza: {task['urgency']} - scadenza: {task['due_date']}\n"
        await update.message.reply_text(msg)

# ------------------- MARCA TASK COME COMPLETATA -------------------
async def donetask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scrivi l'ID della task che vuoi segnare come completata. Usa /tasks per vedere gli ID.")
    return DONE_TASK_ID

async def donetask_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Devi scrivere un numero valido.")
        return DONE_TASK_ID

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, update.effective_user.id))
    task = cursor.fetchone()
    if not task:
        await update.message.reply_text("Task non trovata.")
        conn.close()
        return ConversationHandler.END

    cursor.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Task '{task['task_text']}' segnata come completata.")
    return ConversationHandler.END

# ------------------- NOTIFICHE TASK IN SCADENZA -------------------
async def due_task_notifier(app):
    await asyncio.sleep(5)  # piccolo delay iniziale
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now()
            soon = now + timedelta(minutes=10)

            cursor.execute("SELECT user_id, task_text, due_date FROM tasks WHERE done=0")
            tasks = cursor.fetchall()
            for task in tasks:
                user_id = task['user_id']
                task_text = task['task_text']
                due_date = task['due_date']
                if due_date:
                    due_dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                    if now <= due_dt <= soon:
                        try:
                            await app.bot.send_message(
                                chat_id=user_id,
                                text=f"⏰ La tua task '{task_text}' scade alle {due_date}"
                            )
                        except Exception as e:
                            logger.error(f"Impossibile inviare notifica a {user_id}: {e}")
            conn.close()
        except Exception as e:
            logger.error(f"Errore nel notifier: {e}")

        await asyncio.sleep(60)  # ricontrolla ogni 60 sec

# ------------------- AVVIO BOT -------------------
if __name__ == "__main__":
    try:
        # Inizializza DB
        init_db()

        # Crea l'app del bot
        app = ApplicationBuilder().token(TOKEN).build()

        # Comandi base
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("tasks", list_tasks))

        # Conversazione addtask
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('addtask', addtask_start)],
            states={
                TASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_text)],
                URGENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_urgency)],
                DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_due)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        app.add_handler(conv_handler)

        # Conversazione donetask
        done_handler = ConversationHandler(
            entry_points=[CommandHandler('donetask', donetask_start)],
            states={
                DONE_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, donetask_done)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        app.add_handler(done_handler)

        # Avvio del notifier
        asyncio.create_task(due_task_notifier(app))

        logger.info("Bot avviato e pronto a ricevere messaggi!")
        app.run_polling()

    except Exception:
        logger.exception("Errore nell'avvio del bot")

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from flask import Flask
from threading import Thread
import os

# Логирование (только для отладки, не хранит личные данные)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚙️ НАСТРОЙКИ
TOKEN = "8320394259:AAFvODL3IxxehnmAfozR0mSY8VJI9b_tbwU"  # 👈 ЗАМЕНИ НА ТОКЕН ОТ @BotFather

# 🧠 Хранилище: только ID чатов, куда можно рассылать
subscribers = set()

# 🌐 Веб-сервер для Render (чтобы не было ошибки "Port scan timeout")
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Анонимный чат-бот работает 24/7", 200

def run_web():
    port = int(os.environ.get('PORT', 10000))  # Render требует PORT
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    await update.message.reply_text(
        "🔮 Добро пожаловать в *Абсолютно Анонимный Чат*.\n\n"
        "📩 Пиши что угодно — твоё сообщение получат все участники.\n"
        "👤 Никто не узнает, кто его отправил. Даже админ.\n"
        "🚫 Никаких имён, ID, меток. Только твои слова.\n\n"
        "Готов? Пиши первое сообщение 👇",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)  # добавляем нового пользователя

    # Определяем тип контента
    if update.message.text:
        content = update.message.text
        is_voice = False
    elif update.message.voice:
        content = update.message.voice.file_id
        is_voice = True
    else:
        await update.message.reply_text("Поддерживаются только текст и голосовые сообщения.")
        return

    # Рассылаем ВСЕМ (включая отправителя — для ощущения чата)
    broadcast_text = "📩 Новое анонимное сообщение:" if not is_voice else "📩 Новое анонимное голосовое:"

    success_count = 0
    failed_ids = set()

    for target_id in list(subscribers):  # копируем, чтобы избежать ошибок при удалении
        try:
            await context.bot.send_message(chat_id=target_id, text=broadcast_text)
            if is_voice:
                await context.bot.send_voice(chat_id=target_id, voice=content)
            else:
                await context.bot.send_message(chat_id=target_id, text=content)
            success_count += 1
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение в {target_id}: {e}")
            failed_ids.add(target_id)

    # Удаляем неактивных (заблокировали бота и т.п.)
    for bad_id in failed_ids:
        subscribers.discard(bad_id)

    await update.message.reply_text("✅ Сообщение отправлено анонимно всем.")

def main():
    # Запускаем веб-сервер ДО бота
    keep_alive()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))

    logger.info("🚀 Абсолютно анонимный чат-бот запущен. Никто не знает автора — даже админ.")
    application.run_polling()

if __name__ == '__main__':
    main()

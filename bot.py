from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from flask import Flask
import threading
import os

# Токен бота (получи у @BotFather)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# URL вебхука (для Replit: https://твоё-имя-проекта.username.repl.co)
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# Список ID пользователей, кто уже начал чат с ботом
users = set()

# Flask для UptimeRobot
app = Flask(__name__)

@app.route('/')
def index():
    return "Анонимный чат-бот работает! 💬"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Команда /start
def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    users.add(user_id)
    update.message.reply_text(
        "👋 Добро пожаловать в анонимный чат!\n"
        "Отправь любое сообщение — оно анонимно увидят все участники.\n"
        "⚠️ Никто не узнает, кто именно отправил."
    )

# Обработка сообщений
def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    text = update.message.text

    # Добавляем пользователя, если его ещё нет
    users.add(user_id)

    # Рассылаем сообщение всем, кроме отправителя
    for chat_id in users:
        if chat_id != user_id:
            try:
                context.bot.send_message(chat_id=chat_id, text=f"👤 Аноним: {text}")
            except Exception as e:
                print(f"Ошибка отправки в {chat_id}: {e}")

# Основной запуск бота
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Устанавливаем вебхук
    updater.bot.set_webhook(url=WEBHOOK_URL)

    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Запуск бота (polling не нужен при вебхуке, но для Replit оставим для fallback)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

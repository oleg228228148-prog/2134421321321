from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
import logging
import random
import string

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚙️ НАСТРОЙКИ
ADMIN_ID = 7570777211          # 👈 ЗАМЕНИ НА СВОЙ ID
TOKEN = "8320394259:AAELz_qEuaXZgJUHTvO1DjO3FHZVAOjLAFo" # 👈 ЗАМЕНИ НА ТОКЕН БОТА

# 🧠 Хранилища
user_ids = set()              # кто вообще писал
user_nicknames = {}           # user_id -> "Тень №77"
message_logs = []             # [(user_id, text), ...] — только обычные сообщения
active_messages = {}          # msg_id -> {content, type, author_id, reactions}

# Генерация анонимного ника
def generate_nickname():
    return f"Тень №{random.randint(10, 999)}"

# Генерация ID для сообщения (для реакций)
def generate_message_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_nicknames:
        nickname = generate_nickname()
        user_nicknames[user.id] = nickname
        logger.info(f"Новый пользователь {user.id} -> {nickname}")

    user_ids.add(user.id)
    await update.message.reply_text(
        f"👋 Привет, {user_nicknames[user.id]}!\n"
        "Ты в *Чистом Анонимном Чате* 🎭\n\n"
        "📌 Пиши текст или голосовые — всё отправляется всем анонимно.\n"
        "📌 Ответь на сообщение — поставь реакцию стикером.\n\n"
        "Наслаждайся свободой и тайной 😉",
        parse_mode="Markdown"
    )

# Обработка текста и голосовых
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Генерим ник, если нет
    if user.id not in user_nicknames:
        user_nicknames[user.id] = generate_nickname()

    # Определяем тип контента
    if update.message.text:
        content = update.message.text
        content_type = "text"
    elif update.message.voice:
        content = update.message.voice.file_id
        content_type = "voice"
    else:
        await update.message.reply_text("Поддерживаются только текст и голосовые сообщения.")
        return

    # Генерим уникальный ID сообщения для реакций
    msg_id = generate_message_id()
    active_messages[msg_id] = {
        'content': content,
        'type': content_type,
        'author_id': user.id,
        'reactions': []
    }

    # Формируем подпись для админа
    sender_info = f"👤 Автор: {user_nicknames[user.id]} (@{user.username or '—'}) [ID: {user.id}]"
    message_logs.append((user.id, content))  # Логируем только обычные сообщения

    # Рассылаем ВСЕМ
    broadcast_text = f"📩 *Анонимное сообщение* [{msg_id}]\n{content}" if content_type == "text" \
        else f"📩 *Анонимное голосовое* [{msg_id}]"

    for chat_id in list(user_ids):
        try:
            if chat_id == ADMIN_ID:
                full_text = f"📩 *Анонимка* [{msg_id}]\n{sender_info}\n\n{content}" if content_type == "text" \
                    else f"📩 *Голосовое* [{msg_id}]\n{sender_info}"
                await context.bot.send_message(chat_id=chat_id, text=full_text, parse_mode="Markdown")
                if content_type == "voice":
                    await context.bot.send_voice(chat_id=chat_id, voice=content)
            else:
                await context.bot.send_message(chat_id=chat_id, text=broadcast_text, parse_mode="Markdown")
                if content_type == "voice":
                    await context.bot.send_voice(chat_id=chat_id, voice=content)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение {chat_id}: {e}")

    await update.message.reply_text(f"✅ Сообщение отправлено всем. ID: `{msg_id}`", parse_mode="Markdown")

# Обработка стикеров как реакций
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sticker = update.message.sticker

    # Проверяем, отвечает ли пользователь на сообщение бота
    if not update.message.reply_to_message or not update.message.reply_to_message.from_user.id == context.bot.id:
        return

    reply_text = update.message.reply_to_message.text
    if not reply_text:
        return

    # Извлекаем ID сообщения из текста (например, [ABC123])
    import re
    match = re.search(r'\[([A-Z0-9]{6})\]', reply_text)
    if not match:
        return

    msg_id = match.group(1)
    if msg_id not in active_messages:
        await update.message.reply_text("❌ Это сообщение слишком старое или не существует.")
        return

    # Добавляем реакцию
    reaction = {
        'user_id': user.id,
        'sticker_id': sticker.file_id,
        'emoji': sticker.emoji or "❓"
    }
    active_messages[msg_id]['reactions'].append(reaction)

    # Оповещаем всех о реакции (анонимно)
    reaction_text = f"💬 *Реакция* на сообщение [{msg_id}]: {reaction['emoji']}"
    for chat_id in list(user_ids):
        try:
            await context.bot.send_message(chat_id=chat_id, text=reaction_text, parse_mode="Markdown")
            await context.bot.send_sticker(chat_id=chat_id, sticker=sticker.file_id)
        except Exception as e:
            logger.error(f"Ошибка отправки реакции {chat_id}: {e}")

    await update.message.reply_text("✅ Реакция добавлена анонимно!")

# Команда /admin — личный кабинет админа
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Эта команда только для админа.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("📜 Последние 10 сообщений", callback_data='last10')],
        [InlineKeyboardButton("📥 Экспорт логов (txt)", callback_data='export')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔐 *Админ-панель*", reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stats':
        total_users = len(user_ids)
        total_messages = len(message_logs)  # Только обычные сообщения
        await query.edit_message_text(
            f"📊 *Статистика*\n"
            f"👥 Участников: {total_users}\n"
            f"💬 Сообщений: {total_messages}\n",
            parse_mode="Markdown"
        )

    elif query.data == 'last10':
        last_10 = message_logs[-10:]
        text = "📜 *Последние 10 сообщений:*\n\n"
        for uid, msg in last_10:
            nick = user_nicknames.get(uid, "Неизвестно")
            text += f"💬 — {nick}: {msg[:50]}...\n"
        await query.edit_message_text(text or "Нет сообщений", parse_mode="Markdown")

    elif query.data == 'export':
        if not message_logs:
            await query.edit_message_text("Нет данных для экспорта.")
            return
        filename = f"anon_chat_log_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Анонимный чат — лог сообщений\n")
            f.write("="*40 + "\n")
            for uid, msg in message_logs:
                nick = user_nicknames.get(uid, "???")
                line = f"ОБЫЧНОЕ | {nick} (ID:{uid}) : {msg}\n"
                f.write(line)
        await query.message.reply_document(document=open(filename, 'rb'))
        await query.edit_message_text("✅ Логи экспортированы.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 Чистый анонимный чат-бот (без #секрет) запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
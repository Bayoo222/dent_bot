# dent_bot.py

import logging
import sqlite3
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
from datetime import datetime
import random

# === Конфигурация ===
TOKEN = "7696464203:AAEeceaMsz36om3ayFf1OI3OooQuIU5MX0s"
HF_API_KEY = "hf_yiXHJcVgGElHAoknagufsiDerPyisexT"
ADMINS = [996386959]
DB_PATH = "dent_bot.db"

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === База данных ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        registered_at TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bonuses (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at) VALUES (?, ?, ?, ?)",
                   (user_id, username, first_name, datetime.now().isoformat()))
    cursor.execute("INSERT OR IGNORE INTO bonuses (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_user_bonus(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM bonuses WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_bonus(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE bonuses SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

# === Генерация статьи ===
async def generate_article_from_huggingface(api_key):
    prompts = [
        "🪥 Лайфхак по уходу за зубами: как чистить зубы 2 минуты и не заскучать?",
        "🍬 Правда ли, что сладкое разрушает зубы? Мифы и факты о питании и улыбке!",
        "😁 Секреты белоснежной улыбки: 3 простых совета от стоматолога",
        "😬 Боитесь стоматолога? Вот как перестать бояться визита к врачу!",
        "🦷 Электрическая или обычная щётка — что лучше? Разбираем плюсы и минусы!"
    ]
    prompt = random.choice(prompts)
    url = "https://api-inference.huggingface.co/models/bigscience/bloomz-560m"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 300}}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[0]["generated_text"].replace(prompt, "").strip()
                else:
                    logger.error(f"HuggingFace API error: {resp.status}")
                    return "⚠️ Ошибка генерации статьи."
        except Exception as e:
            logger.error(f"Ошибка генерации статьи: {e}")
            return "⚠️ Ошибка генерации статьи."

# === Рассылка статьи ===
async def scheduled_article(context):
    users = get_all_users()
    article = await generate_article_from_huggingface(HF_API_KEY)

    for user_id, _, _ in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=article)
        except Exception as e:
            logger.warning(f"Ошибка при отправке пользователю {user_id}: {e}")

# === Меню ===
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🦷 Услуги", callback_data="services")],
        [InlineKeyboardButton("🎁 Бонусы", callback_data="bonuses")],
        [InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📤 Рассылка статьи", callback_data="admin_article")],
        [InlineKeyboardButton("➕ Начислить бонусы", callback_data="choose_add_bonus")],
        [InlineKeyboardButton("➖ Списать бонусы", callback_data="choose_remove_bonus")]
    ]
    return InlineKeyboardMarkup(keyboard)

# === Хендлеры ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    if user.id in ADMINS:
        await update.message.reply_text("Привет, админ!", reply_markup=get_admin_menu())
    else:
        await update.message.reply_text("Привет! Добро пожаловать в наш бот.", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "services":
        await query.message.reply_text("🦷 Наши услуги: Чистка, имплантация, лечение.")
    elif query.data == "bonuses":
        bonus = get_user_bonus(query.from_user.id)
        await query.message.reply_text(f"🎁 Ваши бонусы: {bonus} баллов")
    elif query.data == "about":
        await query.message.reply_text("ℹ️ Мы — стоматологическая клиника.")
    elif query.data == "contacts":
        await query.message.reply_text("📞 Телефон: +7 999 123-45-67")
    elif query.data == "admin_users" and query.from_user.id in ADMINS:
        users = get_all_users()
        text = "👥 Список пользователей:\n" + "\n".join([f"{u[2]} (@{u[1]}) — {get_user_bonus(u[0])} бонусов" for u in users])
        await query.message.reply_text(text)
    elif query.data == "admin_article" and query.from_user.id in ADMINS:
        await query.message.reply_text("⏳ Генерация статьи...")
        await scheduled_article(context)
        await query.message.reply_text("✅ Статья разослана!")
    elif query.data in ["choose_add_bonus", "choose_remove_bonus"]:
        action = "add" if query.data == "choose_add_bonus" else "remove"
        context.user_data['bonus_action'] = action
        users = get_all_users()
        buttons = [InlineKeyboardButton(f"{u[2]} (@{u[1]})", callback_data=f"bonus_target_{u[0]}") for u in users]
        markup = InlineKeyboardMarkup.from_column(buttons)
        await query.message.reply_text("Выбери пользователя:", reply_markup=markup)
    elif query.data.startswith("bonus_target_"):
        user_id = int(query.data.split("_")[-1])
        context.user_data['target_user'] = user_id
        await query.message.reply_text("Введи количество бонусов (например: 50):")

async def bonus_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    try:
        amount = int(update.message.text.strip())
        user_id = context.user_data.get('target_user')
        action = context.user_data.get('bonus_action')
        if not user_id or not action:
            return
        update_bonus(user_id, amount if action == 'add' else -amount)
        await update.message.reply_text("✅ Готово!")
        await context.bot.send_message(chat_id=user_id, text=f"🔔 Ваши бонусы были {'начислены' if action == 'add' else 'списаны'}: {amount} баллов")
        context.user_data.clear()
    except:
        await update.message.reply_text("⚠️ Неверный формат. Введи просто число, например: 50")

# === Основной запуск ===
async def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(None, bonus_text_input))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: scheduled_article(app.bot), "interval", hours=48)
    scheduler.start()

    print("Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
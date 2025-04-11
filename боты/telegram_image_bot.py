import logging
import requests
from io import BytesIO
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from deep_translator import GoogleTranslator

# ВСТАВЬ СЮДА СВОЙ TELEGRAM ТОКЕН
TELEGRAM_TOKEN = "7658728324:AAGLB1QFCSNxYWNuOMfO7PU3FxV4hWd6lUQ"
HF_API_KEY = "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"
MODEL_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"

headers = {"Authorization": f"Bearer {HF_API_KEY}"}

# Перевод текста
def translate_to_english(text):
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated
    except Exception as e:
        print("Ошибка перевода:", e)
        return text

# Генерация изображения
def generate_image(prompt):
    try:
        response = requests.post(MODEL_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        print("Ошибка генерации изображения:", e)
        return None

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    translated_prompt = translate_to_english(user_prompt)
    
    await update.message.reply_text("🎨 Генерирую изображение...")

    image_bytes = generate_image(translated_prompt)

    if isinstance(image_bytes, bytes):
        image_file = BytesIO(image_bytes)
        image_file.name = "image.png"
        await update.message.reply_photo(photo=image_file)
    else:
        await update.message.reply_text("❌ Не удалось сгенерировать изображение. Попробуй ещё раз.")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """👋 Привет! Я - Telegram-бот, который генерирует изображения из текста.

Напиши описание, и я сгенерирую его для тебя.

Пример: кот в космосе на скейтборде 🚀"""

    menu_keyboard = [
        [KeyboardButton("🆘 Помощь"), KeyboardButton("ℹ️ Обо мне")],
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📌 Как пользоваться ботом:

1. Напиши описание картинки.
2. Я переведу его на английский.
3. Получишь изображение!

👉 Пример: девушка в стиле аниме под дождём

💡 Советы:
- Указывай стиль: "реализм", "аниме", "фэнтези"
- Чем подробнее — тем круче результат!"""
    await update.message.reply_text(help_text)

# Команда /about
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """🤖 Я — бот, который использует искусственный интеллект для генерации изображений по описанию.

🔍 Использую модель Stable Diffusion от Hugging Face.

📝 Просто опиши, что хочешь увидеть, и я нарисую это!"""
    await update.message.reply_text(about_text)

# Запуск
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()

import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI
from flask import Flask
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found!")
    sys.exit(1)
if not OPENROUTER_KEY:
    logger.error("OPENROUTER_API_KEY not found!")
    sys.exit(1)

logger.info("=== ЗАПУСК БОТА ===")
logger.info(f"Telegram token: {TELEGRAM_TOKEN[:10]}...")
logger.info(f"OpenRouter key: {OPENROUTER_KEY[:10]}...")

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Клиент OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# Flask приложение (только для health check)
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health():
    return "OK"

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info(f"Start from {message.from_user.id}")
    await message.answer("Привет! Я ИИ-помощник. Задавай любые вопросы на русском!")

@dp.message()
async def ask_ai(message: types.Message):
    logger.info(f"Message from {message.from_user.id}: {message.text[:50]}")
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        completion = client.chat.completions.create(
            model="meta-llama/llama-3-70b-instruct",
            messages=[
                {"role": "system", "content": "Ты — русскоязычный ИИ-помощник. Отвечай всегда на русском языке."},
                {"role": "user", "content": message.text}
            ],
            max_tokens=1000,
        )
        answer = completion.choices[0].message.content
        await message.answer(answer)
        logger.info(f"Response sent, length: {len(answer)}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже.")

# Запускаем Flask в отдельном потоке, а бота в основном
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

async def main():
    logger.info("Запуск aiogram бота...")
    # Запускаем Flask в отдельном потоке
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    # Запускаем бота в основном потоке asyncio
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

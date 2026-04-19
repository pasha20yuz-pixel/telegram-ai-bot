import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI
from flask import Flask
import threading

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found")
if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY not found")

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Клиент OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# Flask приложение для поддержания жизни сервиса
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health():
    return "OK"

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я ИИ-помощник. Задавай любые вопросы на русском!")

@dp.message()
async def ask_ai(message: types.Message):
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        completion = client.chat.completions.create(
            model="meta-llama/llama-3-70b-instruct",
            messages=[
                {"role": "system", "content": "Ты — русскоязычный ИИ-помощник. Отвечай всегда на русском языке, подробно и вежливо."},
                {"role": "user", "content": message.text}
            ],
            max_tokens=1000,
        )
        answer = completion.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже.")

# Запуск бота в отдельном потоке
def run_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    # Запускаем Flask для health check
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

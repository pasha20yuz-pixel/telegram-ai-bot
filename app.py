import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI
from collections import defaultdict
from flask import Flask
from threading import Thread

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ФЛASK ДЛЯ RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# === ТОКЕНЫ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Нет токена Telegram")
if not OPENROUTER_KEY:
    raise ValueError("Нет ключа OpenRouter")

# === ПАМЯТЬ ===
user_memory = defaultdict(list)
MAX_MEMORY = 20

# === БОТ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_memory[user_id] = []
    await message.answer(
        "🤖 Привет! Я ИИ-помощник с памятью!\n\n"
        "📝 Я запоминаю наши разговоры\n"
        "🧠 Доступные команды:\n"
        "/start - начать заново (очистить память)\n"
        "/clear - очистить историю диалога\n"
        "/help - показать команды"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📚 Доступные команды:\n\n"
        "/start - начать диалог заново\n"
        "/clear - очистить историю (забыть всё)\n"
        "/help - показать эту справку"
    )

@dp.message(Command("clear"))
async def clear_memory(message: types.Message):
    user_id = message.from_user.id
    user_memory[user_id] = []
    await message.answer("🗑️ История диалога очищена! Я всё забыл.")

# === ОСНОВНОЙ ОБРАБОТЧИК С ПАМЯТЬЮ ===
@dp.message()
async def ask_ai(message: types.Message):
    user_id = message.from_user.id
    
    # Добавляем сообщение пользователя в память
    user_memory[user_id].append({
        "role": "user",
        "content": message.text
    })
    
    # Ограничиваем размер памяти
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id] = user_memory[user_id][-MAX_MEMORY:]
    
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Формируем запрос с историей
        messages_for_api = [
            {"role": "system", "content": "Ты — русскоязычный ИИ-помощник. Отвечай всегда на русском языке, вежливо и полезно. Помни контекст нашего разговора."}
        ]
        
        # Добавляем историю
        for msg in user_memory[user_id]:
            messages_for_api.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        completion = client.chat.completions.create(
            model="meta-llama/llama-3-70b-instruct",
            messages=messages_for_api,
            max_tokens=1000,
            temperature=0.7
        )
        
        answer = completion.choices[0].message.content
        
        # Сохраняем ответ бота в память
        user_memory[user_id].append({
            "role": "assistant",
            "content": answer
        })
        
        await message.answer(answer)
        logger.info(f"User {user_id}: память содержит {len(user_memory[user_id])} сообщений")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("⚠️ Извините, произошла ошибка. Попробуйте позже.")

# === ЗАПУСК ===
async def main():
    # Принудительно удаляем вебхук (на случай, если был)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🤖 Бот с памятью запущен!")
    logger.info("Доступные команды: /start, /clear, /help")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    web_thread = Thread(target=run_web)
    web_thread.start()
    
    # Запускаем бота в основном потоке
    asyncio.run(main())

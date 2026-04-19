import asyncio
import os
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI
import aiohttp

# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === FLASK ДЛЯ RENDER ===
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
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Нет токена Telegram")
if not OPENROUTER_KEY:
    raise ValueError("Нет ключа OpenRouter")

# === ПАМЯТЬ ===
user_memory = defaultdict(list)
MAX_MEMORY = 20

# === НАПОМИНАНИЯ (временное хранилище) ===
reminders = defaultdict(list)

# === НАСТРОЙКИ МОДЕЛИ (только бесплатные) ===
current_model = "meta-llama/llama-3-70b-instruct"
available_models = {
    "llama3": "meta-llama/llama-3-70b-instruct",
    "gemini": "google/gemini-1.5-flash",
    "phi": "microsoft/phi-3-mini-4k-instruct",
    "mistral": "mistralai/mistral-7b-instruct"
}

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def get_weather(city: str):
    """Получает погоду для указанного города"""
    if not OPENWEATHER_KEY:
        return "❌ API ключ для погоды не настроен. Добавьте OPENWEATHER_API_KEY в переменные окружения Render."
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric&lang=ru"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                description = data['weather'][0]['description']
                humidity = data['main']['humidity']
                wind_speed = data['wind']['speed']
                
                return (
                    f"🌍 **Погода в {city}:**\n\n"
                    f"🌡️ Температура: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
                    f"☁️ {description.capitalize()}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind_speed} м/с"
                )
            elif response.status == 404:
                return f"❌ Город '{city}' не найден. Проверьте название."
            else:
                return f"❌ Ошибка получения погоды. Код ошибки: {response.status}"

async def translate_text(text: str, target_lang: str = "ru"):
    """Переводит текст на русский (использует LibreTranslate бесплатно)"""
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": "auto",
        "target": target_lang,
        "format": "text"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data['translatedText']
            else:
                return f"❌ Ошибка перевода. Попробуйте позже."

# === КОМАНДЫ ===

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_memory[user_id] = []
    await message.answer(
        "🤖 **Привет! Я ИИ-помощник с расширенными возможностями!**\n\n"
        "📝 **Основные команды:**\n"
        "/start - начать заново (очистить память)\n"
        "/clear - очистить историю диалога\n"
        "/help - показать все команды\n\n"
        "🌤️ **Погода:**\n"
        "/weather <город> - узнать погоду\n\n"
        "🌍 **Перевод:**\n"
        "/translate <текст> - перевести на русский\n\n"
        "⏰ **Напоминания:**\n"
        "/remind <время> <текст> - создать напоминание\n"
        "/reminders - показать мои напоминания\n\n"
        "🧠 **Настройки ИИ (бесплатные модели):**\n"
        "/model - показать текущую модель\n"
        "/model <название> - сменить модель\n\n"
        "💡 **Примеры:**\n"
        "`/weather Москва`\n"
        "`/translate Hello world`\n"
        "`/remind 15:30 Позвонить маме`\n"
        "`/model llama3`",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📚 **Полный список команд:**\n\n"
        "**Основные:**\n"
        "/start - начать диалог заново\n"
        "/clear - очистить историю\n"
        "/help - эта справка\n\n"
        "**Погода:**\n"
        "/weather <город> - погода в городе\n"
        "Пример: `/weather Санкт-Петербург`\n\n"
        "**Перевод:**\n"
        "/translate <текст> - перевод на русский\n"
        "Пример: `/translate Hello, how are you?`\n\n"
        "**Напоминания:**\n"
        "/remind <время> <текст> - создать напоминание\n"
        "/reminders - список напоминаний\n"
        "Пример: `/remind 14:30 Встреча с командой`\n\n"
        "**ИИ модели (бесплатные):**\n"
        "/model - текущая модель\n"
        "/model llama3 - Llama 3 (70B, рекомендуемая)\n"
        "/model gemini - Google Gemini 1.5 Flash\n"
        "/model phi - Microsoft Phi-3 Mini\n"
        "/model mistral - Mistral 7B",
        parse_mode="Markdown"
    )

@dp.message(Command("clear"))
async def clear_memory(message: types.Message):
    user_id = message.from_user.id
    user_memory[user_id] = []
    await message.answer("🗑️ История диалога очищена! Я всё забыл.")

# === ПОГОДА ===

@dp.message(Command("weather"))
async def weather_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("🌤️ **Как пользоваться:**\n`/weather Москва`\n`/weather Санкт-Петербург`", parse_mode="Markdown")
        return
    
    city = args[1].strip()
    status_msg = await message.answer(f"🔍 Ищу погоду в {city}...")
    weather_info = await get_weather(city)
    await status_msg.edit_text(weather_info, parse_mode="Markdown")

# === ПЕРЕВОД ===

@dp.message(Command("translate"))
async def translate_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("🌍 **Как пользоваться:**\n`/translate Hello world`\n\nПереведу любой текст на русский язык.", parse_mode="Markdown")
        return
    
    text_to_translate = args[1].strip()
    status_msg = await message.answer(f"🔄 Перевожу: `{text_to_translate[:50]}...`", parse_mode="Markdown")
    
    translated = await translate_text(text_to_translate)
    await status_msg.edit_text(
        f"🌍 **Перевод:**\n\n"
        f"📝 Исходный текст: `{text_to_translate[:200]}`\n\n"
        f"🇷🇺 Перевод: {translated}",
        parse_mode="Markdown"
    )

# === НАПОМИНАНИЯ ===

@dp.message(Command("remind"))
async def remind_command(message: types.Message):
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        await message.answer(
            "⏰ **Как пользоваться:**\n"
            "`/remind 15:30 Позвонить маме`\n"
            "`/remind 30м Полить цветы`\n\n"
            "Поддерживаемые форматы времени:\n"
            "- ЧЧ:ММ (время на сегодня)\n"
            "- 30м (через 30 минут)\n"
            "- 2ч (через 2 часа)",
            parse_mode="Markdown"
        )
        return
    
    time_str = args[1]
    reminder_text = args[2]
    user_id = message.from_user.id
    
    # Парсим время
    remind_time = None
    if time_str.endswith('м'):  # минуты
        minutes = int(time_str[:-1])
        remind_time = datetime.now() + timedelta(minutes=minutes)
    elif time_str.endswith('ч'):  # часы
        hours = int(time_str[:-1])
        remind_time = datetime.now() + timedelta(hours=hours)
    elif ':' in time_str:  # время HH:MM
        now = datetime.now()
        hours, minutes = map(int, time_str.split(':'))
        remind_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        if remind_time < now:
            remind_time += timedelta(days=1)
    else:
        await message.answer("❌ Неправильный формат времени. Используйте: `15:30`, `30м` или `2ч`", parse_mode="Markdown")
        return
    
    # Сохраняем напоминание
    reminders[user_id].append({
        "time": remind_time,
        "text": reminder_text,
        "created": datetime.now()
    })
    
    await message.answer(
        f"✅ Напоминание создано!\n\n"
        f"⏰ Время: {remind_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Текст: {reminder_text}"
    )

@dp.message(Command("reminders"))
async def list_reminders(message: types.Message):
    user_id = message.from_user.id
    
    if not reminders[user_id]:
        await message.answer("📭 У вас нет активных напоминаний.")
        return
    
    active_reminders = [r for r in reminders[user_id] if r["time"] > datetime.now()]
    
    if not active_reminders:
        await message.answer("📭 У вас нет активных напоминаний.")
        return
    
    response = "⏰ **Ваши напоминания:**\n\n"
    for i, r in enumerate(active_reminders, 1):
        response += f"{i}. {r['time'].strftime('%d.%m.%Y %H:%M')} - {r['text']}\n"
    
    await message.answer(response, parse_mode="Markdown")

# === СМЕНА МОДЕЛИ ===

@dp.message(Command("model"))
async def model_command(message: types.Message):
    global current_model
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        # Показываем текущую модель
        current_name = [name for name, model_id in available_models.items() if model_id == current_model]
        current_name = current_name[0] if current_name else "unknown"
        
        models_list = "\n".join([f"• {name}" for name in available_models.keys()])
        await message.answer(
            f"🧠 **Текущая модель:** `{current_name}`\n\n"
            f"📚 **Доступные бесплатные модели:**\n{models_list}\n\n"
            f"💡 **Сменить модель:** `/model llama3`\n\n"
            f"⭐ **Рекомендация:** llama3 (самая умная и быстрая)",
            parse_mode="Markdown"
        )
        return
    
    model_name = args[1].strip().lower()
    
    if model_name not in available_models:
        await message.answer(
            f"❌ Модель '{model_name}' не найдена.\n\n"
            f"Доступные модели: {', '.join(available_models.keys())}\n"
            f"Пример: `/model llama3`",
            parse_mode="Markdown"
        )
        return
    
    current_model = available_models[model_name]
    await message.answer(
        f"✅ Модель изменена на: `{model_name}`\n\n"
        f"🔧 ID модели: `{current_model}`\n\n"
        f"💡 Теперь я буду отвечать используя новую модель!",
        parse_mode="Markdown"
    )

# === ОСНОВНОЙ ОБРАБОТЧИК ===

@dp.message()
async def ask_ai(message: types.Message):
    user_id = message.from_user.id
    
    # Добавляем сообщение пользователя в память
    user_memory[user_id].append({
        "role": "user",
        "content": message.text
    })
    
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id] = user_memory[user_id][-MAX_MEMORY:]
    
    # Проверяем напоминания (упрощенно)
    if user_id in reminders:
        now = datetime.now()
        due_reminders = [r for r in reminders[user_id] if r["time"] <= now]
        for r in due_reminders:
            await message.answer(f"⏰ **Напоминание:** {r['text']}\n(создано в {r['created'].strftime('%H:%M')})")
            reminders[user_id].remove(r)
    
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        
        messages_for_api = [
            {"role": "system", "content": "Ты — русскоязычный ИИ-помощник. Отвечай всегда на русском языке, вежливо и полезно. Помни контекст нашего разговора."}
        ]
        
        for msg in user_memory[user_id]:
            messages_for_api.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        completion = client.chat.completions.create(
            model=current_model,
            messages=messages_for_api,
            max_tokens=1000,
            temperature=0.7
        )
        
        answer = completion.choices[0].message.content
        
        user_memory[user_id].append({
            "role": "assistant",
            "content": answer
        })
        
        await message.answer(answer)
        logger.info(f"User {user_id}: память={len(user_memory[user_id])}, модель={current_model}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("⚠️ Извините, произошла ошибка. Попробуйте позже или смените модель через /model")

# === ЗАПУСК ===

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🤖 Бот с расширенными командами запущен!")
    logger.info(f"Текущая модель: {current_model}")
    logger.info("Доступные команды: /start, /clear, /help, /weather, /translate, /remind, /reminders, /model")
    await dp.start_polling(bot)

if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.start()
    asyncio.run(main())

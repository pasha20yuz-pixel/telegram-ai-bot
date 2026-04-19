import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from openai import OpenAI

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ИЗ ФАЙЛА .env (ЭТОЙ СТРОКИ НЕ ХВАТАЕТ!)
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена Telegram из переменной окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Telegram bot token not found in environment variables.")

# Получение API-ключа OpenRouter из переменной окружения
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OpenRouter API key not found in environment variables.")

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализация клиента OpenAI (OpenRouter)
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

# Контекст диалога (для простоты - один контекст на пользователя)
user_contexts = {}


async def get_llm_response(prompt, user_id):
    """
    Отправляет запрос в LLM и возвращает ответ.
    """
    model="meta-llama/llama-3-70b-instruct"  # Выберите подходящую модель
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    user_contexts[user_id].append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=user_contexts[user_id],
            max_tokens=1024,
        )

        response_text = completion.choices[0].message.content

        user_contexts[user_id].append({"role": "assistant", "content": response_text})
        # Ограничиваем контекст до последних нескольких сообщений (например, 5)
        user_contexts[user_id] = user_contexts[user_id][-5:]
        return response_text
    except Exception as e:
        logging.error(f"Ошибка при запросе к LLM: {e}")
        return "Произошла ошибка при обработке запроса. Попробуйте позже."


# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Этот обработчик запускается, когда пользователь отправляет команду `/start`
    """
    await message.answer(
        f"Привет, {message.from_user.first_name}!\nЯ бот, который может общаться с вами через LLM.",
    )


# Обработчик команды /help
@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """
    Этот обработчик запускается, когда пользователь отправляет команду `/help`
    """
    await message.answer(
        "Я бот для общения с LLM.\n"
        "Просто отправьте мне сообщение, и я попробую на него ответить.\n"
        "Команды:\n"
        "/start - Начать работу\n"
        "/help - Получить помощь",
    )


# Обработчик текстовых сообщений
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Этот обработчик обрабатывает все текстовые сообщения, отправленные боту.
    """
    user_id = message.from_user.id
    prompt = message.text
    response = await get_llm_response(prompt, user_id)
    await message.answer(response)


async def main() -> None:
    """
    Запуск бота.
    """
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

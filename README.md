# Telegram LLM Assistant 🤖

A Telegram bot that provides access to Large Language Models through the OpenRouter API.

The project combines an asynchronous Telegram interface with external APIs and utility features such as weather, translation and reminders.

## Features

- 💬 Chat with LLMs through Telegram
- 🧠 Conversation context and user memory
- 🔄 Switch between available LLM models
- 🌤️ Weather information
- 🌍 Text translation
- ⏰ Personal reminders
- ❤️ Health check endpoint
- 🐳 Docker support
- 🔐 Configuration through environment variables
- 🧹 Automated code formatting and linting with pre-commit

## Tech Stack

- **Python 3.11+**
- **aiogram** — Telegram Bot API
- **OpenAI SDK** — communication with OpenRouter
- **aiohttp** — asynchronous HTTP requests
- **Flask** — health check endpoint
- **Docker** — containerization
- **pre-commit** — code quality automation

## Architecture

The application consists of two main components:

- Telegram bot — handles user commands and conversations
- HTTP health endpoint — allows the deployment platform to monitor application availability

External services:

```text
Telegram
   ↓
Telegram Bot
   ↓
Python / aiogram
   ↓
OpenRouter API
   ↓
Large Language Model
```

## Additional integrations:

## Telegram Bot
```text
 ├── OpenRouter
 ├── OpenWeather
 └── LibreTranslate
```
# Setup
## 1. Clone the repository
```bash
git clone https://github.com/pasha20yuz-pixel/telegram-ai-bot.git
cd telegram-ai-bot
```
## 2. Create environment variables

Copy .env.example to .env:
```bash
cp .env.example .env
```
Then add your API keys:
```text
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```
## 3. Install dependencies
```bash
pip install -r requirements.txt
```
## 4. Run the application
```bash
python app.py
```
## Docker

Build the image:
```bash
docker build -t telegram-llm-bot .
```
Run the container:
```bash
docker run -d \
  --name telegram-llm-bot \
  --env-file .env \
  telegram-llm-bot
```
## Code Quality

The project uses pre-commit to automate code quality checks.

Install it with:
```bash
pip install pre-commit
pre-commit install
```
## Project Goals

This project was created as a practical Python project for working with:

- asynchronous programming;
- external APIs;
- LLM integrations;
- environment configuration;
- Docker;
- code quality tools.
## Future Improvements
- Persistent database for user data
- Better separation of application modules
- Automated tests
- CI/CD pipeline
- Improved error handling
- Structured logging

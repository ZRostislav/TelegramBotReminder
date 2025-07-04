import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from datetime import datetime
from aiohttp import web
from config import BOT_TOKEN, CHAT_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

scheduler = AsyncIOScheduler()
tz = timezone('Europe/Chisinau')  # Для Бендер / ПМР

DATA_FILE = "database.json"

# Загрузка / сохранение базы
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"poll_id": None, "answers": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# 📤 Отправка опроса
async def send_poll():
    data = load_data()
    msg = await bot.send_poll(
        chat_id=CHAT_ID,
        question="Ты будешь на служении завтра?",
        options=["Да", "Нет"],
        is_anonymous=False
    )
    data["poll_id"] = msg.poll.id
    data["answers"] = {}
    save_data(data)

    # Пинг всех участников
    await bot.send_message(chat_id=CHAT_ID, text="@all Пожалуйста, ответьте на опрос выше 🙏")

# 💬 Обработка ответа
@dp.poll_answer_handler()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    data = load_data()
    data["answers"][str(poll_answer.user.id)] = {
        "name": poll_answer.user.full_name,
        "option_ids": poll_answer.option_ids
    }
    save_data(data)

# 📣 Пинг в воскресенье
async def sunday_ping():
    data = load_data()
    answers = data.get("answers", {})

    non_respondents = []
    answered_yes = []

    try:
        # async for member in bot.iter_chat_members(CHAT_ID): — работает не во всех случаях, 
        # поэтому можно убрать или использовать только админов, если есть ограничения
        # Но оставим для примера так:
        async for member in bot.iter_chat_members(CHAT_ID):
            user = member.user
            if user.is_bot:
                continue
            uid = str(user.id)

            if uid not in answers:
                non_respondents.append(f"@{user.username}" if user.username else user.full_name)
            elif answers[uid]["option_ids"] == [0]:  # "Да"
                answered_yes.append(f"@{user.username}" if user.username else user.full_name)

    except Exception as e:
        await bot.send_message(CHAT_ID, f"Ошибка при сборе пользователей: {e}")
        return

    msg = "⛪ Доброе утро!\n"
    if answered_yes:
        msg += "✅ Кто собирался быть: " + ", ".join(answered_yes) + "\n"
    if non_respondents:
        msg += "❗ Кто не ответил: " + ", ".join(non_respondents)

    await bot.send_message(CHAT_ID, msg)

# ⏰ Планировщик
scheduler.add_job(send_poll, 'cron', day_of_week='sat', hour=18, minute=0, timezone=tz)
scheduler.add_job(sunday_ping, 'cron', day_of_week='sun', hour=8, minute=0, timezone=tz)

# --- HTTP сервер ---
async def handle(request):
    return web.Response(text="Бот работает!")

async def start_web_app():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("HTTP сервер запущен на порту 8000")

# 🔁 Запуск планировщика и HTTP-сервера в контексте aiogram
async def on_startup(dispatcher):
    scheduler.start()
    asyncio.create_task(start_web_app())  # Запускаем HTTP сервер в фоне

# 🚀 Запуск
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

# main.py
import json
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, CHAT_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

DATA_FILE = "database.json"

# Создаём JSON-хранилище
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"poll_id": None, "answers": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Отправка опроса
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

    # Пингуем всех
    await bot.send_message(chat_id=CHAT_ID, text="@all Пожалуйста, ответьте на опрос выше 🙏")

# Сохраняем ответы на опрос
@dp.poll_answer_handler()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    data = load_data()
    data["answers"][poll_answer.user.id] = {
        "name": poll_answer.user.full_name,
        "option_ids": poll_answer.option_ids
    }
    save_data(data)

# Утренний пинг
async def sunday_ping():
    data = load_data()
    non_respondents = []
    answered_yes = []

    chat = await bot.get_chat(chat_id=CHAT_ID)
    members = data["answers"]

    async for member in bot.iter_chat_members(chat.id):
        user_id = member.user.id
        if user_id not in members:
            non_respondents.append(f"@{member.user.username or member.user.full_name}")
        elif members[user_id]["option_ids"] == [0]:  # 0 = "Да"
            answered_yes.append(f"@{member.user.username or member.user.full_name}")

    message = "⛪ Доброе утро!\n"
    if answered_yes:
        message += "✅ Кто собирался быть: " + ", ".join(answered_yes) + "\n"
    if non_respondents:
        message += "❗ Кто не ответил: " + ", ".join(non_respondents)
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Планируем задачи
scheduler.add_job(send_poll, 'cron', day_of_week='sat', hour=18, minute=0)
scheduler.add_job(sunday_ping, 'cron', day_of_week='sun', hour=8, minute=0)

# Запуск
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)

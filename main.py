import json
import logging
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from datetime import datetime
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
        members = await bot.get_chat_administrators(CHAT_ID)
        all_user_ids = set()

        # Получаем участников, у которых есть username
        async for member in bot.iter_chat_members(CHAT_ID):
            user = member.user
            if user.is_bot:
                continue
            all_user_ids.add(user.id)
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

# 🔁 Запуск планировщика в контексте aiogram
async def on_startup(dispatcher):
    scheduler.start()

# 🚀 Запуск
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

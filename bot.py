import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, PollAnswer
from aiogram.utils.markdown import hlink
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

scheduler = AsyncIOScheduler()
responses = {}
poll_message_id = None
participants = set()

@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Бот запущен. Жду субботу 😊")
    
@dp.message(F.text == "/id")
async def show_chat_id(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")
    
@dp.message(F.text == "/debug")
async def verify_chat(message: Message):
    if message.chat.id == CHAT_ID:
        await message.answer("✅ Бот работает в этом чате.")
    else:
        await message.answer("⛔ Это не тот чат. Бот здесь не работает.")



@dp.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer):
    user_id = poll_answer.user.id
    answer = "Да" if poll_answer.option_ids[0] == 0 else "Нет"
    responses[user_id] = answer
    participants.add(user_id)

async def send_poll():
    global responses, participants, poll_message_id
    responses = {}
    participants = set()

    poll_message = await bot.send_poll(
        chat_id=CHAT_ID,
        question="Ты будешь завтра на Собрании?",
        options=["Да", "Нет"],
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    poll_message_id = poll_message.message_id
    print("✅ Опрос отправлен!")

async def send_reminder():
    mention_list = []

    answered_yes = [uid for uid, answer in responses.items() if answer == "Да"]
    not_answered = participants - set(responses.keys())

    if not answered_yes:
        mention_list = list(participants)
    else:
        mention_list = answered_yes + list(not_answered)

    if mention_list:
        mentions = [hlink("👤", f"tg://user?id={uid}") for uid in mention_list]
        await bot.send_message(CHAT_ID, "Напоминание о собрании! 📣\n" + " ".join(mentions))

async def show_chat_id(message: Message):
    await message.answer(f"CHAT_ID: {message.chat.id}")

dp.message.register(show_chat_id)

def setup_scheduler():
    scheduler.add_job(send_poll, "cron", day_of_week="sat", hour=10, minute=0)
    scheduler.add_job(send_reminder, "cron", day_of_week="sun", hour=9, minute=0)
    scheduler.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    setup_scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

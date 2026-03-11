import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import os

from keyboards import main_keyboard, stats_keyboard
from sleep_logic import calculate_sleep
import database

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("sleep.db")
cursor = conn.cursor()


@dp.message(CommandStart())
async def start(message: Message):
    text = """
👋 Welcome to Sleep Tracker Bot!

Use the buttons below:

🌙 Bed — record when you go to sleep
☀️ Wake — record when you wake up
📊 Stats — see sleep stats for 7 and 30 days

Sleep well 😴
"""
    await message.answer(text, reply_markup=main_keyboard)


@dp.message(lambda message: message.text == "🌙 Bed")
async def bed(message: Message):
    user = message.from_user.id

    cursor.execute("SELECT status FROM sleep WHERE user_id=? AND status='sleeping'", (user,))
    result = cursor.fetchone()

    if result:
        await message.answer(
            "🌙 Your bedtime is already recorded.\nPress ☀️ Wake when you wake up 😌"
        )
        return

    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO sleep (user_id, bed_time, status) VALUES (?, ?, 'sleeping')",
        (user, now)
    )
    conn.commit()

    time_str = datetime.now().strftime("%H:%M")

    await message.answer(
        f"🌙 Good night!\nBed time recorded: {time_str}\nSleep well 😴"
    )


@dp.message(lambda message: message.text == "☀️ Wake")
async def wake(message: Message):
    user = message.from_user.id

    cursor.execute(
        "SELECT id, bed_time FROM sleep WHERE user_id=? AND status='sleeping'",
        (user,)
    )

    row = cursor.fetchone()

    if not row:
        await message.answer(
            "🤔 I don’t see a bedtime record yet.\nPress 🌙 Bed first."
        )
        return

    record_id, bed_time = row
    wake_time = datetime.now().isoformat()

    minutes, score, comment = calculate_sleep(bed_time, wake_time)

    duration_h = minutes // 60
    duration_m = minutes % 60

    bed_str = datetime.fromisoformat(bed_time).strftime("%H:%M")
    wake_str = datetime.now().strftime("%H:%M")

    cursor.execute(
        """UPDATE sleep
        SET wake_time=?, duration=?, score=?, status='done'
        WHERE id=?""",
        (wake_time, minutes, score, record_id)
    )
    conn.commit()

    text = f"""
☀️ Good morning!

Sleep summary:

🌙 Fell asleep: {bed_str}
☀️ Woke up: {wake_str}
⏳ Duration: {duration_h}h {duration_m}m
⭐ Sleep score: {score}/10
💬 Comment: {comment}
"""
    await message.answer(text, reply_markup=main_keyboard)


@dp.message(lambda message: message.text == "📊 Stats")
async def stats(message: Message):
    await message.answer("📊 Choose a stats period:", reply_markup=stats_keyboard)


def get_stats(user, days):
    since = datetime.now() - timedelta(days=days)

    cursor.execute(
        """SELECT duration, score FROM sleep
        WHERE user_id=? AND status='done' AND wake_time>?""",
        (user, since.isoformat())
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    total = len(rows)
    avg_duration = sum(r[0] for r in rows) // total
    avg_score = sum(r[1] for r in rows) / total

    h = avg_duration // 60
    m = avg_duration % 60

    if avg_score >= 9:
        stats_comment = "Excellent sleep pattern 😄"
    elif avg_score >= 8:
        stats_comment = "Very solid sleep 😌"
    elif avg_score >= 7:
        stats_comment = "Not bad, but could be better 🙂"
    elif avg_score >= 6:
        stats_comment = "Your sleep needs improvement 😕"
    else:
        stats_comment = "You should really get more balanced sleep 😵"

    return total, h, m, round(avg_score, 1), stats_comment


@dp.message(lambda message: message.text == "📅 7 Days")
async def stats7(message: Message):
    data = get_stats(message.from_user.id, 7)

    if not data:
        await message.answer(
            "📅 No sleep data found for the last 7 days.\nStart by pressing 🌙 Bed tonight 😴"
        )
        return

    total, h, m, score, comment = data

    text = f"""
📅 Sleep report for the last 7 days

🛌 Total sleeps: {total}
⏳ Average duration: {h}h {m}m
⭐ Average score: {score}/10
💬 Comment: {comment}
"""
    await message.answer(text)


@dp.message(lambda message: message.text == "🗓 30 Days")
async def stats30(message: Message):
    data = get_stats(message.from_user.id, 30)

    if not data:
        await message.answer(
            "🗓 No sleep data found for the last 30 days.\nTrack some sleep first 🌙"
        )
        return

    total, h, m, score, comment = data

    text = f"""
🗓 Sleep report for the last 30 days

🛌 Total sleeps: {total}
⏳ Average duration: {h}h {m}m
⭐ Average score: {score}/10
💬 Comment: {comment}
"""
    await message.answer(text)


@dp.message(lambda message: message.text == "⬅️ Back")
async def back(message: Message):
    await message.answer("Back to main menu.", reply_markup=main_keyboard)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

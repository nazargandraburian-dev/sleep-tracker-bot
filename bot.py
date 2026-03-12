import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import os

from keyboards import main_keyboard, stats_keyboard, language_keyboard
from sleep_logic import calculate_sleep
from translations import translations
import database

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("sleep.db")
cursor = conn.cursor()


def ensure_user_exists(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()


def get_user_language(user_id: int) -> str:
    ensure_user_exists(user_id)
    cursor.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "en"


def set_user_language(user_id: int, language: str):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
    conn.commit()


def get_user_streak(user_id: int) -> int:
    ensure_user_exists(user_id)
    cursor.execute("SELECT streak FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


def set_user_streak(user_id: int, streak: int):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET streak=? WHERE user_id=?", (streak, user_id))
    conn.commit()


def update_streak(user_id: int, bed_time_str: str, sleep_minutes: int):
    bed_time = datetime.fromisoformat(bed_time_str)

    duration_ok = sleep_minutes >= 450  # 7.5 hours

    # streak идет, если лег не позже 00:00
    # считаем нормальным время с 18:00 до 23:59 или ровно 00:00
    bedtime_ok = (
        (18 <= bed_time.hour <= 23)
        or (bed_time.hour == 0 and bed_time.minute == 0)
    )

    current_streak = get_user_streak(user_id)

    if duration_ok and bedtime_ok:
        new_streak = current_streak + 1
        set_user_streak(user_id, new_streak)
        return True, new_streak
    else:
        set_user_streak(user_id, 0)
        return False, 0


def t(user_id: int, key: str) -> str:
    lang = get_user_language(user_id)
    return translations.get(lang, translations["en"]).get(key, key)


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    await message.answer(t(user_id, "start_text"), reply_markup=main_keyboard)


@dp.message(lambda message: message.text == "🌙 Bed")
async def bed(message: Message):
    user = message.from_user.id

    cursor.execute(
        "SELECT status FROM sleep WHERE user_id=? AND status='sleeping'",
        (user,)
    )
    result = cursor.fetchone()

    if result:
        await message.answer(t(user, "bed_already"))
        return

    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO sleep (user_id, bed_time, status) VALUES (?, ?, 'sleeping')",
        (user, now)
    )
    conn.commit()

    time_str = datetime.now().strftime("%H:%M")

    await message.answer(
        t(user, "good_night").format(time=time_str),
        reply_markup=main_keyboard
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
        await message.answer(t(user, "wake_missing"))
        return

    record_id, bed_time = row
    wake_time = datetime.now().isoformat()

    minutes, score, comment = calculate_sleep(bed_time, wake_time)

    duration_h = minutes // 60
    duration_m = minutes % 60

    bed_str = datetime.fromisoformat(bed_time).strftime("%H:%M")
    wake_str = datetime.now().strftime("%H:%M")

    cursor.execute(
        """
        UPDATE sleep
        SET wake_time=?, duration=?, score=?, status='done'
        WHERE id=?
        """,
        (wake_time, minutes, score, record_id)
    )
    conn.commit()

    streak_ok, streak_days = update_streak(user, bed_time, minutes)

    text = t(user, "good_morning").format(
        bed=bed_str,
        wake=wake_str,
        hours=duration_h,
        minutes=duration_m,
        score=score,
        comment=comment
    )

    if streak_ok:
        text += "\n\n" + t(user, "streak_active").format(days=streak_days)
    else:
        text += "\n\n" + t(user, "streak_ended")

    await message.answer(text, reply_markup=main_keyboard)


@dp.message(lambda message: message.text == "📊 Stats")
async def stats(message: Message):
    await message.answer(
        t(message.from_user.id, "stats_choose"),
        reply_markup=stats_keyboard
    )


def get_stats(user, days):
    since = datetime.now() - timedelta(days=days)

    cursor.execute(
        """
        SELECT duration, score FROM sleep
        WHERE user_id=? AND status='done' AND wake_time>?
        """,
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
    user_id = message.from_user.id
    data = get_stats(user_id, 7)

    if not data:
        await message.answer(t(user_id, "stats_7_empty"))
        return

    total, h, m, score, comment = data

    text = (
        f"{t(user_id, 'stats_7_title')}\n\n"
        + t(user_id, "stats_body").format(
            total=total,
            hours=h,
            minutes=m,
            score=score,
            comment=comment
        )
    )

    await message.answer(text)


@dp.message(lambda message: message.text == "🗓 30 Days")
async def stats30(message: Message):
    user_id = message.from_user.id
    data = get_stats(user_id, 30)

    if not data:
        await message.answer(t(user_id, "stats_30_empty"))
        return

    total, h, m, score, comment = data

    text = (
        f"{t(user_id, 'stats_30_title')}\n\n"
        + t(user_id, "stats_body").format(
            total=total,
            hours=h,
            minutes=m,
            score=score,
            comment=comment
        )
    )

    await message.answer(text)


@dp.message(lambda message: message.text == "🌐 Language")
async def language_menu(message: Message):
    await message.answer(
        t(message.from_user.id, "language_choose"),
        reply_markup=language_keyboard
    )


@dp.message(lambda message: message.text == "🇬🇧 English")
async def set_english(message: Message):
    set_user_language(message.from_user.id, "en")
    await message.answer(
        translations["en"]["language_changed_en"],
        reply_markup=main_keyboard
    )


@dp.message(lambda message: message.text == "🇷🇺 Русский")
async def set_russian(message: Message):
    set_user_language(message.from_user.id, "ru")
    await message.answer(
        translations["ru"]["language_changed_ru"],
        reply_markup=main_keyboard
    )


@dp.message(lambda message: message.text == "🇺🇦 Українська")
async def set_ukrainian(message: Message):
    set_user_language(message.from_user.id, "uk")
    await message.answer(
        translations["uk"]["language_changed_uk"],
        reply_markup=main_keyboard
    )


@dp.message(lambda message: message.text == "⬅️ Back")
async def back(message: Message):
    await message.answer(
        t(message.from_user.id, "back_main"),
        reply_markup=main_keyboard
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

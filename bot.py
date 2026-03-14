# FULL FIXED BOT WITH TIMEZONE SUPPORT

import asyncio
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
import os

from keyboards import (
    get_main_keyboard,
    get_stats_keyboard,
    get_settings_keyboard,
    get_language_keyboard,
    get_timezone_keyboard,
    all_button_values,
)

from sleep_logic import calculate_sleep
from translations import translations
from database import conn, cursor

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

tf = TimezoneFinder()
scheduler = AsyncIOScheduler()

MIN_VALID_SLEEP_MINUTES = 90


def ensure_user_exists(user_id: int):
    cursor.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )


def get_user_language(user_id: int):
    ensure_user_exists(user_id)
    cursor.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "en"


def get_user_timezone(user_id: int):
    ensure_user_exists(user_id)
    cursor.execute("SELECT timezone FROM users WHERE user_id=%s", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "UTC"


def get_user_tzinfo(user_id: int):
    try:
        return ZoneInfo(get_user_timezone(user_id))
    except Exception:
        return ZoneInfo("UTC")


def t(user_id: int, key: str, **kwargs):
    lang = get_user_language(user_id)
    text = translations.get(lang, translations["en"]).get(key, key)
    return text.format(**kwargs)


def parse_dt(dt):
    if isinstance(dt, datetime):
        return dt
    return datetime.fromisoformat(dt)


def now_for_user(user_id: int):
    return datetime.now(get_user_tzinfo(user_id))


def format_hhmm(dt):
    return dt.strftime("%H:%M")


@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    ensure_user_exists(user_id)

    lang = get_user_language(user_id)

    await message.answer(
        t(user_id, "start_text"),
        reply_markup=get_main_keyboard(lang),
    )


@dp.message(F.text.in_(all_button_values("bed")))
async def bed(message: Message):

    user_id = message.from_user.id
    lang = get_user_language(user_id)

    cursor.execute(
        "SELECT id FROM sleep WHERE user_id=%s AND status='sleeping'",
        (user_id,),
    )

    if cursor.fetchone():

        await message.answer(
            t(user_id, "bed_already"),
            reply_markup=get_main_keyboard(lang),
        )
        return

    now = now_for_user(user_id)

    cursor.execute(
        "INSERT INTO sleep (user_id, bed_time, status) VALUES (%s,%s,'sleeping')",
        (user_id, now),
    )

    await message.answer(
        t(user_id, "good_night", time=format_hhmm(now)),
        reply_markup=get_main_keyboard(lang),
    )


@dp.message(F.text.in_(all_button_values("wake")))
async def wake(message: Message):

    user_id = message.from_user.id
    lang = get_user_language(user_id)

    cursor.execute(
        "SELECT id, bed_time FROM sleep WHERE user_id=%s AND status='sleeping'",
        (user_id,),
    )

    row = cursor.fetchone()

    if not row:

        await message.answer(
            t(user_id, "wake_missing"),
            reply_markup=get_main_keyboard(lang),
        )
        return

    record_id, bed_time = row

    wake_time = now_for_user(user_id)

    minutes, score, comment = calculate_sleep(
        bed_time.isoformat(),
        wake_time.isoformat(),
    )

    duration_h = minutes // 60
    duration_m = minutes % 60

    tz = get_user_tzinfo(user_id)

    bed_dt = parse_dt(bed_time).astimezone(tz)
    wake_dt = parse_dt(wake_time).astimezone(tz)

    cursor.execute(
        """
        UPDATE sleep
        SET wake_time=%s, duration=%s, score=%s, status='done'
        WHERE id=%s
        """,
        (wake_time, minutes, score, record_id),
    )

    await message.answer(
        t(
            user_id,
            "good_morning",
            bed=format_hhmm(bed_dt),
            wake=format_hhmm(wake_dt),
            hours=duration_h,
            minutes=duration_m,
            score=score,
            comment=comment,
        ),
        reply_markup=get_main_keyboard(lang),
    )


@dp.message(F.text.in_(all_button_values("stats")))
async def stats(message: Message):

    lang = get_user_language(message.from_user.id)

    await message.answer(
        "📊 Choose period",
        reply_markup=get_stats_keyboard(lang),
    )


@dp.message(F.text.in_(all_button_values("settings")))
async def settings(message: Message):

    lang = get_user_language(message.from_user.id)

    await message.answer(
        "⚙️ Settings",
        reply_markup=get_settings_keyboard(lang),
    )


async def main():
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

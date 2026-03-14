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


def set_user_language(user_id: int, lang: str):
    ensure_user_exists(user_id)
    cursor.execute(
        "UPDATE users SET language=%s WHERE user_id=%s",
        (lang, user_id),
    )


def get_user_timezone(user_id: int):
    ensure_user_exists(user_id)
    cursor.execute("SELECT timezone FROM users WHERE user_id=%s", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "UTC"


def set_user_timezone(user_id: int, tz: str):
    ensure_user_exists(user_id)
    cursor.execute(
        "UPDATE users SET timezone=%s WHERE user_id=%s",
        (tz, user_id),
    )


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


def circular_mean_minutes(values):
    if not values:
        return 0

    angles = [2 * math.pi * (v / 1440) for v in values]

    sin_sum = sum(math.sin(a) for a in angles)
    cos_sum = sum(math.cos(a) for a in angles)

    mean_angle = math.atan2(sin_sum, cos_sum)

    if mean_angle < 0:
        mean_angle += 2 * math.pi

    return int(round(mean_angle * 1440 / (2 * math.pi)))


def minutes_to_hhmm(m):
    h = m // 60
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def get_records_for_period(user_id, days):
    tz = get_user_tzinfo(user_id)

    since = datetime.now(tz) - timedelta(days=days)

    cursor.execute(
        """
        SELECT bed_time, wake_time, duration, score
        FROM sleep
        WHERE user_id=%s AND status='done'
        ORDER BY wake_time DESC
        """,
        (user_id,),
    )

    rows = cursor.fetchall()

    result = []

    for bed, wake, duration, score in rows:

        if not wake:
            continue

        wake_dt = parse_dt(wake).astimezone(tz)

        if wake_dt < since:
            continue

        if duration < MIN_VALID_SLEEP_MINUTES:
            continue

        result.append((bed, wake, duration, score))

    return result


def get_stats(user_id, days):

    rows = get_records_for_period(user_id, days)

    if not rows:
        return None

    tz = get_user_tzinfo(user_id)

    bed_values = []
    wake_values = []

    durations = []
    scores = []

    for bed, wake, duration, score in rows:

        bed_dt = parse_dt(bed).astimezone(tz)
        wake_dt = parse_dt(wake).astimezone(tz)

        bed_values.append(bed_dt.hour * 60 + bed_dt.minute)
        wake_values.append(wake_dt.hour * 60 + wake_dt.minute)

        durations.append(duration)
        scores.append(score)

    avg_duration = round(sum(durations) / len(durations))
    avg_score = round(sum(scores) / len(scores), 1)

    avg_bed = minutes_to_hhmm(circular_mean_minutes(bed_values))
    avg_wake = minutes_to_hhmm(circular_mean_minutes(wake_values))

    return {
        "total": len(rows),
        "avg_bed": avg_bed,
        "avg_wake": avg_wake,
        "avg_duration": avg_duration,
        "avg_score": avg_score,
    }


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


async def main():
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

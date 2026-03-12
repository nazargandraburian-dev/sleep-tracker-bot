import asyncio
import math
import sqlite3
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
    main_keyboard,
    stats_keyboard,
    settings_keyboard,
    language_keyboard,
    timezone_keyboard
)
from sleep_logic import calculate_sleep
from translations import translations
import database

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("sleep.db")
cursor = conn.cursor()

tf = TimezoneFinder()
scheduler = AsyncIOScheduler()


def ensure_user_exists(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()


def get_user_language(user_id: int) -> str:
    ensure_user_exists(user_id)
    cursor.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else "en"


def set_user_language(user_id: int, language: str):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
    conn.commit()


def get_user_timezone(user_id: int) -> str:
    ensure_user_exists(user_id)
    cursor.execute("SELECT timezone FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else "UTC"


def set_user_timezone(user_id: int, timezone_name: str):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET timezone=? WHERE user_id=?", (timezone_name, user_id))
    conn.commit()


def get_user_tzinfo(user_id: int) -> ZoneInfo:
    try:
        return ZoneInfo(get_user_timezone(user_id))
    except Exception:
        return ZoneInfo("UTC")


def get_user_streak(user_id: int) -> int:
    ensure_user_exists(user_id)
    cursor.execute("SELECT streak FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


def set_user_streak(user_id: int, streak: int):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET streak=? WHERE user_id=?", (streak, user_id))
    conn.commit()


def get_last_weekly_report(user_id: int):
    ensure_user_exists(user_id)
    cursor.execute("SELECT last_weekly_report FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def set_last_weekly_report(user_id: int, week_key: str):
    ensure_user_exists(user_id)
    cursor.execute("UPDATE users SET last_weekly_report=? WHERE user_id=?", (week_key, user_id))
    conn.commit()


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_language(user_id)
    text = translations.get(lang, translations["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def parse_dt(dt_str: str) -> datetime:
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def now_for_user(user_id: int) -> datetime:
    return datetime.now(get_user_tzinfo(user_id))


def format_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def circular_mean_minutes(values: list[int]) -> int:
    if not values:
        return 0

    angles = [2 * math.pi * (v / 1440) for v in values]
    sin_sum = sum(math.sin(a) for a in angles)
    cos_sum = sum(math.cos(a) for a in angles)

    mean_angle = math.atan2(sin_sum, cos_sum)
    if mean_angle < 0:
        mean_angle += 2 * math.pi

    return int(round(mean_angle * 1440 / (2 * math.pi))) % 1440


def minutes_to_hhmm(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def sleep_comment_from_score(user_id: int, score: int) -> str:
    if score >= 10:
        return t(user_id, "comment_10")
    if score >= 9:
        return t(user_id, "comment_9")
    if score >= 8:
        return t(user_id, "comment_8")
    if score >= 7:
        return t(user_id, "comment_7")
    if score >= 6:
        return t(user_id, "comment_6")
    if score >= 4:
        return t(user_id, "comment_4")
    return t(user_id, "comment_2")


def stats_comment_from_score(user_id: int, avg_score: float) -> str:
    if avg_score >= 9:
        return t(user_id, "stats_comment_9")
    if avg_score >= 8:
        return t(user_id, "stats_comment_8")
    if avg_score >= 7:
        return t(user_id, "stats_comment_7")
    if avg_score >= 6:
        return t(user_id, "stats_comment_6")
    return t(user_id, "stats_comment_4")


def get_records_for_period(user_id: int, days: int):
    now_local = now_for_user(user_id)
    since = now_local - timedelta(days=days)

    cursor.execute(
        """
        SELECT bed_time, wake_time, duration, score
        FROM sleep
        WHERE user_id=? AND status='done'
        ORDER BY wake_time DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    filtered = []

    for bed_time, wake_time, duration, score in rows:
        if not wake_time:
            continue

        wake_dt = parse_dt(wake_time)
        if wake_dt >= since.astimezone(wake_dt.tzinfo):
            filtered.append((bed_time, wake_time, duration, score))

    return filtered


def get_sleep_animal(user_id: int, days: int):
    rows = get_records_for_period(user_id, days)

    if not rows:
        return None, None

    bed_minutes = []
    short_sleep = 0
    late_bed = 0

    for bed_time, _, duration, _ in rows:
        bed_dt = parse_dt(bed_time)
        mins = bed_dt.hour * 60 + bed_dt.minute
        bed_minutes.append(mins)

        if duration < 420:
            short_sleep += 1

        if 0 <= bed_dt.hour < 4:
            late_bed += 1

    spread = max(bed_minutes) - min(bed_minutes) if bed_minutes else 0

    if late_bed >= 4 and short_sleep >= 3:
        return t(user_id, "animal_wolf_name"), t(user_id, "animal_wolf_reason")

    if late_bed >= 4:
        return t(user_id, "animal_owl_name"), t(user_id, "animal_owl_reason")

    if spread >= 240 or short_sleep >= 4:
        return t(user_id, "animal_dolphin_name"), t(user_id, "animal_dolphin_reason")

    return t(user_id, "animal_bear_name"), t(user_id, "animal_bear_reason")


def get_stats(user_id: int, days: int):
    rows = get_records_for_period(user_id, days)

    if not rows:
        return None

    total = len(rows)
    avg_duration = round(sum(r[2] for r in rows) / total)
    avg_score = round(sum(r[3] for r in rows) / total, 1)

    bed_values = []
    wake_values = []

    for bed_time, wake_time, _, _ in rows:
        bed_dt = parse_dt(bed_time)
        wake_dt = parse_dt(wake_time)

        bed_values.append(bed_dt.hour * 60 + bed_dt.minute)
        wake_values.append(wake_dt.hour * 60 + wake_dt.minute)

    avg_bed = minutes_to_hhmm(circular_mean_minutes(bed_values))
    avg_wake = minutes_to_hhmm(circular_mean_minutes(wake_values))

    hours = avg_duration // 60
    minutes = avg_duration % 60
    comment = stats_comment_from_score(user_id, avg_score)

    return {
        "total": total,
        "avg_bed": avg_bed,
        "avg_wake": avg_wake,
        "hours": hours,
        "minutes": minutes,
        "score": avg_score,
        "comment": comment
    }


def build_stats_text(user_id: int, days: int, title_key: str, include_streak: bool = False):
    data = get_stats(user_id, days)
    if not data:
        return None

    text = (
        f"{t(user_id, title_key)}\n\n"
        + t(
            user_id,
            "stats_body",
            total=data["total"],
            avg_bed=data["avg_bed"],
            avg_wake=data["avg_wake"],
            hours=data["hours"],
            minutes=data["minutes"],
            score=data["score"],
            comment=data["comment"]
        )
    )

    if include_streak:
        text += "\n" + t(user_id, "current_streak", days=get_user_streak(user_id))

    animal_name, animal_reason = get_sleep_animal(user_id, days)
    if animal_name and animal_reason:
        text += "\n\n" + t(user_id, "animal_title", animal=animal_name)
        text += "\n" + animal_reason

    return text


def update_streak(user_id: int, bed_time_str: str, sleep_minutes: int):
    bed_time = parse_dt(bed_time_str)
    duration_ok = sleep_minutes >= 450  # 7.5 hours

    bedtime_ok = (
        (18 <= bed_time.hour <= 23)
        or (bed_time.hour == 0 and bed_time.minute == 0)
    )

    current_streak = get_user_streak(user_id)

    if duration_ok and bedtime_ok:
        new_streak = current_streak + 1
        set_user_streak(user_id, new_streak)
        return True, new_streak

    set_user_streak(user_id, 0)
    return False, 0


async def send_weekly_reports():
    cursor.execute("SELECT user_id FROM users")
    user_rows = cursor.fetchall()

    for (user_id,) in user_rows:
        tz = get_user_tzinfo(user_id)
        now_local = datetime.now(tz)

        if not (now_local.weekday() == 6 and now_local.hour == 15 and 0 <= now_local.minute < 5):
            continue

        iso = now_local.isocalendar()
        week_key = f"{iso.year}-W{iso.week}"

        if get_last_weekly_report(user_id) == week_key:
            continue

        text = build_stats_text(user_id, 7, "weekly_title", include_streak=True)
        if text:
            try:
                await bot.send_message(user_id, text, reply_markup=main_keyboard)
                set_last_weekly_report(user_id, week_key)
            except Exception:
                pass


@scheduler.scheduled_job("interval", minutes=1)
async def scheduled_weekly_reports():
    await send_weekly_reports()


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    await message.answer(t(user_id, "start_text"), reply_markup=main_keyboard)


@dp.message(F.text == "🌙 Bed")
async def bed(message: Message):
    user_id = message.from_user.id

    cursor.execute(
        "SELECT status FROM sleep WHERE user_id=? AND status='sleeping'",
        (user_id,)
    )
    result = cursor.fetchone()

    if result:
        await message.answer(t(user_id, "bed_already"), reply_markup=main_keyboard)
        return

    now_local = now_for_user(user_id)

    cursor.execute(
        "INSERT INTO sleep (user_id, bed_time, status) VALUES (?, ?, 'sleeping')",
        (user_id, now_local.isoformat())
    )
    conn.commit()

    await message.answer(
        t(user_id, "good_night", time=format_hhmm(now_local)),
        reply_markup=main_keyboard
    )


@dp.message(F.text == "☀️ Wake")
async def wake(message: Message):
    user_id = message.from_user.id

    cursor.execute(
        "SELECT id, bed_time FROM sleep WHERE user_id=? AND status='sleeping'",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        await message.answer(t(user_id, "wake_missing"), reply_markup=main_keyboard)
        return

    record_id, bed_time = row
    wake_time = now_for_user(user_id).isoformat()

    minutes, score, _ = calculate_sleep(bed_time, wake_time)
    comment = sleep_comment_from_score(user_id, score)

    duration_h = minutes // 60
    duration_m = minutes % 60

    bed_dt = parse_dt(bed_time)
    wake_dt = parse_dt(wake_time)

    cursor.execute(
        """
        UPDATE sleep
        SET wake_time=?, duration=?, score=?, status='done'
        WHERE id=?
        """,
        (wake_time, minutes, score, record_id)
    )
    conn.commit()

    streak_ok, streak_days = update_streak(user_id, bed_time, minutes)

    text = t(
        user_id,
        "good_morning",
        bed=format_hhmm(bed_dt),
        wake=format_hhmm(wake_dt),
        hours=duration_h,
        minutes=duration_m,
        score=score,
        comment=comment
    )

    if streak_ok:
        text += "\n\n" + t(user_id, "streak_active", days=streak_days)
    else:
        text += "\n\n" + t(user_id, "streak_ended")

    await message.answer(text, reply_markup=main_keyboard)


@dp.message(F.text == "📊 Stats")
async def stats(message: Message):
    await message.answer(
        t(message.from_user.id, "stats_choose"),
        reply_markup=stats_keyboard
    )


@dp.message(F.text == "📅 7 Days")
async def stats7(message: Message):
    user_id = message.from_user.id
    text = build_stats_text(user_id, 7, "stats_7_title")

    if not text:
        await message.answer(t(user_id, "stats_7_empty"), reply_markup=stats_keyboard)
        return

    await message.answer(text, reply_markup=stats_keyboard)


@dp.message(F.text == "🗓 30 Days")
async def stats30(message: Message):
    user_id = message.from_user.id
    text = build_stats_text(user_id, 30, "stats_30_title")

    if not text:
        await message.answer(t(user_id, "stats_30_empty"), reply_markup=stats_keyboard)
        return

    await message.answer(text, reply_markup=stats_keyboard)


@dp.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message):
    await message.answer(
        t(message.from_user.id, "settings_choose"),
        reply_markup=settings_keyboard
    )


@dp.message(F.text == "🌐 Language")
async def language_menu(message: Message):
    await message.answer(
        t(message.from_user.id, "language_choose"),
        reply_markup=language_keyboard
    )


@dp.message(F.text == "🕓 Timezone")
async def timezone_menu(message: Message):
    await message.answer(
        t(message.from_user.id, "timezone_choose") + "\n\n" + t(message.from_user.id, "timezone_request"),
        reply_markup=timezone_keyboard
    )


@dp.message(F.location)
async def save_location_timezone(message: Message):
    user_id = message.from_user.id
    location = message.location

    timezone_name = tf.timezone_at(lat=location.latitude, lng=location.longitude)

    if not timezone_name:
        await message.answer(t(user_id, "timezone_failed"), reply_markup=settings_keyboard)
        return

    set_user_timezone(user_id, timezone_name)

    await message.answer(
        t(user_id, "timezone_updated", timezone=timezone_name),
        reply_markup=settings_keyboard
    )


@dp.message(F.text == "🇬🇧 English")
async def set_english(message: Message):
    set_user_language(message.from_user.id, "en")
    await message.answer(t(message.from_user.id, "language_changed"), reply_markup=settings_keyboard)


@dp.message(F.text == "🇷🇺 Русский")
async def set_russian(message: Message):
    set_user_language(message.from_user.id, "ru")
    await message.answer(t(message.from_user.id, "language_changed"), reply_markup=settings_keyboard)


@dp.message(F.text == "🇺🇦 Українська")
async def set_ukrainian(message: Message):
    set_user_language(message.from_user.id, "uk")
    await message.answer(t(message.from_user.id, "language_changed"), reply_markup=settings_keyboard)


@dp.message(F.text == "⬅️ Back")
async def back(message: Message):
    await message.answer(t(message.from_user.id, "back_main"), reply_markup=main_keyboard)


async def main():
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

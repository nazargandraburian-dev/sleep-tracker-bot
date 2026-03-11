from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌙 Bed")],
        [KeyboardButton(text="☀️ Wake")],
        [KeyboardButton(text="📊 Stats")]
    ],
    resize_keyboard=True
)

stats_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 7 Days")],
        [KeyboardButton(text="🗓 30 Days")],
        [KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

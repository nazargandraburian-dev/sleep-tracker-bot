from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌙 Bed")],
        [KeyboardButton(text="☀️ Wake")],
        [KeyboardButton(text="📊 Stats")],
        [KeyboardButton(text="🌐 Language")]
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

language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇬🇧 English")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇺🇦 Українська")],
        [KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

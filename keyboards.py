from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌙 Bed"), KeyboardButton(text="☀️ Wake")],
        [KeyboardButton(text="📊 Stats"), KeyboardButton(text="⚙️ Settings")]
    ],
    resize_keyboard=True
)

stats_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 7 Days"), KeyboardButton(text="🗓 30 Days")],
        [KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

settings_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌐 Language"), KeyboardButton(text="🕓 Timezone")],
        [KeyboardButton(text="🗑 Reset Data")],
        [KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇺🇦 Українська"), KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

timezone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Use my current location", request_location=True)],
        [KeyboardButton(text="⬅️ Back")]
    ],
    resize_keyboard=True
)

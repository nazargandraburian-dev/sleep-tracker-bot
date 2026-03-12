from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BUTTONS = {
    "en": {
        "bed": "🌙 Bed",
        "wake": "☀️ Wake",
        "stats": "📊 Stats",
        "settings": "⚙️ Settings",
        "language": "🌐 Language",
        "timezone": "🕓 Timezone",
        "reset": "🗑 Reset Data",
        "back": "⬅️ Back",
        "stats_7": "📅 7 Days",
        "stats_30": "🗓 30 Days",
        "lang_en": "🇬🇧 English",
        "lang_ru": "🇷🇺 Russian",
        "lang_uk": "🇺🇦 Ukrainian",
        "location": "📍 Use my current location",
    },
    "ru": {
        "bed": "🌙 Сон",
        "wake": "☀️ Подъём",
        "stats": "📊 Статистика",
        "settings": "⚙️ Настройки",
        "language": "🌐 Язык",
        "timezone": "🕓 Часовой пояс",
        "reset": "🗑 Сбросить данные",
        "back": "⬅️ Назад",
        "stats_7": "📅 7 дней",
        "stats_30": "🗓 30 дней",
        "lang_en": "🇬🇧 English",
        "lang_ru": "🇷🇺 Русский",
        "lang_uk": "🇺🇦 Українська",
        "location": "📍 Отправить мою локацию",
    },
    "uk": {
        "bed": "🌙 Сон",
        "wake": "☀️ Пробудження",
        "stats": "📊 Статистика",
        "settings": "⚙️ Налаштування",
        "language": "🌐 Мова",
        "timezone": "🕓 Часовий пояс",
        "reset": "🗑 Скинути дані",
        "back": "⬅️ Назад",
        "stats_7": "📅 7 днів",
        "stats_30": "🗓 30 днів",
        "lang_en": "🇬🇧 English",
        "lang_ru": "🇷🇺 Русский",
        "lang_uk": "🇺🇦 Українська",
        "location": "📍 Надіслати мою локацію",
    }
}


def get_labels(lang: str):
    return BUTTONS.get(lang, BUTTONS["en"])


def all_button_values(key: str):
    return {BUTTONS[lang][key] for lang in BUTTONS}


def get_main_keyboard(lang: str):
    b = get_labels(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b["bed"]), KeyboardButton(text=b["wake"])],
            [KeyboardButton(text=b["stats"]), KeyboardButton(text=b["settings"])],
        ],
        resize_keyboard=True
    )


def get_stats_keyboard(lang: str):
    b = get_labels(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b["stats_7"]), KeyboardButton(text=b["stats_30"])],
            [KeyboardButton(text=b["back"])],
        ],
        resize_keyboard=True
    )


def get_settings_keyboard(lang: str):
    b = get_labels(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b["language"]), KeyboardButton(text=b["timezone"])],
            [KeyboardButton(text=b["reset"])],
            [KeyboardButton(text=b["back"])],
        ],
        resize_keyboard=True
    )


def get_language_keyboard(lang: str):
    b = get_labels(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b["lang_en"]), KeyboardButton(text=b["lang_ru"])],
            [KeyboardButton(text=b["lang_uk"]), KeyboardButton(text=b["back"])],
        ],
        resize_keyboard=True
    )


def get_timezone_keyboard(lang: str):
    b = get_labels(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b["location"], request_location=True)],
            [KeyboardButton(text=b["back"])],
        ],
        resize_keyboard=True
    )

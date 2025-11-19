# requirements:
# pip install python-telegram-bot==20.5

import asyncio
import logging
import os
import random
import string
from datetime import datetime, timedelta

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)
from telegram.constants import ChatMemberStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ВАЖНО: установи переменную окружения BOT_TOKEN или замени ниже строку на токен
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8512545163:AAFs8-3E4-1KA8yjQ8j_jVx-DwMvO9l1eDc")

# Настройки канала (ЗАМЕНИ НА СВОЙ КАНАЛ)
CHANNEL_USERNAME = "@pocoyoipa"  # Замени на username своего канала

# Путь к картинкам
IMAGE_PATHS = [
    "IMG_6482.png",
    "IMG_6483.png",
    "IMG_6489.png",
]

# База данных аккаунтов
ACCOUNTS_DATABASE = {
    "AyuGram": [
        {"email": "ayugram_user1@demo.com", "password": "AyU123!pass", "available": True},
        {"email": "ayugram_user2@demo.com", "password": "AyU456!pass", "available": True},
        {"email": "ayugram_user3@demo.com", "password": "AyU789!pass", "available": True},
    ],
    "OnionGram": [
        {"email": "onion_user1@demo.com", "password": "OnI123!pass", "available": True},
        {"email": "onion_user2@demo.com", "password": "OnI456!pass", "available": True},
        {"email": "onion_user3@demo.com", "password": "OnI789!pass", "available": True},
    ],
    "DarkGram": [
        {"email": "dark_user1@demo.com", "password": "DrK123!pass", "available": True},
        {"email": "dark_user2@demo.com", "password": "DrK456!pass", "available": True},
        {"email": "dark_user3@demo.com", "password": "DrK789!pass", "available": True},
    ],
    "TikTok BH": [
        {"email": "tiktok_user1@demo.com", "password": "TkK123!pass", "available": True},
        {"email": "tiktok_user2@demo.com", "password": "TkK456!pass", "available": True},
        {"email": "tiktok_user3@demo.com", "password": "TkK789!pass", "available": True},
    ],
    "DoxGram": [
        {"email": "dox_user1@demo.com", "password": "DxG123!pass", "available": True},
        {"email": "dox_user2@demo.com", "password": "DxG456!pass", "available": True},
        {"email": "dox_user3@demo.com", "password": "DxG789!pass", "available": True},
    ],
    "Minecraft": [
        {"email": "minecraft_user1@demo.com", "password": "McR123!pass", "available": True},
        {"email": "minecraft_user2@demo.com", "password": "McR456!pass", "available": True},
        {"email": "minecraft_user3@demo.com", "password": "McR789!pass", "available": True},
    ],
    "Прочий мод": [
        {"email": "mod_user1@demo.com", "password": "MdM123!pass", "available": True},
        {"email": "mod_user2@demo.com", "password": "MdM456!pass", "available": True},
        {"email": "mod_user3@demo.com", "password": "MdM789!pass", "available": True},
    ]
}

# Список моделей iPhone
MODEL_ROWS = [
    ["13", "13 Pro", "13 Pro Max"],
    ["14", "14 Pro", "14 Pro Max"],
    ["15", "15 Pro", "15 Pro Max"],
    ["16", "16 Pro", "16 Pro Max"],
]

# Список программ
PROGRAM_ROWS = [
    ["AyuGram", "OnionGram", "DarkGram"],
    ["TikTok BH", "DoxGram", "Minecraft"],
    ["Прочий мод"]
]

# В памяти - хранение выданных "учёток"
SESSIONS = {}

# Хранение выбранных устройств пользователями
USER_SELECTIONS = {}


def make_models_keyboard():
    keyboard = []
    for row in MODEL_ROWS:
        keyboard.append([InlineKeyboardButton(text=m, callback_data=f"model|{m}") for m in row])
    return InlineKeyboardMarkup(keyboard)


def make_programs_keyboard():
    keyboard = []
    for row in PROGRAM_ROWS:
        keyboard.append([InlineKeyboardButton(text=program, callback_data=f"program|{program}") for program in row])
    return InlineKeyboardMarkup(keyboard)


def make_session_buttons(message_id):
    kb = [
        [
            InlineKeyboardButton("❌ Отозвать аккаунт", callback_data=f"revoke|{message_id}"),
            InlineKeyboardButton("⏱️ Таймер", callback_data=f"timer|{message_id}"),
        ]
    ]
    return InlineKeyboardMarkup(kb)


def make_subscription_keyboard():
    """Клавиатура для подписки на канал"""
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_available_account(program_name):
    """Получает доступный аккаунт для программы"""
    if program_name not in ACCOUNTS_DATABASE:
        return None
    
    available_accounts = [acc for acc in ACCOUNTS_DATABASE[program_name] if acc["available"]]
    if not available_accounts:
        return None
    
    # Берем первый доступный аккаунт
    account = available_accounts[0]
    account["available"] = False
    return account


def release_account(program_name, email):
    """Освобождает аккаунт"""
    if program_name not in ACCOUNTS_DATABASE:
        return
    
    for account in ACCOUNTS_DATABASE[program_name]:
        if account["email"] == email:
            account["available"] = True
            break


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, подписан ли пользователь на канал
    """
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, 
            user_id=user_id
        )
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.MEMBER
        ]
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False


async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает сообщение с требованием подписки
    """
    message_text = (
        "📢 *Для использования бота необходимо подписаться на наш канал!*\n\n"
        f"Канал: {CHANNEL_USERNAME}\n\n"
        "После подписки нажми кнопку '✅ Я подписался'"
    )
    
    await update.message.reply_text(
        message_text,
        reply_markup=make_subscription_keyboard(),
        parse_mode='Markdown'
    )


async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопки проверки подписки
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if await check_subscription(user_id, context):
        # Если подписан - показываем основное меню
        chat_id = query.message.chat_id
        caption = "📱 Выберите модель вашего iPhone:\n(На модель ниже 13 установить нельзя — в демо показано)"
        
        try:
            with open(IMAGE_PATHS[0], "rb") as f:
                await context.bot.send_photo(
                    chat_id=chat_id, 
                    photo=f, 
                    caption=caption, 
                    reply_markup=make_models_keyboard()
                )
        except Exception as e:
            logger.exception("Не удалось отправить картинку: %s", e)
            await context.bot.send_message(
                chat_id=chat_id, 
                text=caption, 
                reply_markup=make_models_keyboard()
            )
        
        # Удаляем сообщение с требованием подписки
        await query.message.delete()
    else:
        # Если не подписан - показываем сообщение снова
        await query.edit_message_text(
            "❌ *Ты еще не подписан на канал!*\n\n"
            f"Канал: {CHANNEL_USERNAME}\n\n"
            "Подпишись и нажми кнопку '✅ Я подписался'",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """При /start проверяем подписку и показываем изображение с клавиатурой выбора модели."""
    user_id = update.effective_user.id
    
    # Проверяем подписку на канал
    if not await check_subscription(user_id, context):
        await require_subscription(update, context)
        return
    
    # Если подписан - показываем основное меню
    chat_id = update.effective_chat.id
    caption = "📱 Выберите модель вашего iPhone:\n(На модель ниже 13 установить нельзя — в демо показано)"
    
    try:
        with open(IMAGE_PATHS[0], "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id, 
                photo=f, 
                caption=caption, 
                reply_markup=make_models_keyboard()
            )
    except Exception as e:
        logger.exception("Не удалось отправить картинку: %s", e)
        await context.bot.send_message(
            chat_id=chat_id, 
            text=caption, 
            reply_markup=make_models_keyboard()
        )


async def model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор модели и переходим к выбору программы"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем подписку
    user_id = query.from_user.id
    if not await check_subscription(user_id, context):
        await query.edit_message_text(
            "❌ *Для использования бота необходимо подписаться на канал!*\n\n"
            f"Канал: {CHANNEL_USERNAME}",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    data = query.data  # "model|13"
    _, model = data.split("|", 1)
    
    # Сохраняем выбор модели пользователя
    USER_SELECTIONS[user_id] = {"model": model}
    
    # Показываем выбор программы
    await query.edit_message_caption(
        caption=f"📱 Выбрана модель: *{model}*\n\n🎮 Теперь выберите программу:",
        reply_markup=make_programs_keyboard(),
        parse_mode='Markdown'
    )


async def program_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор программы и выдаем аккаунт"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем подписку
    if not await check_subscription(user_id, context):
        await query.edit_message_text(
            "❌ *Для получения данных необходимо подписаться на канал!*\n\n"
            f"Канал: {CHANNEL_USERNAME}",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    data = query.data  # "program|AyuGram"
    _, program = data.split("|", 1)
    
    # Получаем выбранную ранее модель
    user_selection = USER_SELECTIONS.get(user_id, {})
    model = user_selection.get("model", "Неизвестно")
    
    # Получаем доступный аккаунт
    account = get_available_account(program)
    
    if not account:
        await query.edit_message_caption(
            caption=f"❌ *Извините!*\n\nДля программы *{program}* временно нет доступных аккаунтов.\n\nПопробуйте позже или выберите другую программу.",
            reply_markup=make_programs_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Устанавливаем время истечения
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Отправляем сообщение с данными аккаунта
    text = (
        f"🎯 *Данные для входа*\n\n"
        f"📱 Модель: {model}\n"
        f"🛠️ Программа: {program}\n\n"
        f"📧 Email: `{account['email']}`\n"
        f"🔑 Пароль: `{account['password']}`\n\n"
        f"⏰ У вас есть 10 минут на установку (до {expires_at.strftime('%H:%M:%S')} UTC).\n"
        "Если вы не используете эти данные, они автоматически станут неактивными."
    )

    sent = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        parse_mode="Markdown",
    )

    # Сохраняем сессию
    message_id = sent.message_id
    SESSIONS[message_id] = {
        "email": account['email'],
        "password": account['password'],
        "program": program,
        "model": model,
        "expires_at": expires_at,
        "revoked": False,
        "chat_id": query.message.chat_id,
        "user_id": user_id,
        "message_id": message_id,
    }

    # Добавляем кнопки управления
    await context.bot.edit_message_reply_markup(
        chat_id=query.message.chat_id, 
        message_id=message_id, 
        reply_markup=make_session_buttons(message_id)
    )

    # Запускаем таймер
    asyncio.create_task(session_countdown(context, message_id))


async def session_countdown(context: ContextTypes.DEFAULT_TYPE, message_id: int):
    """Задача: следит за сроком и по истечении отмечает сессию неактивной."""
    session = SESSIONS.get(message_id)
    if not session:
        return
    
    now = datetime.utcnow()
    until = (session["expires_at"] - now).total_seconds()
    if until > 0:
        await asyncio.sleep(until)

    # После сна проверяем состояние
    session = SESSIONS.get(message_id)
    if not session:
        return
    
    if not session["revoked"]:
        session["revoked"] = True
        # Освобождаем аккаунт
        release_account(session["program"], session["email"])
        
        chat_id = session["chat_id"]
        try:
            edit_text = "🔒 Сессия истекла — эти данные больше не действительны."
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=edit_text
            )
        except Exception:
            logger.exception("Не удалось отредактировать сообщение при окончании таймера.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline кнопок"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Обработка проверки подписки
    if data == "check_subscription":
        await subscription_callback(update, context)
        return

    # Обработка выбора модели
    if data.startswith("model|"):
        await model_selected(update, context)
        return

    # Обработка выбора программы
    if data.startswith("program|"):
        await program_selected(update, context)
        return

    # Обработка управления сессией
    if data.startswith("revoke|") or data.startswith("timer|"):
        action, mid = data.split("|", 1)
        try:
            message_id = int(mid)
        except ValueError:
            await query.edit_message_text("Ошибка: неверный идентификатор сессии.")
            return

        session = SESSIONS.get(message_id)
        if not session:
            await query.edit_message_text("Сессии не найдено или она уже удалена.")
            return

        if action == "revoke":
            if session["revoked"]:
                await query.edit_message_text("⚠️ Сессия уже была отозвана или истекла.")
                return
            session["revoked"] = True
            # Освобождаем аккаунт
            release_account(session["program"], session["email"])
            try:
                await context.bot.edit_message_text(
                    chat_id=session["chat_id"],
                    message_id=message_id,
                    text="❌ Аккаунт отозван. Данные больше не действительны."
                )
            except Exception:
                logger.exception("Не удалось отредактировать сообщение при отзыве.")
        elif action == "timer":
            if session["revoked"]:
                await query.edit_message_text("Сессия уже отозвана/истекла.")
                return
            remaining = session["expires_at"] - datetime.utcnow()
            secs = int(remaining.total_seconds())
            if secs <= 0:
                await query.edit_message_text("⏰ Время вышло — сессия истекла.")
                session["revoked"] = True
                release_account(session["program"], session["email"])
                return
            mins, sec = divmod(secs, 60)
            await query.edit_message_text(f"⏱️ Осталось времени: {mins} мин {sec} сек.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Запускаем бота с базой данных аккаунтов...")
    app.run_polling()


if __name__ == "__main__":
    main()

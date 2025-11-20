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

# Модератор для помощи
MODERATOR_USERNAME = "@kattyshechk"

# Путь к картинкам для каждого этапа
IMAGE_PATHS = {
    "stage1": "stage1_welcome.png",  # Этап 1: Приветствие и выбор модели
    "stage2": "stage2_programs.png",  # Этап 2: Выбор программы
    "stage3": "stage3_credentials.png",  # Этап 3: Выдача данных
}

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

# Хранение message_id для очистки
USER_MESSAGES = {}


def make_models_keyboard():
    keyboard = []
    for row in MODEL_ROWS:
        keyboard.append([InlineKeyboardButton(text=m, callback_data=f"model|{m}") for m in row])
    keyboard.append([InlineKeyboardButton("🆘 Помощь", url=f"https://t.me/{MODERATOR_USERNAME[1:]}")])
    return InlineKeyboardMarkup(keyboard)


def make_programs_keyboard():
    keyboard = []
    for row in PROGRAM_ROWS:
        keyboard.append([InlineKeyboardButton(text=program, callback_data=f"program|{program}") for program in row])
    keyboard.append([InlineKeyboardButton("🆘 Помощь", url=f"https://t.me/{MODERATOR_USERNAME[1:]}")])
    return InlineKeyboardMarkup(keyboard)


def make_session_buttons(message_id):
    kb = [
        [
            InlineKeyboardButton("❌ Отозвать аккаунт", callback_data=f"revoke|{message_id}"),
            InlineKeyboardButton("⏱️ Таймер", callback_data=f"timer|{message_id}"),
        ],
        [InlineKeyboardButton("🆘 Помощь", url=f"https://t.me/{MODERATOR_USERNAME[1:]}")]
    ]
    return InlineKeyboardMarkup(kb)


def make_subscription_keyboard():
    """Клавиатура для подписки на канал"""
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")],
        [InlineKeyboardButton("🆘 Помощь", url=f"https://t.me/{MODERATOR_USERNAME[1:]}")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def cleanup_user_messages(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Очищает предыдущие сообщения бота для пользователя"""
    if chat_id in USER_MESSAGES:
        for msg_id in USER_MESSAGES[chat_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
        USER_MESSAGES[chat_id] = []


async def add_user_message(chat_id: int, message_id: int):
    """Добавляет message_id в список сообщений пользователя"""
    if chat_id not in USER_MESSAGES:
        USER_MESSAGES[chat_id] = []
    USER_MESSAGES[chat_id].append(message_id)


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
    chat_id = update.effective_chat.id
    await cleanup_user_messages(chat_id, context)
    
    message_text = (
        "📢 *Для использования бота необходимо подписаться на наш канал!*\n\n"
        f"Канал: {CHANNEL_USERNAME}\n\n"
        "После подписки нажми кнопку '✅ Я подписался'\n\n"
        f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
    )
    
    sent = await update.message.reply_text(
        message_text,
        reply_markup=make_subscription_keyboard(),
        parse_mode='Markdown'
    )
    await add_user_message(chat_id, sent.message_id)


async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопки проверки подписки
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    if await check_subscription(user_id, context):
        # Если подписан - показываем основное меню
        await cleanup_user_messages(chat_id, context)
        
        caption = (
            "🎯 *ЭТАП 1: ВЫБОР МОДЕЛИ УСТРОЙСТВА*\n\n"
            "📱 Выберите модель вашего iPhone:\n"
            "(На модель ниже 13 установить нельзя — в демо показано)\n\n"
            f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
        )
        
        try:
            with open(IMAGE_PATHS["stage1"], "rb") as f:
                sent = await context.bot.send_photo(
                    chat_id=chat_id, 
                    photo=f, 
                    caption=caption, 
                    reply_markup=make_models_keyboard(),
                    parse_mode='Markdown'
                )
                await add_user_message(chat_id, sent.message_id)
        except Exception as e:
            logger.exception("Не удалось отправить картинку: %s", e)
            sent = await context.bot.send_message(
                chat_id=chat_id, 
                text=caption, 
                reply_markup=make_models_keyboard(),
                parse_mode='Markdown'
            )
            await add_user_message(chat_id, sent.message_id)
        
        # Удаляем сообщение с требованием подписки
        await query.message.delete()
    else:
        # Если не подписан - показываем сообщение снова
        await query.edit_message_text(
            "❌ *Ты еще не подписан на канал!*\n\n"
            f"Канал: {CHANNEL_USERNAME}\n\n"
            "Подпишись и нажми кнопку '✅ Я подписался'\n\n"
            f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """При /start проверяем подписку и показываем изображение с клавиатурой выбора модели."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Очищаем предыдущие сообщения
    await cleanup_user_messages(chat_id, context)
    
    # Проверяем подписку на канал
    if not await check_subscription(user_id, context):
        await require_subscription(update, context)
        return
    
    # Если подписан - показываем основное меню
    caption = (
        "🎯 *ЭТАП 1: ВЫБОР МОДЕЛИ УСТРОЙСТВА*\n\n"
        "📱 Выберите модель вашего iPhone:\n"
        "(На модель ниже 13 установить нельзя — в демо показано)\n\n"
        f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
    )
    
    try:
        with open(IMAGE_PATHS["stage1"], "rb") as f:
            sent = await context.bot.send_photo(
                chat_id=chat_id, 
                photo=f, 
                caption=caption, 
                reply_markup=make_models_keyboard(),
                parse_mode='Markdown'
            )
            await add_user_message(chat_id, sent.message_id)
    except Exception as e:
        logger.exception("Не удалось отправить картинку: %s", e)
        sent = await context.bot.send_message(
            chat_id=chat_id, 
            text=caption, 
            reply_markup=make_models_keyboard(),
            parse_mode='Markdown'
        )
        await add_user_message(chat_id, sent.message_id)


async def model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор модели и переходим к выбору программы"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем подписку
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    if not await check_subscription(user_id, context):
        await cleanup_user_messages(chat_id, context)
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text="❌ *Для использования бота необходимо подписаться на канал!*\n\n"
                 f"Канал: {CHANNEL_USERNAME}\n\n"
                 f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )
        await add_user_message(chat_id, sent.message_id)
        return
    
    data = query.data  # "model|13"
    _, model = data.split("|", 1)
    
    # Сохраняем выбор модели пользователя
    USER_SELECTIONS[user_id] = {"model": model}
    
    # Очищаем предыдущие сообщения
    await cleanup_user_messages(chat_id, context)
    
    # Показываем выбор программы
    caption = (
        f"🎯 *ЭТАП 2: ВЫБОР ПРОГРАММЫ*\n\n"
        f"📱 Выбрана модель: *{model}*\n\n"
        f"🎮 Теперь выберите программу:\n\n"
        f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
    )
    
    try:
        with open(IMAGE_PATHS["stage2"], "rb") as f:
            sent = await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=caption,
                reply_markup=make_programs_keyboard(),
                parse_mode='Markdown'
            )
            await add_user_message(chat_id, sent.message_id)
    except Exception as e:
        logger.exception("Не удалось отправить картинку: %s", e)
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=make_programs_keyboard(),
            parse_mode='Markdown'
        )
        await add_user_message(chat_id, sent.message_id)


async def program_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор программы и выдаем аккаунт"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # Проверяем подписку
    if not await check_subscription(user_id, context):
        await cleanup_user_messages(chat_id, context)
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text="❌ *Для получения данных необходимо подписаться на канал!*\n\n"
                 f"Канал: {CHANNEL_USERNAME}\n\n"
                 f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )
        await add_user_message(chat_id, sent.message_id)
        return
    
    data = query.data  # "program|AyuGram"
    _, program = data.split("|", 1)
    
    # Получаем выбранную ранее модель
    user_selection = USER_SELECTIONS.get(user_id, {})
    model = user_selection.get("model", "Неизвестно")
    
    # Получаем доступный аккаунт
    account = get_available_account(program)
    
    if not account:
        await cleanup_user_messages(chat_id, context)
        caption = (
            f"❌ *Извините!*\n\n"
            f"Для программы *{program}* временно нет доступных аккаунтов.\n\n"
            f"Попробуйте позже или выберите другую программу.\n\n"
            f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
        )
        
        try:
            with open(IMAGE_PATHS["stage2"], "rb") as f:
                sent = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=caption,
                    reply_markup=make_programs_keyboard(),
                    parse_mode='Markdown'
                )
                await add_user_message(chat_id, sent.message_id)
        except Exception as e:
            logger.exception("Не удалось отправить картинку: %s", e)
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=make_programs_keyboard(),
                parse_mode='Markdown'
            )
            await add_user_message(chat_id, sent.message_id)
        return
    
    # Устанавливаем время истечения
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Очищаем предыдущие сообщения
    await cleanup_user_messages(chat_id, context)
    
    # Отправляем сообщение с данными аккаунта
    text = (
        f"🎯 *ЭТАП 3: ДАННЫЕ ДЛЯ ВХОДА*\n\n"
        f"📱 Модель: {model}\n"
        f"🛠️ Программа: {program}\n\n"
        f"📧 Email: `{account['email']}`\n"
        f"🔑 Пароль: `{account['password']}`\n\n"
        f"⏰ У вас есть 10 минут на установку (до {expires_at.strftime('%H:%M:%S')} UTC).\n"
        f"Если вы не используете эти данные, они автоматически станут неактивными.\n\n"
        f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
    )

    try:
        with open(IMAGE_PATHS["stage3"], "rb") as f:
            sent = await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=text,
                parse_mode="Markdown",
                reply_markup=make_session_buttons(0)  # Временно, потом обновим
            )
    except Exception as e:
        logger.exception("Не удалось отправить картинку: %s", e)
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=make_session_buttons(0)  # Временно, потом обновим
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
        "chat_id": chat_id,
        "user_id": user_id,
        "message_id": message_id,
    }

    # Обновляем кнопки с правильным message_id
    await context.bot.edit_message_caption(
        chat_id=chat_id,
        message_id=message_id,
        caption=text,
        reply_markup=make_session_buttons(message_id),
        parse_mode="Markdown"
    )

    await add_user_message(chat_id, message_id)

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
            edit_text = (
                "🔒 *Сессия истекла* — эти данные больше не действительны.\n\n"
                f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
            )
            await context.bot.edit_message_caption(
                chat_id=chat_id, 
                message_id=message_id, 
                caption=edit_text,
                parse_mode='Markdown'
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
                await query.answer("⚠️ Сессия уже была отозвана или истекла.", show_alert=True)
                return
            session["revoked"] = True
            # Освобождаем аккаунт
            release_account(session["program"], session["email"])
            try:
                edit_text = (
                    "❌ *Аккаунт отозван* — данные больше не действительны.\n\n"
                    f"*Если у вас возникли вопросы или ошибка, свяжитесь с {MODERATOR_USERNAME}*"
                )
                await context.bot.edit_message_caption(
                    chat_id=session["chat_id"],
                    message_id=message_id,
                    caption=edit_text,
                    parse_mode='Markdown'
                )
            except Exception:
                logger.exception("Не удалось отредактировать сообщение при отзыве.")
        elif action == "timer":
            if session["revoked"]:
                await query.answer("Сессия уже отозвана/истекла.", show_alert=True)
                return
            remaining = session["expires_at"] - datetime.utcnow()
            secs = int(remaining.total_seconds())
            if secs <= 0:
                await query.answer("⏰ Время вышло — сессия истекла.", show_alert=True)
                session["revoked"] = True
                release_account(session["program"], session["email"])
                return
            mins, sec = divmod(secs, 60)
            # Показываем alert с временем (сообщение не редактируется)
            await query.answer(f"⏱️ Осталось времени: {mins} мин {sec} сек.", show_alert=True)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Запускаем бота с улучшенной системой сообщений...")
    app.run_polling()


if __name__ == "__main__":
    main()

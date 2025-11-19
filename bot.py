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

# Путь к картинкам, которые ты загрузил(а)
IMAGE_PATHS = [
    "IMG_6482.png",
    "IMG_6483.png",
    "IMG_6489.png",
]

# В памяти - хранение выданных "учёток"
# dict: message_id -> {email, password, expires_at, revoked, chat_id}
SESSIONS = {}

# Список моделей (как в скриншоте)
MODEL_ROWS = [
    ["13", "13 Pro", "13 Pro Max"],
    ["14", "14 Pro", "14 Pro Max"],
    ["15", "15 Pro", "15 Pro Max"],
    ["16", "16 Pro", "16 Pro Max"],
    ["17", "17 Pro", "17 Pro Max"],
]


def gen_demo_email():
    # Генерируем демонстрационный email (без реального домена)
    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{local}@example.com"


def gen_demo_password():
    return ''.join(random.choices(string.ascii_letters + string.digits + "_-@", k=10))


def make_models_keyboard():
    keyboard = []
    for row in MODEL_ROWS:
        keyboard.append([InlineKeyboardButton(text=m, callback_data=f"model|{m}") for m in row])
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
    """Обрабатываем выбор модели — выдаём тестовые (демо) креды с 10-мин таймером."""
    query = update.callback_query
    await query.answer()
    
    # Проверяем подписку перед выдачей данных
    user_id = query.from_user.id
    if not await check_subscription(user_id, context):
        await query.edit_message_text(
            "❌ *Для получения данных необходимо подписаться на канал! В случае ошибки отпишите модератору @kattyshechk*\n\n"
            f"Канал: {CHANNEL_USERNAME}",
            reply_markup=make_subscription_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    data = query.data  # "model|13"
    _, model = data.split("|", 1)
    chat_id = query.message.chat_id

    # создаём демонстрационные данные
    email = gen_demo_email()
    password = gen_demo_password()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # отправляем сообщение с данными
    text = (
        "🔐 Данные для входа (демо):\n"
        f"📧 Email: `{email}`\n"
        f"🔑 Пароль: `{password}`\n\n"
        f"⏰ У вас есть 10 минут на установку (до {expires_at.isoformat()} UTC).\n"
        "Если вы не используете эти данные, они автоматически станут неактивными. В случае ошибки отпишите модератору @kattyshechk"
    )

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=None,
    )

    # Сохраняем сессию, индексируем по message_id (можно по любому уникальному id)
    message_id = sent.message_id
    SESSIONS[message_id] = {
        "email": email,
        "password": password,
        "expires_at": expires_at,
        "revoked": False,
        "chat_id": chat_id,
        "model": model,
        "message_id": message_id,
    }

    # Отправляем кнопки для отзыва / таймера под тем же сообщением (редактируем reply_markup)
    await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=make_session_buttons(message_id))

    # Создаём фон. задачу, которая через 10 минут пометит сессию как истёкшую и отредактирует сообщение
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

    # после сна проверим состояние
    session = SESSIONS.get(message_id)
    if not session:
        return
    if not session["revoked"]:
        session["revoked"] = True
        chat_id = session["chat_id"]
        try:
            edit_text = (
                "🔒 Сессия истекла — эти демонстрационные данные больше не действительны. Отпишите модератору @kattyshechk"
            )
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=edit_text)
        except Exception:
            logger.exception("Не удалось отредактировать сообщение при окончании таймера.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline кнопок revoke|..., timer|... и model|..."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Обработка проверки подписки
    if data == "check_subscription":
        await subscription_callback(update, context)
        return

    if data.startswith("model|"):
        # перенаправляем в handler выбора модели
        await model_selected(update, context)
        return

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
        try:
            await context.bot.edit_message_text(
                chat_id=session["chat_id"],
                message_id=message_id,
                text="❌ Аккаунт отозван. Данные больше не действительны."
            )
        except Exception:
            logger.exception("Не удалось отредактировать сообщение при отзыве.")
    elif action == "timer":
        # показываем оставшееся время (не изменяем состояния)
        if session["revoked"]:
            await query.edit_message_text("Сессия уже отозвана/истекла.")
            return
        remaining = session["expires_at"] - datetime.utcnow()
        secs = int(remaining.total_seconds())
        if secs <= 0:
            await query.edit_message_text("⏰ Время вышло — сессия истекла.")
            session["revoked"] = True
            return
        mins, sec = divmod(secs, 60)
        await query.edit_message_text(f"⏱️ Осталось времени: {mins} мин {sec} сек.")
    else:
        await query.edit_message_text("Неизвестная команда.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Запускаем бота...")
    app.run_polling()


if __name__ == "__main__":
    main()

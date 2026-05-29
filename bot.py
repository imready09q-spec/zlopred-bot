import logging
import random
import json
import os
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto, InlineQueryResultGif, InlineQueryResultCachedPhoto, InlineQueryResultCachedGif, InlineQueryResultCachedMpeg4Gif
from telegram.ext import Application, CommandHandler, MessageHandler, InlineQueryHandler, filters, ContextTypes
from uuid import uuid4

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8780650454:AAElu1Pc-Ft0AU1_s2dyEoAxYdrSqd5btUY"
ADMIN_ID = 1753669334
DB_FILE = "predictions.json"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== БАЗА ПРЕДСКАЗАНИЙ =====
DEFAULT_PREDICTIONS = [
    {"type": "text", "text": "Решишь сделать модную стрижку, но получится хуйня, с которой ещё 2 недели ходить, пока волосы не отрастут."},
    {"type": "text", "text": "Сегодня {user} — синоним слова петушара."},
    {"type": "text", "text": "Завтра утром тебе стоит вкусно позавтракать. Должно же быть в твоей жизни хоть что-то приятное."},
    {"type": "text", "text": "Попросишь знакомого айтишника разработать тебе приложение. Он разработает… нет, не твоё очко. Какую-то хуйню забагованную он разработает."},
    {"type": "text", "text": "Сегодня {user} узнает, что о нём думают коллеги и друзья. Спойлер: ничего хорошего. Причём слово «долбоёб» будет звучать чаще других."},
    {"type": "text", "text": "Звёзды говорят, что {user} сегодня будет продуктивным. Звёзды врут."},
    {"type": "text", "text": "Сегодня {user} поймёт смысл жизни. Потом забудет. Потом снова поймёт. Потом пойдёт спать."},
    {"type": "text", "text": "Удача улыбнётся {user} сегодня. Но у удачи кривые зубы, так что не обольщайся."},
]


def load_predictions():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return list(DEFAULT_PREDICTIONS)


def save_predictions(predictions):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)


def get_user_mention(user):
    """Возвращает отметку пользователя — @username или ссылку на профиль"""
    if user.username:
        return f"@{user.username}"
    else:
        name = user.first_name or "Безымянный"
        return f'<a href="tg://user?id={user.id}">{name}</a>'


def apply_user(text, user):
    """Подставляет отметку пользователя вместо {user}"""
    mention = get_user_mention(user)
    return text.replace("{user}", mention)


def get_random_prediction(user):
    predictions = load_predictions()
    pred = random.choice(predictions)
    return pred, apply_user(pred.get("text", ""), user) if pred.get("text") else None


# ===== КОМАНДЫ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я - ясновидящий и могу предсказывать будущее.\n\n"
        "Могу погадать в личке через команду /future, но лучше всего меня добавить в групповой чат с твоими друзьями и вызывать через /future@ZlopredBot - "
        "тогда я смогу предсказывать групповые события."
    )


async def future(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    predictions = load_predictions()

    if not predictions:
        await update.message.reply_text("База предсказаний пуста. Админ ещё ничего не добавил 😔")
        return

    pred = random.choice(predictions)
    text = apply_user(pred.get("text", "Твоё мем-сказание."), user) if pred.get("text") else "Твоё мем-сказание."

    if pred["type"] == "text":
        await update.message.reply_text(
            f"🔮 {get_user_mention(user)}, твоё предсказание:\n\n{text}",
            parse_mode="HTML"
        )
    elif pred["type"] == "photo":
        await update.message.reply_photo(
            photo=pred["file_id"],
            caption=f"🔮 {get_user_mention(user)}, твоё предсказание:\n\n{text}",
            parse_mode="HTML"
        )
    elif pred["type"] in ("gif", "video"):
        await update.message.reply_animation(
            animation=pred["file_id"],
            caption=f"🔮 {get_user_mention(user)}, твоё предсказание:\n\n{text}",
            parse_mode="HTML"
        )


async def add_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "Используй так:\n/add Текст предсказания\n\nИли просто отправь фото/гиф с подписью — добавится автоматически."
        )
        return

    text = " ".join(context.args)
    predictions = load_predictions()
    predictions.append({"type": "text", "text": text})
    save_predictions(predictions)

    await update.message.reply_text(f"✅ Добавлено!\n\n«{text}»")


async def delete_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Используй: /del номер\nНомера смотри через /list")
        return

    num = int(context.args[0]) - 1
    predictions = load_predictions()

    if num < 0 or num >= len(predictions):
        await update.message.reply_text(f"Нет предсказания с номером {num + 1}")
        return

    removed = predictions.pop(num)
    save_predictions(predictions)

    removed_text = removed.get("text", "[медиа]")
    await update.message.reply_text(f"🗑 Удалено:\n\n«{removed_text[:100]}»")


async def list_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    predictions = load_predictions()

    if not predictions:
        await update.message.reply_text("База пуста. Добавь через /add")
        return

    lines = [f"📋 Предсказания ({len(predictions)}):\n"]
    for i, pred in enumerate(predictions, 1):
        if pred["type"] == "text":
            short = pred["text"][:60] + ("..." if len(pred["text"]) > 60 else "")
            lines.append(f"{i}. {short}")
        elif pred["type"] == "photo":
            caption = pred.get("text", "")[:40]
            lines.append(f"{i}. 🖼 [фото] {caption}")
        elif pred["type"] in ("gif", "video"):
            caption = pred.get("text", "")[:40]
            lines.append(f"{i}. 🎞 [гиф] {caption}")

    # Разбиваем на части если список большой
    message = "\n".join(lines)
    if len(message) > 4000:
        chunks = []
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) > 3800:
                chunks.append(chunk)
                chunk = line + "\n"
            else:
                chunk += line + "\n"
        if chunk:
            chunks.append(chunk)
        for ch in chunks:
            await update.message.reply_text(ch)
    else:
        await update.message.reply_text(message)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото и гиф от админа"""
    if update.effective_user.id != ADMIN_ID:
        return

    message = update.message
    caption = message.caption or "Твоё мем-сказание."
    predictions = load_predictions()

    if message.photo:
        file_id = message.photo[-1].file_id
        predictions.append({"type": "photo", "file_id": file_id, "text": caption})
        save_predictions(predictions)
        await message.reply_text(f"✅ Фото добавлено!\n\nПодпись: «{caption}»")

    elif message.animation:
        file_id = message.animation.file_id
        predictions.append({"type": "gif", "file_id": file_id, "text": caption})
        save_predictions(predictions)
        await message.reply_text(f"✅ Гиф добавлен!\n\nПодпись: «{caption}»")

    elif message.video:
        file_id = message.video.file_id
        predictions.append({"type": "video", "file_id": file_id, "text": caption})
        save_predictions(predictions)
        await message.reply_text(f"✅ Видео добавлено!\n\nПодпись: «{caption}»")


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инлайн режим"""
    user = update.inline_query.from_user
    predictions = load_predictions()

    if not predictions:
        return

    results = []
    sample = random.sample(predictions, min(5, len(predictions)))

    for pred in sample:
        text = apply_user(pred.get("text", "Твоё мем-сказание."), user) if pred.get("text") else "Твоё мем-сказание."
        full_text = f"🔮 {get_user_mention(user)}, твоё предсказание:\n\n{text}"

        if pred["type"] == "text":
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="🔮 Получить предсказание",
                    description=text[:100],
                    input_message_content=InputTextMessageContent(
                        message_text=full_text,
                        parse_mode="HTML"
                    )
                )
            )
        elif pred["type"] == "photo":
            results.append(
                InlineQueryResultCachedPhoto(
                    id=str(uuid4()),
                    photo_file_id=pred["file_id"],
                    title="🔮 Получить предсказание",
                    caption=full_text,
                    parse_mode="HTML"
                )
            )
        elif pred["type"] in ("gif", "video"):
            results.append(
                InlineQueryResultCachedMpeg4Gif(
                    id=str(uuid4()),
                    mpeg4_file_id=pred["file_id"],
                    title="🔮 Получить предсказание",
                    caption=full_text,
                    parse_mode="HTML"
                )
            )

    if results:
        await update.inline_query.answer(results, cache_time=1)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("future", future))
    app.add_handler(CommandHandler("add", add_prediction))
    app.add_handler(CommandHandler("del", delete_prediction))
    app.add_handler(CommandHandler("list", list_predictions))
    app.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION | filters.VIDEO, handle_media))
    app.add_handler(InlineQueryHandler(inline_query))

    logger.info("Злопред запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

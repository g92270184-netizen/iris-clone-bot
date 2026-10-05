import asyncio
import logging
import random
import re
from datetime import datetime, timedelta
from collections import Counter
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAEiEH4fphS6uwbxTftrNVYRZalWHYOR3cI"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА (в памяти) ==========
users = {}          # {uid: {"messages": 0, "points": 0, "level": 1, "bio": "Не заполнено", "reg_date": "..."}}
chat_messages = {}  # {chat_id: {uid: count}}
chat_words = {}     # {chat_id: Counter слов}
chat_daily = {}     # {chat_id: {date: count}}
chat_hourly = {}    # {chat_id: {hour: count}}
antibot = {}        # {chat_id: bool}
user_names = {}     # {uid: "Имя"}

# ========== УРОВНИ ==========
def required_points(level):
    return 250 * level * (level + 1)

def get_level(points):
    level = 1
    while points >= required_points(level):
        level += 1
    return level - 1 if level > 1 else 1

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "messages": 0,
            "points": 0,
            "level": 1,
            "bio": "Не заполнено",
            "reg_date": datetime.now().strftime("%d.%m.%Y")
        }
    return users[uid]

# ========== ПРОВЕРКИ ==========
async def is_bot_admin(chat_id):
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        return member.status in ("administrator", "creator")
    except:
        return False

async def is_user_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        "🌟 <b>Даркграм Бот</b> 🌟\n\n"
        "📌 <b>Команды:</b>\n"
        "👤 /я — твой профиль\n"
        "📝 /анкета — заполнить анкету\n"
        "🏆 /стат — таблица лидеров\n"
        "📊 /аналитика — аналитика чата\n"
        "🔤 /слова — топ слов в чате\n"
        "🤖 /антибот — глушилка ботов",
        parse_mode="HTML"
    )

# ==================================================
#                    АНКЕТА
# ==================================================
@dp.message(Command("анкета"))
async def cmd_anketa(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Напиши: <code>/анкета Твой текст</code>", parse_mode="HTML")
        return
    u = get_user(message.from_user.id)
    u["bio"] = args[1]
    await message.answer(f"✅ <b>Анкета обновлена!</b>\n\n📖 <i>{args[1]}</i>", parse_mode="HTML")

# ==================================================
#                    ПРОФИЛЬ
# ==================================================
@dp.message(Command("я"))
async def cmd_me(message: types.Message):
    u = get_user(message.from_user.id)
    next_level = u["level"] + 1
    need = required_points(next_level)
    left = need - u["points"]
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    chat_id = message.chat.id
    chat_name = message.chat.title or "Личка"
    chat_count = chat_messages.get(chat_id, {}).get(message.from_user.id, 0)

    stars = "⭐" * min(u["level"], 10)
    if u["level"] > 10:
        stars += f" +{u['level'] - 10}"

    await message.answer(
        "👤 <b>Твой профиль</b>\n\n"
        f"🏷 <b>Имя:</b> {message.from_user.first_name}\n"
        f"🔗 <b>Юзернейм:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n\n"
        "📊 <b>Прогресс</b>\n"
        f"🎖 <b>Уровень {u['level']}</b> {stars}\n"
        f"✨ <b>Очки:</b> {u['points']} / {need}\n"
        f"🎯 <b>До следующего:</b> {left}\n\n"
        "📈 <b>Статистика</b>\n"
        f"💬 Всего сообщений: {u['messages']}\n"
        f"📍 В этом чате: {chat_count}\n\n"
        "💬 <b>Этот чат</b>\n"
        f"📛 {chat_name}\n"
        f"🆔 <code>{chat_id}</code>\n\n"
        "📝 <b>Анкета</b>\n"
        f"{u['bio']}\n\n"
        f"📅 <i>В боте с {u['reg_date']}</i>",
        parse_mode="HTML"
    )

# ==================================================
#                    ТАБЛИЦА ЛИДЕРОВ
# ==================================================
@dp.message(Command("стат"))
async def cmd_stat(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in chat_messages or not chat_messages[chat_id]:
        await message.answer("🏆 Пока никто не писал.", parse_mode="HTML")
        return

    sorted_users = sorted(chat_messages[chat_id].items(), key=lambda x: x[1], reverse=True)
    text = "🏆 <b>Таблица лидеров</b>\n\n<blockquote>"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, count) in enumerate(sorted_users[:10]):
        try:
            member = await bot.get_chat_member(chat_id, uid)
            name = member.user.first_name
        except:
            name = f"ID{uid}"
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} <b>{name}</b> — {count} 💬\n"
    text += "</blockquote>\n"
    total = sum(chat_messages[chat_id].values())
    text += f"📊 <b>Всего сообщений:</b> {total}"
    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    ТОП СЛОВ
# ==================================================
@dp.message(Command("слова"))
async def cmd_words(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in chat_words or not chat_words[chat_id]:
        await message.answer("🔤 Пока нет данных о словах.")
        return

    # Убираем стоп-слова
    stop_words = {"и", "в", "на", "с", "по", "не", "что", "это", "я", "ты", "он", "она",
                  "а", "но", "да", "нет", "у", "к", "о", "за", "из", "то", "как", "так",
                  "же", "бы", "для", "от", "до", "мы", "вы", "они", "все", "был", "была"}

    top = chat_words[chat_id].most_common(50)
    filtered = [(w, c) for w, c in top if w not in stop_words and len(w) > 2][:15]

    if not filtered:
        await message.answer("🔤 Пока нет интересных слов.")
        return

    text = "🔤 <b>Топ слов в чате</b>\n\n<blockquote>"
    for i, (word, count) in enumerate(filtered, 1):
        text += f"{i}. <b>{word}</b> — {count} раз\n"
    text += "</blockquote>"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    АНАЛИТИКА
# ==================================================
@dp.message(Command("аналитика"))
async def cmd_analytics(message: types.Message):
    chat_id = message.chat.id

    total = sum(chat_messages.get(chat_id, {}).values())
    users_count = len(chat_messages.get(chat_id, {}))
    avg = total // users_count if users_count else 0

    text = "📊 <b>Аналитика чата</b>\n\n"

    # Общая статистика
    text += "📈 <b>Общее</b>\n"
    text += f"💬 Всего сообщений: {total}\n"
    text += f"👥 Участников: {users_count}\n"
    text += f"📊 Среднее на человека: {avg}\n\n"

    # По дням
    if chat_id in chat_daily and chat_daily[chat_id]:
        text += "📅 <b>По дням</b>\n"
        sorted_days = sorted(chat_daily[chat_id].items(), reverse=True)[:5]
        for day, cnt in sorted_days:
            text += f"  {day}: {cnt} сообщений\n"
        text += "\n"

    # По часам
    if chat_id in chat_hourly and chat_hourly[chat_id]:
        text += "🕐 <b>Топ часов активности</b>\n"
        sorted_hours = sorted(chat_hourly[chat_id].items(), key=lambda x: x[1], reverse=True)[:3]
        for hour, cnt in sorted_hours:
            text += f"  {hour}:00 — {cnt} сообщений\n"
        text += "\n"

    # Топ-3 слова
    if chat_id in chat_words and chat_words[chat_id]:
        text += "🔤 <b>Топ-3 слова</b>\n"
        stop_words = {"и", "в", "на", "с", "по", "не", "что", "это", "я", "ты", "он", "она"}
        top = [(w, c) for w, c in chat_words[chat_id].most_common(20) if w not in stop_words and len(w) > 2][:3]
        for word, cnt in top:
            text += f"  {word} — {cnt} раз\n"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    АНТИ-БОТ
# ==================================================
@dp.message(Command("антибот"))
async def cmd_antibot(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Только в группе.")
        return
    if not await is_user_admin(message.chat.id, message.from_user.id):
        await message.answer("🚫 Только админы.")
        return

    args = message.text.split()
    if len(args) < 2:
        status = "включён" if antibot.get(message.chat.id) else "выключен"
        await message.answer(f"🤖 Анти-бот сейчас <b>{status}</b>", parse_mode="HTML")
        return

    action = args[1].lower()
    if action in ("вкл", "on"):
        antibot[message.chat.id] = True
        await message.answer("🤖 <b>Анти-бот включён</b>", parse_mode="HTML")
    elif action in ("выкл", "off"):
        antibot[message.chat.id] = False
        await message.answer("🤖 Анти-бот выключен.")

# ==================================================
#                    БОТ ДОБАВЛЕН
# ==================================================
@dp.message(lambda m: m.new_chat_members and any(bot.id == u.id for u in m.new_chat_members))
async def on_added_to_group(message: types.Message):
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Я <b>Даркграм Бот</b> — считаю сообщения, слова и веду аналитику.\n\n"
        "⚠️ Назначьте меня админом.\n\n"
        "📊 /аналитика — статистика чата\n"
        "🔤 /слова — топ слов\n"
        "🏆 /стат — лидеры",
        parse_mode="HTML"
    )

# ==================================================
#                    СЧЁТЧИК + АНАЛИТИКА
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    # Анти-бот
    if antibot.get(chat_id) and message.from_user.is_bot and uid != bot.id:
        try:
            await message.delete()
        except:
            pass
        return

    # Проверка админа
    if message.chat.type != "private":
        if not await is_bot_admin(chat_id):
            return

    # Сохраняем имя
    user_names[uid] = message.from_user.first_name

    # Счётчик сообщений
    if chat_id not in chat_messages:
        chat_messages[chat_id] = {}
    if uid not in chat_messages[chat_id]:
        chat_messages[chat_id][uid] = 0
    chat_messages[chat_id][uid] += 1

    # === АНАЛИТИКА: СЛОВА ===
    if chat_id not in chat_words:
        chat_words[chat_id] = Counter()
    # Разбиваем на слова, убираем мусор
    words = re.findall(r'[а-яёa-z]+', text.lower())
    for word in words:
        if len(word) > 2:
            chat_words[chat_id][word] += 1

    # === АНАЛИТИКА: ПО ДНЯМ ===
    today = datetime.now().strftime("%d.%m")
    if chat_id not in chat_daily:
        chat_daily[chat_id] = {}
    chat_daily[chat_id][today] = chat_daily[chat_id].get(today, 0) + 1

    # === АНАЛИТИКА: ПО ЧАСАМ ===
    hour = datetime.now().hour
    if chat_id not in chat_hourly:
        chat_hourly[chat_id] = {}
    chat_hourly[chat_id][hour] = chat_hourly[chat_id].get(hour, 0) + 1

    # === ОЧКИ И УРОВНИ ===
    u = get_user(uid)
    u["messages"] += 1
    points_gain = random.randint(1, 25)
    u["points"] += points_gain

    new_level = get_level(u["points"])
    if new_level > u["level"]:
        u["level"] = new_level
        phrases = {
            2: "🌱 Ты только начинаешь!",
            3: "🔥 Набираешь обороты!",
            5: "💪 Пятый уровень!",
            10: "🏅 Десятый уровень!",
            20: "👑 Легенда!",
            50: "🌟 ТЫ БОГ ЧАТА!"
        }
        phrase = phrases.get(new_level, "✨ Продолжай!")
        try:
            await message.answer(
                "🎉 <b>Новый уровень!</b>\n\n"
                f"🎖 <b>{message.from_user.first_name}</b> — <b>{new_level}</b>!\n\n"
                f"{phrase}",
                parse_mode="HTML"
            )
        except:
            pass

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

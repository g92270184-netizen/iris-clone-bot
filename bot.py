import asyncio
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAHgauVp5Q5-xE4Muc8qY643bd8SucTOPrI"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА (в памяти) ==========
users = {}          # {uid: {"messages": 0, "points": 0, "level": 1, "bio": "Не заполнено", "reg_date": "..."}}
chat_messages = {}  # {chat_id: {uid: count}}

# ========== УРОВНИ ==========
def required_points(level):
    """Сколько нужно очков для уровня N.
    500, 5000, 15000, 30000, 50000..."""
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

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        "<b>Даркграм Бот</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Я считаю сообщения и выдаю уровни за активность.\n\n"
        "<b>Команды:</b>\n\n"
        "  /я — твой профиль\n"
        "  /анкета текст — заполнить анкету\n"
        "  /стат — таблица лидеров",
        parse_mode="HTML"
    )

# ==================================================
#                    АНКЕТА
# ==================================================
@dp.message(Command("анкета"))
async def cmd_anketa(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "<b>Анкета</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Напиши:\n"
            "<code>/анкета Твой текст о себе</code>",
            parse_mode="HTML"
        )
        return
    u = get_user(message.from_user.id)
    u["bio"] = args[1]
    await message.answer(
        "<b>Анкета обновлена</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>О себе:</b> {args[1]}",
        parse_mode="HTML"
    )

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

    # Прогресс-бар
    prev_need = required_points(u["level"]) if u["level"] > 1 else 0
    progress = u["points"] - prev_need
    total_need = need - prev_need
    filled = int((progress / total_need) * 10) if total_need > 0 else 0
    bar = "█" * filled + "░" * (10 - filled)

    await message.answer(
        "<b>Профиль</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Имя:</b> {message.from_user.first_name}\n"
        f"<b>Юзернейм:</b> {username}\n"
        f"<b>ID:</b> <code>{message.from_user.id}</code>\n\n"
        "<b>Уровень</b>\n"
        f"  {u['level']} уровень\n"
        f"  {bar} {progress} / {total_need}\n"
        f"  До следующего: <b>{left}</b> очков\n\n"
        "<b>Статистика</b>\n"
        f"  Очки: {u['points']}\n"
        f"  Сообщений: {u['messages']}\n\n"
        "<b>Этот чат</b>\n"
        f"  Название: {chat_name}\n"
        f"  ID чата: <code>{chat_id}</code>\n"
        f"  Сообщений здесь: {chat_count}\n\n"
        "<b>Анкета</b>\n"
        f"  {u['bio']}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>В боте с {u['reg_date']}</i>",
        parse_mode="HTML"
    )

# ==================================================
#                    ТАБЛИЦА ЛИДЕРОВ
# ==================================================
@dp.message(Command("стат"))
async def cmd_stat(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in chat_messages or not chat_messages[chat_id]:
        await message.answer(
            "<b>Таблица лидеров</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Пока нет данных о сообщениях.",
            parse_mode="HTML"
        )
        return

    sorted_users = sorted(chat_messages[chat_id].items(), key=lambda x: x[1], reverse=True)

    text = (
        "<b>Таблица лидеров</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<blockquote>"
    )
    medals = ["1.", "2.", "3."]
    for i, (uid, count) in enumerate(sorted_users[:10]):
        try:
            member = await bot.get_chat_member(chat_id, uid)
            name = member.user.first_name
        except:
            name = f"ID{uid}"
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} {name} — {count} сообщений\n"
    text += "</blockquote>\n"
    total = sum(chat_messages[chat_id].values())
    text += "━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<b>Всего сообщений:</b> {total}"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    БОТ ДОБАВЛЕН В ГРУППУ
# ==================================================
@dp.message(lambda m: m.new_chat_members and any(bot.id == u.id for u in m.new_chat_members))
async def on_added_to_group(message: types.Message):
    await message.answer(
        "<b>Даркграм Бот</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Привет! Я считаю сообщения и выдаю уровни за активность.\n\n"
        "  /я — профиль\n"
        "  /стат — таблица лидеров",
        parse_mode="HTML"
    )

# ==================================================
#                    СЧЁТЧИК + ОЧКИ + УРОВНИ
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    # Считаем сообщение в этом чате
    if chat_id not in chat_messages:
        chat_messages[chat_id] = {}
    if uid not in chat_messages[chat_id]:
        chat_messages[chat_id][uid] = 0
    chat_messages[chat_id][uid] += 1

    # Очки и уровни
    u = get_user(uid)
    u["messages"] += 1
    points_gain = random.randint(1, 25)
    u["points"] += points_gain

    # Проверка на повышение уровня
    new_level = get_level(u["points"])
    if new_level > u["level"]:
        u["level"] = new_level
        try:
            await message.answer(
                "<b>Новый уровень!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"{message.from_user.first_name} достиг <b>{new_level}</b> уровня.\n"
                f"Очков: {u['points']}",
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

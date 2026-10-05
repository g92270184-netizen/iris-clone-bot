import asyncio
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAFWzDc_JGDUHx5uJo-WU3RtBA2CH43UpAo"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА (в памяти) ==========
users = {}          # {uid: {"messages": 0, "points": 0, "level": 1, "bio": "Не заполнено", "reg_date": "..."}}
chat_messages = {}  # {chat_id: {uid: count}}
antibot = {}        # {chat_id: True/False} — включена ли глушилка ботов

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

    if message.chat.type != "private":
        bot_admin = await is_bot_admin(message.chat.id)
        if not bot_admin:
            await message.answer(
                "⚠️ <b>Внимание!</b>\n\n"
                "Я работаю только если я <b>администратор</b> в этом чате.\n\n"
                "📌 <b>Как назначить меня админом:</b>\n"
                "1. Откройте настройки группы\n"
                "2. Управление участниками\n"
                "3. Найдите меня в списке\n"
                "4. Назначьте администратором\n\n"
                "После этого я смогу считать сообщения и выдавать уровни.",
                parse_mode="HTML"
            )
            return

        await message.answer(
            "🌟 <b>Даркграм Бот</b> 🌟\n\n"
            "Спасибо, что назначили меня админом! Теперь я работаю.\n\n"
            "📌 <b>Что я умею:</b>\n"
            "👤 /я — твой профиль\n"
            "📝 /анкета — заполнить анкету\n"
            "🏆 /стат — таблица лидеров\n"
            "🤖 /антибот — глушилка ботов\n\n"
            "💬 Просто общайся — за каждое сообщение получаешь очки!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🌟 <b>Даркграм Бот</b> 🌟\n\n"
            "Привет! Я слежу за активностью в чате и выдаю уровни.\n\n"
            "📌 <b>Что я умею:</b>\n"
            "👤 /я — твой профиль\n"
            "📝 /анкета — заполнить анкету\n"
            "🏆 /стат — таблица лидеров\n"
            "🤖 /антибот — глушилка ботов\n\n"
            "⚠️ <b>Важно:</b> Чтобы я работал в группе, назначьте меня <b>администратором</b>.",
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
            "📝 <b>Анкета</b>\n\n"
            "Напиши так:\n"
            "<code>/анкета Твой текст о себе</code>",
            parse_mode="HTML"
        )
        return
    u = get_user(message.from_user.id)
    u["bio"] = args[1]
    await message.answer(
        "✅ <b>Анкета обновлена!</b>\n\n"
        f"📖 <i>{args[1]}</i>",
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

    if message.chat.type != "private":
        bot_admin = await is_bot_admin(chat_id)
        if not bot_admin:
            await message.answer(
                "⚠️ <b>Я не админ в этом чате.</b>\n\n"
                "Назначьте меня администратором, чтобы я мог вести статистику.",
                parse_mode="HTML"
            )
            return

    if chat_id not in chat_messages or not chat_messages[chat_id]:
        await message.answer(
            "🏆 <b>Таблица лидеров</b>\n\n"
            "😔 Пока никто не написал ни одного сообщения.",
            parse_mode="HTML"
        )
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
    text += f"📊 <b>Всего сообщений в чате:</b> {total}"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    АНТИ-БОТ (ГЛУШИЛКА)
# ==================================================
@dp.message(Command("антибот"))
async def cmd_antibot(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Только в группе.")
        return
    if not await is_user_admin(message.chat.id, message.from_user.id):
        await message.answer("🚫 Только админы могут включать анти-бот.")
        return

    args = message.text.split()
    if len(args) < 2:
        status = "включён" if antibot.get(message.chat.id) else "выключен"
        await message.answer(
            f"🤖 <b>Анти-бот сейчас {status}</b>\n\n"
            "Используй: <code>/антибот вкл</code> или <code>/антибот выкл</code>",
            parse_mode="HTML"
        )
        return

    action = args[1].lower()
    if action in ("вкл", "on", "да"):
        antibot[message.chat.id] = True
        await message.answer(
            "🤖 <b>Анти-бот включён</b>\n\n"
            "Теперь сообщения от других ботов будут удаляться.",
            parse_mode="HTML"
        )
    elif action in ("выкл", "off", "нет"):
        antibot[message.chat.id] = False
        await message.answer("🤖 Анти-бот выключен.")
    else:
        await message.answer("Используй: вкл или выкл")

# ==================================================
#                    БОТ ДОБАВЛЕН В ГРУППУ
# ==================================================
@dp.message(lambda m: m.new_chat_members and any(bot.id == u.id for u in m.new_chat_members))
async def on_added_to_group(message: types.Message):
    await message.answer(
        "👋 <b>Всем привет!</b>\n\n"
        "Я <b>Даркграм Бот</b> — слежу за активностью и выдаю уровни.\n\n"
        "⚠️ <b>Чтобы я работал, назначьте меня администратором!</b>\n\n"
        "📌 <b>Как это сделать:</b>\n"
        "1. Настройки группы\n"
        "2. Управление участниками\n"
        "3. Найдите меня\n"
        "4. Назначьте админом\n\n"
        "После этого напишите /start",
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

    # === ГЛУШИЛКА БОТОВ ===
    if antibot.get(chat_id) and message.from_user.is_bot and uid != bot.id:
        try:
            await message.delete()
        except:
            pass
        return

    # === ПРОВЕРКА: БОТ АДМИН? ===
    if message.chat.type != "private":
        bot_admin = await is_bot_admin(chat_id)
        if not bot_admin:
            return

    # Считаем сообщение
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

    # Повышение уровня
    new_level = get_level(u["points"])
    if new_level > u["level"]:
        u["level"] = new_level

        phrases = {
            2: "🌱 Ты только начинаешь свой путь!",
            3: "🔥 Ты набираешь обороты!",
            5: "💪 Пятый уровень, неплохо!",
            10: "🏅 Десятый уровень! Ты в топе!",
            15: "🚀 Пятнадцатый! Космос!",
            20: "👑 Двадцатый уровень! Легенда!",
            30: "💎 Тридцатый уровень! Бриллиант!",
            40: "🔥 Сороковой! Ты неугасим!",
            50: "🌟 ПЯТИДЕСЯТЫЙ УРОВЕНЬ! ТЫ БОГ ЧАТА!"
        }
        phrase = phrases.get(new_level, "✨ Продолжай в том же духе!")

        try:
            await message.answer(
                "🎉 <b>Новый уровень!</b> 🎉\n\n"
                f"🎖 <b>{message.from_user.first_name}</b> достиг <b>{new_level}</b> уровня!\n\n"
                f"✨ Очков: <b>{u['points']}</b>\n"
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

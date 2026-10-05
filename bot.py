import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAFhU0xLmECcx_8nYvW3hlHvdjcgY3ZwKTg"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА ==========
users = {}          # {uid: {"messages": 0, "bio": "Не заполнено"}}
chat_messages = {}  # {chat_id: {uid: count}}
group_titles = {}   # {chat_id: "Название"}

def get_user(uid):
    if uid not in users:
        users[uid] = {"messages": 0, "bio": "Не заполнено"}
    return users[uid]

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        "<b>Привет!</b>\n\n"
        "Я считаю сообщения в группах и в личке.\n\n"
        "<b>Команды:</b>\n"
        "• /стат — таблица лидеров чата\n"
        "• /анкета текст — заполнить анкету\n"
        "• /я — посмотреть анкету",
        parse_mode="HTML"
    )

# ========== АНКЕТА ==========
@dp.message(Command("анкета"))
async def cmd_anketa(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /анкета Твой текст о себе")
        return
    u = get_user(message.from_user.id)
    u["bio"] = args[1]
    await message.answer(f"Анкета обновлена: {u['bio']}")

@dp.message(Command("я"))
async def cmd_me(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(
        f"<b>Твоя анкета</b>\n"
        f"Имя: {message.from_user.first_name}\n"
        f"Сообщений: {u['messages']}\n"
        f"О себе: {u['bio']}",
        parse_mode="HTML"
    )

# ========== ТАБЛИЦА ЛИДЕРОВ (цитированный текст) ==========
@dp.message(Command("стат"))
async def cmd_stat(message: types.Message):
    chat_id = message.chat.id

    if chat_id not in chat_messages or not chat_messages[chat_id]:
        await message.answer("Пока нет данных о сообщениях в этом чате.")
        return

    sorted_users = sorted(chat_messages[chat_id].items(), key=lambda x: x[1], reverse=True)

    text = "<b>🏆 Таблица лидеров по сообщениям</b>\n\n<blockquote>"
    for i, (uid, count) in enumerate(sorted_users[:10], 1):
        try:
            member = await bot.get_chat_member(chat_id, uid)
            name = member.user.first_name
        except:
            name = f"ID{uid}"

        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        text += f"{medal} {name} — {count} сообщений\n"

    text += "</blockquote>"

    total = sum(chat_messages[chat_id].values())
    text += f"\n<b>Всего сообщений в чате:</b> {total}"

    await message.answer(text, parse_mode="HTML")

# ========== БОТ ДОБАВЛЕН В ГРУППУ ==========
@dp.message(lambda m: m.new_chat_members and any(bot.id == u.id for u in m.new_chat_members))
async def on_added_to_group(message: types.Message):
    chat_id = message.chat.id
    group_titles[chat_id] = message.chat.title or "Без названия"
    await message.answer(
        "Привет! Я буду считать сообщения в этой группе.\n"
        "Таблица лидеров: /стат"
    )

# ========== СЧЁТЧИК СООБЩЕНИЙ ==========
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    # Запоминаем название группы
    if message.chat.type != "private":
        if chat_id not in group_titles:
            group_titles[chat_id] = message.chat.title or "Без названия"

    # Считаем сообщение в этом чате
    if chat_id not in chat_messages:
        chat_messages[chat_id] = {}
    if uid not in chat_messages[chat_id]:
        chat_messages[chat_id][uid] = 0
    chat_messages[chat_id][uid] += 1

    # Общий счётчик
    u = get_user(uid)
    u["messages"] += 1

# ========== ЗАПУСК ==========
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

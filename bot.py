import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAEpBIEuEF2N7ikTCtoT8Jt0rDP2mJ3Xu_4"

WEBAPP_URL = "https://g92270184-netizen.github.io/iris-clone-bot/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}
chat_messages = {}
group_titles = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {"messages": 0, "bio": "Не заполнено"}
    return users[uid]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рейтинг чата", web_app=WebAppInfo(url=WEBAPP_URL + "/top"))]
    ])
    await message.answer(
        "<b>Привет!</b>\n\n"
        "Я считаю сообщения в группах и в личке.\n\n"
        "<b>Команды:</b>\n"
        "• /стат — статистика чата\n"
        "• /анкета текст — заполнить анкету\n"
        "• /я — посмотреть анкету\n"
        "• /группы — список групп",
        parse_mode="HTML",
        reply_markup=kb
    )

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

@dp.message(Command("группы"))
async def cmd_groups(message: types.Message):
    if not group_titles:
        await message.answer("Бот пока не добавлен ни в одну группу.")
        return
    text = "<b>Группы, где бот считает:</b>\n\n<blockquote>"
    for cid, title in group_titles.items():
        count = sum(chat_messages.get(cid, {}).values())
        text += f"• {title} — {count} сообщений\n"
    text += "</blockquote>"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("стат"))
async def cmd_stat(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in chat_messages or not chat_messages[chat_id]:
        await message.answer("Пока нет данных о сообщениях в этом чате.")
        return
    sorted_users = sorted(chat_messages[chat_id].items(), key=lambda x: x[1], reverse=True)
    text = "<b>Статистика сообщений</b>\n\n<blockquote>"
    for i, (uid, count) in enumerate(sorted_users[:10], 1):
        try:
            member = await bot.get_chat_member(chat_id, uid)
            name = member.user.first_name
        except:
            name = f"ID{uid}"
        text += f"{i}. {name} — {count} сообщений\n"
    text += "</blockquote>"
    total = sum(chat_messages[chat_id].values())
    text += f"\nВсего: <b>{total}</b>"
    await message.answer(text, parse_mode="HTML")

@dp.message(lambda m: m.new_chat_members and any(bot.id == u.id for u in m.new_chat_members))
async def on_added_to_group(message: types.Message):
    chat_id = message.chat.id
    group_titles[chat_id] = message.chat.title or "Без названия"
    await message.answer("Привет! Я считаю сообщения в этой группе. Статистика: /стат")

@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""
    if not text.strip():
        return
    if message.chat.type != "private":
        if chat_id not in group_titles:
            group_titles[chat_id] = message.chat.title or "Без названия"
    if chat_id not in chat_messages:
        chat_messages[chat_id] = {}
    if uid not in chat_messages[chat_id]:
        chat_messages[chat_id][uid] = 0
    chat_messages[chat_id][uid] += 1
    u = get_user(uid)
    u["messages"] += 1

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

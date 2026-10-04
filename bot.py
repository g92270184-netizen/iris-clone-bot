import asyncio
import logging
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8870858743:AAFpdYOLw-YOkYxyPq_CRO2fDBEWc_aDJCw"
WEBAPP_URL = "https://example.com"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}
muted = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "balance": 0, "warns": 0, "messages": 0, "partner": None,
            "bio": "Не заполнено", "age": "Не указано", "city": "Не указан"
        }
    return users[uid]

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Рейтинг чата", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")]
    ])
    await message.answer(
        "👋 Привет! Я бот-клон Ирис.\n\n"
        "💰 Экономика: /баланс, /бонус, /передать, /топ\n"
        "🛡 Модерация: /мут, /варн, /бан, /кик\n"
        "❤️ Отношения: /брак, /развод, /партнёр\n"
        "🎲 Игры: /дуэль, /рулетка, /шип, /кубик\n"
        "👤 Профиль: /профиль, /анкета\n"
        "📊 Рейтинг: /рейтинг",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "profile")
async def cb_profile(call: types.CallbackQuery):
    u = get_user(call.from_user.id)
    await call.message.answer(
        f"👤 Профиль: {call.from_user.first_name}\n"
        f"💰 Баланс: {u['balance']} ирисок\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"⚠️ Варнов: {u['warns']}\n"
        f"📝 О себе: {u['bio']}"
    )
    await call.answer()

# ========== ПРОФИЛЬ И АНКЕТА ==========
@dp.message(Command("профиль"))
async def cmd_profile(message: types.Message):
    u = get_user(message.from_user.id)
    partner_name = "Нет"
    if u["partner"]:
        try:
            p = await bot.get_chat(u["partner"])
            partner_name = p.first_name
        except:
            pass
    await message.answer(
        f"👤 Профиль\n"
        f"Имя: {message.from_user.first_name}\n"
        f"💰 Баланс: {u['balance']}\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"⚠️ Варнов: {u['warns']}\n"
        f"❤️ Партнёр: {partner_name}\n"
        f"📝 О себе: {u['bio']}"
    )

@dp.message(Command("анкета"))
async def cmd_anketa(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /анкета Твой текст о себе")
        return
    u = get_user(message.from_user.id)
    u["bio"] = args[1]
    await message.answer(f"✅ Анкета обновлена: {u['bio']}")

@dp.message(Command("возраст"))
async def cmd_age(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /возраст 18")
        return
    u = get_user(message.from_user.id)
    u["age"] = args[1]
    await message.answer(f"✅ Возраст: {u['age']}")

@dp.message(Command("город"))
async def cmd_city(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /город Москва")
        return
    u = get_user(message.from_user.id)
    u["city"] = args[1]
    await message.answer(f"✅ Город: {u['city']}")

# ========== ЭКОНОМИКА ==========
@dp.message(Command("баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(f"💰 Баланс: {u['balance']} ирисок")

@dp.message(Command("бонус"))
async def cmd_bonus(message: types.Message):
    u = get_user(message.from_user.id)
    b = random.randint(10, 50)
    u["balance"] += b
    await message.answer(f"🎁 Бонус: +{b} ирисок. Всего: {u['balance']}")

@dp.message(Command("передать"))
async def cmd_transfer(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение получателя и напиши сумму.")
        return
    try:
        amount = int(message.text.split()[1])
    except:
        await message.answer("Формат: /передать 100 (в ответ на сообщение)")
        return
    sender = get_user(message.from_user.id)
    if sender["balance"] < amount:
        await message.answer("❌ Недостаточно ирисок.")
        return
    receiver = get_user(message.reply_to_message.from_user.id)
    sender["balance"] -= amount
    receiver["balance"] += amount
    await message.answer(f"✅ Передано {amount} ирисок.")

@dp.message(Command("топ"))
async def cmd_top(message: types.Message):
    top = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:5]
    if not top:
        await message.answer("Пока пусто.")
        return
    text = "🏆 Топ по ирискам:\n"
    for i, (uid, d) in enumerate(top, 1):
        try:
            u = await bot.get_chat(uid)
            name = u.first_name
        except:
            name = f"ID{uid}"
        text += f"{i}. {name} — {d['balance']}\n"
    await message.answer(text)

@dp.message(Command("рейтинг"))
async def cmd_rating(message: types.Message):
    top = sorted(users.items(), key=lambda x: x[1]["messages"], reverse=True)[:10]
    if not top:
        await message.answer("Пока пусто.")
        return
    text = "📊 Топ по сообщениям:\n"
    for i, (uid, d) in enumerate(top, 1):
        try:
            u = await bot.get_chat(uid)
            name = u.first_name
        except:
            name = f"ID{uid}"
        text += f"{i}. {name} — {d['messages']} сообщений\n"
    await message.answer(text)

# ========== МОДЕРАЦИЯ ==========
@dp.message(Command("мут"))
async def cmd_mute(message: types.Message):
    if message.chat.type == "private" or not message.reply_to_message:
        await message.answer("Только в группе и в ответ на сообщение.")
        return
    target = message.reply_to_message.from_user
    try:
        minutes = int(message.text.split()[1])
    except:
        minutes = 10
    muted.setdefault(message.chat.id, {})[target.id] = datetime.now() + timedelta(minutes=minutes)
    await message.answer(f"🔇 {target.first_name} замучен на {minutes} мин.")

@dp.message(Command("варн"))
async def cmd_warn(message: types.Message):
    if message.chat.type == "private" or not message.reply_to_message:
        await message.answer("Только в группе и в ответ на сообщение.")
        return
    target = message.reply_to_message.from_user
    u = get_user(target.id)
    u["warns"] += 1
    if u["warns"] >= 3:
        muted.setdefault(message.chat.id, {})[target.id] = datetime.now() + timedelta(hours=1)
        u["warns"] = 0
        await message.answer(f"⛔ {target.first_name} получил 3/3 и мут на час.")
    else:
        await message.answer(f"⚠️ {target.first_name}: {u['warns']}/3 варнов.")

@dp.message(Command("бан"))
async def cmd_ban(message: types.Message):
    if message.chat.type == "private" or not message.reply_to_message:
        await message.answer("Только в группе и в ответ на сообщение.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await message.answer(f"🔨 {target.first_name} забанен.")
    except Exception as e:
        await message.answer(f"Не удалось забанить: {e}")

@dp.message(Command("кик"))
async def cmd_kick(message: types.Message):
    if message.chat.type == "private" or not message.reply_to_message:
        await message.answer("Только в группе и в ответ на сообщение.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.answer(f"👢 {target.first_name} кикнут.")
    except Exception as e:
        await message.answer(f"Не удалось кикнуть: {e}")

# ========== ОТНОШЕНИЯ ==========
@dp.message(Command("брак"))
async def cmd_marry(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение того, кому хочешь предложить брак.")
        return
    a = get_user(message.from_user.id)
    b = get_user(message.reply_to_message.from_user.id)
    if a["partner"] or b["partner"]:
        await message.answer("Кто-то из вас уже в браке.")
        return
    a["partner"] = message.reply_to_message.from_user.id
    b["partner"] = message.from_user.id
    await message.answer(f"💍 {message.from_user.first_name} и {message.reply_to_message.from_user.first_name} теперь в браке!")

@dp.message(Command("развод"))
async def cmd_divorce(message: types.Message):
    u = get_user(message.from_user.id)
    if not u["partner"]:
        await message.answer("Ты не в браке.")
        return
    p = get_user(u["partner"])
    p["partner"] = None
    u["partner"] = None
    await message.answer("💔 Вы развелись.")

@dp.message(Command("партнёр"))
async def cmd_partner(message: types.Message):
    u = get_user(message.from_user.id)
    if not u["partner"]:
        await message.answer("У тебя нет партнёра.")
        return
    try:
        p = await bot.get_chat(u["partner"])
        await message.answer(f"❤️ Твой партнёр: {p.first_name}")
    except:
        await message.answer("Не удалось найти партнёра.")

# ========== ИГРЫ ==========
@dp.message(Command("рулетка"))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id)
    bet = random.randint(1, 50)
    if random.random() < 0.5:
        u["balance"] += bet
        await message.answer(f"🎉 Выиграл {bet} ирисок! Баланс: {u['balance']}")
    else:
        u["balance"] = max(0, u["balance"] - bet)
        await message.answer(f"😢 Проиграл {bet} ирисок. Баланс: {u['balance']}")

@dp.message(Command("дуэль"))
async def cmd_duel(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение соперника.")
        return
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    winner = random.choice([a, b])
    await message.answer(f"⚔️ Дуэль! Победил {winner}!")

@dp.message(Command("шип"))
async def cmd_ship(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение того, с кем хочешь шиппериться.")
        return
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    percent = random.randint(0, 100)
    await message.answer(f"💞 {a} + {b} = {percent}% совместимости!")

@dp.message(Command("кубик"))
async def cmd_dice(message: types.Message):
    result = random.randint(1, 6)
    await message.answer(f"🎲 Выпало: {result}")

@dp.message(Command("монетка"))
async def cmd_coin(message: types.Message):
    result = random.choice(["Орёл", "Решка"])
    await message.answer(f"🪙 {result}")

@dp.message(Command("рандом"))
async def cmd_random(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Формат: /рандом 1 100")
        return
    try:
        a, b = int(args[1]), int(args[2])
        await message.answer(f"🎯 Случайное число: {random.randint(a, b)}")
    except:
        await message.answer("Неверный формат чисел.")

# ========== РП ==========
RP_ACTIONS = {
    "обнять": "🤗 {a} обнял(а) {b}",
    "поцеловать": "😘 {a} поцеловал(а) {b}",
    "ударить": "👊 {a} ударил(а) {b}",
    "погладить": "✋ {a} погладил(а) {b}",
    "укусить": "🦷 {a} укусил(а) {b}",
    "лизнуть": "👅 {a} лизнул(а) {b}",
}

@dp.message(lambda m: m.text and m.text.split()[0].lower() in RP_ACTIONS)
async def cmd_rp(message: types.Message):
    if not message.reply_to_message:
        return
    cmd = message.text.split()[0].lower()
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    await message.answer(RP_ACTIONS[cmd].format(a=a, b=b))

# ========== СЧЁТЧИК СООБЩЕНИЙ ==========
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    if chat_id in muted and uid in muted[chat_id]:
        if datetime.now() < muted[chat_id][uid]:
            return
        else:
            del muted[chat_id][uid]

    u = get_user(uid)
    u["messages"] += 1
    u["balance"] += 1

# ========== ЗАПУСК ==========
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

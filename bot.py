import asyncio
import logging
import random
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8953012145:AAGEU0AyFtuQFmCAcKwRMZrtR_3hmxQelAU"

DATA_FILE = "data.json"
VIP_PRICE = 50000
VIP_DAYS = 7
CASE_COOLDOWN_HOURS = 1

# ========== ФАЙЛ ДАННЫХ ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid, name=None):
    data = load_data()
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "name": name or f"ID{uid}", "iriski": 0, "messages": 0,
            "wins": 0, "losses": 0, "points": 0, "level": 1,
            "last_bonus": None, "last_case": None, "vip_until": None
        }
    elif name:
        data[uid]["name"] = name
    save_data(data)
    return data[uid]

def update_user(uid, **kwargs):
    data = load_data()
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "name": f"ID{uid}", "iriski": 0, "messages": 0,
            "wins": 0, "losses": 0, "points": 0, "level": 1,
            "last_bonus": None, "last_case": None, "vip_until": None
        }
    data[uid].update(kwargs)
    save_data(data)

def is_vip(uid):
    u = get_user(uid)
    if not u.get("vip_until"):
        return False
    try:
        return datetime.fromisoformat(u["vip_until"]) > datetime.now()
    except:
        return False

# ========== УРОВНИ ОПЫТА ==========
def required_points(level):
    return 250 * level * (level + 1)

def get_level(points):
    level = 1
    while points >= required_points(level):
        level += 1
    return level - 1 if level > 1 else 1

def sync_points(uid):
    u = get_user(uid)
    earned = (u["iriski"] // 1000) * 200
    if earned > u.get("points", 0):
        update_user(uid, points=earned, level=get_level(earned))

# ========== УРОВНИ ИРИСОК ==========
IRISKI_LEVELS = [
    (0, "Новичок"),
    (500, "Копитель"),
    (2000, "Богач"),
    (5000, "Торговец"),
    (10000, "Инвестор"),
    (25000, "Банкир"),
    (50000, "Магнат"),
    (100000, "Олигарх"),
    (250000, "Легенда"),
    (500000, "Король ирисок"),
]

def get_iriski_level(iriski):
    level = 1
    title = "Новичок"
    for i, (need, name) in enumerate(IRISKI_LEVELS, 1):
        if iriski >= need:
            level = i
            title = name
    return level, title

# ========== АНТИ-БОТ ==========
antibot = {}
bot_enabled = {}

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================================================
#                МЕНЮ
# ==================================================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Кейс", callback_data="menu_case")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="menu_economy")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="⭐ VIP", callback_data="menu_vip")]
    ])

def economy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data="eco_balance"),
         InlineKeyboardButton(text="🏆 Топ", callback_data="eco_top")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")]
    ])

def stats_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Топ по ирискам", callback_data="stats_iriski")],
        [InlineKeyboardButton(text="💬 Топ по сообщениям", callback_data="stats_messages")],
        [InlineKeyboardButton(text="📈 Общая статистика", callback_data="stats_total")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")]
    ])

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.first_name)
    bot_enabled[message.chat.id] = True
    await message.answer(
        "🎰 <b>Darkgram Casino</b>\n\n"
        "🎁 <b>Кейс</b> — раз в час даёт ириски\n"
        "💎 <b>Ириски</b> — валюта, редко падают за сообщения\n"
        "⭐ <b>VIP</b> — x2 ириски и бонусы\n\n"
        "Команды (можно без /):\n"
        "  кейс, баланс, топ, профиль, статистика, вип\n"
        "  кубик 100, слоты 100, рулетка 100 красное, монетка 100\n\n"
        "Пиши команды без / — я пойму.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ==================================================
#                КОЛБЭКИ
# ==================================================
@dp.callback_query(lambda c: c.data == "menu_main")
async def cb_main(call: types.CallbackQuery):
    await call.message.edit_text("🎰 <b>Главное меню</b>", parse_mode="HTML", reply_markup=main_menu())
    await call.answer()

@dp.callback_query(lambda c: c.data == "menu_economy")
async def cb_eco(call: types.CallbackQuery):
    await call.message.edit_text("💰 <b>Экономика</b>", parse_mode="HTML", reply_markup=economy_menu())
    await call.answer()

@dp.callback_query(lambda c: c.data == "menu_stats")
async def cb_stats(call: types.CallbackQuery):
    await call.message.edit_text("📊 <b>Статистика</b>", parse_mode="HTML", reply_markup=stats_menu())
    await call.answer()

@dp.callback_query(lambda c: c.data == "menu_profile")
async def cb_profile(call: types.CallbackQuery):
    await show_profile(call.message)
    await call.answer()

@dp.callback_query(lambda c: c.data == "menu_vip")
async def cb_vip(call: types.CallbackQuery):
    await call.message.edit_text(
        f"⭐ <b>VIP-статус</b>\n\n"
        f"Цена: {VIP_PRICE} ирисок\n"
        f"Срок: {VIP_DAYS} дней\n\n"
        f"Что даёт:\n"
        f"• x2 ириски за сообщения и кейс\n"
        f"• x2 бонус\n"
        f"• x1.5 выигрыш в играх",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить VIP", callback_data="vip_buy")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")]
        ])
    )
    await call.answer()

@dp.callback_query(lambda c: c.data == "menu_case")
async def cb_case(call: types.CallbackQuery):
    await call.message.answer("Напиши команду <code>кейс</code>", parse_mode="HTML")
    await call.answer()

# ==================================================
#                    КЕЙС
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("кейс", "/кейс"))
async def cmd_case(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    now = datetime.now()

    if u.get("last_case"):
        last = datetime.fromisoformat(u["last_case"])
        diff = now - last
        if diff < timedelta(hours=CASE_COOLDOWN_HOURS):
            left = timedelta(hours=CASE_COOLDOWN_HOURS) - diff
            m = left.seconds // 60
            s = left.seconds % 60
            await message.answer(f"⏰ Следующий кейс через <b>{m}мин {s}сек</b>", parse_mode="HTML")
            return

    # Рандом: шансы
    roll = random.random()
    if roll < 0.60:
        reward = random.randint(10, 50)
        rarity = "Обычный"
    elif roll < 0.90:
        reward = random.randint(50, 200)
        rarity = "Редкий"
    elif roll < 0.98:
        reward = random.randint(200, 500)
        rarity = "Эпический"
    else:
        reward = random.randint(500, 2000)
        rarity = "ЛЕГЕНДАРНЫЙ!"

    if is_vip(message.from_user.id):
        reward *= 2

    new_iriski = u["iriski"] + reward
    update_user(message.from_user.id, iriski=new_iriski, last_case=now.isoformat())
    sync_points(message.from_user.id)

    await message.answer(
        f"🎁 <b>Кейс открыт!</b>\n\n"
        f"🎖 Редкость: <b>{rarity}</b>\n"
        f"💎 Получено: <b>+{reward}</b> ирисок\n"
        f"💰 Баланс: {new_iriski}",
        parse_mode="HTML"
    )

# ==================================================
#                    БАЛАНС
# ==================================================
async def show_balance(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    ir_level, ir_title = get_iriski_level(u["iriski"])
    await message.answer(
        "💰 <b>Баланс</b>\n\n"
        f"💎 Ирисок: <b>{u['iriski']}</b>\n"
        f"📊 Уровень ирисок: <b>{ir_level}</b> ({ir_title})\n"
        f"✨ Очков: {u['points']}\n"
        f"🎖 Уровень: {u['level']}\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().strip() in ("баланс", "/баланс"))
async def cmd_balance(message: types.Message):
    await show_balance(message)

@dp.callback_query(lambda c: c.data == "eco_balance")
async def cb_balance(call: types.CallbackQuery):
    await show_balance(call.message)
    await call.answer()

# ==================================================
#                    ТОП ПО ИРИСКАМ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("топ", "/топ"))
async def cmd_top(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("🏆 Пока нет игроков.")
        return
    sorted_users = sorted(data.items(), key=lambda x: x[1]["iriski"], reverse=True)[:10]
    text = "🏆 <b>Топ по ирискам</b>\n\n<pre>"
    text += "Место  Имя           Ириски\n"
    text += "─────────────────────────────\n"
    for i, (uid, u) in enumerate(sorted_users, 1):
        name = u.get("name", f"ID{uid}")
        if len(name) > 12:
            name = name[:11] + "…"
        text += f"{i:<6} {name:<13} {u['iriski']}\n"
    text += "</pre>"
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "eco_top")
async def cb_top(call: types.CallbackQuery):
    await cmd_top(call.message)
    await call.answer()

@dp.callback_query(lambda c: c.data == "stats_iriski")
async def cb_stats_iriski(call: types.CallbackQuery):
    await cmd_top(call.message)
    await call.answer()

# ==================================================
#                ТОП ПО СООБЩЕНИЯМ
# ==================================================
@dp.callback_query(lambda c: c.data == "stats_messages")
async def cb_stats_messages(call: types.CallbackQuery):
    data = load_data()
    if not data:
        await call.message.answer("Пока нет данных.")
        await call.answer()
        return
    sorted_users = sorted(data.items(), key=lambda x: x[1]["messages"], reverse=True)[:10]
    text = "💬 <b>Топ по сообщениям</b>\n\n<pre>"
    text += "Место  Имя           Сообщений\n"
    text += "───────────────────────────────\n"
    for i, (uid, u) in enumerate(sorted_users, 1):
        name = u.get("name", f"ID{uid}")
        if len(name) > 12:
            name = name[:11] + "…"
        text += f"{i:<6} {name:<13} {u['messages']}\n"
    text += "</pre>"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

# ==================================================
#                ОБЩАЯ СТАТИСТИКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("статистика", "/статистика"))
async def cmd_stats(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("📊 Пока нет данных.")
        return
    total_iriski = sum(u["iriski"] for u in data.values())
    total_wins = sum(u["wins"] for u in data.values())
    total_losses = sum(u["losses"] for u in data.values())
    total_messages = sum(u["messages"] for u in data.values())
    richest = max(data.items(), key=lambda x: x[1]["iriski"])

    await message.answer(
        "📊 <b>Общая статистика</b>\n\n"
        f"👥 Игроков: {len(data)}\n"
        f"💎 Всего ирисок: {total_iriski}\n"
        f"💬 Всего сообщений: {total_messages}\n\n"
        "🎮 <b>Игры</b>\n"
        f"🏆 Побед: {total_wins}\n"
        f"💀 Поражений: {total_losses}\n\n"
        f"👑 <b>Самый богатый:</b> {richest[1].get('name', '???')} ({richest[1]['iriski']} 💎)",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "stats_total")
async def cb_stats_total(call: types.CallbackQuery):
    await cmd_stats(call.message)
    await call.answer()

# ==================================================
#                    ПРОФИЛЬ
# ==================================================
async def show_profile(message: types.Message):
    sync_points(message.from_user.id)
    u = get_user(message.from_user.id, message.from_user.first_name)
    next_level = u["level"] + 1
    need = required_points(next_level)
    left = need - u["points"]
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    ir_level, ir_title = get_iriski_level(u["iriski"])

    stars = "⭐" * min(u["level"], 10)
    if u["level"] > 10:
        stars += f" +{u['level'] - 10}"

    await message.answer(
        "👤 <b>Твой профиль</b>\n\n"
        f"🏷 Имя: {message.from_user.first_name}\n"
        f"🔗 Юзернейм: {username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        "💎 <b>Ириски</b>\n"
        f"Баланс: {u['iriski']}\n"
        f"Уровень: <b>{ir_level}</b> ({ir_title})\n\n"
        "📊 <b>Опыт</b>\n"
        f"🎖 Уровень: <b>{u['level']}</b> {stars}\n"
        f"✨ Очки: {u['points']} / {need}\n"
        f"🎯 До следующего: {left}\n\n"
        "📈 <b>Статистика</b>\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().strip() in ("профиль", "/профиль", "я", "/я"))
async def cmd_profile(message: types.Message):
    await show_profile(message)

# ==================================================
#                    VIP
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("вип", "/вип", "vip", "/vip"))
async def cmd_vip(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    if is_vip(message.from_user.id):
        until = datetime.fromisoformat(u["vip_until"]).strftime("%d.%m.%Y %H:%M")
        await message.answer(f"⭐ <b>У тебя активен VIP</b>\n\nДействует до: {until}", parse_mode="HTML")
    else:
        await message.answer(
            f"⭐ <b>VIP-статус</b>\n\n"
            f"Цена: {VIP_PRICE} ирисок\n"
            f"Срок: {VIP_DAYS} дней\n\n"
            f"Напиши <code>вип купить</code> чтобы купить.",
            parse_mode="HTML"
        )

@dp.message(lambda m: m.text and m.text.lower().strip() in ("вип купить", "/вип купить"))
async def cmd_vip_buy(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    if is_vip(message.from_user.id):
        await message.answer("⭐ У тебя уже есть VIP.")
        return
    if u["iriski"] < VIP_PRICE:
        await message.answer(f"❌ Недостаточно ирисок. Нужно: {VIP_PRICE}. У тебя: {u['iriski']}")
        return
    until = (datetime.now() + timedelta(days=VIP_DAYS)).isoformat()
    update_user(message.from_user.id, iriski=u["iriski"] - VIP_PRICE, vip_until=until)
    await message.answer(
        f"⭐ <b>VIP куплен!</b>\n\n"
        f"💎 -{VIP_PRICE} ирисок\n"
        f"📅 Действует до: {datetime.fromisoformat(until).strftime('%d.%m.%Y')}",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "vip_buy")
async def cb_vip_buy(call: types.CallbackQuery):
    await call.message.answer("Напиши <code>вип купить</code>", parse_mode="HTML")
    await call.answer()

# ==================================================
#                АНТИ-БОТ И ОТКЛЮЧЕНИЕ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("антибот", "/антибот")))
async def cmd_antibot(message: types.Message):
    if message.chat.type == "private":
        await message.answer("🛡 Только в группе.")
        return
    args = message.text.replace("/", "").lower().split()
    chat_id = message.chat.id
    if len(args) < 2:
        status = "включён" if antibot.get(chat_id) else "выключен"
        await message.answer(f"🛡 <b>Анти-бот: {status}</b>", parse_mode="HTML")
        return
    if args[1] in ("вкл", "on"):
        antibot[chat_id] = True
        await message.answer("🛡 <b>Анти-бот включён</b>", parse_mode="HTML")
    elif args[1] in ("выкл", "off"):
        antibot[chat_id] = False
        await message.answer("🛡 Анти-бот выключен.")

@dp.message(lambda m: m.text and m.text.lower().strip() in ("бот выкл", "/бот выкл"))
async def cmd_bot_off(message: types.Message):
    bot_enabled[message.chat.id] = False
    await message.answer("🔴 <b>Бот отключён.</b>", parse_mode="HTML")

@dp.message(lambda m: m.text and m.text.lower().strip() in ("бот вкл", "/бот вкл"))
async def cmd_bot_on(message: types.Message):
    bot_enabled[message.chat.id] = True
    await message.answer("🟢 <b>Бот включён.</b>", parse_mode="HTML")

# ==================================================
#                    ИГРЫ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("кубик", "/кубик")))
async def cmd_dice(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🎲 <code>кубик 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно. У тебя: {u['iriski']}")
        return
    p, b = random.randint(1, 6), random.randint(1, 6)
    if p > b:
        win = int(bet * 1.5) if is_vip(message.from_user.id) else bet
        update_user(message.from_user.id, iriski=u["iriski"] + win, wins=u["wins"] + 1)
        sync_points(message.from_user.id)
        await message.answer(f"🏆 Победа!\n🎲 Ты: {p} | Бот: {b}\n💰 +{win}\n💎 {u['iriski'] + win}")
    elif p < b:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n🎲 Ты: {p} | Бот: {b}\n💸 -{bet}\n💎 {u['iriski'] - bet}")
    else:
        await message.answer(f"🤝 Ничья! {p} = {b}")

@dp.message(lambda m: m.text and m.text.lower().startswith(("слоты", "/слоты")))
async def cmd_slots(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🎰 <code>слоты 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно. У тебя: {u['iriski']}")
        return
    sym = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    s1, s2, s3 = random.choice(sym), random.choice(sym), random.choice(sym)
    if s1 == s2 == s3:
        win = bet * (10 if s1 == "7️⃣" else (5 if s1 == "💎" else 3))
        update_user(message.from_user.id, iriski=u["iriski"] + win, wins=u["wins"] + 1)
        sync_points(message.from_user.id)
        await message.answer(f"💥 ДЖЕКПОТ!\n{s1}|{s2}|{s3}\n💰 +{win}\n💎 {u['iriski'] + win}")
    elif s1 == s2 or s2 == s3 or s1 == s3:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        sync_points(message.from_user.id)
        await message.answer(f"✨ Два в ряд!\n{s1}|{s2}|{s3}\n💰 +{bet}\n💎 {u['iriski'] + bet}")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n{s1}|{s2}|{s3}\n💸 -{bet}\n💎 {u['iriski'] - bet}")

@dp.message(lambda m: m.text and m.text.lower().startswith(("рулетка", "/рулетка")))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("🎡 <code>рулетка 100 красное</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка числом.")
        return
    color = args[2].lower().replace("ё", "е")
    if color not in ("красное", "черное"):
        await message.answer("❌ Цвет: красное или чёрное")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно. У тебя: {u['iriski']}")
        return
    result = random.choice(["красное", "черное"])
    if result == color:
        win = int(bet * 1.5) if is_vip(message.from_user.id) else bet
        update_user(message.from_user.id, iriski=u["iriski"] + win, wins=u["wins"] + 1)
        sync_points(message.from_user.id)
        await message.answer(f"🏆 Победа!\n🎡 {result}\n💰 +{win}\n💎 {u['iriski'] + win}")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n🎡 {result}\n💸 -{bet}\n💎 {u['iriski'] - bet}")

@dp.message(lambda m: m.text and m.text.lower().startswith(("монетка", "/монетка")))
async def cmd_coin(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🪙 <code>монетка 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно. У тебя: {u['iriski']}")
        return
    result = random.choice(["орёл", "решка"])
    win = random.choice([True, False])
    if win:
        win_amount = int(bet * 1.5) if is_vip(message.from_user.id) else bet
        update_user(message.from_user.id, iriski=u["iriski"] + win_amount, wins=u["wins"] + 1)
        sync_points(message.from_user.id)
        await message.answer(f"🏆 Победа!\n🪙 {result}\n💰 +{win_amount}\n💎 {u['iriski'] + win_amount}")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n🪙 {result}\n💸 -{bet}\n💎 {u['iriski'] - bet}")

# ==================================================
#                    СЧЁТЧИК
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    if bot_enabled.get(chat_id) is False:
        return

    if antibot.get(chat_id) and message.from_user.is_bot and uid != bot.id:
        try:
            await message.delete()
        except:
            pass
        return

    u = get_user(uid, message.from_user.first_name)

    # Ириски — редко (5% шанс), 1-5 ирисок
    gain = 0
    if random.random() < 0.05:
        gain = random.randint(1, 5)
        if is_vip(uid):
            gain *= 2

    update_user(uid, messages=u["messages"] + 1, iriski=u["iriski"] + gain)
    sync_points(uid)

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Darkgram Casino запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

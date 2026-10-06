import asyncio
import logging
import random
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8953012145:AAEvi1swCkp0CXk3mowQc6kXr_lUXyqx8cM"

DATA_FILE = "data.json"

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
            "name": name or f"ID{uid}", "iriski": 100, "messages": 0,
            "wins": 0, "losses": 0, "points": 0, "level": 1,
            "last_bonus": None, "last_points_check": 0
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
            "name": f"ID{uid}", "iriski": 100, "messages": 0,
            "wins": 0, "losses": 0, "points": 0, "level": 1,
            "last_bonus": None, "last_points_check": 0
        }
    data[uid].update(kwargs)
    save_data(data)

# ========== УРОВНИ ==========
def required_points(level):
    """500, 5000, 15000, 30000, 50000..."""
    return 250 * level * (level + 1)

def get_level(points):
    level = 1
    while points >= required_points(level):
        level += 1
    return level - 1 if level > 1 else 1

def sync_points_from_iriski(uid):
    """За каждые 1000 ирисок даётся +200 очков"""
    u = get_user(uid)
    earned = (u["iriski"] // 1000) * 200
    if earned > u.get("points", 0):
        update_user(uid, points=earned, level=get_level(earned))

# ========== АНТИ-БОТ ==========
antibot = {}

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        "🎰 <b>Darkgram Casino</b>\n\n"
        "💰 <b>Экономика</b>\n"
        "  баланс — сколько ирисок\n"
        "  бонус — ежедневный бонус\n"
        "  топ — таблица лидеров\n"
        "  профиль — уровень и очки\n\n"
        "🎲 <b>Игры</b>\n"
        "  кубик 100\n"
        "  слоты 100\n"
        "  рулетка 100 красное\n"
        "  монетка 100\n\n"
        "🛡 <b>Модерация</b>\n"
        "  антибот вкл / антибот выкл\n\n"
        "💬 Пиши команды без / — я пойму.\n"
        "🎁 За каждые 1000 ирисок даётся +200 очков.",
        parse_mode="HTML"
    )

# ==================================================
#                    БАЛАНС
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("баланс", "/баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        "💰 <b>Баланс</b>\n\n"
        f"💎 Ирисок: <b>{u['iriski']}</b>\n"
        f"✨ Очков: {u['points']}\n"
        f"🎖 Уровень: {u['level']}\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}",
        parse_mode="HTML"
    )

# ==================================================
#                    БОНУС
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("бонус", "/бонус"))
async def cmd_bonus(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    now = datetime.now()
    if u.get("last_bonus"):
        last = datetime.fromisoformat(u["last_bonus"])
        diff = now - last
        if diff < timedelta(hours=24):
            left = timedelta(hours=24) - diff
            h = left.seconds // 3600
            m = (left.seconds % 3600) // 60
            await message.answer(f"⏰ Следующий бонус через <b>{h}ч {m}мин</b>", parse_mode="HTML")
            return
    bonus = random.randint(100, 500)
    new_iriski = u["iriski"] + bonus
    update_user(message.from_user.id, iriski=new_iriski, last_bonus=now.isoformat())
    sync_points_from_iriski(message.from_user.id)
    await message.answer(
        "🎁 <b>Бонус получен!</b>\n\n"
        f"💎 +{bonus} ирисок\n"
        f"💰 Баланс: {new_iriski}",
        parse_mode="HTML"
    )

# ==================================================
#                    ТОП
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("топ", "/топ"))
async def cmd_top(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("🏆 Пока нет игроков.")
        return
    sorted_users = sorted(data.items(), key=lambda x: x[1]["iriski"], reverse=True)[:10]
    text = "🏆 <b>Таблица лидеров</b>\n\n<pre>"
    text += "Место  Имя           Ириски\n"
    text += "─────────────────────────────\n"
    for i, (uid, u) in enumerate(sorted_users, 1):
        name = u.get("name", f"ID{uid}")
        if len(name) > 12:
            name = name[:11] + "…"
        text += f"{i:<6} {name:<13} {u['iriski']}\n"
    text += "</pre>"
    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    ПРОФИЛЬ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("профиль", "/профиль", "я", "/я"))
async def cmd_profile(message: types.Message):
    sync_points_from_iriski(message.from_user.id)
    u = get_user(message.from_user.id, message.from_user.first_name)
    next_level = u["level"] + 1
    need = required_points(next_level)
    left = need - u["points"]
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"

    stars = "⭐" * min(u["level"], 10)
    if u["level"] > 10:
        stars += f" +{u['level'] - 10}"

    await message.answer(
        "👤 <b>Твой профиль</b>\n\n"
        f"🏷 Имя: {message.from_user.first_name}\n"
        f"🔗 Юзернейм: {username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        "📊 <b>Прогресс</b>\n"
        f"🎖 Уровень: <b>{u['level']}</b> {stars}\n"
        f"✨ Очки: {u['points']} / {need}\n"
        f"🎯 До следующего: {left}\n\n"
        "📈 <b>Статистика</b>\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}\n"
        f"💎 Ирисок: {u['iriski']}",
        parse_mode="HTML"
    )

# ==================================================
#                    АНТИ-БОТ
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
        await message.answer(f"🛡 <b>Анти-бот: {status}</b>\n\nИспользуй: <code>антибот вкл</code> или <code>антибот выкл</code>", parse_mode="HTML")
        return
    action = args[1]
    if action in ("вкл", "on", "да"):
        antibot[chat_id] = True
        await message.answer("🛡 <b>Анти-бот включён</b>\n\nСообщения от других ботов будут удаляться.", parse_mode="HTML")
    elif action in ("выкл", "off", "нет"):
        antibot[chat_id] = False
        await message.answer("🛡 Анти-бот выключен.")

# ==================================================
#                    КУБИК
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("кубик", "/кубик")))
async def cmd_dice(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🎲 Формат: <code>кубик 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    p, b = random.randint(1, 6), random.randint(1, 6)
    if p > b:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        sync_points_from_iriski(message.from_user.id)
        await message.answer(f"🏆 <b>Победа!</b>\n\n🎲 Ты: {p} | Бот: {b}\n💰 +{bet}\n💎 Баланс: {u['iriski'] + bet}", parse_mode="HTML")
    elif p < b:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 <b>Проигрыш</b>\n\n🎲 Ты: {p} | Бот: {b}\n💸 -{bet}\n💎 Баланс: {u['iriski'] - bet}", parse_mode="HTML")
    else:
        await message.answer(f"🤝 <b>Ничья!</b>\n\n🎲 {p} = {b}", parse_mode="HTML")

# ==================================================
#                    СЛОТЫ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("слоты", "/слоты")))
async def cmd_slots(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🎰 Формат: <code>слоты 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    sym = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    s1, s2, s3 = random.choice(sym), random.choice(sym), random.choice(sym)
    if s1 == s2 == s3:
        win = bet * (10 if s1 == "7️⃣" else (5 if s1 == "💎" else 3))
        update_user(message.from_user.id, iriski=u["iriski"] + win, wins=u["wins"] + 1)
        sync_points_from_iriski(message.from_user.id)
        await message.answer(f"💥 <b>ДЖЕКПОТ!</b>\n\n{s1} | {s2} | {s3}\n💰 +{win}\n💎 Баланс: {u['iriski'] + win}", parse_mode="HTML")
    elif s1 == s2 or s2 == s3 or s1 == s3:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        sync_points_from_iriski(message.from_user.id)
        await message.answer(f"✨ <b>Два в ряд!</b>\n\n{s1} | {s2} | {s3}\n💰 +{bet}\n💎 Баланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 <b>Проигрыш</b>\n\n{s1} | {s2} | {s3}\n💸 -{bet}\n💎 Баланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    РУЛЕТКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("рулетка", "/рулетка")))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("🎡 Формат: <code>рулетка 100 красное</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return
    color = args[2].lower().replace("ё", "е")
    if color not in ("красное", "черное"):
        await message.answer("❌ Цвет: красное или чёрное")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    result = random.choice(["красное", "черное"])
    if result == color:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        sync_points_from_iriski(message.from_user.id)
        await message.answer(f"🏆 <b>Победа!</b>\n\n🎡 Выпало: {result}\n💰 +{bet}\n💎 Баланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 <b>Проигрыш</b>\n\n🎡 Выпало: {result}\n💸 -{bet}\n💎 Баланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    МОНЕТКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("монетка", "/монетка")))
async def cmd_coin(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("🪙 Формат: <code>монетка 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    result = random.choice(["орёл", "решка"])
    win = random.choice([True, False])
    if win:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        sync_points_from_iriski(message.from_user.id)
        await message.answer(f"🏆 <b>Победа!</b>\n\n🪙 Выпало: {result}\n💰 +{bet}\n💎 Баланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 <b>Проигрыш</b>\n\n🪙 Выпало: {result}\n💸 -{bet}\n💎 Баланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    СЧЁТЧИК + АНТИБОТ
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    # АНТИ-БОТ
    if antibot.get(chat_id) and message.from_user.is_bot and uid != bot.id:
        try:
            await message.delete()
        except:
            pass
        return

    u = get_user(uid, message.from_user.first_name)
    update_user(uid, messages=u["messages"] + 1)
    sync_points_from_iriski(uid)

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Darkgram Casino запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

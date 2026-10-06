import asyncio
import logging
import random
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask, Response
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAGrZHNqRbBnYXdDSN5PwffrmlvAQp75Uf0"

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
        data[uid] = {"name": name or f"ID{uid}", "iriski": 100, "messages": 0, "wins": 0, "losses": 0, "last_bonus": None}
    elif name:
        data[uid]["name"] = name
    save_data(data)
    return data[uid]

def update_user(uid, **kwargs):
    data = load_data()
    uid = str(uid)
    if uid not in data:
        data[uid] = {"name": f"ID{uid}", "iriski": 100, "messages": 0, "wins": 0, "losses": 0, "last_bonus": None}
    data[uid].update(kwargs)
    save_data(data)

# ========== FLASK ==========
flask_app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Топ игроков</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; }
        body { background: #0a0a0a; color: #fff; padding: 16px; min-height: 100vh; }
        h1 { font-size: 22px; font-weight: 600; margin-bottom: 16px; text-align: center; }
        .list { background: #1c1c1e; border-radius: 14px; overflow: hidden; }
        .list-item { display: flex; align-items: center; padding: 12px 14px; border-bottom: 1px solid #2c2c2e; }
        .list-item:last-child { border-bottom: none; }
        .rank { width: 30px; font-size: 16px; font-weight: 600; color: #8e8e93; text-align: center; margin-right: 10px; }
        .rank.gold { color: #ffd60a; }
        .rank.silver { color: #c0c0c0; }
        .rank.bronze { color: #cd7f32; }
        .name { flex: 1; font-size: 15px; font-weight: 500; }
        .score { font-size: 15px; font-weight: 600; color: #ffd60a; }
        .empty { text-align: center; color: #8e8e93; padding: 40px 0; }
    </style>
</head>
<body>
    <h1>🏆 Таблица лидеров</h1>
    <div class="list" id="list"><div class="empty">Загрузка...</div></div>
    <script>
        async function load() {
            const res = await fetch('/api/top');
            const data = await res.json();
            const list = document.getElementById('list');
            if (!data || data.length === 0) {
                list.innerHTML = '<div class="empty">Пока никто не играл</div>';
                return;
            }
            list.innerHTML = data.map((u, i) => {
                let cls = '';
                if (i === 0) cls = 'gold';
                else if (i === 1) cls = 'silver';
                else if (i === 2) cls = 'bronze';
                return `<div class="list-item">
                    <div class="rank ${cls}">${i + 1}</div>
                    <div class="name">${u.name}</div>
                    <div class="score">💎 ${u.iriski}</div>
                </div>`;
            }).join('');
        }
        load();
        setInterval(load, 10000);
    </script>
</body>
</html>
"""

@flask_app.route('/')
def index():
    return Response(HTML, mimetype='text/html')

@flask_app.route('/ping')
def ping():
    return Response("OK", mimetype='text/plain')

@flask_app.route('/api/top')
def api_top():
    data = load_data()
    users = [{"name": u.get("name", f"ID{uid}"), "iriski": u.get("iriski", 0)} for uid, u in data.items()]
    users.sort(key=lambda x: x["iriski"], reverse=True)
    return flask_app.response_class(
        response=json.dumps(users[:50], ensure_ascii=False),
        mimetype='application/json'
    )

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.first_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Таблица лидеров", web_app=WebAppInfo(url="https://iris-clone-bot.onrender.com"))]
    ])
    await message.answer(
        "🎰 <b>Darkgram Casino</b> 🎰\n\n"
        "💰 /баланс\n"
        "🎁 /бонус\n"
        "🏆 /топ\n"
        "📊 /статистика\n\n"
        "🎲 /кубик 100\n"
        "🎰 /слоты 100\n"
        "🎡 /рулетка 100 красное",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message(Command("баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        f"💰 <b>Баланс</b>\n\n"
        f"💎 Ирисок: <b>{u['iriski']}</b>\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}",
        parse_mode="HTML"
    )

@dp.message(Command("бонус"))
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
    update_user(message.from_user.id, iriski=u["iriski"] + bonus, last_bonus=now.isoformat())
    await message.answer(f"🎁 <b>Бонус!</b>\n\n💎 +{bonus}\n💰 Баланс: {u['iriski'] + bonus}", parse_mode="HTML")

@dp.message(Command("топ"))
async def cmd_top(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("🏆 Пока нет игроков.")
        return
    sorted_users = sorted(data.items(), key=lambda x: x[1]["iriski"], reverse=True)[:10]
    text = "🏆 <b>Топ богачей</b>\n\n<pre>"
    text += "№  Имя         Ириски\n"
    text += "─────────────────────\n"
    for i, (uid, u) in enumerate(sorted_users, 1):
        name = u.get("name", f"ID{uid}")
        if len(name) > 10:
            name = name[:9] + "…"
        text += f"{i:<3}{name:<12}{u['iriski']}\n"
    text += "</pre>"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("статистика"))
async def cmd_stats(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("📊 Пока нет данных.")
        return
    total = sum(u["iriski"] for u in data.values())
    wins = sum(u["wins"] for u in data.values())
    losses = sum(u["losses"] for u in data.values())
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Игроков: {len(data)}\n"
        f"💎 Всего ирисок: {total}\n"
        f"🏆 Побед: {wins}\n"
        f"💀 Поражений: {losses}",
        parse_mode="HTML"
    )

@dp.message(Command("кубик"))
async def cmd_dice(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.split()
    if len(args) < 2:
        await message.answer("🎲 /кубик 100")
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
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"🏆 Победа!\n🎲 Ты: {p} | Бот: {b}\n💰 +{bet}\n💎 {u['iriski'] + bet}")
    elif p < b:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n🎲 Ты: {p} | Бот: {b}\n💸 -{bet}\n💎 {u['iriski'] - bet}")
    else:
        await message.answer(f"🤝 Ничья! {p} = {b}")

@dp.message(Command("слоты"))
async def cmd_slots(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.split()
    if len(args) < 2:
        await message.answer("🎰 /слоты 100")
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
        await message.answer(f"💥 ДЖЕКПОТ!\n{s1}|{s2}|{s3}\n💰 +{win}\n💎 {u['iriski'] + win}")
    elif s1 == s2 or s2 == s3 or s1 == s3:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"✨ Два в ряд!\n{s1}|{s2}|{s3}\n💰 +{bet}\n💎 {u['iriski'] + bet}")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n{s1}|{s2}|{s3}\n💸 -{bet}\n💎 {u['iriski'] - bet}")

@dp.message(Command("рулетка"))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.split()
    if len(args) < 3:
        await message.answer("🎡 /рулетка 100 красное")
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
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"🏆 Победа!\n🎡 {result}\n💰 +{bet}\n💎 {u['iriski'] + bet}")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"💀 Проигрыш\n🎡 {result}\n💸 -{bet}\n💎 {u['iriski'] - bet}")

@dp.message()
async def handle_message(message: types.Message):
    uid = message.from_user.id
    if not (message.text or "").strip():
        return
    u = get_user(uid, message.from_user.first_name)
    update_user(uid, messages=u["messages"] + 1, iriski=u["iriski"] + random.randint(1, 10))

async def main():
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_flask, daemon=True).start()
    print("Darkgram Bot запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

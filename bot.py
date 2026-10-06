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
BOT_TOKEN = "8953012145:AAHqw-JLnUAUsAuju3mjTW2cU6eDhBrzXMk"

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
    <h1>Таблица лидеров</h1>
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
                    <div class="score">${u.iriski}</div>
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
        [InlineKeyboardButton(text="Таблица лидеров", web_app=WebAppInfo(url="https://iris-clone-bot.onrender.com"))]
    ])
    await message.answer(
        "<b>Darkgram Casino</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Экономика</b>\n"
        "  баланс — сколько ирисок\n"
        "  бонус — ежедневный бонус\n"
        "  топ — таблица лидеров\n"
        "  статистика — общая статистика\n\n"
        "<b>Игры</b>\n"
        "  кубик 100 — ставка на кубик\n"
        "  слоты 100 — игровые автоматы\n"
        "  рулетка 100 красное — ставка на цвет\n"
        "  монетка 100 — орёл или решка\n\n"
        "<b>Общение</b>\n"
        "  перевести @юзернейм 100 — передать ириски\n"
        "  дуэль @юзернейм 100 — вызвать на дуэль\n\n"
        "Пиши команды без / — я пойму.",
        parse_mode="HTML",
        reply_markup=kb
    )

# ==================================================
#                    БАЛАНС
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("баланс", "/баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        "<b>Баланс</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Ирисок: <b>{u['iriski']}</b>\n"
        f"Побед: {u['wins']}\n"
        f"Поражений: {u['losses']}",
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
            await message.answer(f"Следующий бонус через <b>{h}ч {m}мин</b>", parse_mode="HTML")
            return
    bonus = random.randint(100, 500)
    update_user(message.from_user.id, iriski=u["iriski"] + bonus, last_bonus=now.isoformat())
    await message.answer(
        "<b>Бонус получен</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"+{bonus} ирисок\n"
        f"Баланс: {u['iriski'] + bonus}",
        parse_mode="HTML"
    )

# ==================================================
#                    ТОП
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("топ", "/топ"))
async def cmd_top(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("Пока нет игроков.")
        return
    sorted_users = sorted(data.items(), key=lambda x: x[1]["iriski"], reverse=True)[:10]
    text = "<b>Таблица лидеров</b>\n\n<pre>"
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
#                    СТАТИСТИКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("статистика", "/статистика"))
async def cmd_stats(message: types.Message):
    data = load_data()
    if not data:
        await message.answer("Пока нет данных.")
        return
    total = sum(u["iriski"] for u in data.values())
    wins = sum(u["wins"] for u in data.values())
    losses = sum(u["losses"] for u in data.values())
    await message.answer(
        "<b>Статистика</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Игроков: {len(data)}\n"
        f"Всего ирисок: {total}\n"
        f"Побед: {wins}\n"
        f"Поражений: {losses}",
        parse_mode="HTML"
    )

# ==================================================
#                    КУБИК
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("кубик", "/кубик")))
async def cmd_dice(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("Формат: <code>кубик 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    p, b = random.randint(1, 6), random.randint(1, 6)
    if p > b:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"<b>Победа</b>\nТы: {p} | Бот: {b}\n+{bet}\nБаланс: {u['iriski'] + bet}", parse_mode="HTML")
    elif p < b:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"<b>Проигрыш</b>\nТы: {p} | Бот: {b}\n-{bet}\nБаланс: {u['iriski'] - bet}", parse_mode="HTML")
    else:
        await message.answer(f"<b>Ничья</b>\n{p} = {b}", parse_mode="HTML")

# ==================================================
#                    СЛОТЫ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("слоты", "/слоты")))
async def cmd_slots(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("Формат: <code>слоты 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    sym = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    s1, s2, s3 = random.choice(sym), random.choice(sym), random.choice(sym)
    if s1 == s2 == s3:
        win = bet * (10 if s1 == "7️⃣" else (5 if s1 == "💎" else 3))
        update_user(message.from_user.id, iriski=u["iriski"] + win, wins=u["wins"] + 1)
        await message.answer(f"<b>Джекпот</b>\n{s1} | {s2} | {s3}\n+{win}\nБаланс: {u['iriski'] + win}", parse_mode="HTML")
    elif s1 == s2 or s2 == s3 or s1 == s3:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"<b>Два в ряд</b>\n{s1} | {s2} | {s3}\n+{bet}\nБаланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"<b>Проигрыш</b>\n{s1} | {s2} | {s3}\n-{bet}\nБаланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    РУЛЕТКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("рулетка", "/рулетка")))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("Формат: <code>рулетка 100 красное</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("Ставка должна быть числом.")
        return
    color = args[2].lower().replace("ё", "е")
    if color not in ("красное", "черное"):
        await message.answer("Цвет: красное или чёрное")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    result = random.choice(["красное", "черное"])
    if result == color:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"<b>Победа</b>\nВыпало: {result}\n+{bet}\nБаланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"<b>Проигрыш</b>\nВыпало: {result}\n-{bet}\nБаланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    МОНЕТКА
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("монетка", "/монетка")))
async def cmd_coin(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("Формат: <code>монетка 100</code>", parse_mode="HTML")
        return
    try:
        bet = int(args[1])
    except:
        await message.answer("Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    result = random.choice(["орёл", "решка"])
    win = random.choice([True, False])
    if win:
        update_user(message.from_user.id, iriski=u["iriski"] + bet, wins=u["wins"] + 1)
        await message.answer(f"<b>Победа</b>\nВыпало: {result}\n+{bet}\nБаланс: {u['iriski'] + bet}", parse_mode="HTML")
    else:
        update_user(message.from_user.id, iriski=u["iriski"] - bet, losses=u["losses"] + 1)
        await message.answer(f"<b>Проигрыш</b>\nВыпало: {result}\n-{bet}\nБаланс: {u['iriski'] - bet}", parse_mode="HTML")

# ==================================================
#                    ПЕРЕВОД ИРИСОК
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("перевести", "/перевести")))
async def cmd_transfer(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("Формат: <code>перевести @юзернейм 100</code>", parse_mode="HTML")
        return
    target_username = args[1].lstrip("@").lower()
    try:
        amount = int(args[2])
    except:
        await message.answer("Сумма должна быть числом.")
        return
    if amount <= 0 or u["iriski"] < amount:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    data = load_data()
    target_id = None
    for uid, udata in data.items():
        if udata.get("name", "").lower() == target_username:
            target_id = uid
            break
    if not target_id:
        await message.answer("Игрок не найден. Он должен хотя бы раз написать в чат.")
        return
    if target_id == str(message.from_user.id):
        await message.answer("Нельзя перевести самому себе.")
        return
    target_u = data[target_id]
    update_user(message.from_user.id, iriski=u["iriski"] - amount)
    update_user(target_id, iriski=target_u["iriski"] + amount)
    await message.answer(
        f"<b>Перевод выполнен</b>\n"
        f"Кому: @{target_username}\n"
        f"Сумма: {amount}\n"
        f"Твой баланс: {u['iriski'] - amount}",
        parse_mode="HTML"
    )

# ==================================================
#                    ДУЭЛЬ
# ==================================================
pending_duels = {}

@dp.message(lambda m: m.text and m.text.lower().startswith(("дуэль", "/дуэль")))
async def cmd_duel(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("Формат: <code>дуэль @юзернейм 100</code>", parse_mode="HTML")
        return
    target_username = args[1].lstrip("@").lower()
    try:
        bet = int(args[2])
    except:
        await message.answer("Ставка должна быть числом.")
        return
    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"Недостаточно ирисок. У тебя: {u['iriski']}")
        return
    data = load_data()
    target_id = None
    for uid, udata in data.items():
        if udata.get("name", "").lower() == target_username:
            target_id = uid
            break
    if not target_id:
        await message.answer("Игрок не найден.")
        return
    if target_id == str(message.from_user.id):
        await message.answer("Нельзя вызвать себя.")
        return
    target_u = data[target_id]
    if target_u["iriski"] < bet:
        await message.answer("У соперника недостаточно ирисок.")
        return

    duel_id = f"{message.from_user.id}_{target_id}_{int(datetime.now().timestamp())}"
    pending_duels[duel_id] = {
        "challenger_id": str(message.from_user.id),
        "challenger_name": message.from_user.first_name,
        "target_id": target_id,
        "target_name": target_u["name"],
        "bet": bet,
        "chat_id": message.chat.id
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Принять", callback_data=f"duel_accept_{duel_id}"),
         InlineKeyboardButton(text="Отклонить", callback_data=f"duel_decline_{duel_id}")]
    ])
    await message.answer(
        f"<b>Вызов на дуэль</b>\n"
        f"Вызвал: {message.from_user.first_name}\n"
        f"Вызван: {target_u['name']}\n"
        f"Ставка: {bet}\n\n"
        f"У соперника 5 минут.",
        parse_mode="HTML",
        reply_markup=kb
    )
    asyncio.create_task(duel_timeout(duel_id))

async def duel_timeout(duel_id):
    await asyncio.sleep(300)
    if duel_id in pending_duels:
        d = pending_duels.pop(duel_id)
        try:
            await bot.send_message(d["chat_id"], f"<b>Дуэль отменена</b> — {d['target_name']} не ответил.", parse_mode="HTML")
        except:
            pass

@dp.callback_query(lambda c: c.data.startswith("duel_accept_"))
async def cb_accept(call: types.CallbackQuery):
    duel_id = call.data.replace("duel_accept_", "")
    if duel_id not in pending_duels:
        await call.answer("Дуэль истекла.", show_alert=True)
        return
    d = pending_duels.pop(duel_id)
    if str(call.from_user.id) != d["target_id"]:
        await call.answer("Это не твоя дуэль.", show_alert=True)
        return
    u1 = get_user(int(d["challenger_id"]), d["challenger_name"])
    u2 = get_user(int(d["target_id"]), d["target_name"])
    bet = d["bet"]
    if u1["iriski"] < bet or u2["iriski"] < bet:
        await call.message.edit_text("Недостаточно ирисок у кого-то из игроков.")
        return
    r1, r2 = random.randint(1, 6), random.randint(1, 6)
    if r1 == r2:
        await call.message.edit_text(f"<b>Ничья</b>\n{d['challenger_name']}: {r1}\n{d['target_name']}: {r2}", parse_mode="HTML")
        return
    if r1 > r2:
        winner, loser = d["challenger_id"], d["target_id"]
        wname, lname = d["challenger_name"], d["target_name"]
    else:
        winner, loser = d["target_id"], d["challenger_id"]
        wname, lname = d["target_name"], d["challenger_name"]
    wu = get_user(int(winner))
    lu = get_user(int(loser))
    update_user(int(winner), iriski=wu["iriski"] + bet, wins=wu["wins"] + 1)
    update_user(int(loser), iriski=lu["iriski"] - bet, losses=lu["losses"] + 1)
    await call.message.edit_text(
        f"<b>Дуэль завершена</b>\n"
        f"{d['challenger_name']}: {r1}\n"
        f"{d['target_name']}: {r2}\n\n"
        f"Победил: <b>{wname}</b>\n"
        f"Выигрыш: {bet}",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("duel_decline_"))
async def cb_decline(call: types.CallbackQuery):
    duel_id = call.data.replace("duel_decline_", "")
    if duel_id not in pending_duels:
        await call.answer("Дуэль истекла.", show_alert=True)
        return
    d = pending_duels.pop(duel_id)
    if str(call.from_user.id) != d["target_id"]:
        await call.answer("Это не твоя дуэль.", show_alert=True)
        return
    await call.message.edit_text(f"<b>Дуэль отклонена</b>\n{d['target_name']} отказался.", parse_mode="HTML")

# ==================================================
#                    СЧЁТЧИК
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    uid = message.from_user.id
    if not (message.text or "").strip():
        return
    u = get_user(uid, message.from_user.first_name)
    update_user(uid, messages=u["messages"] + 1, iriski=u["iriski"] + random.randint(1, 10))

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_flask, daemon=True).start()
    print("Darkgram Casino запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

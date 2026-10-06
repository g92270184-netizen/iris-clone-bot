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
BOT_TOKEN = "8953012145:AAG7lEEvJn3s6gK3VlbyJ0vMYkTi6zUUv2E"

DATA_FILE = "data.json"

# ========== РЕДКОСТИ ==========
RARITY_EMOJI = {
    "common": "⚪", "rare": "🟢", "epic": "🔵",
    "legendary": "🟣", "mythic": "🔴", "divine": "🟡"
}
RARITY_NAMES = {
    "common": "Обычный", "rare": "Редкий", "epic": "Эпический",
    "legendary": "Легендарный", "mythic": "Мифический", "divine": "Божественный"
}
RARITY_PRICE = {
    "common": 100, "rare": 500, "epic": 2000,
    "legendary": 10000, "mythic": 50000, "divine": 250000
}
CRAFT_NEXT = {
    "common": "rare", "rare": "epic", "epic": "legendary",
    "legendary": "mythic", "mythic": "divine"
}

CASES = {
    "обычный": {"price": 500, "chances": {"common": 0.60, "rare": 0.30, "epic": 0.10}},
    "редкий": {"price": 2000, "chances": {"rare": 0.50, "epic": 0.35, "legendary": 0.15}},
    "эпический": {"price": 5000, "chances": {"epic": 0.50, "legendary": 0.35, "mythic": 0.15}},
    "легендарный": {"price": 15000, "chances": {"legendary": 0.60, "mythic": 0.30, "divine": 0.10}},
    "божественный": {"price": 50000, "chances": {"mythic": 0.70, "divine": 0.30}}
}

def generate_id(rarity):
    if rarity == "common": return str(random.randint(1000000, 9999999))
    if rarity == "rare": return str(random.randint(100000, 999999))
    if rarity == "epic": return str(random.randint(10000, 99999))
    if rarity == "legendary": return str(random.randint(1000, 9999))
    if rarity == "mythic": return str(random.randint(100, 999))
    if rarity == "divine": return str(random.randint(10, 99))

def get_rarity(chances):
    r = random.random(); cum = 0
    for rarity, chance in chances.items():
        cum += chance
        if r <= cum: return rarity
    return list(chances.keys())[-1]

# ========== ДАННЫЕ ==========
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid, name=None):
    data = load_data()
    uid = str(uid)
    if uid not in data:
        data[uid] = {"name": name or f"ID{uid}", "iriski": 1000, "ids": [], "messages": 0}
    elif name:
        data[uid]["name"] = name
    save_data(data)
    return data[uid]

def update_user(uid, **kwargs):
    data = load_data()
    uid = str(uid)
    if uid not in data:
        data[uid] = {"name": f"ID{uid}", "iriski": 1000, "ids": [], "messages": 0}
    data[uid].update(kwargs)
    save_data(data)

# ========== АУКЦИОН ==========
def get_auctions():
    data = load_data()
    return data.get("auctions", {})

def save_auctions(auctions):
    data = load_data()
    data["auctions"] = auctions
    save_data(data)

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
        [InlineKeyboardButton(text="🎁 Кейсы", callback_data="show_cases"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inv")],
        [InlineKeyboardButton(text="🔨 Крафт", callback_data="show_craft"),
         InlineKeyboardButton(text="📢 Аукцион", callback_data="show_auction")],
        [InlineKeyboardButton(text="🏆 Коллекция", callback_data="show_coll")]
    ])
    await message.answer(
        "🎰 <b>ID-Кейсы</b>\n\n"
        "⚪ Обычный | 🟢 Редкий | 🔵 Эпический\n"
        "🟣 Легендарный | 🔴 Мифический | 🟡 Божественный\n\n"
        "<b>Команды:</b>\n"
        "  кейсы — список кейсов\n"
        "  открыть обычный\n"
        "  айди — инвентарь\n"
        "  продать 777777 — продать себе\n"
        "  крафт 777777 — 3 в 1\n"
        "  аукцион 777777 5000 — выставить\n"
        "  ставка 777777 6000 — сделать ставку\n"
        "  аукционы — список лотов\n"
        "  обмен @юзер 777777 1000 — продать игроку\n"
        "  коллекция — топ",
        parse_mode="HTML",
        reply_markup=kb
    )

# ==================================================
#                    КЕЙСЫ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("кейсы", "/кейсы"))
async def cmd_cases(message: types.Message):
    text = "🎁 <b>Кейсы</b>\n\n"
    for name, data in CASES.items():
        text += f"<b>{name.capitalize()}</b> — {data['price']} ирисок\n"
        for rarity, chance in data["chances"].items():
            text += f"  {RARITY_EMOJI[rarity]} {RARITY_NAMES[rarity]}: {int(chance*100)}%\n"
        text += "\n"
    text += "Открывай: <code>открыть обычный</code>"
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "show_cases")
async def cb_cases(call: types.CallbackQuery):
    await cmd_cases(call.message); await call.answer()

@dp.message(lambda m: m.text and m.text.lower().startswith(("открыть", "/открыть")))
async def cmd_open(message: types.Message):
    args = message.text.replace("/", "").lower().split()
    if len(args) < 2:
        await message.answer("Формат: <code>открыть обычный</code>", parse_mode="HTML"); return
    case_name = args[1]
    if case_name not in CASES:
        await message.answer("Нет такого кейса."); return
    case = CASES[case_name]
    u = get_user(message.from_user.id, message.from_user.first_name)
    if u["iriski"] < case["price"]:
        await message.answer(f"❌ Недостаточно. Нужно: {case['price']}"); return
    rarity = get_rarity(case["chances"])
    new_id = generate_id(rarity)
    ids = u["ids"] + [{"id": new_id, "rarity": rarity}]
    update_user(message.from_user.id, iriski=u["iriski"] - case["price"], ids=ids)
    await message.answer(
        f"🎁 <b>Кейс открыт!</b>\n\n"
        f"{RARITY_EMOJI[rarity]} <b>{RARITY_NAMES[rarity]}</b>\n"
        f"🆔 <code>{new_id}</code>\n\n"
        f"💰 Баланс: {u['iriski'] - case['price']}",
        parse_mode="HTML"
    )

# ==================================================
#                    ИНВЕНТАРЬ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("айди", "/айди", "инвентарь", "/инвентарь"))
async def cmd_inv(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    if not u["ids"]:
        await message.answer("🎒 У тебя нет ID."); return
    text = "🎒 <b>Твои ID</b>\n\n"
    for item in u["ids"]:
        text += f"{RARITY_EMOJI[item['rarity']]} <code>{item['id']}</code> — {RARITY_NAMES[item['rarity']]}\n"
    total = sum(RARITY_PRICE[i["rarity"]] for i in u["ids"])
    text += f"\n💰 Стоимость: {total}"
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "show_inv")
async def cb_inv(call: types.CallbackQuery):
    await cmd_inv(call.message); await call.answer()

# ==================================================
#                    ПРОДАЖА СЕБЕ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("продать", "/продать")))
async def cmd_sell(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("Формат: <code>продать 777777</code>", parse_mode="HTML"); return
    target_id = args[1]
    u = get_user(message.from_user.id, message.from_user.first_name)
    found = next((i for i in u["ids"] if i["id"] == target_id), None)
    if not found:
        await message.answer("❌ Нет такого ID."); return
    price = RARITY_PRICE[found["rarity"]]
    ids = [i for i in u["ids"] if i["id"] != target_id]
    update_user(message.from_user.id, iriski=u["iriski"] + price, ids=ids)
    await message.answer(
        f"💰 <b>Продан!</b>\n\n"
        f"{RARITY_EMOJI[found['rarity']]} <code>{target_id}</code>\n"
        f"+{price} ирисок\n"
        f"Баланс: {u['iriski'] + price}",
        parse_mode="HTML"
    )

# ==================================================
#                    КРАФТ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("крафт", "/крафт")))
async def cmd_craft(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer(
            "🔨 <b>Крафт</b>\n\n"
            "3 ID одной редкости → 1 ID следующей.\n\n"
            "Формат: <code>крафт 777777</code>",
            parse_mode="HTML"
        ); return
    target_id = args[1]
    u = get_user(message.from_user.id, message.from_user.first_name)
    found = next((i for i in u["ids"] if i["id"] == target_id), None)
    if not found:
        await message.answer("❌ Нет такого ID."); return
    rarity = found["rarity"]
    if rarity not in CRAFT_NEXT:
        await message.answer("❌ Божественные ID не крафтятся."); return
    same = [i for i in u["ids"] if i["rarity"] == rarity]
    if len(same) < 3:
        await message.answer(f"❌ Нужно 3 ID редкости {RARITY_NAMES[rarity]}. У тебя: {len(same)}"); return
    to_remove = same[:3]
    ids = [i for i in u["ids"] if i not in to_remove]
    new_rarity = CRAFT_NEXT[rarity]
    new_id = generate_id(new_rarity)
    ids.append({"id": new_id, "rarity": new_rarity})
    update_user(message.from_user.id, ids=ids)
    await message.answer(
        f"🔨 <b>Крафт успешен!</b>\n\n"
        f"Убрано: 3 × {RARITY_EMOJI[rarity]} {RARITY_NAMES[rarity]}\n"
        f"Получено: {RARITY_EMOJI[new_rarity]} <b>{RARITY_NAMES[new_rarity]}</b>\n"
        f"🆔 <code>{new_id}</code>",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "show_craft")
async def cb_craft(call: types.CallbackQuery):
    await call.message.answer(
        "🔨 <b>Крафт</b>\n\n"
        "3 ID одной редкости → 1 следующей.\n\n"
        "Формат: <code>крафт 777777</code>",
        parse_mode="HTML"
    ); await call.answer()

# ==================================================
#                    АУКЦИОН
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("аукцион ", "/аукцион ")))
async def cmd_auction(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("Формат: <code>аукцион 777777 5000</code>", parse_mode="HTML"); return
    target_id = args[1]
    try:
        start_price = int(args[2])
    except:
        await message.answer("❌ Цена числом."); return
    if start_price < 100:
        await message.answer("❌ Минимальная цена: 100"); return
    u = get_user(message.from_user.id, message.from_user.first_name)
    found = next((i for i in u["ids"] if i["id"] == target_id), None)
    if not found:
        await message.answer("❌ Нет такого ID."); return
    auctions = get_auctions()
    if target_id in auctions:
        await message.answer("❌ Уже на аукционе."); return
    auctions[target_id] = {
        "seller_id": str(message.from_user.id),
        "seller_name": message.from_user.first_name,
        "rarity": found["rarity"],
        "price": start_price,
        "top_bidder": None,
        "top_bidder_name": None,
        "created": datetime.now().isoformat()
    }
    save_auctions(auctions)
    # Убираем из инвентаря
    ids = [i for i in u["ids"] if i["id"] != target_id]
    update_user(message.from_user.id, ids=ids)
    await message.answer(
        f"📢 <b>Аукцион создан!</b>\n\n"
        f"{RARITY_EMOJI[found['rarity']]} <code>{target_id}</code>\n"
        f"Стартовая цена: {start_price}\n\n"
        f"Ставки: <code>ставка {target_id} сумма</code>",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().strip() in ("аукционы", "/аукционы", "аукцион", "/аукцион"))
async def cmd_auctions(message: types.Message):
    auctions = get_auctions()
    if not auctions:
        await message.answer("📢 Аукционов пока нет."); return
    text = "📢 <b>Активные аукционы</b>\n\n"
    for tid, a in auctions.items():
        top = a["top_bidder_name"] or "нет ставок"
        text += (
            f"{RARITY_EMOJI[a['rarity']]} <code>{tid}</code>\n"
            f"  Продавец: {a['seller_name']}\n"
            f"  Цена: {a['price']}\n"
            f"  Лидер: {top}\n\n"
        )
    text += "Ставка: <code>ставка 777777 5000</code>"
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "show_auction")
async def cb_auction(call: types.CallbackQuery):
    await cmd_auctions(call.message); await call.answer()

@dp.message(lambda m: m.text and m.text.lower().startswith(("ставка", "/ставка")))
async def cmd_bid(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 3:
        await message.answer("Формат: <code>ставка 777777 5000</code>", parse_mode="HTML"); return
    target_id = args[1]
    try:
        amount = int(args[2])
    except:
        await message.answer("❌ Сумма числом."); return
    auctions = get_auctions()
    if target_id not in auctions:
        await message.answer("❌ Лот не найден."); return
    a = auctions[target_id]
    if str(message.from_user.id) == a["seller_id"]:
        await message.answer("❌ Ты продавец."); return
    if amount <= a["price"]:
        await message.answer(f"❌ Ставка должна быть больше {a['price']}"); return
    u = get_user(message.from_user.id, message.from_user.first_name)
    if u["iriski"] < amount:
        await message.answer(f"❌ Недостаточно. У тебя: {u['iriski']}"); return
    # Возвращаем прошлому лидеру
    if a["top_bidder"]:
        prev = get_user(int(a["top_bidder"]))
        update_user(int(a["top_bidder"]), iriski=prev["iriski"] + a["price"])
    # Списываем у нового
    update_user(message.from_user.id, iriski=u["iriski"] - amount)
    a["price"] = amount
    a["top_bidder"] = str(message.from_user.id)
    a["top_bidder_name"] = message.from_user.first_name
    save_auctions(auctions)
    await message.answer(
        f"✅ <b>Ставка принята</b>\n\n"
        f"Лот: <code>{target_id}</code>\n"
        f"Новая цена: {amount}\n"
        f"Лидер: {message.from_user.first_name}",
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text and m.text.lower().startswith(("завершить", "/завершить")))
async def cmd_finish_auction(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 2:
        await message.answer("Формат: <code>завершить 777777</code>", parse_mode="HTML"); return
    target_id = args[1]
    auctions = get_auctions()
    if target_id not in auctions:
        await message.answer("❌ Лот не найден."); return
    a = auctions[target_id]
    if str(message.from_user.id) != a["seller_id"]:
        await message.answer("❌ Только продавец может завершить."); return
    if not a["top_bidder"]:
        # Никто не купил — возвращаем ID продавцу
        seller = get_user(int(a["seller_id"]))
        ids = seller["ids"] + [{"id": target_id, "rarity": a["rarity"]}]
        update_user(int(a["seller_id"]), ids=ids)
        del auctions[target_id]; save_auctions(auctions)
        await message.answer("❌ Никто не купил. ID возвращён."); return
    # Отдаём ID покупателю
    buyer = get_user(int(a["top_bidder"]))
    ids = buyer["ids"] + [{"id": target_id, "rarity": a["rarity"]}]
    update_user(int(a["top_bidder"]), ids=ids)
    # Деньги продавцу
    seller = get_user(int(a["seller_id"]))
    update_user(int(a["seller_id"]), iriski=seller["iriski"] + a["price"])
    del auctions[target_id]; save_auctions(auctions)
    await message.answer(
        f"✅ <b>Аукцион завершён</b>\n\n"
        f"{RARITY_EMOJI[a['rarity']]} <code>{target_id}</code>\n"
        f"Купил: {a['top_bidder_name']}\n"
        f"Цена: {a['price']}",
        parse_mode="HTML"
    )

# ==================================================
#                    ОБМЕН
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().startswith(("обмен", "/обмен")))
async def cmd_trade(message: types.Message):
    args = message.text.replace("/", "").split()
    if len(args) < 4:
        await message.answer("Формат: <code>обмен @юзернейм 777777 1000</code>", parse_mode="HTML"); return
    target_username = args[1].lstrip("@").lower()
    target_id = args[2]
    try:
        price = int(args[3])
    except:
        await message.answer("❌ Цена числом."); return
    u = get_user(message.from_user.id, message.from_user.first_name)
    found = next((i for i in u["ids"] if i["id"] == target_id), None)
    if not found:
        await message.answer("❌ Нет такого ID."); return
    # Ищем покупателя
    data = load_data()
    buyer_id = None
    for uid, udata in data.items():
        if uid == "auctions":
            continue
        if udata.get("name", "").lower() == target_username:
            buyer_id = uid
            break
    if not buyer_id:
        await message.answer("❌ Игрок не найден."); return
    if buyer_id == str(message.from_user.id):
        await message.answer("❌ Нельзя обменять с собой."); return
    buyer = get_user(int(buyer_id))
    if buyer["iriski"] < price:
        await message.answer("❌ У покупателя недостаточно ирисок."); return
    # Переводим
    ids = [i for i in u["ids"] if i["id"] != target_id]
    update_user(message.from_user.id, iriski=u["iriski"] + price, ids=ids)
    buyer_ids = buyer["ids"] + [found]
    update_user(int(buyer_id), iriski=buyer["iriski"] - price, ids=buyer_ids)
    await message.answer(
        f"🤝 <b>Обмен выполнен</b>\n\n"
        f"{RARITY_EMOJI[found['rarity']]} <code>{target_id}</code>\n"
        f"Продано: {message.from_user.first_name} → {target_username}\n"
        f"Цена: {price}",
        parse_mode="HTML"
    )

# ==================================================
#                    КОЛЛЕКЦИЯ
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("коллекция", "/коллекция"))
async def cmd_coll(message: types.Message):
    data = load_data()
    users_list = []
    for uid, u in data.items():
        if uid == "auctions": continue
        total = sum(RARITY_PRICE[i["rarity"]] for i in u.get("ids", []))
        users_list.append((u.get("name", f"ID{uid}"), total))
    users_list.sort(key=lambda x: x[1], reverse=True)
    text = "🏆 <b>Топ коллекций</b>\n\n<pre>"
    text += "Место  Имя           Стоимость\n"
    text += "─────────────────────────────\n"
    for i, (name, total) in enumerate(users_list[:10], 1):
        if len(name) > 12: name = name[:11] + "…"
        text += f"{i:<6} {name:<13} {total}\n"
    text += "</pre>"
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "show_coll")
async def cb_coll(call: types.CallbackQuery):
    await cmd_coll(call.message); await call.answer()

# ==================================================
#                    БАЛАНС
# ==================================================
@dp.message(lambda m: m.text and m.text.lower().strip() in ("баланс", "/баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    total = sum(RARITY_PRICE[i["rarity"]] for i in u["ids"])
    await message.answer(
        f"💰 <b>Баланс</b>\n\n"
        f"💎 Ирисок: <b>{u['iriski']}</b>\n"
        f"🎒 ID: {len(u['ids'])}\n"
        f"📊 Стоимость: {total}",
        parse_mode="HTML"
    )

# ==================================================
#                    СЧЁТЧИК
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    uid = message.from_user.id
    if not (message.text or "").strip(): return
    u = get_user(uid, message.from_user.first_name)
    update_user(uid, messages=u["messages"] + 1)

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("ID-Кейсы запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

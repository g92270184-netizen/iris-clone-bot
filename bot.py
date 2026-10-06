import asyncio
import logging
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА (в кавычки):
# ==========================================
BOT_TOKEN = "8996485032:AAHVFQ5kYXw184kAEuiEFyzb2pJhQvvAeTc"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА ==========
users = {}
chat_messages = {}
pending_duels = {}  # {duel_id: {...}}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "iriski": 100,
            "messages": 0,
            "wins": 0,
            "losses": 0,
            "last_bonus": None
        }
    return users[uid]

# ==================================================
#                    СТАРТ
# ==================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        "🎰 <b>Darkgram Casino</b> 🎰\n\n"
        "💰 <b>Экономика:</b>\n"
        "  /баланс — сколько ирисок\n"
        "  /бонус — ежедневный бонус\n"
        "  /топ — топ по ирискам\n"
        "  /статистика — общая статистика\n\n"
        "🎲 <b>Игры:</b>\n"
        "  /кубик 100 — ставка на кубик\n"
        "  /слоты 100 — игровые автоматы\n"
        "  /рулетка 100 красное — ставка на цвет\n\n"
        "⚔️ <b>Дуэли:</b>\n"
        "  /дуэль @юзернейм 100 — вызвать игрока\n\n"
        "💬 За каждое сообщение — 1-10 ирисок",
        parse_mode="HTML"
    )

# ==================================================
#                    БАЛАНС
# ==================================================
@dp.message(Command("баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(
        "💰 <b>Твой баланс</b>\n\n"
        f"💎 Ирисок: <b>{u['iriski']}</b>\n"
        f"🏆 Побед: {u['wins']}\n"
        f"💀 Поражений: {u['losses']}",
        parse_mode="HTML"
    )

# ==================================================
#                    БОНУС
# ==================================================
@dp.message(Command("бонус"))
async def cmd_bonus(message: types.Message):
    u = get_user(message.from_user.id)
    now = datetime.now()

    if u["last_bonus"]:
        diff = now - u["last_bonus"]
        if diff < timedelta(hours=24):
            left = timedelta(hours=24) - diff
            hours = left.seconds // 3600
            minutes = (left.seconds % 3600) // 60
            await message.answer(f"⏰ Следующий бонус через: <b>{hours}ч {minutes}мин</b>", parse_mode="HTML")
            return

    bonus = random.randint(100, 500)
    u["iriski"] += bonus
    u["last_bonus"] = now
    await message.answer(
        "🎁 <b>Ежедневный бонус!</b>\n\n"
        f"💎 Получено: <b>+{bonus}</b> ирисок\n"
        f"💰 Баланс: <b>{u['iriski']}</b>",
        parse_mode="HTML"
    )

# ==================================================
#                    ТОП
# ==================================================
@dp.message(Command("топ"))
async def cmd_top(message: types.Message):
    if not users:
        await message.answer("🏆 Пока нет игроков.")
        return

    sorted_users = sorted(users.items(), key=lambda x: x[1]["iriski"], reverse=True)[:10]

    text = "🏆 <b>Топ богачей</b>\n\n<pre>"
    text += "Место  Имя           Ириски\n"
    text += "─────────────────────────────\n"

    for i, (uid, data) in enumerate(sorted_users, 1):
        try:
            member = await bot.get_chat(uid)
            name = member.first_name
        except:
            name = f"ID{uid}"

        if len(name) > 12:
            name = name[:11] + "…"

        text += f"{i:<6} {name:<13} {data['iriski']}\n"

    text += "</pre>"
    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    СТАТИСТИКА
# ==================================================
@dp.message(Command("статистика"))
async def cmd_stats(message: types.Message):
    if not users:
        await message.answer("📊 Пока нет данных.")
        return

    total_iriski = sum(u["iriski"] for u in users.values())
    total_wins = sum(u["wins"] for u in users.values())
    total_losses = sum(u["losses"] for u in users.values())

    await message.answer(
        "📊 <b>Общая статистика казино</b>\n\n"
        f"👥 Игроков: <b>{len(users)}</b>\n"
        f"💎 Всего ирисок: <b>{total_iriski}</b>\n\n"
        "🎮 <b>Игры</b>\n"
        f"🏆 Побед: {total_wins}\n"
        f"💀 Поражений: {total_losses}",
        parse_mode="HTML"
    )

# ==================================================
#                    КУБИК
# ==================================================
@dp.message(Command("кубик"))
async def cmd_dice(message: types.Message):
    u = get_user(message.from_user.id)
    args = message.text.split()

    if len(args) < 2:
        await message.answer("🎲 Используй: <code>/кубик 100</code>", parse_mode="HTML")
        return

    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return

    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return

    player = random.randint(1, 6)
    bot_roll = random.randint(1, 6)

    if player > bot_roll:
        u["iriski"] += bet
        u["wins"] += 1
        result = f"🏆 <b>Победа!</b>\n\n🎲 Ты: {player}\n🎲 Бот: {bot_roll}\n\n💰 +{bet}\n💎 Баланс: {u['iriski']}"
    elif player < bot_roll:
        u["iriski"] -= bet
        u["losses"] += 1
        result = f"💀 <b>Проигрыш</b>\n\n🎲 Ты: {player}\n🎲 Бот: {bot_roll}\n\n💸 -{bet}\n💎 Баланс: {u['iriski']}"
    else:
        result = f"🤝 <b>Ничья!</b>\n\n🎲 Ты: {player}\n🎲 Бот: {bot_roll}"

    await message.answer(result, parse_mode="HTML")

# ==================================================
#                    СЛОТЫ
# ==================================================
@dp.message(Command("слоты"))
async def cmd_slots(message: types.Message):
    u = get_user(message.from_user.id)
    args = message.text.split()

    if len(args) < 2:
        await message.answer("🎰 Используй: <code>/слоты 100</code>", parse_mode="HTML")
        return

    try:
        bet = int(args[1])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return

    if bet <= 0 or u["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {u['iriski']}")
        return

    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    s1, s2, s3 = random.choice(symbols), random.choice(symbols), random.choice(symbols)

    if s1 == s2 == s3:
        win = bet * 10 if s1 == "7️⃣" else (bet * 5 if s1 == "💎" else bet * 3)
        u["iriski"] += win
        u["wins"] += 1
        text = f"💥 <b>ДЖЕКПОТ!</b>\n\n{s1} | {s2} | {s3}\n\n💰 +{win}\n💎 Баланс: {u['iriski']}"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = bet * 2
        u["iriski"] += win - bet
        u["wins"] += 1
        text = f"✨ <b>Два совпадения!</b>\n\n{s1} | {s2} | {s3}\n\n💰 +{win - bet}\n💎 Баланс: {u['iriski']}"
    else:
        u["iriski"] -= bet
        u["losses"] += 1
        text = f"💀 <b>Проигрыш</b>\n\n{s1} | {s2} | {s3}\n\n💸 -{bet}\n💎 Баланс: {u['iriski']}"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    РУЛЕТКА
# ==================================================
@dp.message(Command("рулетка"))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id)
    args = message.text.split()

    if len(args) < 3:
        await message.answer("🎡 Используй: <code>/рулетка 100 красное</code>", parse_mode="HTML")
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
        u["iriski"] += bet
        u["wins"] += 1
        text = f"🏆 <b>Победа!</b>\n\n🎡 Выпало: {result}\n\n💰 +{bet}\n💎 Баланс: {u['iriski']}"
    else:
        u["iriski"] -= bet
        u["losses"] += 1
        text = f"💀 <b>Проигрыш</b>\n\n🎡 Выпало: {result}\n\n💸 -{bet}\n💎 Баланс: {u['iriski']}"

    await message.answer(text, parse_mode="HTML")

# ==================================================
#                    ДУЭЛЬ (PvP)
# ==================================================
@dp.message(Command("дуэль"))
async def cmd_duel(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "⚔️ <b>Как вызвать на дуэль:</b>\n"
            "<code>/дуэль @юзернейм 100</code>",
            parse_mode="HTML"
        )
        return

    # Парсим юзернейм
    target_username = args[1].lstrip("@")
    try:
        bet = int(args[2])
    except:
        await message.answer("❌ Ставка должна быть числом.")
        return

    challenger = get_user(message.from_user.id)
    if challenger["iriski"] < bet:
        await message.answer(f"❌ Недостаточно ирисок. У тебя: {challenger['iriski']}")
        return

    if bet <= 0:
        await message.answer("❌ Ставка должна быть больше 0.")
        return

    # Ищем игрока по юзернейму
    target_id = None
    for uid, u in users.items():
        try:
            member = await bot.get_chat(uid)
            if member.username and member.username.lower() == target_username.lower():
                target_id = uid
                break
        except:
            continue

    if not target_id:
        # Пробуем найти через chat_members
        await message.answer(f"❌ Игрок @{target_username} не найден. Убедись, что он писал в чат.")
        return

    if target_id == message.from_user.id:
        await message.answer("❌ Нельзя вызвать самого себя.")
        return

    target = get_user(target_id)
    if target["iriski"] < bet:
        await message.answer(f"❌ У игрока @{target_username} недостаточно ирисок.")
        return

    # Создаём дуэль
    duel_id = f"{message.from_user.id}_{target_id}_{int(datetime.now().timestamp())}"
    pending_duels[duel_id] = {
        "challenger_id": message.from_user.id,
        "challenger_name": message.from_user.first_name,
        "target_id": target_id,
        "target_username": target_username,
        "bet": bet,
        "chat_id": message.chat.id,
        "created": datetime.now()
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"duel_decline_{duel_id}")
        ]
    ])

    # Отправляем в чат
    await message.answer(
        f"⚔️ <b>Вызов на дуэль!</b>\n\n"
        f"🎯 <b>Кто вызвал:</b> {message.from_user.first_name}\n"
        f"🎯 <b>Кого вызвали:</b> @{target_username}\n"
        f"💎 <b>Ставка:</b> {bet} ирисок\n\n"
        f"⏰ У @{target_username} есть <b>5 минут</b>, чтобы принять или отклонить.",
        parse_mode="HTML",
        reply_markup=kb
    )

    # Автоотмена через 5 минут
    asyncio.create_task(duel_timeout(duel_id))

async def duel_timeout(duel_id):
    await asyncio.sleep(300)  # 5 минут
    if duel_id in pending_duels:
        duel = pending_duels.pop(duel_id)
        try:
            await bot.send_message(
                duel["chat_id"],
                f"⏰ <b>Дуэль отменена</b>\n\n@{duel['target_username']} не ответил за 5 минут.",
                parse_mode="HTML"
            )
        except:
            pass

# ==================================================
#                  ОБРАБОТКА КНОПОК ДУЭЛИ
# ==================================================
@dp.callback_query(lambda c: c.data.startswith("duel_accept_"))
async def cb_duel_accept(call: types.CallbackQuery):
    duel_id = call.data.replace("duel_accept_", "")
    if duel_id not in pending_duels:
        await call.answer("⏰ Дуэль уже истекла.", show_alert=True)
        return

    duel = pending_duels.pop(duel_id)

    # Проверяем, что нажал именно тот, кого вызвали
    if call.from_user.id != duel["target_id"]:
        await call.answer("❌ Это не твоя дуэль!", show_alert=True)
        pending_duels[duel_id] = duel
        return

    challenger = get_user(duel["challenger_id"])
    target = get_user(duel["target_id"])
    bet = duel["bet"]

    if challenger["iriski"] < bet or target["iriski"] < bet:
        await call.message.edit_text("❌ У одного из игроков недостаточно ирисок.")
        return

    # Бросок кубиков
    roll1 = random.randint(1, 6)
    roll2 = random.randint(1, 6)

    if roll1 > roll2:
        winner_id = duel["challenger_id"]
        winner_name = duel["challenger_name"]
        loser_id = duel["target_id"]
    elif roll2 > roll1:
        winner_id = duel["target_id"]
        winner_name = f"@{duel['target_username']}"
        loser_id = duel["challenger_id"]
    else:
        await call.message.edit_text(
            f"🤝 <b>Ничья!</b>\n\n"
            f"{duel['challenger_name']}: 🎲 {roll1}\n"
            f"@{duel['target_username']}: 🎲 {roll2}\n\n"
            f"💎 Ставки возвращены.",
            parse_mode="HTML"
        )
        return

    # Переводим ириски
    get_user(winner_id)["iriski"] += bet
    get_user(loser_id)["iriski"] -= bet
    get_user(winner_id)["wins"] += 1
    get_user(loser_id)["losses"] += 1

    await call.message.edit_text(
        f"⚔️ <b>Дуэль завершена!</b>\n\n"
        f"{duel['challenger_name']}: 🎲 {roll1}\n"
        f"@{duel['target_username']}: 🎲 {roll2}\n\n"
        f"🏆 <b>Победитель:</b> {winner_name}\n"
        f"💰 Выигрыш: <b>{bet}</b> ирисок",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("duel_decline_"))
async def cb_duel_decline(call: types.CallbackQuery):
    duel_id = call.data.replace("duel_decline_", "")
    if duel_id not in pending_duels:
        await call.answer("⏰ Дуэль уже истекла.", show_alert=True)
        return

    duel = pending_duels.pop(duel_id)

    if call.from_user.id != duel["target_id"]:
        await call.answer("❌ Это не твоя дуэль!", show_alert=True)
        pending_duels[duel_id] = duel
        return

    await call.message.edit_text(
        f"❌ <b>Дуэль отклонена</b>\n\n"
        f"@{duel['target_username']} отказался от вызова.",
        parse_mode="HTML"
    )

# ==================================================
#                    СЧЁТЧИК
# ==================================================
@dp.message()
async def handle_message(message: types.Message):
    uid = message.from_user.id
    text = message.text or ""

    if not text.strip():
        return

    u = get_user(uid)
    u["messages"] += 1
    u["iriski"] += random.randint(1, 10)

# ==================================================
#                    ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Darkgram Casino запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

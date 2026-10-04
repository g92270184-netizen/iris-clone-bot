import asyncio
import logging
import random
import re
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, Response, jsonify
from flask_cors import CORS

# ==========================================
BOT_TOKEN = "8870858743:AAEMxWrLtQR45PoScyI9531P47HQtIjKIlg"
WEBAPP_URL = "https://iris-clone-bot.onrender.com"
# ==========================================

DB = 'iris.db'


def init_db():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        uid INTEGER PRIMARY KEY, name TEXT, username TEXT,
        balance INTEGER DEFAULT 0, warns INTEGER DEFAULT 0,
        messages INTEGER DEFAULT 0, partner INTEGER DEFAULT 0,
        bio TEXT DEFAULT 'Не заполнено', photo TEXT DEFAULT ''
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, uid INTEGER, time INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS mutes (
        chat_id INTEGER, uid INTEGER, until INTEGER, reason TEXT,
        PRIMARY KEY (chat_id, uid)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bans (
        chat_id INTEGER, uid INTEGER, until INTEGER, reason TEXT,
        PRIMARY KEY (chat_id, uid)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS warns_db (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, uid INTEGER, reason TEXT, by_uid INTEGER, time INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS mods (
        chat_id INTEGER, uid INTEGER,
        PRIMARY KEY (chat_id, uid)
    )''')
    conn.commit(); conn.close()

init_db()


# ==========================================
# БАЗА
# ==========================================
def get_user(uid, name='', username=''):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE uid=?', (uid,))
    row = c.fetchone()
    if not row:
        c.execute('INSERT INTO users (uid, name, username) VALUES (?, ?, ?)',
                  (uid, name, username))
        conn.commit()
        c.execute('SELECT * FROM users WHERE uid=?', (uid,))
        row = c.fetchone()
    elif name:
        c.execute('UPDATE users SET name=?, username=? WHERE uid=?', (name, username, uid))
        conn.commit()
    conn.close()
    return {
        'uid': row[0], 'name': row[1], 'username': row[2],
        'balance': row[3], 'warns': row[4], 'messages': row[5],
        'partner': row[6], 'bio': row[7], 'photo': row[8]
    }


def update_user(uid, **kwargs):
    conn = sqlite3.connect(DB); c = conn.cursor()
    for k, v in kwargs.items():
        c.execute(f'UPDATE users SET {k}=? WHERE uid=?', (v, uid))
    conn.commit(); conn.close()


def add_message(chat_id, uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT INTO messages (chat_id, uid, time) VALUES (?, ?, ?)',
              (chat_id, uid, int(time.time())))
    c.execute('UPDATE users SET messages = messages + 1 WHERE uid=?', (uid,))
    conn.commit(); conn.close()


def get_chat_top(chat_id, limit=30):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''SELECT uid, COUNT(*) FROM messages 
                 WHERE chat_id=? GROUP BY uid ORDER BY COUNT(*) DESC LIMIT ?''',
              (chat_id, limit))
    rows = c.fetchall()
    result = []
    for uid, cnt in rows:
        c.execute('SELECT name, photo FROM users WHERE uid=?', (uid,))
        r = c.fetchone()
        result.append({
            'uid': uid,
            'name': (r[0] if r else 'Аноним') or 'Аноним',
            'count': cnt,
            'photo': (r[1] if r else '') or ''
        })
    conn.close()
    return result


def is_muted(chat_id, uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT until FROM mutes WHERE chat_id=? AND uid=?', (chat_id, uid))
    row = c.fetchone()
    conn.close()
    if not row: return False
    if row[0] == 0 or row[0] > int(time.time()): return True
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('DELETE FROM mutes WHERE chat_id=? AND uid=?', (chat_id, uid))
    conn.commit(); conn.close()
    return False


def is_banned(chat_id, uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT until FROM bans WHERE chat_id=? AND uid=?', (chat_id, uid))
    row = c.fetchone()
    conn.close()
    if not row: return False
    if row[0] == 0 or row[0] > int(time.time()): return True
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('DELETE FROM bans WHERE chat_id=? AND uid=?', (chat_id, uid))
    conn.commit(); conn.close()
    return False


def get_warns_count(chat_id, uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM warns_db WHERE chat_id=? AND uid=?', (chat_id, uid))
    n = c.fetchone()[0]; conn.close()
    return n


def add_warn(chat_id, uid, reason, by_uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT INTO warns_db (chat_id, uid, reason, by_uid, time) VALUES (?, ?, ?, ?, ?)',
              (chat_id, uid, reason, by_uid, int(time.time())))
    conn.commit(); conn.close()


def remove_warn(chat_id, uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('DELETE FROM warns_db WHERE id IN (SELECT id FROM warns_db WHERE chat_id=? AND uid=? ORDER BY id DESC LIMIT 1)',
              (chat_id, uid))
    conn.commit(); conn.close()


def parse_time(text):
    """5m, 1h, 1d, forever → секунды или 0 для навсегда"""
    text = text.strip().lower()
    if text in ('forever', 'навсегда', '0', 'inf'): return 0
    m = re.match(r'^(\d+)\s*([smhd]?)$', text)
    if not m: return None
    num = int(m.group(1))
    mult = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    return num * mult.get(m.group(2) or 'm', 60)


def fmt_time(sec):
    if sec == 0: return 'навсегда'
    if sec < 60: return f'{sec}с'
    if sec < 3600: return f'{sec // 60}м'
    if sec < 86400: return f'{sec // 3600}ч'
    return f'{sec // 86400}д'


def time_until(ts):
    if ts is None: return '—'
    if ts == 0: return 'навсегда'
    left = ts - int(time.time())
    if left <= 0: return 'истёк'
    return fmt_time(left)


# ==========================================
# ПРОВЕРКА ПРАВ
# ==========================================
async def is_admin_or_mod(message):
    """Проверяет, что автор — админ или модератор"""
    if message.chat.type == 'private': return False
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ('administrator', 'creator'):
            return True
    except: pass
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT 1 FROM mods WHERE chat_id=? AND uid=?',
              (message.chat.id, message.from_user.id))
    row = c.fetchone(); conn.close()
    return bool(row)


async def can_punish(message, target_uid):
    """Нельзя наказывать админов и себя"""
    if message.from_user.id == target_uid: return False, "Себе нельзя"
    try:
        m = await message.bot.get_chat_member(message.chat.id, target_uid)
        if m.status in ('administrator', 'creator'):
            return False, "Это админ"
    except: pass
    return True, ''


# ==========================================
# БОТ
# ==========================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def main_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Топ чата", web_app=WebAppInfo(url=WEBAPP_URL + '/top'))]
    ])
    return kb


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.first_name or '', message.from_user.username or '')
    text = (
        "👋 <b>Ирис-бот</b>\n\n"
        "<b>💰 Экономика:</b>\n"
        "/баланс — баланс\n/бонус — ежедневный бонус\n/передать — перевод\n/топ — топ по ирискам\n\n"
        "<b>🛡 Модерация:</b>\n"
        "/мут uid 1h причина\n/варн uid причина\n/бан uid 1d причина\n/кик uid\n"
        "/размут uid\n/разбан uid\n/снятьварн uid\n"
        "/муты — список мутов\n/баны — список банов\n\n"
        "<b>📊 Статистика:</b>\n"
        "/стат — топ чата\n/рейтинг — топ по сообщениям\n\n"
        "<b>👤 Профиль:</b>\n"
        "/профиль — моя инфа\n/анкета текст — о себе\n\n"
        "<b>🎲 Игры:</b>\n"
        "/рулетка /дуэль /шип /кубик /монетка /рандом a b"
    )
    await message.answer(text, parse_mode='HTML', reply_markup=main_kb())


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)


# ==========================================
# СТАТИСТИКА
# ==========================================
@dp.message(Command("стат", "stat"))
async def cmd_stat(message: types.Message):
    if message.chat.type == 'private':
        await message.answer("Только в группах.")
        return
    top = get_chat_top(message.chat.id, 10)
    if not top:
        await message.answer("Пока нет данных.")
        return
    medals = ['🥇', '🥈', '🥉']
    quote = ''
    for i, u in enumerate(top):
        p = medals[i] if i < 3 else f'{i+1}.'
        quote += f'{p} {u["name"]} — {u["count"]}\n'
    total = sum(u['count'] for u in top)
    text = (
        f'📊 <b>Статистика сообщений</b>\n\n'
        f'<blockquote>{quote}</blockquote>\n'
        f'Всего: <b>{total}</b>'
    )
    await message.answer(text, parse_mode='HTML')


@dp.message(Command("рейтинг"))
async def cmd_rating(message: types.Message):
    await cmd_stat(message)


# ==========================================
# ПРОФИЛЬ
# ==========================================
@dp.message(Command("профиль"))
async def cmd_profile(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.first_name or '', message.from_user.username or '')
    partner_name = 'Нет'
    if u['partner']:
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute('SELECT name FROM users WHERE uid=?', (u['partner'],))
        r = c.fetchone(); conn.close()
        if r: partner_name = r[0]
    warns = get_warns_count(message.chat.id, message.from_user.id) if message.chat.type != 'private' else 0
    await message.answer(
        f"👤 <b>Профиль</b>\n"
        f"Имя: {u['name']}\n"
        f"💰 Баланс: {u['balance']}\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"⚠️ Варнов: {warns}\n"
        f"❤️ Партнёр: {partner_name}\n"
        f"📝 О себе: {u['bio']}",
        parse_mode='HTML'
    )


@dp.message(Command("анкета"))
async def cmd_anketa(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /анкета Твой текст")
        return
    update_user(message.from_user.id, bio=args[1][:200])
    await message.answer(f"✅ Анкета обновлена")


# ==========================================
# ЭКОНОМИКА
# ==========================================
@dp.message(Command("баланс"))
async def cmd_balance(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(f"💰 Баланс: <b>{u['balance']}</b> ирисок", parse_mode='HTML')


@dp.message(Command("бонус"))
async def cmd_bonus(message: types.Message):
    u = get_user(message.from_user.id)
    b = random.randint(10, 50)
    update_user(message.from_user.id, balance=u['balance'] + b)
    await message.answer(f"🎁 Бонус: +{b}. Всего: {u['balance'] + b}")


@dp.message(Command("передать"))
async def cmd_transfer(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение получателя.")
    try:
        amount = int(message.text.split()[1])
    except:
        return await message.answer("Формат: /передать 100 (в ответ)")
    if amount <= 0: return await message.answer("Сумма > 0")
    sender = get_user(message.from_user.id)
    if sender['balance'] < amount:
        return await message.answer("❌ Недостаточно")
    receiver_uid = message.reply_to_message.from_user.id
    receiver = get_user(receiver_uid)
    update_user(message.from_user.id, balance=sender['balance'] - amount)
    update_user(receiver_uid, balance=receiver['balance'] + amount)
    await message.answer(f"✅ Передано {amount} ирисок")


@dp.message(Command("топ"))
async def cmd_top(message: types.Message):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT name, balance FROM users ORDER BY balance DESC LIMIT 10')
    rows = c.fetchall(); conn.close()
    if not rows: return await message.answer("Пусто")
    medals = ['🥇', '🥈', '🥉']
    quote = ''
    for i, (name, bal) in enumerate(rows):
        p = medals[i] if i < 3 else f'{i+1}.'
        quote += f'{p} {name} — {bal}\n'
    await message.answer(f"🏆 <b>Топ по ирискам</b>\n\n<blockquote>{quote}</blockquote>", parse_mode='HTML')


# ==========================================
# МОДЕРАЦИЯ
# ==========================================
async def get_target(message, args):
    """Цель: из reply или из uid"""
    if message.reply_to_message:
        return message.reply_to_message.from_user.id, args
    if args:
        try:
            uid = int(args[0])
            return uid, args[1:]
        except: pass
    return None, args


@dp.message(Command("мут", "mute"))
async def cmd_mute(message: types.Message):
    if message.chat.type == 'private': return
    if not await is_admin_or_mod(message):
        return await message.answer("❌ Нет прав")
    parts = message.text.split()[1:]
    target, rest = await get_target(message, parts)
    if not target: return await message.answer("Ответь на сообщение или укажи uid")
    ok, err = await can_punish(message, target)
    if not ok: return await message.answer(f"❌ {err}")

    time_str = rest[0] if rest else '1h'
    sec = parse_time(time_str)
    if sec is None: return await message.answer("Время: 5m, 1h, 1d, forever")
    reason = ' '.join(rest[1:]) if len(rest) > 1 else 'Без причины'

    until = 0 if sec == 0 else int(time.time()) + sec
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO mutes (chat_id, uid, until, reason) VALUES (?, ?, ?, ?)',
              (message.chat.id, target, until, reason))
    conn.commit(); conn.close()

    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(seconds=sec) if sec else None
        )
    except Exception as e:
        pass

    await message.answer(f"🔇 <code>{target}</code> замучен на {time_until(until)}\n📌 Причина: {reason}", parse_mode='HTML')


@dp.message(Command("варн", "warn"))
async def cmd_warn(message: types.Message):
    if message.chat.type == 'private': return
    if not await is_admin_or_mod(message):
        return await message.answer("❌ Нет прав")
    parts = message.text.split()[1:]
    target, rest = await get_target(message, parts)
    if not target: return await message.answer("Ответь на сообщение или укажи uid")
    ok, err = await can_punish(message, target)
    if not ok: return await message.answer(f"❌ {err}")

    reason = ' '.join(rest) if rest else 'Без причины'
    add_warn(message.chat.id, target, reason, message.from_user.id)
    warns = get_warns_count(message.chat.id, target)

    await message.answer(f"⚠️ <code>{target}</code> варн ({warns}/5)\n📌 {reason}", parse_mode='HTML')

    auto = ''
    if warns >= 5:
        until = int(time.time()) + 86400
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bans (chat_id, uid, until, reason) VALUES (?, ?, ?, ?)',
                  (message.chat.id, target, until, f'{warns} варнов'))
        conn.commit(); conn.close()
        try: await message.bot.ban_chat_member(message.chat.id, target)
        except: pass
        auto = '\n🔨 Автобан на 1 день'
    elif warns >= 3:
        until = int(time.time()) + 3600
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO mutes (chat_id, uid, until, reason) VALUES (?, ?, ?, ?)',
                  (message.chat.id, target, until, f'{warns} варнов'))
        conn.commit(); conn.close()
        try:
            await message.bot.restrict_chat_member(
                message.chat.id, target,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(hours=1)
            )
        except: pass
        auto = '\n🔇 Автомут на 1 час'

    if auto: await message.answer(auto)


@dp.message(Command("бан", "ban"))
async def cmd_ban(message: types.Message):
    if message.chat.type == 'private': return
    if not await is_admin_or_mod(message):
        return await message.answer("❌ Нет прав")
    parts = message.text.split()[1:]
    target, rest = await get_target(message, parts)
    if not target: return await message.answer("Ответь на сообщение или укажи uid")
    ok, err = await can_punish(message, target)
    if not ok: return await message.answer(f"❌ {err}")

    time_str = rest[0] if rest else 'forever'
    sec = parse_time(time_str)
    if sec is None: return await message.answer("Время: 5m, 1h, 1d, forever")
    reason = ' '.join(rest[1:]) if len(rest) > 1 else 'Без причины'
    until = 0 if sec == 0 else int(time.time()) + sec

    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO bans (chat_id, uid, until, reason) VALUES (?, ?, ?, ?)',
              (message.chat.id, target, until, reason))
    conn.commit(); conn.close()

    try: await message.bot.ban_chat_member(message.chat.id, target)
    except Exception as e:
        return await message.answer(f"❌ Не удалось: {e}")

    await message.answer(f"🔨 <code>{target}</code> забанен на {time_until(until)}\n📌 {reason}", parse_mode='HTML')


@dp.message(Command("кик", "kick"))
async def cmd_kick(message: types.Message):
    if message.chat.type == 'private': return
    if not await is_admin_or_mod(message):
        return await message.answer("❌ Нет прав")
    parts = message.text.split()[1:]
    target, _ = await get_target(message, parts)
    if not target: return await message.answer("Ответь или uid")
    ok, err = await can_punish(message, target)
    if not ok: return await message.answer(f"❌ {err}")
    try:
        await message.bot.ban_chat_member(message.chat.id, target)
        await message.bot.unban_chat_member(message.chat.id, target)
        await message.answer(f"👢 <code>{target}</code> кикнут", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ {e}")


@dp.message(Command("размут", "unmute"))
async def cmd_unmute(message: types.Message):
    if not await is_admin_or_mod(message): return
    parts = message.text.split()[1:]
    target, _ = await get_target(message, parts)
    if not target: return
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('DELETE FROM mutes WHERE chat_id=? AND uid=?', (message.chat.id, target))
    conn.commit(); conn.close()
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target,
            permissions=types.ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            )
        )
    except: pass
    await message.answer(f"✅ <code>{target}</code> размучен", parse_mode='HTML')


@dp.message(Command("разбан", "unban"))
async def cmd_unban(message: types.Message):
    if not await is_admin_or_mod(message): return
    parts = message.text.split()[1:]
    target, _ = await get_target(message, parts)
    if not target: return
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('DELETE FROM bans WHERE chat_id=? AND uid=?', (message.chat.id, target))
    conn.commit(); conn.close()
    try: await message.bot.unban_chat_member(message.chat.id, target)
    except: pass
    await message.answer(f"✅ <code>{target}</code> разбанен", parse_mode='HTML')


@dp.message(Command("снятьварн"))
async def cmd_unwarn(message: types.Message):
    if not await is_admin_or_mod(message): return
    parts = message.text.split()[1:]
    target, _ = await get_target(message, parts)
    if not target: return
    remove_warn(message.chat.id, target)
    n = get_warns_count(message.chat.id, target)
    await message.answer(f"✅ <code>{target}</code> снят варн ({n}/5)", parse_mode='HTML')


@dp.message(Command("муты"))
async def cmd_mutes(message: types.Message):
    if not await is_admin_or_mod(message): return
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT uid, until, reason FROM mutes WHERE chat_id=?', (message.chat.id,))
    rows = c.fetchall(); conn.close()
    if not rows: return await message.answer("Мутов нет")
    text = '🔇 <b>Муты</b>\n\n'
    for uid, until, reason in rows:
        text += f'<code>{uid}</code> — {time_until(until)} ({reason})\n'
    await message.answer(text, parse_mode='HTML')


@dp.message(Command("баны"))
async def cmd_bans(message: types.Message):
    if not await is_admin_or_mod(message): return
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT uid, until, reason FROM bans WHERE chat_id=?', (message.chat.id,))
    rows = c.fetchall(); conn.close()
    if not rows: return await message.answer("Банов нет")
    text = '🔨 <b>Баны</b>\n\n'
    for uid, until, reason in rows:
        text += f'<code>{uid}</code> — {time_until(until)} ({reason})\n'
    await message.answer(text, parse_mode='HTML')


# ==========================================
# ИГРЫ
# ==========================================
@dp.message(Command("рулетка"))
async def cmd_roulette(message: types.Message):
    u = get_user(message.from_user.id)
    bet = random.randint(1, 50)
    if random.random() < 0.5:
        update_user(message.from_user.id, balance=u['balance'] + bet)
        await message.answer(f"🎉 Выиграл {bet}! Баланс: {u['balance'] + bet}")
    else:
        new = max(0, u['balance'] - bet)
        update_user(message.from_user.id, balance=new)
        await message.answer(f"😢 Проиграл {bet}. Баланс: {new}")


@dp.message(Command("дуэль"))
async def cmd_duel(message: types.Message):
    if not message.reply_to_message: return await message.answer("Ответь на соперника.")
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    w = random.choice([a, b])
    await message.answer(f"⚔️ Победил {w}!")


@dp.message(Command("шип"))
async def cmd_ship(message: types.Message):
    if not message.reply_to_message: return await message.answer("Ответь на сообщение.")
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    await message.answer(f"💞 {a} + {b} = {random.randint(0,100)}%")


@dp.message(Command("кубик"))
async def cmd_dice(message: types.Message):
    await message.answer(f"🎲 {random.randint(1,6)}")


@dp.message(Command("монетка"))
async def cmd_coin(message: types.Message):
    await message.answer(f"🪙 {random.choice(['Орел','Решка'])}")


@dp.message(Command("рандом"))
async def cmd_random(message: types.Message):
    args = message.text.split()
    if len(args) < 3: return await message.answer("Формат: /рандом 1 100")
    try:
        a, b = int(args[1]), int(args[2])
        await message.answer(f"🎯 {random.randint(a, b)}")
    except: await message.answer("Неверный формат")


# ==========================================
# РП
# ==========================================
RP_ACTIONS = {
    "обнять": "🤗 {a} обнял(а) {b}",
    "поцеловать": "😘 {a} поцеловал(а) {b}",
    "ударить": "👊 {a} ударил(а) {b}",
    "погладить": "✋ {a} погладил(а) {b}",
    "укусить": "🦷 {a} укусил(а) {b}",
    "лизнуть": "👅 {a} лизнул(а) {b}",
}

@dp.message(lambda m: m.text and m.text.split() and m.text.split()[0].lower() in RP_ACTIONS)
async def cmd_rp(message: types.Message):
    if not message.reply_to_message: return
    cmd = message.text.split()[0].lower()
    a = message.from_user.first_name
    b = message.reply_to_message.from_user.first_name
    await message.answer(RP_ACTIONS[cmd].format(a=a, b=b))


# ==========================================
# СЧЁТЧИК + АНТИМУТ
# ==========================================
@dp.message()
async def handle_message(message: types.Message):
    if not message.from_user or message.from_user.is_bot: return
    text = message.text or ''
    if not text.strip(): return

    chat_id = message.chat.id
    uid = message.from_user.id

    if message.chat.type in ('group', 'supergroup'):
        if is_banned(chat_id, uid):
            try: await message.delete()
            except: pass
            return

        if is_muted(chat_id, uid):
            try: await message.delete()
            except: pass
            return

        get_user(uid, message.from_user.first_name or '', message.from_user.username or '')
        add_message(chat_id, uid)


# ==========================================
# FLASK — HTML ТОП
# ==========================================
HTML_TOP = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Топ чата</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif}
body{background:#0a0a0a;color:#fff;padding:16px;min-height:100vh}
.header{margin-bottom:24px}
.header h1{font-size:22px;font-weight:700;letter-spacing:-.5px}
.loader{display:flex;justify-content:center;padding:60px}
.loader div{width:24px;height:24px;border:2px solid #2c2c2e;border-top-color:#ffd60a;border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.podium{display:flex;align-items:flex-end;justify-content:center;gap:6px;margin-bottom:24px}
.podium-item{display:flex;flex-direction:column;align-items:center;flex:1;max-width:110px}
.podium-avatar{width:56px;height:56px;border-radius:50%;object-fit:cover;margin-bottom:6px;border:3px solid;background:#2c2c2e}
.podium-name{font-size:12px;font-weight:600;text-align:center;max-width:100px;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.podium-score{font-size:12px;color:#ffd60a;font-weight:700;margin-bottom:6px}
.podium-base{width:100%;border-radius:10px 10px 0 0;display:flex;justify-content:center;align-items:flex-start;padding-top:8px;font-size:26px;font-weight:900;color:rgba(0,0,0,.55)}
.podium-1{background:linear-gradient(180deg,#ffd60a,#c9a000);height:110px}
.podium-2{background:linear-gradient(180deg,#d0d0d0,#909090);height:85px}
.podium-3{background:linear-gradient(180deg,#e8a87c,#a05a2c);height:68px}
.list{background:#1c1c1e;border-radius:16px;overflow:hidden}
.list-item{display:flex;align-items:center;padding:12px 14px;border-bottom:1px solid #2c2c2e}
.list-item:last-child{border-bottom:none}
.list-rank{width:26px;font-size:14px;font-weight:700;color:#8e8e93;text-align:center;margin-right:10px}
.list-avatar{width:40px;height:40px;border-radius:50%;object-fit:cover;margin-right:10px;background:#2c2c2e}
.list-name{flex:1;font-size:15px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list-score{font-size:14px;font-weight:700;color:#ffd60a}
.empty{text-align:center;padding:40px;color:#8e8e93;font-size:14px}
</style>
</head>
<body>
<div class="header"><h1>🏆 Топ чата</h1></div>
<div id="app"><div class="loader"><div></div></div></div>
<script>
const tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();if(tg.setHeaderColor)tg.setHeaderColor('#0a0a0a')}
function esc(s){return String(s||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]))}
function fmt(n){return Number(n||0).toLocaleString('ru-RU')}
function render(data){
  const app=document.getElementById('app');
  if(!data||!data.length){app.innerHTML='<div class="empty">Пока никто не писал</div>';return}
  const top3=data.slice(0,3),rest=data.slice(3);
  const order=[top3[1],top3[0],top3[2]],ranks=[2,1,3];
  let h='<div class="podium">';
  order.forEach((u,i)=>{if(!u)return;const r=ranks[i];
    const c=r===1?'#ffd60a':r===2?'#d0d0d0':'#e8a87c';
    const av=u.photo?`<img src="${esc(u.photo)}" class="podium-avatar" style="border-color:${c}">`:`<div class="podium-avatar" style="border-color:${c}"></div>`;
    h+=`<div class="podium-item">${av}<div class="podium-name">${esc(u.name)}</div><div class="podium-score">${fmt(u.count)}</div><div class="podium-base podium-${r}">${r}</div></div>`;
  });
  h+='</div><div class="list">';
  rest.forEach((u,i)=>{const r=i+4;
    const av=u.photo?`<img src="${esc(u.photo)}" class="list-avatar">`:`<div class="list-avatar"></div>`;
    h+=`<div class="list-item"><div class="list-rank">${r}</div>${av}<div class="list-name">${esc(u.name)}</div><div class="list-score">${fmt(u.count)}</div></div>`;
  });
  h+='</div>';
  app.innerHTML=h;
}
async function load(){
  try{
    const params=new URLSearchParams(window.location.search);
    const chatId=params.get('chat_id')||tg?.initDataUnsafe?.chat?.id||0;
    const r=await fetch('/api/top?chat_id='+chatId);
    const d=await r.json();
    render(d.top||[]);
  }catch(e){document.getElementById('app').innerHTML='<div class="empty">❌ Ошибка</div>'}
}
load();setInterval(load,15000);
</script>
</body>
</html>'''


flask_app = Flask(__name__)
CORS(flask_app)


@flask_app.route('/')
@flask_app.route('/top')
def flask_index():
    return Response(HTML_TOP, mimetype='text/html')


@flask_app.route('/api/top')
def flask_top():
    chat_id = request.args.get('chat_id', type=int) or 0
    return jsonify({'top': get_chat_top(chat_id, 30)})


@flask_app.route('/health')
def flask_health():
    return 'OK'


from flask import request

def run_flask():
    port = int(os.environ.get('FLASK_PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


threading.Thread(target=run_flask, daemon=True).start()


# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print('Bot started')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

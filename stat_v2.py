import json
import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# === TOKEN va ADMINLAR ===
BOT_TOKEN = "7898788869:AAEJ95exK_eBhbT9_nULblyFJnZkgLLAyKE"
ADMINS = [825063446, 6775888461, 5035706309]

OBUNA_FILE = "obuna.json"
BLOCK_FILE = "blocked.json"
LOG_FILE = "statlog.txt"

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === JSON FUNKSIYALAR ===
def load_json(file, default=None):
    if not os.path.exists(file):
        save_json(file, default or {})
        return default or {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump({str(k): v for k, v in data.items()}, f, indent=4)

def write_log(text):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {text}\n")

# === OBUNA FUNKSIYALARI ===
def load_obuna():
    return load_json(OBUNA_FILE, {})

def save_obuna(data):
    save_json(OBUNA_FILE, data)

# === BLOK FUNKSIYALARI ===
def load_blocked():
    return load_json(BLOCK_FILE, {})

def save_blocked(data):
    save_json(BLOCK_FILE, data)

def is_blocked(user_id):
    data = load_blocked()
    uid = str(user_id)
    if uid in data:
        end = datetime.fromisoformat(data[uid])
        if end > datetime.now():
            return True, end
        else:
            # Blok muddati tugasa o‘chiramiz
            del data[uid]
            save_blocked(data)
    return False, None

def add_block(user_id, days):
    data = load_blocked()
    end_date = datetime.now() + timedelta(days=days)
    data[str(user_id)] = end_date.isoformat()
    save_blocked(data)
    return end_date

def remove_block(user_id):
    data = load_blocked()
    if str(user_id) in data:
        del data[str(user_id)]
        save_blocked(data)
        return True
    return False

# === AVTO TOZALASH OBUNA ===
async def auto_clean_and_alert_admins():
    while True:
        data = load_obuna()
        now = datetime.now()
        yangilangan = {}
        removed_users = []
        old_data = data.copy()

        for uid, iso in data.items():
            dt = datetime.fromisoformat(iso)
            if dt.date() == (now.date() + timedelta(days=1)):
                try:
                    await bot.send_message(int(uid), "⏳ Diqqat! Sizning obunangiz ertaga tugaydi.")
                except:
                    pass
            if dt < now:
                removed_users.append(uid)
            else:
                yangilangan[uid] = iso

        save_obuna(yangilangan)

        for uid in removed_users:
            dt = datetime.fromisoformat(old_data[uid])
            text = (
                f"🔻 <code>{uid}</code> — 🗓 <b>{dt.strftime('%Y-%m-%d')}</b>\n"
                f"⏰ Tekshiruv vaqti: <b>{now.strftime('%Y-%m-%d %H:%M:%S')}</b>\n"
                f"📌 Obunasi tugadi va o‘chirildi."
            )
            for admin_id in ADMINS:
                try:
                    await bot.send_message(admin_id, text)
                except:
                    pass

        await asyncio.sleep(3600)

# === AVTO TEKSHIRISH BLOK ===
async def auto_check_blocked():
    while True:
        data = load_blocked()
        now = datetime.now()
        for uid, end in list(data.items()):
            end_date = datetime.fromisoformat(end)
            if end_date <= now:
                try:
                    await bot.send_message(int(uid), "✅ Sizning blok muddatingiz tugadi. Endi botdan foydalanishingiz mumkin.")
                except:
                    pass
                del data[uid]
                save_blocked(data)
        await asyncio.sleep(3600)

# === ADMIN PANELI ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikani ko‘rish", callback_data="stats")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="users")],
        [InlineKeyboardButton(text="🚫 Bloklanganlar", callback_data="blocked")],
    ])
    await message.answer("🛠 Admin panel:", reply_markup=kb)

# === STATISTIKA CALLBACK ===
@dp.callback_query(F.data == "stats")
async def handle_stats_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await call.answer("⛔ Siz admin emassiz.", show_alert=True)
    await stats_handler(call.message)
    await call.answer()

# === FOYDALANUVCHILAR CALLBACK ===
@dp.callback_query(F.data == "users")
async def handle_users_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await call.answer("⛔ Siz admin emassiz.", show_alert=True)
    await send_users_with_delete_buttons(call.message)
    await call.answer()

# === BLOKLANGANLAR CALLBACK ===
@dp.callback_query(F.data == "blocked")
async def handle_blocked_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await call.answer("⛔ Siz admin emassiz.", show_alert=True)
    await send_blocked_users(call.message)
    await call.answer()

# === /stats KOMANDASI ===
@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    data = load_obuna()
    now = datetime.now()
    active = {uid: dt for uid, dt in data.items() if datetime.fromisoformat(dt) > now}
    expired = {uid: dt for uid, dt in data.items() if datetime.fromisoformat(dt) <= now}

    text = (
        f"📊 <b>Obuna statistikasi:</b>\n\n"
        f"👥 Umumiy: <b>{len(data)}</b>\n"
        f"✅ Faol: <b>{len(active)}</b>\n"
        f"❌ Tugagan: <b>{len(expired)}</b>"
    )
    await message.answer(text)

# === FOYDALANUVCHILARNI KO‘RISH (O‘CHIRISH TUGMASI BILAN) ===
async def send_users_with_delete_buttons(message: Message):
    data = load_obuna()
    now = datetime.now()

    active_users = {uid: dt for uid, dt in data.items() if datetime.fromisoformat(dt) > now}

    if not active_users:
        return await message.answer("🚫 Hozircha faol foydalanuvchi yo‘q.")

    for uid, dt in active_users.items():
        user_text = f"<code>{uid}</code> — 🗓 {datetime.fromisoformat(dt).strftime('%Y-%m-%d')}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"delete_{uid}")]
        ])
        await message.answer(user_text, reply_markup=kb)

# === BLOKLANGANLARNI KO‘RISH ===
async def send_blocked_users(message: Message):
    data = load_blocked()
    now = datetime.now()
    if not data:
        return await message.answer("🚫 Bloklangan foydalanuvchilar yo‘q.")
    for uid, dt in data.items():
        end = datetime.fromisoformat(dt)
        status = "⏳ Hali blokda" if end > now else "✅ Tugagan"
        await message.answer(f"<code>{uid}</code>\n🗓 Tugash: {end.strftime('%Y-%m-%d %H:%M')}\n📌 {status}")

# === FOYDALANUVCHINI O‘CHIRISH ===
@dp.callback_query(F.data.startswith("delete_"))
async def delete_user_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await call.answer("⛔ Siz admin emassiz.", show_alert=True)

    uid = call.data.split("_")[1]
    data = load_obuna()

    if uid in data:
        del data[uid]
        save_obuna(data)
        await call.message.edit_text(f"❌ Foydalanuvchi <code>{uid}</code> o‘chirildi.")
        write_log(f"Admin {call.from_user.id} foydalanuvchini o‘chirdi: {uid}")
    else:
        await call.answer("🚫 Bunday foydalanuvchi topilmadi.", show_alert=True)

# === /check KOMANDASI ===
@dp.message(Command("check"))
async def check_user(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("⚠️ Format: <code>/check user_id</code>")

    uid = parts[1]
    data = load_obuna()

    if uid not in data:
        return await message.answer(f"🔍 <code>{uid}</code> ro‘yxatda yo‘q.")

    dt = datetime.fromisoformat(data[uid])
    status = "✅ Faol" if dt > datetime.now() else "❌ Tugagan"
    await message.answer(f"<code>{uid}</code>\n🗓 Sana: {dt.date()}\n📌 Holati: {status}")

# === /block KOMANDASI ===
@dp.message(Command("block"))
async def block_user(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    parts = message.text.split()
    if len(parts) != 3:
        return await message.answer("⚠️ Format: <code>/block user_id kun</code>")

    uid = parts[1]
    days = int(parts[2])

    if days < 1 or days > 30:
        return await message.answer("⚠️ Kun 1 dan 30 gacha bo‘lishi kerak!")

    end = add_block(uid, days)
    try:
        await bot.send_message(int(uid), f"🚫 Siz {days} kunga bloklandingiz!\n🗓 Tugash: {end.strftime('%Y-%m-%d %H:%M')}")
    except:
        pass

    await message.answer(f"✅ Foydalanuvchi <code>{uid}</code> {days} kunga bloklandi.")

# === /unblock KOMANDASI ===
@dp.message(Command("unblock"))
async def unblock_user(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("⚠️ Format: <code>/unblock user_id</code>")

    uid = parts[1]
    if remove_block(uid):
        await message.answer(f"✅ <code>{uid}</code> blokdan chiqarildi.")
        try:
            await bot.send_message(int(uid), "✅ Siz blokdan chiqarildingiz.")
        except:
            pass
    else:
        await message.answer("🚫 Bunday foydalanuvchi blokda emas.")

# === /blocked KOMANDASI ===
@dp.message(Command("blocked"))
async def blocked_list(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    data = load_blocked()
    if not data:
        return await message.answer("🚫 Bloklangan foydalanuvchilar yo‘q.")

    now = datetime.now()
    text = "🚫 <b>Bloklangan foydalanuvchilar:</b>\n\n"
    for uid, dt in data.items():
        end = datetime.fromisoformat(dt)
        status = "⏳ Hali blokda" if end > now else "✅ Tugagan"
        text += f"<code>{uid}</code> — 🗓 {end.strftime('%Y-%m-%d %H:%M')} ({status})\n"
    await message.answer(text)

# === MAIN ===
async def main():
    asyncio.create_task(auto_clean_and_alert_admins())
    asyncio.create_task(auto_check_blocked())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

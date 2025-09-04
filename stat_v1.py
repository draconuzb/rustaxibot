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
LOG_FILE = "statlog.txt"

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === JSON FUNKSIYALAR ===
def load_obuna():
    if not os.path.exists(OBUNA_FILE):
        save_obuna({})
        return {}
    with open(OBUNA_FILE, "r") as f:
        return json.load(f)

def save_obuna(data):
    # user_id larni har doim str qilib saqlaymiz
    str_data = {str(k): v for k, v in data.items()}
    with open(OBUNA_FILE, "w") as f:
        json.dump(str_data, f, indent=4)

def write_log(text):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {text}\n")

# === AVTO TOZALASH VA ADMINLARGA OGOLANTIRISH ===
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

        await asyncio.sleep(3600)  # 1 soat

# === ADMIN PANELI ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikani ko‘rish", callback_data="stats")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="users")],
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

# === FOYDALANUVCHINI O‘CHIRISH ===
@dp.callback_query(F.data.startswith("delete_"))
async def delete_user_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await call.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        uid = call.data.split("_")[1]
    except IndexError:
        return await call.answer("❌ ID topilmadi.", show_alert=True)

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

# === MAIN ===
async def main():
    asyncio.create_task(auto_clean_and_alert_admins())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

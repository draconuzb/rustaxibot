import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from config import BOT_TOKEN, ADMINS, CARD_NUMBER

# Fayl nomlari
OBUNA_FILE = "obuna.json"
PENDING_FILE = "pending.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

def load_json(file):
    return json.load(open(file)) if os.path.exists(file) else {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def is_subscribed(user_id):
    data = load_json(OBUNA_FILE)
    uid = str(user_id)
    if uid in data:
        end = datetime.fromisoformat(data[uid])
        if end > datetime.now():
            return True
        else:
            del data[uid]
            save_json(OBUNA_FILE, data)
    return False

def add_subscription(user_id, days):
    data = load_json(OBUNA_FILE)
    end_date = datetime.now() + timedelta(days=days)
    data[str(user_id)] = end_date.isoformat()
    save_json(OBUNA_FILE, data)
    return end_date

@dp.message(CommandStart())
async def start(message: Message):
    if is_subscribed(message.from_user.id):
        end = datetime.fromisoformat(load_json(OBUNA_FILE)[str(message.from_user.id)])
        return await message.answer(f"✅ Siz obunadasiz!\n🗓 Tugash: {end.strftime('%Y-%m-%d %H:%M')}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Screenshot yuborish", callback_data="send_ss")]
    ])
    await message.answer(
        f"👋 Salom {message.from_user.full_name}!\n"
        f"💳 Karta: <code>{CARD_NUMBER}</code>\n"
        f"💸 Narx: 200 000 so'm\n\n"
        f"📸 Screenshot yuboring, admin ko‘rib tasdiqlaydi.",
        reply_markup=kb
    )

@dp.callback_query(F.data == "send_ss")
async def ss_call(call: CallbackQuery):
    await call.message.answer("📸 Screenshotni shu yerga yuboring.")
    await call.answer()

@dp.message(F.photo)
async def handle_screenshot(message: Message):
    caption = (
        f"🆕 <b>Yangi to‘lov</b>\n"
        f"👤 @{message.from_user.username or 'no_username'}\n"
        f"🆔 <code>{message.from_user.id}</code>\n"
        f"👥 {message.from_user.full_name}"
    )

    # Tugmalar
    buttons = []
    row = []
    for i in range(1, 31):
        row.append(InlineKeyboardButton(text=f"{i} kun", callback_data=f"select_{message.from_user.id}_{i}"))
        if i % 5 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_{message.from_user.id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
    ])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    for admin_id in ADMINS:
        sent = await bot.send_photo(
            admin_id,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=markup
        )
        pending = load_json(PENDING_FILE)
        pending[str(message.from_user.id)] = {
            "msg_id": sent.message_id,
            "admin_id": admin_id,
            "days": None
        }
        save_json(PENDING_FILE, pending)

    await message.answer("✅ Screenshot yuborildi. Admin tekshiradi.")

@dp.callback_query(F.data.startswith("select_"))
async def select_duration(call: CallbackQuery):
    _, uid, days = call.data.split("_")
    uid = str(uid)
    days = int(days)

    pending = load_json(PENDING_FILE)
    if uid in pending:
        pending[uid]["days"] = days
        save_json(PENDING_FILE, pending)
        await call.answer(f"☑ {days} kun tanlandi.")
    else:
        await call.answer("⚠ Avval screenshot yuborilsin.")

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_user(call: CallbackQuery):
    _, uid = call.data.split("_")
    pending = load_json(PENDING_FILE)

    if uid not in pending:
        return await call.answer("⚠ Bu foydalanuvchi allaqachon tasdiqlangan yoki rad etilgan!", show_alert=True)

    info = pending[uid]
    if not info.get("days"):
        return await call.answer("⛔ Avval kun tanlanishi kerak!", show_alert=True)

    user_id = int(uid)
    days = int(info["days"])
    end = add_subscription(user_id, days)

    await bot.send_message(user_id, f"🎉 Obunangiz {days} kunga yoqildi!\n🗓 Tugash: {end.strftime('%Y-%m-%d %H:%M')}")
    await call.answer("✅ Tasdiqlandi.")
    await bot.delete_message(info["admin_id"], info["msg_id"])

    del pending[uid]
    save_json(PENDING_FILE, pending)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(call: CallbackQuery):
    _, uid = call.data.split("_")
    user_id = int(uid)
    pending = load_json(PENDING_FILE)

    if uid in pending:
        info = pending[uid]
        await bot.delete_message(info["admin_id"], info["msg_id"])
        del pending[uid]
        save_json(PENDING_FILE, pending)

    await bot.send_message(user_id, "❌ To‘lovingiz rad etildi. Iltimos, qayta urinib ko‘ring.")
    await call.answer("🚫 Rad etildi.")

# ✅ /admin komandasi uchun statistikani ko‘rsatish
@dp.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Siz admin emassiz!")
    data = load_json(OBUNA_FILE)
    await message.answer(f"📊 Umumiy obunachilar soni: <b>{len(data)}</b> ta")

# 🔔 Obunasi tugashiga 1 kun qolganlarga eslatma yuborish
async def remind_expiring_users():
    while True:
        data = load_json(OBUNA_FILE)
        now = datetime.now()
        for uid, end in list(data.items()):
            end_date = datetime.fromisoformat(end)
            if 0 < (end_date - now).days <= 1:
                try:
                    await bot.send_message(int(uid), "⏳ Diqqat! Obunangiz 1 kun ichida tugaydi. Iltimos, uni yangilang.")
                except:
                    continue
        await asyncio.sleep(3600)  # 1 soatda bir marta

async def main():
    asyncio.create_task(remind_expiring_users())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import json
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, PeerUser

# 🔑 Telegram API ma'lumotlari
api_id = 21382075
api_hash = '22145968ba0e89dee86eeeab455adc33'

client = TelegramClient('taxi_tolov_bot', api_id, api_hash)

# 📂 Fayllar
OBUNA_FILE = "obuna.json"
BLOCK_FILE = "blocked.json"

# 🚫 Faqat bir marta ogohlantirish uchun
ogohlantirilganlar = set()

# 📂 JSON o‘qish/yozish
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# 🔒 Bloklash
def add_block(user_id, days):
    data = load_json(BLOCK_FILE)
    end = datetime.now() + timedelta(days=days)
    data[str(user_id)] = end.isoformat()
    save_json(BLOCK_FILE, data)
    return end

def is_blocked(user_id):
    data = load_json(BLOCK_FILE)
    uid = str(user_id)
    if uid in data:
        end = datetime.fromisoformat(data[uid])
        if end > datetime.now():
            return True
        else:
            # ⏳ Muddati tugagan
            del data[uid]
            save_json(BLOCK_FILE, data)
    return False

# 🔓 Blok tugaganda xabar yuborish
async def check_block_expire():
    while True:
        data = load_json(BLOCK_FILE)
        now = datetime.now()
        for uid, end in list(data.items()):
            end_date = datetime.fromisoformat(end)
            if end_date <= now:
                try:
                    await client.send_message(int(uid), "✅ Sizning blok muddatingiz tugadi. Endi botdan yana foydalanishingiz mumkin.")
                except:
                    pass
                del data[uid]
                save_json(BLOCK_FILE, data)
        await asyncio.sleep(3600)  # har 1 soatda tekshiradi

# 📩 Oddiy xabarlar uchun handler
@client.on(events.NewMessage)
async def handler(event):
    try:
        sender = await event.get_sender()
        myself = await client.get_me()
        user_id_str = str(sender.id)

        # 🔒 Bloklangan foydalanuvchi bo‘lsa
        if is_blocked(sender.id):
            return await event.reply("🚫 Siz bloklangansiz! Iltimos, muddat tugashini kuting.")

        # 📂 Obuna faylini o‘qish
        obunachilar = load_json(OBUNA_FILE)

        # 🛑 O‘zimiz yoki obunachilar bo‘lsa – chiqamiz
        if str(myself.id) == user_id_str or user_id_str in obunachilar:
            return

        is_blocked_msg = False

        # 📷 Rasm
        if isinstance(event.message.media, MessageMediaPhoto):
            is_blocked_msg = True

        # 🎥 Video
        elif isinstance(event.message.media, MessageMediaDocument):
            mime = event.message.media.document.mime_type
            if mime and mime.startswith("video/"):
                is_blocked_msg = True
            else:
                for attr in event.message.media.document.attributes:
                    if attr.__class__.__name__ in ("VideoSize", "DocumentAttributeVideo"):
                        is_blocked_msg = True
                        break

        # 🔗 Link
        elif event.raw_text and any(x in event.raw_text.lower() for x in ["http://", "https://"]):
            is_blocked_msg = True

        # ❌ Agar obunasiz foydalanuvchi reklama tashlasa
        if is_blocked_msg:
            try:
                await event.delete()
            except Exception as e:
                print(f"❌ Xabar o‘chmadi: {e}")

            # 🔔 Ogohlantirish faqat bir marta
            if user_id_str not in ogohlantirilganlar:
                ism = sender.first_name or "foydalanuvchi"
                mention = f"<a href='tg://user?id={sender.id}'>{ism}</a>"

                javob = (
                    f"👋 Salom {mention}!\n\n"
                    f"📢 Guruhda e'lon qoldirish uchun sizga <b>obuna</b> kerak.\n\n"
                    f"👉 <a href='https://t.me/taxi_tolov_bot?start=start'>Obuna bo'lish</a>\n\n"
                    f"✅ Obunadan so‘ng bemalol e'lon joylashingiz mumkin."
                )

                # Guruhga yuborish
                await client.send_message(event.chat_id, javob, parse_mode="html")

                # Lichkaga yuborish
                try:
                    await client.send_message(PeerUser(sender.id), javob, parse_mode="html")
                except:
                    print(f"❌ {sender.id} lichkasi yopiq")

                ogohlantirilganlar.add(user_id_str)

    except Exception as e:
        print(f"⚠️ Umumiy xatolik: {e}")

# 🔑 Admin komandasi orqali bloklash
@client.on(events.NewMessage(pattern=r"^/block (\d+) (\d+)$"))
async def block_cmd(event):
    try:
        uid = int(event.pattern_match.group(1))
        days = int(event.pattern_match.group(2))

        if days < 1 or days > 30:
            return await event.reply("⚠ Kun 1 dan 30 gacha bo‘lishi kerak!")

        end = add_block(uid, days)

        try:
            await client.send_message(uid, f"🚫 Siz {days} kunga bloklandingiz!\n🗓 Tugash: {end.strftime('%Y-%m-%d %H:%M')}")
        except:
            pass

        await event.reply(f"✅ Foydalanuvchi {uid} {days} kunga bloklandi.")
    except Exception as e:
        await event.reply(f"❌ Xatolik: {e}")

# ▶️ Botni ishga tushirish
async def main():
    await client.start()
    print("✅ Bot ishga tushdi...")
    asyncio.create_task(check_block_expire())
    await client.run_until_disconnected()

asyncio.run(main())

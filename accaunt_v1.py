import json
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, PeerUser

# 🔑 Telegram API ma'lumotlari
api_id = 21382075              # <-- o'zingizniki bilan almashtiring
api_hash = '22145968ba0e89dee86eeeab455adc33'  # <-- o'zingizniki bilan almashtiring

client = TelegramClient('taxi_tolov_bot', api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    try:
        sender = await event.get_sender()
        myself = await client.get_me()

        # 🧾 Har safar obuna.json ni yangidan o‘qish (dict shaklda)
        try:
            with open('obuna.json', 'r') as f:
                obunachilar = json.load(f)  # dict: {"user_id (str)": "timestamp"}
        except Exception as e:
            print(f"⚠️ obuna.json o‘qishda xatolik: {e}")
            obunachilar = {}

        # 👤 Foydalanuvchi ID si str shaklida bo'lishi kerak
        user_id_str = str(sender.id)

        # 🛑 O‘zimiz yoki obunachilar ro‘yxatida bo‘lsa – tegmaymiz
        if str(myself.id) == user_id_str or user_id_str in obunachilar:
            return

        # 🖼 Faqat rasm yoki rasm + matn bo‘lsa ishlasin
        if isinstance(event.message.media, MessageMediaPhoto):
            # ❌ Xabarni o‘chirish
            await event.delete()

            # 🏷 Foydalanuvchining ismi va mention
            ism = sender.first_name or "foydalanuvchi"
            mention = f"[{ism}](tg://user?id={sender.id})"

            # 📩 Javob xabari
            javob = (
                f"**👋 [Salom {mention}](https://t.me/taxi_tolov_bot?start=start)!**\n\n"
                f"**[Guruhda e'lon qoldirish uchun sizga faollashtirilgan obuna kerak 📢](https://t.me/taxi_tolov_bot?start=start)**\n\n"
                f"**[Tez va oson ulanish uchun bu yerni bosing 👇](https://t.me/taxi_tolov_bot?start=start)**\n\n"
                f"**👉 Obuna bo'lish:** [https://t.me/taxi_tolov_bot?start=start](https://t.me/taxi_tolov_bot?start=start)\n\n"
                f"**[Obunadan so‘ng bemalol e'lon joylashingiz mumkin ✅](https://t.me/taxi_tolov_bot?start=start)**"

            )

            # 🗣 Guruhga yuborish
            await client.send_message(event.chat_id, javob, parse_mode='markdown')

            # ✉️ Lichkaga yuborish
            await client.send_message(PeerUser(sender.id), javob, parse_mode='markdown')

    except Exception as e:
        print(f"⚠️ Umumiy xatolik: {e}")

# ▶️ Botni ishga tushuramiz
client.start()
print("✅ Bot ishga tushdi va obuna.json (dict) asosida tekshiruv qilmoqda...")
client.run_until_disconnected()

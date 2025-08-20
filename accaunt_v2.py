import json
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, PeerUser

# 🔑 Telegram API ma'lumotlari
api_id = 21382075              # <-- o'zingizniki bilan almashtiring
api_hash = '22145968ba0e89dee86eeeab455adc33'  # <-- o'zingizniki bilan almashtiring

client = TelegramClient('taxi_tolov_bot', api_id, api_hash)

# 🚫 Faqat bir marta ogohlantirish uchun
ogohlantirilganlar = set()

@client.on(events.NewMessage)
async def handler(event):
    try:
        sender = await event.get_sender()
        myself = await client.get_me()
        user_id_str = str(sender.id)

        # 📂 obuna.json ni o‘qish
        try:
            with open("obuna.json", "r") as f:
                obunachilar = json.load(f)   # dict: {"user_id (str)": "timestamp"}
        except Exception:
            obunachilar = {}

        # 🛑 O‘zimiz yoki obunachilar bo‘lsa – chiqamiz
        if str(myself.id) == user_id_str or user_id_str in obunachilar:
            return

        is_blocked = False

        # 📷 Rasm
        if isinstance(event.message.media, MessageMediaPhoto):
            is_blocked = True

        # 🎥 Video yoki videoxabar
        elif isinstance(event.message.media, MessageMediaDocument):
            mime = event.message.media.document.mime_type
            if mime and mime.startswith("video/"):
                is_blocked = True
            else:
                for attr in event.message.media.document.attributes:
                    if attr.__class__.__name__ in ("VideoSize", "DocumentAttributeVideo"):
                        is_blocked = True
                        break

        # 🔗 Link (http/https)
        elif event.raw_text and any(x in event.raw_text.lower() for x in ["http://", "https://"]):
            is_blocked = True

        # ❌ Agar bloklangan kontent bo‘lsa
        if is_blocked:
            try:
                await event.delete()
            except Exception as e:
                print(f"❌ Xabar o‘chmadi: {e}")

            # 🔔 Ogohlantirish faqat bir marta
            if user_id_str not in ogohlantirilganlar:
                ism = sender.first_name or "foydalanuvchi"
                mention = f"<a href='tg://user?id={sender.id}'>{ism}</a>"

                javob = (
                    f"👋 Salom {mention}!<br><br>"
                    f"📢 Guruhda e'lon qoldirish uchun sizga <b>obuna</b> kerak.<br><br>"
                    f"👉 <a href='https://t.me/taxi_tolov_bot?start=start'>Obuna bo'lish</a><br><br>"
                    f"✅ Obunadan so‘ng bemalol e'lon joylashingiz mumkin."
                )

                # Guruhga yuborish
                await client.send_message(event.chat_id, javob, parse_mode="html")

                # Lichkaga yuborish (agar start bosgan bo‘lsa)
                try:
                    await client.send_message(PeerUser(sender.id), javob, parse_mode="html")
                except:
                    print(f"❌ {sender.id} lichkasi yopiq")

                # Foydalanuvchini ogohlantirilganlar ro‘yxatiga qo‘shish
                ogohlantirilganlar.add(user_id_str)

    except Exception as e:
        print(f"⚠️ Umumiy xatolik: {e}")


# ▶️ Botni ishga tushirish
client.start()
print("✅ Bot ishga tushdi va obuna.json asosida tekshiruv qilmoqda...")
client.run_until_disconnected()

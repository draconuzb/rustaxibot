import json
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, PeerUser

# 🔑 Telegram API ma'lumotlari
api_id = 21382075              # <-- o'zingizniki bilan almashtiring
api_hash = '22145968ba0e89dee86eeeab455adc33'  # <-- o'zingizniki bilan almashtiring

client = TelegramClient('taxi_tolov_bot', api_id, api_hash)

# 🚫 Faqat bir marta ogohlantirish uchun
ogohlantirilganlar = set()

def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@client.on(events.NewMessage)
async def handler(event):
    try:
        sender = await event.get_sender()
        myself = await client.get_me()
        user_id_str = str(sender.id)

        # 📂 obuna.json
        obunachilar = load_json("obuna.json", {})

        # 📂 blocked.json
        blocked_users = load_json("blocked.json", {})

        # 🛑 O‘zimiz bo‘lsa chiqamiz
        if str(myself.id) == user_id_str:
            return

        # ✅ Avval blok muddatini tekshiramiz
        if user_id_str in blocked_users:
            tugash_vaqti = blocked_users[user_id_str]
            try:
                dt = datetime.fromisoformat(tugash_vaqti)
                if datetime.now() >= dt:
                    # ⏳ Blok muddati tugagan → olib tashlaymiz
                    del blocked_users[user_id_str]
                    save_json("blocked.json", blocked_users)
                    print(f"✅ {user_id_str} blokdan chiqarildi (muddati tugagan).")

                    # 🎉 Foydalanuvchiga xabar yuboramiz
                    javob = (
                        f"✅ Hurmatli {sender.first_name}, sizning <b>blok muddati tugadi</b>.\n\n"
                        f"Endi guruhda bemalol yozishingiz mumkin. 😉"
                    )
                    try:
                        await client.send_message(PeerUser(sender.id), javob, parse_mode="html")
                    except:
                        print(f"❌ {sender.id} lichkasi yopiq")

                else:
                    # 🚫 Hali blokda
                    try:
                        await event.delete()
                    except Exception as e:
                        print(f"❌ Bloklangan foydalanuvchi xabari o‘chmadi: {e}")

                    ism = sender.first_name or "foydalanuvchi"
                    mention = f"<a href='tg://user?id={sender.id}'>{ism}</a>"

                    await client.send_message(
                        event.chat_id,
                        f"⛔ {mention}, bu foydalanuvchi bloklangan.",
                        parse_mode="html"
                    )

                    javob = (
                        f"⛔ Hurmatli {ism}, siz hozirda <b>bloklangansiz</b>.\n\n"
                        f"📅 Blok tugash sanasi: <b>{dt.strftime('%Y-%m-%d %H:%M:%S')}</b>\n\n"
                        f"🤝 Agar muammo bo‘lsa "
                        f"<a href='https://t.me/your_admin_username'>admin bilan bog‘laning</a>."
                    )

                    try:
                        await client.send_message(PeerUser(sender.id), javob, parse_mode="html")
                    except:
                        print(f"❌ {sender.id} lichkasi yopiq")

                    return  # boshqa tekshiruvlarga o‘tmaymiz
            except Exception as e:
                print(f"⚠️ Blok vaqti noto‘g‘ri formatda: {e}")

        # 🛑 Obunachilar bo‘lsa chiqamiz
        if user_id_str in obunachilar:
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

                ogohlantirilganlar.add(user_id_str)

    except Exception as e:
        print(f"⚠️ Umumiy xatolik: {e}")


# ▶️ Botni ishga tushirish
client.start()
print("✅ Bot ishga tushdi va obuna.json + blocked.json asosida tekshiruv qilmoqda...")
client.run_until_disconnected()

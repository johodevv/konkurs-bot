import asyncio
import os
import logging
import sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from pyrogram import Client, raw
from pyrogram.errors import FloodWait

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "@channel")
FORCE_GROUP = os.getenv("FORCE_GROUP", "@group")

PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels(username TEXT UNIQUE)")
conn.commit()

# ================= BOT =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ================= USERBOT =================
userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ================= STATES =================
class Form(StatesGroup):
    channel = State()
    confirm = State()
    ad = State()

# ================= WEB (Render fix) =================
async def handle(request):
    return web.Response(text="OK")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# ================= CHECK SUB =================
async def check_sub(user_id):
    try:
        c1 = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        c2 = await bot.get_chat_member(FORCE_GROUP, user_id)
        return c1.status != "left" and c2.status != "left"
    except:
        return False

# ================= START =================
@dp.message(F.text == "/start")
async def start(m: Message, state: FSMContext):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)", (m.from_user.id,))
    conn.commit()

    if not await check_sub(m.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanal", url=f"https://t.me/{FORCE_CHANNEL[1:]}")],
            [InlineKeyboardButton(text="💬 Guruh", url=f"https://t.me/{FORCE_GROUP[1:]}")]
        ])

        return await m.answer(
            "❗ <b>Davom etish uchun obuna bo‘ling</b>",
            reply_markup=kb
        )

    await m.answer(
        "🔥 <b>KONKURS PLATFORMASI</b>\n\n"
        "🚀 Kanalingizni tez o‘stiring\n"
        "📢 Obunachilar oqimi olish\n\n"
        "👇 Kanal linkingizni yuboring:"
    )

    await state.set_state(Form.channel)

# ================= CHANNEL ADD =================
@dp.message(Form.channel)
async def get_channel(m: Message, state: FSMContext):
    try:
        chat = await bot.get_chat(m.text)

        if not chat.username:
            return await m.answer("❌ Public kanal kerak")

        await state.update_data(channel=f"@{chat.username}")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Admin berdim", callback_data="confirm")]
        ])

        await m.answer(
            "⚙️ Kanalga botni admin qiling\n"
            "Keyin tasdiqlang:",
            reply_markup=kb
        )

        await state.set_state(Form.confirm)

    except:
        await m.answer("❌ Xato kanal")

# ================= CONFIRM =================
@dp.callback_query(Form.confirm, F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel = data.get("channel")

    try:
        chat = await bot.get_chat(channel)
        member = await bot.get_chat_member(chat.id, bot.id)

        if member.status not in ["administrator", "creator"]:
            return await call.message.answer("❌ Bot admin emas")

        cursor.execute("INSERT OR IGNORE INTO channels VALUES(?)", (channel,))
        conn.commit()

        await call.message.answer("✅ Kanal qo‘shildi")
        await state.clear()

    except Exception as e:
        await call.message.answer("❌ Xatolik")

# ================= FOLDER LOGIC =================
async def create_folder_link():
    try:
        channels = cursor.execute("SELECT username FROM channels").fetchall()
        peers = []

        for ch in channels:
            try:
                chat = await userbot.get_chat(ch[0])
                peer = await userbot.resolve_peer(chat.id)
                peers.append(peer)
            except:
                pass

        if not peers:
            return None

        result = await userbot.invoke(
            raw.functions.chatlists.ExportChatlistInvite(
                chatlist=raw.types.InputChatlistDialogFilter(filter_id=1),
                title="Konkurs Jild",
                peers=peers
            )
        )

        return f"https://t.me/+{result.slug}"

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await create_folder_link()

    except Exception as e:
        logging.error(e)
        return None

# ================= ADS =================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "/ads")
async def ads(m: Message, state: FSMContext):
    await m.answer("Reklama yubor:")
    await state.set_state(Form.ad)

@dp.message(Form.ad)
async def send_ads(m: Message, state: FSMContext):
    channels = cursor.execute("SELECT username FROM channels").fetchall()

    link = await create_folder_link()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Jildga qo‘shilish", url=link or "https://t.me")]
    ])

    for ch in channels:
        try:
            await bot.send_message(ch[0], m.text, reply_markup=kb)
        except:
            pass

    await m.answer("✅ Yuborildi")
    await state.clear()

# ================= MAIN =================
async def main():
    await userbot.start()

    await asyncio.gather(
        dp.start_polling(bot),
        web_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
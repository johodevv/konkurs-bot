import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.raw import functions, types as raw_types

# --- SOZLAMALAR ---
BOT_TOKEN = "8589756374:AAEE_kKLmNXMUWcM-EiQgurIuiblpbrToec"
API_ID = 28466899
API_HASH = "2f1948ccca564e8973e8cf9c3204d2e9"
SESSION_STRING = "AgGyXtMABg1dy66Kd9DjaNIUSds6CTQomsUhCmXVn0-fseieC4qzyP2Oq5EVAPrqsP-F7ws3ZkE4bpXbPYNZ-09jL31iMYZZhIPSfPjRSJd_k9xQrClvjsttXLcwelTLA7csRH9sPVER8ACTIgozIyTZzO891s4sVt5KhQKuPI4wSaF8YmtB_84n844SH_senWKCVDN92peoAFy39W263sVSUzOg8-Jg8UEmD8KhmN9RWtOnyKOqueNSJiDzyG1ae793emljY8jxNM3_4dEqkimzi5OahguB8QZ4yIzuPyM04mV_MqjQv_sq-XOsQ3zuKYZwgqZ95PNen1paIL3B527h0OwaAAAAAAH2gY3GAA"
ADMIN_ID = 8430652870

REQUIRED_CHANNELS = ["@ortiqboyovichch", "@jildgaqoshil"]
PREMIUM_IMAGE = "https://clm.sh/s/167b0b72-f851-4043-8557-01004a806954"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_bot = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

# --- BAZA FUNKSIYALARI ---
def init_db():
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('CREATE TABLE IF NOT EXISTS channels (chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

async def check_sub(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

async def get_jild_url():
    conn = sqlite3.connect('konkurs_bot.db')
    rows = conn.execute('SELECT chat_id, link FROM channels').fetchall()
    conn.close()
    if not rows: return None
    
    peers = []
    if not user_bot.is_connected: await user_bot.start()
    for cid, link in rows:
        try:
            chat = await user_bot.get_chat(link)
            peers.append(await user_bot.resolve_peer(chat.id))
        except: continue
    
    if not peers: return None
    f_id = 200
    try:
        await user_bot.invoke(functions.messages.UpdateDialogFilter(id=f_id, filter=raw_types.DialogFilter(id=f_id, title="❤️ Konkurs", include_peers=peers, pinned_peers=[], exclude_peers=[])))
        invites = await user_bot.invoke(functions.chatlists.GetExportedInvites(chatlist=raw_types.InputChatlistDialogFilter(filter_id=f_id)))
        if invites.invites: return invites.invites[0].url
        invite = await user_bot.invoke(functions.chatlists.ExportChatlistInvite(chatlist=raw_types.InputChatlistDialogFilter(filter_id=f_id), title="Konkurs", peers=peers))
        return invite.url
    except: return None

# --- ASOSIY HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanal 1", url="https://t.me/ortiqboyovichch")],
            [InlineKeyboardButton(text="💬 Guruh 2", url="https://t.me/jildgaqoshil")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check")]
        ])
        await message.answer("👋 Botdan foydalanish uchun obuna bo'ling!", reply_markup=kb)
        return
    
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("✅ Salom! Kanal linkini yuboring (Masalan: @username):")

@dp.callback_query(F.data == "check")
async def check_call(callback: types.CallbackQuery):
    if await check_sub(callback.from_user.id):
        await callback.message.edit_text("✅ Rahmat! Kanal linkini yuboring:")
    else:
        await callback.answer("❌ Obuna bo'lmadingiz!", show_alert=True)

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('konkurs_bot.db')
        u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        c_count = conn.execute('SELECT COUNT(*) FROM channels').fetchone()[0]
        conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Tarqatish", callback_data="send_all")]])
        await message.answer(f"📊 Userlar: {u_count}\n📢 Kanallar: {c_count}", reply_markup=kb)

@dp.callback_query(F.data == "send_all")
async def send_call(callback: types.CallbackQuery):
    await callback.message.edit_text("⏳ Jild tayyorlanmoqda, kuting...")
    link = await get_jild_url()
    
    conn = sqlite3.connect('konkurs_bot.db')
    # Barcha qo'shilgan kanallarni olish
    chans = conn.execute('SELECT chat_id FROM channels').fetchall()
    conn.close()

    if not chans:
        await callback.message.answer("❌ Bazada kanal yo'q!")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=link or "https://t.me/")]])
    success = 0
    for (cid,) in chans:
        try:
            # Kanalga rasm va jild tugmasini yuborish
            await bot.send_photo(chat_id=cid, photo=PREMIUM_IMAGE, caption="🎁 DIQQAT KONKURS!\n\nPastdagi jildga obuna bo'ling!", reply_markup=kb)
            success += 1
            await asyncio.sleep(0.3)
        except: continue
    
    await callback.message.answer(f"✅ Xabar {success} ta kanalga rasm bilan yuborildi!")

@dp.message(F.text.startswith("@"))
async def add_link(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Admin qildim", callback_data=f"save_{message.text}")]])
    await message.answer(f"Botni {message.text} kanaliga admin qiling va tugmani bosing:", reply_markup=kb)

@dp.callback_query(F.data.startswith("save_"))
async def save_call(callback: types.CallbackQuery):
    l = callback.data.replace("save_", "")
    try:
        chat = await bot.get_chat(l)
        conn = sqlite3.connect('konkurs_bot.db')
        conn.execute('INSERT OR REPLACE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, l))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"✅ **{chat.title}** muvaffaqiyatli qo'shildi!")
    except:
        await callback.answer("❌ Xato! Bot kanalda admin ekanligini tekshiring.", show_alert=True)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    if not user_bot.is_connected: await user_bot.start()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await user_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
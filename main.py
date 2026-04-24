import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F # F importi joyida!
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

# Majburiy obuna va rasm linki
REQUIRED_CHANNELS = ["@ortiqboyovichch", "@jildgaqoshil"] 
PREMIUM_IMAGE = "https://clm.sh/s/167b0b72-f851-4043-8557-01004a806954"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_bot = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('konkurs_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

async def check_sub(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

async def refresh_folder_and_get_link():
    conn = sqlite3.connect('konkurs_bot.db')
    rows = conn.execute('SELECT chat_id, link FROM channels').fetchall()
    conn.close()
    if not rows: return None
    peers = []
    if not user_bot.is_connected: await user_bot.start()
    for cid, link in rows:
        try:
            chat = await user_bot.get_chat(link if link.startswith("@") else cid)
            peers.append(await user_bot.resolve_peer(chat.id))
        except: continue
    if not peers: return None
    folder_id = 200
    try:
        await user_bot.invoke(functions.messages.UpdateDialogFilter(id=folder_id, filter=raw_types.DialogFilter(id=folder_id, title="❤️ Konkurs", include_peers=peers, pinned_peers=[], exclude_peers=[])))
        invites = await user_bot.invoke(functions.chatlists.GetExportedInvites(chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id)))
        if invites.invites: return invites.invites[0].url
        invite = await user_bot.invoke(functions.chatlists.ExportChatlistInvite(chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id), title="Konkurs", peers=peers))
        return invite.url
    except: return None

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Rasmiy kanal", url="https://t.me/ortiqboyovichch")],
            [InlineKeyboardButton(text="💬 Muhokama guruhi", url="https://t.me/jildgaqoshil")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer("👋 **Salom!**\n\nBotinga kirish uchun kanallarga a'zo bo'ling!", reply_markup=kb, parse_mode="Markdown")
        return
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("🎉 **Muvaffaqiyatli kirdingiz!**\n\nKanal linkini yuboring (Masalan: `@kanal_nomi`)", parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    if await check_sub(callback.from_user.id):
        await callback.message.edit_text("✅ Rahmat! Kanal linkini yuborishingiz mumkin:")
    else:
        await callback.answer("❌ Obuna bo'lmadingiz!", show_alert=True)

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('konkurs_bot.db')
        u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        c_count = conn.execute('SELECT COUNT(*) FROM channels').fetchone()[0]
        conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Konkursni tarqatish", callback_data="broadcast")]])
        await message.answer(f"📊 **Statistika**\n\n👤 Userlar: {u_count}\n📢 Kanallar: {c_count}", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "broadcast")
async def broadcast_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("⏳ **Jild yangilanmoqda...**")
    url = await refresh_folder_and_get_link()
    
    conn = sqlite3.connect('konkurs_bot.db')
    channels = conn.execute('SELECT chat_id FROM channels').fetchall()
    conn.close()

    if not channels:
        await callback.message.answer("❌ Bazada kanallar yo'q! Avval kanal qo'shing.")
        return

    text = "💎 **TELEGRAM PREMIUM KONKURSI!**\n\n🎁 Jildga qo'shiling va 6 oylik Premium yutib oling!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url or "#")]])
    
    success = 0
    for (cid,) in channels:
        try:
            await bot.send_photo(chat_id=cid, photo=PREMIUM_IMAGE, caption=text, reply_markup=kb, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.5)
        except: continue
    await callback.message.answer(f"✅ Konkurs {success} ta kanalga rasm bilan tarqatildi!")

@dp.message(F.text.startswith("@") | F.text.contains("t.me/"))
async def handle_link(message: types.Message):
    link = message.text.strip().split('/')[-1]
    if not link.startswith("@"): link = f"@{link}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Admin qildim", callback_data=f"v_{link}")]])
    await message.answer(f"Botni {link} kanaliga admin qiling va tugmani bosing 👇", reply_markup=kb)

@dp.callback_query(F.data.startswith("v_"))
async def verify_handler(callback: types.CallbackQuery):
    link = callback.data.split("_")[1]
    try:
        chat = await bot.get_chat(link)
        conn = sqlite3.connect('konkurs_bot.db')
        # Muhim: Ma'lumotni bazaga yozishni qat'iylashtiramiz
        conn.execute('INSERT OR REPLACE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, link))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"✅ **{chat.title}** muvaffaqiyatli qo'shildi!")
    except:
        await callback.answer("❌ Xato! Bot adminligini tekshiring.", show_alert=True)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await user_bot.start()
    try:
        await dp.start_polling(bot)
    finally:
        await user_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
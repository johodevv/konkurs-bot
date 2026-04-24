import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.raw import functions, types as raw_types

# --- SOZMALAR ---
# Yangi tokening muvaffaqiyatli o'rnatildi!
BOT_TOKEN = "8589756374:AAGsylGrZ8hQxHg9GIo6P3ptInruTd_pMpg"
API_ID = 28466899
API_HASH = "2f1948ccca564e8973e8cf9c3204d2e9"
SESSION_STRING = "AgGyXtMABg1dy66Kd9DjaNIUSds6CTQomsUhCmXVn0-fseieC4qzyP2Oq5EVAPrqsP-F7ws3ZkE4bpXbPYNZ-09jL31iMYZZhIPSfPjRSJd_k9xQrClvjsttXLcwelTLA7csRH9sPVER8ACTIgozIyTZzO891s4sVt5KhQKuPI4wSaF8YmtB_84n844SH_senWKCVDN92peoAFy39W263sVSUzOg8-Jg8UEmD8KhmN9RWtOnyKOqueNSJiDzyG1ae793emljY8jxNM3_4dEqkimzi5OahguB8QZ4yIzuPyM04mV_MqjQv_sq-XOsQ3zuKYZwgqZ95PNen1paIL3B527h0OwaAAAAAAH2gY3GAA"
ADMIN_ID = 8430652870

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_bot = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

# Reklama kutish holati
admin_waiting_post = {}

def init_db():
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('CREATE TABLE IF NOT EXISTS channels (chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

async def refresh_folder_and_get_link():
    conn = sqlite3.connect('konkurs_bot.db')
    rows = conn.execute('SELECT chat_id, link FROM channels').fetchall()
    conn.close()
    if not rows: return None
    
    if not user_bot.is_connected: await user_bot.start()
    peers = []
    for cid, link in rows:
        try:
            try: chat = await user_bot.get_chat(link)
            except: chat = await user_bot.join_chat(link)
            peers.append(await user_bot.resolve_peer(chat.id))
        except: continue
        
    if not peers: return None
    folder_id = 200
    try:
        await user_bot.invoke(functions.messages.UpdateDialogFilter(
            id=folder_id, 
            filter=raw_types.DialogFilter(id=folder_id, title="❤️ Konkurs", include_peers=peers, pinned_peers=[], exclude_peers=[])
        ))
        invites = await user_bot.invoke(functions.chatlists.GetExportedInvites(chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id)))
        if invites.invites: return invites.invites[0].url
        invite = await user_bot.invoke(functions.chatlists.ExportChatlistInvite(chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id), title="Konkurs", peers=peers))
        return invite.url
    except: return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Salom! Kanal linkini yuboring yoki /admin paneliga kiring.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Reklama Tarqatish", callback_data="start_ads")]])
        await message.answer("🛠 Admin panel. Reklama yuborish uchun pastdagi tugmani bosing:", reply_markup=kb)

@dp.callback_query(F.data == "start_ads")
async def start_ads(callback: types.CallbackQuery):
    admin_waiting_post[callback.from_user.id] = True
    await callback.message.edit_text("📝 Menga reklama xabarini yuboring (Rasm, matn yoki video).\n\nBot uning tagiga avtomatik jild tugmasini qo'shadi.")

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_admin_messages(message: types.Message):
    # Agar admin reklama yuborish holatida bo'lsa
    if admin_waiting_post.get(message.from_user.id):
        status_msg = await message.answer("⏳ Jild tayyorlanmoqda, kuting...")
        url = await refresh_folder_and_get_link()
        
        if not url:
            await status_msg.edit_text("❌ Xato: Kanallar topilmadi yoki jild yaratib bo'lmadi.")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url)]])
        
        conn = sqlite3.connect('konkurs_bot.db')
        channels = conn.execute('SELECT chat_id FROM channels').fetchall()
        conn.close()

        success = 0
        for (cid,) in channels:
            try:
                await message.copy_to(chat_id=cid, reply_markup=kb)
                success += 1
                await asyncio.sleep(0.5)
            except: continue
            
        await status_msg.edit_text(f"✅ Reklama {success} ta kanalga muvaffaqiyatli tarqatildi!")
        admin_waiting_post[message.from_user.id] = False
    
    # Kanal linklarini qabul qilish (Oddiy holat)
    elif message.text and (message.text.startswith("@") or "t.me/" in message.text):
        link = message.text.strip().split('/')[-1]
        if not link.startswith("@"): link = f"@{link}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Admin qildim", callback_data=f"v_{link}")]])
        await message.answer(f"Botni {link} kanaliga admin qiling va tugmani bosing.", reply_markup=kb)

@dp.callback_query(F.data.startswith("v_"))
async def verify_channel(callback: types.CallbackQuery):
    link = callback.data.split('_')[1]
    try:
        chat = await bot.get_chat(link)
        conn = sqlite3.connect('konkurs_bot.db')
        conn.execute('INSERT OR IGNORE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, link))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"✅ {chat.title} bazaga qo'shildi!")
    except:
        await callback.answer("Bot hali admin emas yoki link xato!", show_alert=True)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    if not user_bot.is_connected: await user_bot.start()
    print("Bot yangi token bilan ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
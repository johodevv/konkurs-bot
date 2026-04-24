import asyncio
import sqlite3
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from pyrogram import Client
from pyrogram.raw import functions, types as raw_types
from aiohttp import web

# --- SOZMALAR ---
BOT_TOKEN = "8589756374:AAGsylGrZ8hQxHg9GIo6P3ptInruTd_pMpg"
API_ID = 28466899
API_HASH = "2f1948ccca564e8973e8cf9c3204d2e9"
SESSION_STRING = "AgGyXtMABg1dy66Kd9DjaNIUSds6CTQomsUhCmXVn0-fseieC4qzyP2Oq5EVAPrqsP-F7ws3ZkE4bpXbPYNZ-09jL31iMYZZhIPSfPjRSJd_k9xQrClvjsttXLcwelTLA7csRH9sPVER8ACTIgozIyTZzO891s4sVt5KhQKuPI4wSaF8YmtB_84n844SH_senWKCVDN92peoAFy39W263sVSUzOg8-Jg8UEmD8KhmN9RWtOnyKOqueNSJiDzyG1ae793emljY8jxNM3_4dEqkimzi5OahguB8QZ4yIzuPyM04mV_MqjQv_sq-XOsQ3zuKYZwgqZ95PNen1paIL3B527h0OwaAAAAAAH2gY3GAA"
ADMIN_ID = 8430652870

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_bot = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

admin_states = {}

# --- RENDER PORTINI BAND QILISH (O'CHIB QOLMASLIGI UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render avtomatik beradigan PORT yoki 10000-portda ishlaydi
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server {port}-portda ishga tushdi.")

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('CREATE TABLE IF NOT EXISTS channels (chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

async def get_folder_link():
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

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("👋 Salom! Botga xush kelibsiz.\nKanal linkini yuboring yoki admin paneldan foydalaning.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('konkurs_bot.db')
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        channel_count = conn.execute('SELECT COUNT(*) FROM channels').fetchone()[0]
        conn.close()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Reklama Tarqatish", callback_data="start_ads")],
            [InlineKeyboardButton(text="🔄 Statistikani yangilash", callback_data="refresh_stats")]
        ])
        
        text = f"📊 <b>Statistika</b>\n\n👤 Userlar: <code>{user_count}</code>\n📢 Kanallar: <code>{channel_count}</code>"
        await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "start_ads")
async def start_ads_handler(callback: types.CallbackQuery):
    admin_states[callback.from_user.id] = "waiting_post"
    await callback.message.edit_text("📝 Menga reklama postini yuboring. Bot uning ostiga avtomatik jild tugmasini qo'shadi.")

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_admin_input(message: types.Message):
    # 1. Reklama tarqatish
    if admin_states.get(message.from_user.id) == "waiting_post":
        status_msg = await message.answer("⏳ Jild havolasi olinmoqda...")
        url = await get_folder_link()
        
        if not url:
            await status_msg.edit_text("❌ Xato: Jild yaratish uchun kanallar yetarli emas.")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url)]])
        
        conn = sqlite3.connect('konkurs_bot.db')
        users = conn.execute('SELECT user_id FROM users').fetchall()
        conn.close()

        count = 0
        for (uid,) in users:
            try:
                await message.copy_to(chat_id=uid, reply_markup=kb)
                count += 1
                await asyncio.sleep(0.05) # Tezlikni biroz oshirdik
            except: continue
            
        await status_msg.edit_text(f"✅ Post {count} ta foydalanuvchiga tarqatildi!")
        admin_states[message.from_user.id] = None

    # 2. Kanal linkini qabul qilish (t.me va @ uchun)
    elif message.text and ("t.me/" in message.text or message.text.startswith("@")):
        # Linkni tozalash va username ni ajratib olish
        raw_text = message.text.strip()
        if "t.me/" in raw_text:
            link = raw_text.split('/')[-1].split('?')[0] # t.me/username/123 yoki t.me/username?start bo'lsa ham ishlaydi
        else:
            link = raw_text.replace("@", "")
        
        username = f"@{link}"
        
        me = await bot.get_me()
        admin_link = f"https://t.me/{me.username}?startchannel=true&admin=post_messages+edit_messages+delete_messages"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Botni kanalga admin qilish", url=admin_link)],
            [InlineKeyboardButton(text="✅ Admin qildim (Tekshirish)", callback_data=f"v_{link}")]
        ])
        
        # HTML rejimida Markdown xatolaridan qutulamiz
        await message.answer(
            f"Kanal: <b>{username}</b>\n\n1. Botni kanalga admin qiling.\n2. Tekshirish tugmasini bosing.", 
            reply_markup=kb, 
            parse_mode=ParseMode.HTML
        )

@dp.callback_query(F.data.startswith("v_"))
async def verify_channel(callback: types.CallbackQuery):
    link = callback.data.split('_')[1]
    try:
        chat = await bot.get_chat(f"@{link}")
        bot_member = await bot.get_chat_member(chat_id=chat.id, user_id=(await bot.get_me()).id)
        
        if bot_member.status in ["administrator", "creator"]:
            conn = sqlite3.connect('konkurs_bot.db')
            conn.execute('INSERT OR IGNORE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, f"@{link}"))
            conn.commit()
            conn.close()
            await callback.message.edit_text(f"✅ <b>{chat.title}</b> muvaffaqiyatli qo'shildi!", parse_mode=ParseMode.HTML)
        else:
            await callback.answer("❌ Bot hali bu kanalda admin emas!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xato: Bot kanalda yo'q yoki havola noto'g'ri.", show_alert=True)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    
    # 1. Web serverni ishga tushirish (Render uchun)
    await start_web_server()
    
    # 2. Botlarni ishga tushirish
    if not user_bot.is_connected: 
        await user_bot.start()
        
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot va UserBot muvaffaqiyatli ishga tushdi!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if user_bot.is_connected:
            await user_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
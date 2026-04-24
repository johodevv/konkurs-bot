import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types , F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.raw import functions, types as raw_types
from pyrogram.errors import PeerIdInvalid, FloodWait

# --- SOZLAMALAR ---
BOT_TOKEN = "8589756374:AAEE_kKLmNXMUWcM-EiQgurIuiblpbrToec"
API_ID = 28466899
API_HASH = "2f1948ccca564e8973e8cf9c3204d2e9"
ADMIN_ID = 8430652870

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_bot = Client("my_account", api_id=API_ID, api_hash=API_HASH)

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('konkurs_bot.db')
    cursor = conn.cursor()
    # Kanallar jadvaliga link ustunini aniq qo'shamiz
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels 
                      (chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

# --- JILDNI YANGILASH VA LINK OLISH ---
async def refresh_folder_and_get_link():
    conn = sqlite3.connect('konkurs_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, link FROM channels')
    rows = cursor.fetchall()
    conn.close()

    if not rows: return None

    peers = []
    if not user_bot.is_connected: 
        await user_bot.start()

    for cid, link in rows:
        try:
            # Avval username orqali chatni topishga harakat qilamiz (Peer id invalid dan qochish uchun)
            chat = await user_bot.get_chat(link if link.startswith("@") else cid)
            await user_bot.join_chat(chat.id)
            peers.append(await user_bot.resolve_peer(chat.id))
        except (PeerIdInvalid, Exception) as e:
            logging.error(f"Kanal qo'shishda xato {link}: {e}")
            continue

    if not peers: return None

    folder_id = 200 
    
    try:
        # 1. Jildni yangilash
        await user_bot.invoke(
            functions.messages.UpdateDialogFilter(
                id=folder_id,
                filter=raw_types.DialogFilter(
                    id=folder_id, 
                    title="❤️ Konkurs", 
                    include_peers=peers, 
                    pinned_peers=[], 
                    exclude_peers=[]
                )
            )
        )
        
        # 2. Mavjud linkni tahrirlash (Limitdan qochish uchun)
        invites = await user_bot.invoke(
            functions.chatlists.GetExportedInvites(
                chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id)
            )
        )
        
        if invites.invites:
            existing_invite = invites.invites[0]
            await user_bot.invoke(
                functions.chatlists.EditExportedInvite(
                    chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id),
                    slug=existing_invite.url.split('/')[-1],
                    title="Konkurs Jildi",
                    peers=peers
                )
            )
            return existing_invite.url
            
        # 3. Agar link bo'lmasa, yangi yaratish
        invite = await user_bot.invoke(
            functions.chatlists.ExportChatlistInvite(
                chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id),
                title="Konkurs Jildi", peers=peers
            )
        )
        return invite.url
    except FloodWait as e:
        logging.warning(f"FloodWait: {e.value} soniya kuting")
        return None
    except Exception as e:
        logging.error(f"Jild xatosi: {e}")
        return None

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('konkurs_bot.db')
        u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        c_count = conn.execute('SELECT COUNT(*) FROM channels').fetchone()[0]
        conn.close()
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Konkursni tarqatish", callback_data="broadcast")]
        ])
        await message.answer(f"📊 **Statistika**\n\n👤 Userlar: {u_count}\n📢 Kanallar: {c_count}", reply_markup=kb)

@dp.callback_query(F.data == "broadcast")
async def broadcast_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("⏳ Jild yangilanmoqda, kuting...")
    url = await refresh_folder_and_get_link()
    
    if not url:
        await callback.message.answer("❌ Jild linkini olib bo'lmadi. Keyinroq urinib ko'ring.")
        return

    text = "🎁 **DIQQAT KONKURS!**\n\nPastdagi jildga obuna bo'ling va Premium yutib oling!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url)]])

    conn = sqlite3.connect('konkurs_bot.db')
    channels = conn.execute('SELECT chat_id FROM channels').fetchall()
    conn.close()

    success = 0
    for (cid,) in channels:
        try:
            await bot.send_message(cid, text, reply_markup=kb, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.5)
        except: continue
    
    await callback.message.answer(f"✅ Xabar {success} ta kanalga yuborildi!")

# --- USER KOMANDALARI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("✅ Salom! Jildga qo'shish uchun kanal linkini yuboring (Masalan: @username)")

@dp.message(F.text.startswith("@") | F.text.contains("t.me/"))
async def handle_link(message: types.Message):
    raw_link = message.text.strip()
    # Linkni tozalash
    link = raw_link.split('/')[-1]
    if not link.startswith("@"): link = f"@{link}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Admin qildim", callback_data=f"v_{link}")]])
    await message.answer(f"Botni {link} kanaliga admin qiling va tugmani bosing 👇", reply_markup=kb)

@dp.callback_query(F.data.startswith("v_"))
async def verify_handler(callback: types.CallbackQuery):
    link = callback.data.split("_")[1]
    try:
        chat = await bot.get_chat(link)
        me = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        
        if me.status in ['administrator', 'creator']:
            conn = sqlite3.connect('konkurs_bot.db')
            conn.execute('INSERT OR IGNORE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, link))
            conn.commit()
            conn.close()
            
            await callback.message.edit_text(f"⌛️ {chat.title} qabul qilindi. Jild yangilanmoqda...")
            url = await refresh_folder_and_get_link()
            
            if url:
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url)]])
                await callback.message.answer(f"🎉 Muvaffaqiyatli qo'shildi!", reply_markup=kb)
            else:
                await callback.message.answer("⚠️ Kanal qo'shildi, lekin jild linkini yangilashda xato yuz berdi.")
        else:
            await callback.answer("❌ Bot admin emas!", show_alert=True)
    except Exception as e:
        logging.error(f"Verify xatosi: {e}")
        await callback.answer("❌ Kanal topilmadi yoki bot admin emas.", show_alert=True)

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
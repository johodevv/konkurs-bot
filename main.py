import asyncio
import sqlite3
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, errors
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

# --- BAZA ---
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

# --- JILDNI YANGILASH VA HAVOLA OLISH ---
async def refresh_folder_and_get_link():
    conn = sqlite3.connect('konkurs_bot.db')
    rows = conn.execute('SELECT chat_id, link FROM channels').fetchall()
    conn.close()
    if not rows: return None

    if not user_bot.is_connected: await user_bot.start()
    
    peers = []
    for cid, link in rows:
        try:
            # Eng muhim joy: UserBot kanalga a'zo bo'lishi kerak
            try:
                chat = await user_bot.get_chat(link)
            except:
                chat = await user_bot.join_chat(link)
            
            peers.append(await user_bot.resolve_peer(chat.id))
        except Exception as e:
            logging.error(f"Peer xatosi ({link}): {e}")
            continue

    if not peers: return None
    
    folder_id = 200
    try:
        # Jildni yangilash
        await user_bot.invoke(functions.messages.UpdateDialogFilter(
            id=folder_id, 
            filter=raw_types.DialogFilter(id=folder_id, title="❤️ Konkurs", include_peers=peers, pinned_peers=[], exclude_peers=[])
        ))
        
        # Mavjud havolani tekshirish
        invites = await user_bot.invoke(functions.chatlists.GetExportedInvites(
            chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id)
        ))
        
        if invites.invites:
            return invites.invites[0].url
            
        # Yangi havola yaratish
        invite = await user_bot.invoke(functions.chatlists.ExportChatlistInvite(
            chatlist=raw_types.InputChatlistDialogFilter(filter_id=folder_id), 
            title="Konkurs", 
            peers=peers
        ))
        return invite.url
    except Exception as e:
        logging.error(f"Jild xatosi: {e}")
        return None

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Rasmiy kanal", url="https://t.me/ortiqboyovichch")],
            [InlineKeyboardButton(text="💬 Muhokama guruhi", url="https://t.me/jildgaqoshil")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("👋 **Xush kelibsiz!**\n\nIshtirok etish uchun kanallarga a'zo bo'ling.", reply_markup=kb, parse_mode="Markdown")
        return

    conn = sqlite3.connect('konkurs_bot.db')
    conn.execute('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\nKanal linkini yuboring (Masalan: `@username`)", parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    if await check_sub(callback.from_user.id):
        await callback.message.edit_text("🎉 Rahmat! Endi kanal linkini yuboring:")
    else:
        await callback.answer("❌ Hali a'zo bo'lmadingiz!", show_alert=True)

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('konkurs_bot.db')
        u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        c_count = conn.execute('SELECT COUNT(*) FROM channels').fetchone()[0]
        conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Tarqatishni boshlash", callback_data="broadcast")]])
        await message.answer(f"📊 **Statistika**\n\nUserlar: {u_count}\nKanallar: {c_count}", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "broadcast")
async def broadcast_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("⏳ Jild tayyorlanmoqda, kuting...")
    url = await refresh_folder_and_get_link()
    
    if not url:
        await callback.message.answer("❌ Xato: Jild linkini olib bo'lmadi. Kanallar qo'shilganini tekshiring.")
        return

    text = (
        "💎 **TELEGRAM PREMIUM KONKURSI!**\n\n"
        "Pastdagi tugma orqali jildga qo'shiling va yutib olish imkoniyatini qo'lga kiriting! 🎁"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Jildga qo'shilish", url=url)]])

    conn = sqlite3.connect('konkurs_bot.db')
    channels = conn.execute('SELECT chat_id FROM channels').fetchall()
    conn.close()

    success = 0
    for (cid,) in channels:
        try:
            await bot.send_photo(chat_id=cid, photo=PREMIUM_IMAGE, caption=text, reply_markup=kb, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.5)
        except: continue
    await callback.message.answer(f"✅ Konkurs {success} ta kanalga rasm bilan yuborildi!")

@dp.message(F.text.startswith("@") | F.text.contains("t.me/"))
async def handle_link(message: types.Message):
    if not await check_sub(message.from_user.id): return
    link = message.text.strip().split('/')[-1]
    if not link.startswith("@"): link = f"@{link}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Admin qildim", callback_data=f"v_{link}")]])
    await message.answer(f"Botni {link} kanaliga **admin** qiling va tugmani bosing 👇", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("v_"))
async def verify_handler(callback: types.CallbackQuery):
    link = callback.data.split('_')[1]
    try:
        chat = await bot.get_chat(link)
        me = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if me.status in ['administrator', 'creator']:
            conn = sqlite3.connect('konkurs_bot.db')
            conn.execute('INSERT OR IGNORE INTO channels VALUES (?, ?, ?)', (chat.id, chat.title, link))
            conn.commit()
            conn.close()
            await callback.message.edit_text(f"✅ **{chat.title}** muvaffaqiyatli qo'shildi!")
        else:
            await callback.answer("❌ Bot admin emas!", show_alert=True)
    except: await callback.answer("❌ Xato! Linkni tekshiring.", show_alert=True)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    if not user_bot.is_connected: await user_bot.start()
    print("Botlar uyg'ondi...")
    try:
        await dp.start_polling(bot)
    finally:
        await user_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
import os
import asyncio
import sqlite3
from pyrogram import Client
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- SOZLAMALAR ---
API_ID = 28466899
API_HASH = "2f1948ccca564e8973e8cf9c3204d2e9"
SESSION_STRING = "AgGyXtMABg1dy66Kd9DjaNIUSds6CTQomsUhCmXVn0-fseieC4qzyP2Oq5EVAPrqsP-F7ws3ZkE4bpXbPYNZ-09jL31iMYZZhIPSfPjRSJd_k9xQrClvjsttXLcwelTLA7csRH9sPVER8ACTIgozIyTZzO891s4sVt5KhQKuPI4wSaF8YmtB_84n844SH_senWKCVDN92peoAFy39W263sVSUzOg8-Jg8UEmD8KhmN9RWtOnyKOqueNSJiDzyG1ae793emljY8jxNM3_4dEqkimzi5OahguB8QZ4yIzuPyM04mV_MqjQv_sq-XOsQ3zuKYZwgqZ95PNen1paIL3B527h0OwaAAAAAAH2gY3GAA"
BOT_TOKEN = "7052994065:AAGr3Mv8XpG4O7m8Cq5uE8-ZInY-k1XzF3Y"

# Ma'lumotlar bazasini sozlash
db = sqlite3.connect("konkurs.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, referrer_id INTEGER)")
db.commit()

# Botlarni yaratish
user_bot = Client("my_user_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- BOT FUNKSIYALARI ---

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # Bazada bormi tekshirish
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()

    if not user_exists:
        referrer_id = None
        if len(args) > 1 and args[1].isdigit():
            referrer_id = int(args[1])
            if referrer_id != user_id:
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (referrer_id,))
                await bot.send_message(referrer_id, "Tabriklaymiz! Do'stingiz qo'shildi va sizga 1 ball berildi.")
        
        cursor.execute("INSERT INTO users (user_id, points, referrer_id) VALUES (?, 0, ?)", (user_id, referrer_id))
        db.commit()

    # Klaviatura yaratish
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔗 Taklif qilish havolasi", callback_data="get_link"))
    builder.row(types.InlineKeyboardButton(text="📊 Mening ballarim", callback_data="my_points"))

    await message.answer(
        f"Salom {message.from_user.full_name}!\nKonkurs botimizga xush kelibsiz. Do'stlarni taklif qiling va ball yig'ing!",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data == "my_points")
async def show_points(callback: types.CallbackQuery):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (callback.from_user.id,))
    points = cursor.fetchone()[0]
    await callback.answer(f"Sizda {points} ball bor.", show_alert=True)

@dp.callback_query(lambda c: c.data == "get_link")
async def send_link(callback: types.CallbackQuery):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    await callback.message.answer(f"Sizning referal havolangiz:\n`{link}`", parse_mode="Markdown")
    await callback.answer()

async def main():
    print("Botlar Render-da muvaffaqiyatli ishlamoqda...")
    await user_bot.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
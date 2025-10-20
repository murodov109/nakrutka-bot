from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from random import choice
import asyncio

TOKEN = "8382109071:AAGsX1zJY7cqvVFekJTXDbYHP8nfRT8tYvk"
ADMIN_ID = 7617397626
REQUIRED_CHANNELS = ["@jonli_obunachipro", "@kerakli_xizmatlarn1"]
MAIN_CHANNEL = "@jonli_obunachipro"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

CARD_NUMBER = "8600 XXXX XXXX XXXX"
user_balances = {}
daily_tasks = {}

class OrderState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_link = State()

class PaymentState(StatesGroup):
    waiting_for_method = State()

async def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        member = await bot.get_chat_member(channel, user_id)
        if member.status not in ["member", "creator", "administrator"]:
            return False
    return True

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        markup = InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(InlineKeyboardButton("Tekshirish ✅", callback_data="check_subs"))
        await message.answer("Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Buyurtma berish", "Balansim")
    markup.add("To‘lov qilish", "Vazifalar")
    if message.from_user.id == ADMIN_ID:
        markup.add("Admin panel")
    await message.answer("Xush kelibsiz!", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "check_subs")
async def check_subs(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await start(callback.message)
    else:
        await callback.answer("Hali ham obuna bo‘lmagansiz.")

@dp.message_handler(lambda msg: msg.text == "Balansim")
async def balance(message: types.Message):
    bal = user_balances.get(message.from_user.id, 0)
    await message.answer(f"Balansingiz: {bal} so‘m")

@dp.message_handler(lambda msg: msg.text == "Buyurtma berish")
async def order(message: types.Message):
    await message.answer("Buyurtma linkini yuboring:")
    await OrderState.waiting_for_link.set()

@dp.message_handler(state=OrderState.waiting_for_link)
async def order_link(message: types.Message, state: FSMContext):
    await message.answer("Buyurtma qabul qilindi. Admin tez orada ko‘rib chiqadi.")
    await bot.send_message(ADMIN_ID, f"Buyurtma:\nID: {message.from_user.id}\nLink: {message.text}")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "To‘lov qilish")
async def payment(message: types.Message):
    await message.answer(f"To‘lov uchun karta:\n{CARD_NUMBER}")

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Admin panel")
async def admin_panel(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Karta raqamini o‘zgartirish", "Reklama tarqatish")
    markup.add("Bonus qo‘shish", "Omadli f tanlash")
    markup.add("Vazifa: qo‘shish")
    await message.answer("Admin panel:", reply_markup=markup)

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Karta raqamini o‘zgartirish")
async def change_card(message: types.Message):
    await message.answer("Yangi karta raqamini kiriting:")
    await PaymentState.waiting_for_method.set()

@dp.message_handler(state=PaymentState.waiting_for_method)
async def save_card(message: types.Message, state: FSMContext):
    global CARD_NUMBER
    CARD_NUMBER = message.text
    await message.answer("Karta raqami yangilandi.")
    await state.finish()

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Reklama tarqatish")
async def broadcast_start(message: types.Message):
    await message.answer("Reklama matnini yuboring:")
    await OrderState.waiting_for_link.set()

@dp.message_handler(state=OrderState.waiting_for_link)
async def broadcast_send(message: types.Message, state: FSMContext):
    for user_id in user_balances.keys():
        try:
            await bot.send_message(user_id, f"Reklama:\n{message.text}")
        except:
            continue
    await message.answer("Reklama yuborildi.")
    await state.finish()

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Bonus qo‘shish")
async def bonus_start(message: types.Message):
    await message.answer("Foydalanuvchi ID va miqdorni yozing (masalan: 123456789 500):")
    await OrderState.waiting_for_amount.set()

@dp.message_handler(state=OrderState.waiting_for_amount)
async def bonus_add(message: types.Message, state: FSMContext):
    try:
        uid, amount = message.text.split()
        uid = int(uid)
        amount = int(amount)
        user_balances[uid] = user_balances.get(uid, 0) + amount
        await message.answer(f"{uid} foydalanuvchiga +{amount} so‘m qo‘shildi.")
        await bot.send_message(uid, f"Admin tomonidan +{amount} so‘m bonus berildi.")
    except:
        await message.answer("Xato format. Qayta kiriting.")
    await state.finish()

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text.startswith("Vazifa:"))
async def add_task(message: types.Message):
    try:
        text, bonus = message.text.replace("Vazifa:", "").split("|")
        daily_tasks["text"] = text.strip()
        daily_tasks["bonus"] = int(bonus.strip())
        await message.answer("Vazifa qo‘shildi.")
    except:
        await message.answer("Xato format. Foydalaning: Vazifa: matn | bonus")

@dp.message_handler(lambda msg: msg.text == "Vazifalar")
async def show_task(message: types.Message):
    if "text" in daily_tasks:
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Bajardim", callback_data="task_done"))
        await message.answer(f"Kunlik vazifa:\n{daily_tasks['text']}\nMukofot: {daily_tasks['bonus']} so‘m", reply_markup=markup)
    else:
        await message.answer("Bugungi vazifa hali qo‘shilmagan.")

@dp.callback_query_handler(lambda c: c.data == "task_done")
async def task_done(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bonus = daily_tasks.get("bonus", 0)
    user_balances[user_id] = user_balances.get(user_id, 0) + bonus
    await callback.message.answer(f"Vazifa bajarildi. +{bonus} so‘m qo‘shildi.")

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Omadli f tanlash")
async def lucky_user(message: types.Message):
    if user_balances:
        lucky = choice(list(user_balances.keys()))
        try:
            user = await bot.get_chat(lucky)
            uname = user.username or "Foydalanuvchi"
            await message.answer(f"Bugungi omadli f:\nID: {lucky}\nUsername: @{uname}")
            for uid in user_balances.keys():
                if uid != lucky:
                    await bot.send_message(uid, f"Bugungi omadli f: @{uname}")
        except:
            await message.answer("Tanlangan foydalanuvchini topib bo‘lmadi.")
    else:
        await message.answer("Foydalanuvchilar ro‘yxati bo‘sh.")

async def main():
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

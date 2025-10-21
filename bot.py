import telebot
from telebot import types
from random import choice

TOKEN = "8382109071:AAGsX1zJY7cqvVFekJTXDbYHP8nfRT8tYvk"
ADMIN_ID = 7617397626
REQUIRED_CHANNELS = ["@jonli_obunachipro", "@kerakli_xizmatlarn1"]
MAIN_CHANNEL = "@jonli_obunachipro"

bot = telebot.TeleBot(TOKEN)
CARD_NUMBER = "8600 XXXX XXXX XXXX"
user_balances = {}
daily_tasks = {}

def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def start(message):
    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data="check_subs"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Buyurtma berish", "Balansim")
    markup.row("To‘lov qilish", "Vazifalar")
    if message.from_user.id == ADMIN_ID:
        markup.row("Admin panel")
    bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_subs")
def check_subs(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Hali ham obuna bo‘lmagansiz.")

@bot.message_handler(func=lambda msg: msg.text == "Balansim")
def balance(msg):
    bal = user_balances.get(msg.from_user.id, 0)
    bot.send_message(msg.chat.id, f"Balansingiz: {bal} so‘m")

@bot.message_handler(func=lambda msg: msg.text == "Buyurtma berish")
def order(msg):
    bot.send_message(msg.chat.id, "Buyurtma linkini yuboring:")
    bot.register_next_step_handler(msg, order_link)

def order_link(msg):
    bot.send_message(msg.chat.id, "Buyurtma qabul qilindi. Admin tez orada ko‘rib chiqadi.")
    bot.send_message(ADMIN_ID, f"Buyurtma:\nID: {msg.from_user.id}\nLink: {msg.text}")

@bot.message_handler(func=lambda msg: msg.text == "To‘lov qilish")
def payment(msg):
    bot.send_message(msg.chat.id, f"To‘lov uchun karta:\n{CARD_NUMBER}")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Admin panel")
def admin_panel(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Karta raqamini o‘zgartirish", "Reklama tarqatish")
    markup.row("Bonus qo‘shish", "Omadli f tanlash")
    markup.row("Vazifa: qo‘shish")
    bot.send_message(msg.chat.id, "Admin panel:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Karta raqamini o‘zgartirish")
def change_card(msg):
    bot.send_message(msg.chat.id, "Yangi karta raqamini kiriting:")
    bot.register_next_step_handler(msg, save_card)

def save_card(msg):
    global CARD_NUMBER
    CARD_NUMBER = msg.text
    bot.send_message(msg.chat.id, "Karta raqami yangilandi.")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Reklama tarqatish")
def broadcast_start(msg):
    bot.send_message(msg.chat.id, "Reklama matnini yuboring:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(msg):
    for uid in user_balances.keys():
        try:
            bot.send_message(uid, f"Reklama:\n{msg.text}")
        except:
            continue
    bot.send_message(msg.chat.id, "Reklama yuborildi.")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Bonus qo‘shish")
def bonus_start(msg):
    bot.send_message(msg.chat.id, "Foydalanuvchi ID va miqdorni yozing (masalan: 123456789 500):")
    bot.register_next_step_handler(msg, bonus_add)

def bonus_add(msg):
    try:
        uid, amount = msg.text.split()
        uid = int(uid)
        amount = int(amount)
        user_balances[uid] = user_balances.get(uid, 0) + amount
        bot.send_message(msg.chat.id, f"{uid} foydalanuvchiga +{amount} so‘m qo‘shildi.")
        bot.send_message(uid, f"Admin tomonidan +{amount} so‘m bonus berildi.")
    except:
        bot.send_message(msg.chat.id, "Xato format. Qayta kiriting.")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text.startswith("Vazifa:"))
def add_task(msg):
    try:
        text, bonus = msg.text.replace("Vazifa:", "").split("|")
        daily_tasks["text"] = text.strip()
        daily_tasks["bonus"] = int(bonus.strip())
        bot.send_message(msg.chat.id, "Vazifa qo‘shildi.")
    except:
        bot.send_message(msg.chat.id, "Xato format. Foydalaning: Vazifa: matn | bonus")

@bot.message_handler(func=lambda msg: msg.text == "Vazifalar")
def show_task(msg):
    if "text" in daily_tasks:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Bajardim", callback_data="task_done"))
        bot.send_message(msg.chat.id, f"Kunlik vazifa:\n{daily_tasks['text']}\nMukofot: {daily_tasks['bonus']} so‘m", reply_markup=markup)
    else:
        bot.send_message(msg.chat.id, "Bugungi vazifa hali qo‘shilmagan.")

@bot.callback_query_handler(func=lambda call: call.data == "task_done")
def task_done(call):
    uid = call.from_user.id
    bonus = daily_tasks.get("bonus", 0)
    user_balances[uid] = user_balances.get(uid, 0) + bonus
    bot.send_message(uid, f"Vazifa bajarildi. +{bonus} so‘m qo‘shildi.")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "Omadli f tanlash")
def lucky_user(msg):
    if user_balances:
        lucky = choice(list(user_balances.keys()))
        try:
            user = bot.get_chat(lucky)
            uname = user.username or "Foydalanuvchi"
            bot.send_message(msg.chat.id, f"Bugungi omadli f:\nID: {lucky}\nUsername: @{uname}")
            for uid in user_balances.keys():
                if uid != lucky:
                    bot.send_message(uid, f"Bugungi omadli f: @{uname}")
        except:
            bot.send_message(msg.chat.id, "Tanlangan foydalanuvchini topib bo‘lmadi.")
    else:
        bot.send_message(msg.chat.id, "Foydalanuvchilar ro‘yxati bo‘sh.")

bot.polling(none_stop=True)

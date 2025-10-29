import telebot
from telebot import types
from flask import Flask
import threading, json, os
from random import choice

TOKEN = "8382109071:AAGsX1zJY7cqvVFekJTXDbYHP8nfRT8tYvk"
ADMIN_ID = 7617397626
CARD_NUMBER = "8600 XXXX XXXX XXXX"

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "tasks": {}, "orders": {}, "channels": ["@jonli_obunachipro", "@kerakli_xizmatlarn1"], "admins": [ADMIN_ID]}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

bot = telebot.TeleBot(TOKEN)

def check_subscription(user_id):
    data = load_data()
    for ch in data["channels"]:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def start(message):
    data = load_data()
    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in data["channels"]:
            markup.add(types.InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data="check_subs"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 Buyurtma berish", "💰 Hisobim")
    markup.row("🧾 Hisobni to‘ldirish", "🧩 Vazifalar")
    markup.row("🤝 Pul ishlash")
    if message.from_user.id in data["admins"]:
        markup.row("👑 Admin panel")
    bot.send_message(message.chat.id, "Xush kelibsiz! Quyidagi tugmalardan birini tanlang 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_subs")
def check_subs(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Hali ham obuna bo‘lmagansiz.")

@bot.message_handler(func=lambda msg: msg.text == "💰 Hisobim")
def my_balance(msg):
    data = load_data()
    bal = data["users"].get(str(msg.from_user.id), {}).get("balance", 0)
    bot.send_message(msg.chat.id, f"Sizning balansingiz: {bal} so‘m 💵")

@bot.message_handler(func=lambda msg: msg.text == "👑 Admin panel")
def admin_panel(msg):
    data = load_data()
    if msg.from_user.id not in data["admins"]:
        bot.send_message(msg.chat.id, "Siz admin emassiz.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Statistika", "💳 Karta raqamini o‘zgartirish")
    markup.row("🧩 Vazifa qo‘shish", "💸 Hisobga pul qo‘shish")
    markup.row("🍀 Omadli foydalanuvchi", "📢 Reklama tarqatish")
    markup.row("🔗 Majburiy kanallar", "👤 Admin qo‘shish")
    markup.row("🔙 Orqaga")
    bot.send_message(msg.chat.id, "Admin panel:", reply_markup=markup)

app = Flask('')
@app.route('/')
def home():
    return "Bot 24/7 ishlayapti ✅"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

bot.polling(none_stop=True)

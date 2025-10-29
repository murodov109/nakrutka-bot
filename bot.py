import telebot
from telebot import types
import json
import os
from flask import Flask
import threading

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

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 24/7 ishlayapti ✅"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

@bot.message_handler(commands=['start'])
def start(message):
    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data["users"]:
        data["users"][user_id] = {"balance": 0, "tasks_done": [], "referal": None}
        save_data(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Buyurtma berish", "💰 Hisobim")
    markup.add("🧾 Hisobni to‘ldirish", "🎯 Vazifalar")
    markup.add("🤝 Pul ishlash")
    bot.send_message(message.chat.id, "👋 Salom! Botga xush kelibsiz!\nBu yerda siz buyurtma berishingiz yoki pul ishlashingiz mumkin 💸", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 Hisobim")
def my_balance(msg):
    data = load_data()
    bal = data["users"].get(str(msg.from_user.id), {}).get("balance", 0)
    bot.send_message(msg.chat.id, f"Sizning balansingiz: {bal} so‘m")

@bot.message_handler(func=lambda m: m.text == "🧾 Hisobni to‘ldirish")
def tolov(message):
    bot.send_message(message.chat.id, "💵 Hisobni to‘ldirish uchun quyidagi kartaga to‘lov yuboring:\n\n💳 9860 1234 5678 9012\n\nSo‘ng '✅ To‘lov qildim' deb yozing.")

@bot.message_handler(func=lambda m: m.text == "🛒 Buyurtma berish")
def buyurtma(message):
    msg = bot.send_message(message.chat.id, "📦 Buyurtma miqdorini kiriting (masalan: 10)")
    bot.register_next_step_handler(msg, buyurtma_miqdori)

def buyurtma_miqdori(message):
    try:
        miqdor = int(message.text)
        msg = bot.send_message(message.chat.id, "📎 Kanal yoki post havolasini yuboring:")
        bot.register_next_step_handler(msg, buyurtma_havola, miqdor)
    except:
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting.")

def buyurtma_havola(message, miqdor):
    link = message.text
    user_id = str(message.from_user.id)
    data = load_data()
    summa = miqdor * 100
    if data["users"][user_id]["balance"] < summa:
        bot.send_message(message.chat.id, f"💸 Sizda mablag‘ yetarli emas. Kerakli summa: {summa} so‘m.")
        return
    data["users"][user_id]["balance"] -= summa
    order_id = str(len(data["orders"]) + 1)
    data["orders"][order_id] = {"owner": user_id, "link": link, "done": 0, "total": miqdor}
    save_data(data)
    markup = types.InlineKeyboardMarkup()
    tugma = types.InlineKeyboardButton(f"💸 Pul ishlash (0/{miqdor})", callback_data=f"work_{order_id}")
    markup.add(tugma)
    bot.send_message(message.chat.id, "✅ Buyurtma qabul qilindi!")
    bot.send_message(-1000000000, f"🆕 Yangi buyurtma!\n🔗 {link}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("work_"))
def work_task(call):
    order_id = call.data.split("_")[1]
    data = load_data()
    user_id = str(call.from_user.id)
    order = data["orders"][order_id]

    if user_id == order["owner"]:
        bot.answer_callback_query(call.id, "❌ O‘zingizning buyurtmangizni bajara olmaysiz.")
        return

    if order_id in data["users"][user_id]["tasks_done"]:
        bot.answer_callback_query(call.id, "✅ Siz bu vazifani allaqachon bajargansiz.")
        return

    all_joined = True
    for ch in data["channels"]:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status == "left":
                all_joined = False
        except:
            all_joined = False

    if not all_joined:
        bot.answer_callback_query(call.id, "🚫 Avval barcha majburiy kanallarga obuna bo‘ling.")
        return

    data["users"][user_id]["balance"] += 100
    data["users"][user_id]["tasks_done"].append(order_id)
    order["done"] += 1

    if order["done"] >= order["total"]:
        markup = types.InlineKeyboardMarkup()
        tugma = types.InlineKeyboardButton("✅ Buyurtma bajarildi", callback_data="done")
        markup.add(tugma)
    else:
        markup = types.InlineKeyboardMarkup()
        tugma = types.InlineKeyboardButton(f"💸 Pul ishlash ({order['done']}/{order['total']})", callback_data=f"work_{order_id}")
        markup.add(tugma)

    save_data(data)
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup)
    except:
        pass

    bot.answer_callback_query(call.id, "💰 Vazifa bajarildi, balansga 100 so‘m qo‘shildi!")

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Statistika", "💳 Karta raqamini o‘zgartirish")
    markup.row("🧩 Vazifa qo‘shish", "💸 Hisobga pul qo‘shish")
    markup.row("🍀 Omadli foydalanuvchi", "📢 Reklama tarqatish")
    markup.row("🔗 Majburiy kanallar", "👤 Admin qo‘shish")
    markup.row("🔙 Orqaga")
    bot.send_message(message.chat.id, "Admin panel:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👤 Admin qo‘shish")
def add_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "🆔 Yangi admin ID sini yuboring:")
    bot.register_next_step_handler(msg, save_admin)

def save_admin(message):
    data = load_data()
    try:
        new_admin = int(message.text)
        if new_admin not in data["admins"]:
            data["admins"].append(new_admin)
            save_data(data)
            bot.send_message(message.chat.id, "✅ Yangi admin muvaffaqiyatli qo‘shildi.")
        else:
            bot.send_message(message.chat.id, "⚠️ Bu foydalanuvchi allaqachon admin.")
    except:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri ID format.")

bot.polling(none_stop=True)

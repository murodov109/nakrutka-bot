import telebot
from telebot import types
from random import choice
from flask import Flask
import threading

TOKEN = "8382109071:AAGsX1zJY7cqvVFekJTXDbYHP8nfRT8tYvk"
ADMIN_ID = 7617397626
REQUIRED_CHANNELS = ["@jonli_obunachipro", "@kerakli_xizmatlarn1"]
MAIN_CHANNEL = "@jonli_obunachipro"

bot = telebot.TeleBot(TOKEN)
CARD_NUMBER = "8600 XXXX XXXX XXXX"
user_balances = {}
daily_tasks = {}
orders = {}
completed_tasks = {}
referrals = {}
order_progress = {}

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

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
    markup.row("🛒 Buyurtma berish", "💰 Hisobim")
    markup.row("🎯 Vazifalar", "💳 Hisobni to‘ldirish")
    markup.row("👥 Pul ishlash")
    if message.from_user.id == ADMIN_ID:
        markup.row("⚙️ Admin panel")
    bot.send_message(message.chat.id, "Xush kelibsiz! Quyidagi tugmalar orqali harakat qiling 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_subs")
def check_subs(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Hali ham obuna bo‘lmagansiz.")

@bot.message_handler(func=lambda msg: msg.text == "💰 Hisobim")
def balance(msg):
    bal = user_balances.get(msg.from_user.id, 0)
    bot.send_message(msg.chat.id, f"Sizning hisobingiz: {bal} so‘m")

@bot.message_handler(func=lambda msg: msg.text == "🛒 Buyurtma berish")
def order_start(msg):
    bot.send_message(msg.chat.id, "Buyurtma sonini kiriting (masalan: 10):")
    bot.register_next_step_handler(msg, order_amount)

def order_amount(msg):
    try:
        count = int(msg.text)
        cost = count * 100
        uid = msg.from_user.id
        if user_balances.get(uid, 0) < cost:
            bot.send_message(msg.chat.id, f"Balansingizda yetarli mablag‘ yo‘q.\nKerakli summa: {cost} so‘m")
            return
        orders[uid] = {"count": count, "cost": cost}
        bot.send_message(msg.chat.id, "Kanal yoki guruh havolasini yuboring:")
        bot.register_next_step_handler(msg, order_link)
    except:
        bot.send_message(msg.chat.id, "Iltimos, raqam kiriting.")

def order_link(msg):
    uid = msg.from_user.id
    link = msg.text
    if uid not in orders:
        bot.send_message(msg.chat.id, "Buyurtma ma’lumotlari topilmadi.")
        return
    count = orders[uid]["count"]
    cost = orders[uid]["cost"]
    user_balances[uid] -= cost
    order_progress[uid] = {"done": 0, "total": count}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"💸 Pul ishlash (0/{count})", callback_data=f"task_{uid}"))
    post_text = f"🆕 Yangi buyurtma!\nObuna bo‘ling va 100 so‘m oling!\n{link}"
    bot.send_message(MAIN_CHANNEL, post_text, reply_markup=markup)
    bot.send_message(msg.chat.id, f"Buyurtma qabul qilindi! {cost} so‘m hisobingizdan yechildi.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
def task_do(call):
    try:
        order_owner = int(call.data.split("_")[1])
        uid = call.from_user.id
        if order_owner == uid:
            bot.answer_callback_query(call.id, "O‘zingizning buyurtmangizni bajara olmaysiz.")
            return
        if uid in completed_tasks.get(order_owner, []):
            bot.answer_callback_query(call.id, "Siz bu vazifani allaqachon bajargansiz.")
            return
        if not check_subscription(uid):
            bot.answer_callback_query(call.id, "Avval majburiy kanallarga obuna bo‘ling.")
            return
        completed_tasks.setdefault(order_owner, []).append(uid)
        order_progress[order_owner]["done"] += 1
        bot.send_message(uid, "✅ Vazifa bajarildi! Hisobingizga 100 so‘m qo‘shildi.")
        user_balances[uid] = user_balances.get(uid, 0) + 100
        done = order_progress[order_owner]["done"]
        total = order_progress[order_owner]["total"]
        if done >= total:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "✅ Buyurtma muvaffaqiyatli bajarildi!")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💸 Pul ishlash ({done}/{total})", callback_data=f"task_{order_owner}"))
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        pass

@bot.message_handler(func=lambda msg: msg.text == "💳 Hisobni to‘ldirish")
def pay(msg):
    bot.send_message(msg.chat.id, f"To‘lov uchun karta: {CARD_NUMBER}\nTo‘lov qilganingizdan so‘ng 'Tolov qildim' deb yozing.")

@bot.message_handler(func=lambda msg: msg.text.lower() == "tolov qildim")
def pay_check(msg):
    bot.send_message(ADMIN_ID, f"Foydalanuvchi {msg.from_user.id} to‘lovni amalga oshirdi. Tekshirib tasdiqlang.")

@bot.message_handler(func=lambda msg: msg.text == "👥 Pul ishlash")
def referal(msg):
    ref_link = f"https://t.me/{bot.get_me().username}?start={msg.from_user.id}"
    bot.send_message(msg.chat.id, f"Sizning referal havolangiz:\n{ref_link}\nHar bir do‘st uchun 300 so‘m olasiz!")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "⚙️ Admin panel")
def admin(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Bot statistikasi", "➕ Vazifa qo‘shish")
    markup.row("💳 Karta raqamni o‘zgartirish", "🎁 Foydalanuvchi hisobiga pul qo‘shish")
    markup.row("🍀 Omadli foydalanuvchi", "📢 Reklama tarqatish")
    markup.row("🔗 Majburiy kanallarni o‘zgartirish")
    bot.send_message(msg.chat.id, "Admin panel:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "📊 Bot statistikasi")
def stats(msg):
    total_users = len(user_balances)
    active = sum(1 for u in user_balances if user_balances[u] > 0)
    bot.send_message(msg.chat.id, f"Umumiy foydalanuvchilar: {total_users}\nFaol foydalanuvchilar: {active}")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)

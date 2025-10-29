import os
import telebot
from telebot import types
from random import choice
from flask import Flask
import threading

TOKEN = "8382109071:AAGsX1zJY7cqvVFekJTXDbYHP8nfRT8tYvk"
ADMIN_ID = 7617397626
REQUIRED_CHANNELS = ["@jonli_obunachipro", "@kerakli_xizmatlarn1"]
MAIN_CHANNEL = "@jonli_obunachipro"
CARD_NUMBER = "8600 XXXX XXXX XXXX"

bot = telebot.TeleBot(TOKEN)
user_balances = {}
daily_tasks = {}
orders = {}
pending_payments = {}
referrals = {}
user_states = {}
order_completers = {}
stats = {"total_orders": 0, "total_payments": 0}

def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True

def main_menu_markup(is_admin=False):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🛒 Buyurtma berish", "💰 Hisobim")
    m.row("🧩 Vazifalar", "💳 Hisobni to'ldirish")
    m.row("💸 Pul ishlash")
    if is_admin:
        m.row("⚙️ Admin panel")
    return m

def admin_panel_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("📊 Bot statistikasi", "🧾 Vazifa qo'shish")
    m.row("💵 Karta raqamni o'zgartirish", "➕ Foydalanuvchi hisobiga pul qo'shish")
    m.row("🍀 Omadli foydalanuvchi", "📢 Reklama tarqatish")
    m.row("🔗 Majburiy kanallarni o'zgartirish")
    return m

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = ""
    if message.text and " " in message.text:
        args = message.text.split(" ",1)[1].strip()
    if args.isdigit():
        ref = int(args)
        if ref != user_id:
            referrals.setdefault(ref, []).append(user_id)
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton("🔔 Obuna bo'lish: " + ch, url="https://t.me/" + ch[1:]))
        markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs"))
        bot.send_message(message.chat.id, "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=markup)
        return
    is_admin = user_id == ADMIN_ID
    bot.send_message(message.chat.id, "👋 Xush kelibsiz, " + (message.from_user.first_name or "Foydalanuvchi") + "!", reply_markup=main_menu_markup(is_admin))

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def cb_check_subs(call):
    if check_subscription(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Hali ham obuna bo'lmagansiz.")

@bot.message_handler(func=lambda m: m.text == "💰 Hisobim")
def handle_balance(m):
    bal = user_balances.get(m.from_user.id, 0)
    bot.send_message(m.chat.id, "💰 Hisobingiz: " + str(bal) + " so'm")

@bot.message_handler(func=lambda m: m.text == "🛒 Buyurtma berish")
def handle_order_start(m):
    user_states[m.from_user.id] = {"step":"await_count"}
    bot.send_message(m.chat.id, "Nechta obunachi kerak? (raqam bilan kiriting)")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_count")
def handle_order_count(m):
    try:
        cnt = int(m.text.strip())
        if cnt <= 0:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Iltimos to'g'ri raqam kiriting.")
        return
    total = cnt * 100
    user_states[m.from_user.id] = {"step":"confirm_order","count":cnt,"total":total}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm_order"))
    markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_order"))
    bot.send_message(m.chat.id, "Jami: " + str(total) + " so'm. Tasdiqlaysizmi?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data in ["confirm_order","cancel_order"])
def cb_confirm_order(call):
    uid = call.from_user.id
    state = user_states.get(uid, {})
    if call.data == "cancel_order":
        user_states.pop(uid, None)
        bot.answer_callback_query(call.id, "Buyurtma bekor qilindi.")
        bot.send_message(call.message.chat.id, "Buyurtma bekor qilindi.", reply_markup=main_menu_markup(uid==ADMIN_ID))
        return
    if state.get("step") != "confirm_order":
        bot.answer_callback_query(call.id, "Hech nima kutilmoqda.")
        return
    total = state["total"]
    bal = user_balances.get(uid,0)
    if bal < total:
        bot.answer_callback_query(call.id, "Hisobingizda yetarli mablag' yo'q.")
        bot.send_message(call.message.chat.id, "💰 Hisobingiz: " + str(bal) + " so'm. Yetarli summa yo'q.")
        user_states.pop(uid, None)
        return
    user_balances[uid] = bal - total
    user_states[uid]["step"] = "await_channel"
    bot.answer_callback_query(call.id, "To'lov yechildi. Kanal yoki guruh havolasini yuboring.")
    bot.send_message(call.message.chat.id, "Kanal yoki guruh havolasini yuboring:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_channel")
def handle_order_channel(m):
    uid = m.from_user.id
    link = m.text.strip()
    st = user_states.get(uid)
    cnt = st.get("count")
    total = st.get("total")
    order_id = len(orders)+1
    orders[order_id] = {"owner":uid,"count":cnt,"total":total,"link":link,"completed":0,"message_id":None,"chat_id":None}
    order_completers[order_id] = set()
    stats["total_orders"] += 1
    user_states.pop(uid, None)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💸 Pul ishlash (0/" + str(cnt) + ")", callback_data="earn_" + str(order_id)))
    owner_text = "Yangi buyurtma " + str(order_id) + "\nID: " + str(order_id) + "\nFoydalanuvchi: " + str(uid) + "\nSumma: " + str(total) + "\nLink: " + link
    bot.send_message(uid, "✅ Buyurtma qabul qilindi. Adminga xabar yuborildi. Buyurtma ID: " + str(order_id))
    try:
        bot.send_message(ADMIN_ID, owner_text)
    except:
        pass
    try:
        sent = bot.send_message(MAIN_CHANNEL, "🔔 Buyurtma " + str(order_id) + "\nLink: " + link + "\nPul ishlash uchun pastdagi tugmani bosing.", reply_markup=kb)
        orders[order_id]["message_id"] = sent.message_id
        orders[order_id]["chat_id"] = sent.chat.id
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_"))
def cb_earn(call):
    order_id = int(call.data.split("_",1)[1])
    order = orders.get(order_id)
    if not order:
        bot.answer_callback_query(call.id, "Buyurtma topilmadi.")
        return
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "Iltimos, kanalga obuna bo'ling va tasdiqlang.")
    bot.send_message(uid, "Buyurtma " + str(order_id) + " bo'yicha kanalga obuna bo'ling va /tasdiqlash_" + str(order_id) + " yozing.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/tasdiqlash_"))
def handle_verify(m):
    try:
        order_id = int(m.text.split("_",1)[1])
    except:
        return
    order = orders.get(order_id)
    if not order:
        bot.send_message(m.chat.id, "Buyurtma topilmadi.")
        return
    user = m.from_user
    if not check_subscription(user.id):
        bot.send_message(m.chat.id, "Siz majburiy kanallarga obuna bo'lmagansiz.")
        return
    if user.id in order_completers.get(order_id,set()):
        bot.send_message(m.chat.id, "❗ Siz ushbu vazifani allaqachon bajargansiz.")
        return
    order["completed"] += 1
    order_completers[order_id].add(user.id)
    user_balances[user.id] = user_balances.get(user.id,0) + 100
    bot.send_message(m.chat.id, "✅ Vazifa tasdiqlandi. Hisobingizga 100 so'm qo'shildi.")
    owner = order["owner"]
    try:
        bot.send_message(owner, "Sizning buyurtmangiz " + str(order_id) + " uchun bitta bajarildi (" + str(order["completed"]) + "/" + str(order["count"]) + ")")
    except:
        pass
    cnt = order["count"]
    comp = order["completed"]
    chat_id = order.get("chat_id")
    message_id = order.get("message_id")
    if chat_id and message_id:
        if comp >= cnt:
            try:
                bot.edit_message_text("✅ Buyurtma " + str(order_id) + " muvaffaqiyatli bajarildi", chat_id, message_id)
            except:
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
                except:
                    pass
        else:
            try:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("💸 Pul ishlash (" + str(comp) + "/" + str(cnt) + ")", callback_data="earn_" + str(order_id)))
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
            except:
                pass

@bot.message_handler(func=lambda m: m.text == "💳 Hisobni to'ldirish")
def handle_topup_start(m):
    user_states[m.from_user.id] = {"step":"await_topup_amount"}
    bot.send_message(m.chat.id, "Qancha to'ldirmoqchisiz? (raqam)")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_topup_amount")
def handle_topup_amount(m):
    try:
        amt = int(m.text.strip())
        if amt <= 0:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Iltimos to'g'ri raqam kiriting.")
        return
    user_states[m.from_user.id] = {"step":"await_receipt","amount":amt}
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 To'lov qildim", callback_data="paid_proceed"))
    bot.send_message(m.chat.id, "Karta raqam: " + CARD_NUMBER + "\nPul o'tkazganingizdan keyin '💳 To'lov qildim' tugmasini bosing va chek yuboring.", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "paid_proceed")
def cb_paid_proceed(call):
    uid = call.from_user.id
    state = user_states.get(uid, {})
    if state.get("step") != "await_receipt":
        bot.answer_callback_query(call.id, "Hech nima bekor.")
        return
    bot.answer_callback_query(call.id, "Iltimos to'lov chekini yuboring (rasm yoki matn).")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_receipt", content_types=['photo','text','document'])
def handle_receipt(m):
    uid = m.from_user.id
    state = user_states.get(uid, {})
    amt = state.get("amount",0)
    pid = len(pending_payments)+1
    pending_payments[pid] = {"user":uid,"amount":amt,"receipt":m}
    user_states.pop(uid, None)
    bot.send_message(uid, "📨 Ariza yaratildi, admin tasdiqlashini kuting.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="approve_pay_" + str(pid)))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="reject_pay_" + str(pid)))
    text = "To'lov arizasi " + str(pid) + "\nFoydalanuvchi: " + str(uid) + "\nSumma: " + str(amt)
    if m.content_type == "photo":
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=text, reply_markup=kb)
    elif m.content_type == "document":
        bot.send_document(ADMIN_ID, m.document.file_id, caption=text, reply_markup=kb)
    else:
        bot.send_message(ADMIN_ID, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_pay_") or c.data.startswith("reject_pay_"))
def cb_handle_payment_admin(call):
    parts = call.data.split("_")
    action = parts[0]
    pid = int(parts[2])
    p = pending_payments.get(pid)
    if not p:
        bot.answer_callback_query(call.id, "Ariza topilmadi.")
        return
    if action == "approve":
        uid = p["user"]
        amt = p["amount"]
        user_balances[uid] = user_balances.get(uid,0) + amt
        stats["total_payments"] += amt
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
        bot.send_message(call.message.chat.id, "Ariza " + str(pid) + " tasdiqlandi.")
        bot.send_message(uid, "✅ Sizning to'lovingiz " + str(amt) + " so'm tasdiqlandi. Hisobingizga qo'shildi.")
        pending_payments.pop(pid, None)
    else:
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
        bot.send_message(call.message.chat.id, "Ariza " + str(pid) + " bekor qilindi.")
        bot.send_message(p["user"], "❌ Sizning to'lov arizangiz bekor qilindi.")
        pending_payments.pop(pid, None)

@bot.message_handler(func=lambda m: m.text == "🧩 Vazifalar")
def handle_tasks(m):
    if not daily_tasks:
        bot.send_message(m.chat.id, "Hozircha vazifa yo'q.")
        return
    lines = []
    for i,t in enumerate(daily_tasks.get("list",[]),1):
        lines.append(str(i) + ". " + t['text'] + " - " + str(t['bonus']) + " so'm")
    bot.send_message(m.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda m: m.text == "💸 Pul ishlash")
def handle_referral(m):
    me = bot.get_me()
    link = "https://t.me/" + me.username + "?start=" + str(m.from_user.id)
    bot.send_message(m.chat.id, "Sizning referal havolangiz:\n" + link + "\nHar bir to'liq obunadan so'ng sizga 300 so'm beriladi.")

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin panel" and m.from_user.id == ADMIN_ID)
def handle_admin(m):
    bot.send_message(m.chat.id, "👑 Admin panel:", reply_markup=admin_panel_markup())

@bot.message_handler(func=lambda m: m.text == "📊 Bot statistikasi" and m.from_user.id == ADMIN_ID)
def admin_stats(m):
    total_users = len(user_balances)
    active_24h = "N/A"
    text = "👥 Foydalanuvchilar: " + str(total_users) + "\n⚡ Aktiv (24h): " + str(active_24h) + "\n🗂️ Buyurtmalar jami: " + str(stats['total_orders']) + "\n💳 To'lovlar jami: " + str(stats['total_payments'])
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "💵 Karta raqamni o'zgartirish" and m.from_user.id == ADMIN_ID)
def admin_change_card(m):
    user_states[ADMIN_ID] = {"step":"await_new_card"}
    bot.send_message(m.chat.id, "Yangi karta raqamini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_new_card")
def admin_save_card(m):
    global CARD_NUMBER
    CARD_NUMBER = m.text.strip()
    user_states.pop(ADMIN_ID, None)
    bot.send_message(m.chat.id, "✅ Karta yangilandi.")

@bot.message_handler(func=lambda m: m.text == "🧾 Vazifa qo'shish" and m.from_user.id == ADMIN_ID)
def admin_add_task_start(m):
    user_states[ADMIN_ID] = {"step":"await_task"}
    bot.send_message(m.chat.id, "Vazifa matnini va bonusni kiriting (matn | bonus):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_task")
def admin_add_task_save(m):
    try:
        text,bonus = m.text.split("|",1)
        daily_tasks.setdefault("list",[]).append({"text":text.strip(),"bonus":int(bonus.strip())})
        bot.send_message(m.chat.id, "✅ Vazifa qo'shildi.")
    except:
        bot.send_message(m.chat.id, "Format xato. Matn | bonus tarzida yuboring.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "➕ Foydalanuvchi hisobiga pul qo'shish" and m.from_user.id == ADMIN_ID)
def admin_add_balance_start(m):
    user_states[ADMIN_ID] = {"step":"await_topup_user"}
    bot.send_message(m.chat.id, "Foydalanuvchi ID sini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_topup_user")
def admin_add_balance_get_user(m):
    try:
        uid = int(m.text.strip())
        user_states[ADMIN_ID] = {"step":"await_topup_amount","target":uid}
        bot.send_message(m.chat.id, "Summa kiriting:")
    except:
        bot.send_message(m.chat.id, "Iltimos to'g'ri ID kiriting.")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_topup_amount")
def admin_add_balance_finish(m):
    try:
        amt = int(m.text.strip())
        target = user_states[ADMIN_ID]["target"]
        user_balances[target] = user_balances.get(target,0) + amt
        bot.send_message(m.chat.id, str(target) + " hisobiga " + str(amt) + " qo'shildi.")
        bot.send_message(target, "✅ Sizning hisobingizga admin tomonidan " + str(amt) + " so'm qo'shildi.")
    except:
        bot.send_message(m.chat.id, "Xato summa.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🍀 Omadli foydalanuvchi" and m.from_user.id == ADMIN_ID)
def admin_lucky(m):
    if not user_balances:
        bot.send_message(m.chat.id, "Foydalanuvchilar yo'q.")
        return
    lucky = choice(list(user_balances.keys()))
    try:
        u = bot.get_chat(lucky)
        uname = u.username or "Foydalanuvchi"
    except:
        uname = "Foydalanuvchi"
    bot.send_message(m.chat.id, "🎉 Bugungi omadli: ID " + str(lucky) + " @" + str(uname))
    for uid in user_balances.keys():
        if uid != lucky:
            bot.send_message(uid, "🎉 Bugungi omadli foydalanuvchimiz: @" + str(uname))

@bot.message_handler(func=lambda m: m.text == "📢 Reklama tarqatish" and m.from_user.id == ADMIN_ID)
def admin_broadcast_start(m):
    user_states[ADMIN_ID] = {"step":"await_broadcast"}
    bot.send_message(m.chat.id, "Reklama matnini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_broadcast", content_types=['text','photo','document'])
def admin_broadcast_send(m):
    for uid in list(user_balances.keys()):
        try:
            if m.content_type == "text":
                bot.send_message(uid, "📣 Reklama:\n" + m.text)
            elif m.content_type == "photo":
                bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption or "")
            else:
                bot.send_document(uid, m.document.file_id, caption=m.caption or "")
        except:
            continue
    bot.send_message(ADMIN_ID, "✅ Reklama yuborildi.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🔗 Majburiy kanallarni o'zgartirish" and m.from_user.id == ADMIN_ID)
def admin_change_channels_start(m):
    user_states[ADMIN_ID] = {"step":"await_channels"}
    bot.send_message(m.chat.id, "Yangi kanallarni vergul bilan yuboring masalan: @kanal1,@kanal2")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_channels")
def admin_change_channels_save(m):
    try:
        parts = [p.strip() for p in m.text.split(",") if p.strip()]
        if parts:
            global REQUIRED_CHANNELS
            REQUIRED_CHANNELS = parts
            bot.send_message(m.chat.id, "🔔 Majburiy kanallar yangilandi.")
        else:
            bot.send_message(m.chat.id, "Hech nima topilmadi.")
    except:
        bot.send_message(m.chat.id, "Xato format.")
    user_states.pop(ADMIN_ID, None)

app = Flask('')
@app.route('/')
def home():
    return "Bot ishlayapti"
def run():
    app.run(host="0.0.0.0", port=8080)
bot.infinity_polling()

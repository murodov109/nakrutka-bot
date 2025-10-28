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
    m.row("Buyurtma berish", "Hisobim")
    m.row("Vazifalar", "Hisobni to‘ldirish")
    m.row("Pul ishlash")
    if is_admin:
        m.row("Admin panel")
    return m

def admin_panel_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("Bot statistikasi", "Vazifa qo‘shish")
    m.row("Karta raqamni o‘zgartirish", "Foydalanuvchi hisobiga pul qo‘shish")
    m.row("Omadli foydalanuvchi", "Reklama tarqatish")
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
            markup.add(types.InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data="check_subs"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)
        return
    is_admin = user_id == ADMIN_ID
    bot.send_message(message.chat.id, f"Xush kelibsiz, {message.from_user.first_name}!", reply_markup=main_menu_markup(is_admin))

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def cb_check_subs(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Hali ham obuna bo‘lmagansiz.")

@bot.message_handler(func=lambda m: m.text == "Hisobim")
def handle_balance(m):
    bal = user_balances.get(m.from_user.id, 0)
    bot.send_message(m.chat.id, f"Hisobingiz: {bal} so‘m")

@bot.message_handler(func=lambda m: m.text == "Buyurtma berish")
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
        bot.send_message(m.chat.id, "Iltimos to‘g‘ri raqam kiriting.")
        return
    total = cnt * 100
    user_states[m.from_user.id] = {"step":"confirm_order","count":cnt,"total":total}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Tasdiqlayman ✅", callback_data="confirm_order"))
    markup.add(types.InlineKeyboardButton("Bekor qilish ❌", callback_data="cancel_order"))
    bot.send_message(m.chat.id, f"Jami: {total} so‘m. Tasdiqlaysizmi?", reply_markup=markup)

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
        bot.answer_callback_query(call.id, "Hisobingizda yetarli mablag‘ yo‘q.")
        bot.send_message(call.message.chat.id, f"Hisobingiz: {bal} so‘m. Yetarli summa yo‘q.")
        user_states.pop(uid, None)
        return
    user_balances[uid] = bal - total
    user_states[uid]["step"] = "await_channel"
    bot.answer_callback_query(call.id, "To‘lov yechildi. Kanal yoki guruh havolasini yuboring.")
    bot.send_message(call.message.chat.id, "Kanal yoki guruh havolasini yuboring:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_channel")
def handle_order_channel(m):
    uid = m.from_user.id
    link = m.text.strip()
    st = user_states.get(uid)
    cnt = st.get("count")
    total = st.get("total")
    order_id = len(orders)+1
    orders[order_id] = {"owner":uid,"count":cnt,"total":total,"link":link,"completed":0}
    stats["total_orders"] += 1
    user_states.pop(uid, None)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"Pul ishlash ({orders[order_id]['completed']}/{cnt})", callback_data=f"earn_{order_id}"))
    bot.send_message(m.chat.id, "Buyurtma qabul qilindi. Admin haydaladi. Buyurtma ID: "+str(order_id))
    bot.send_message(ADMIN_ID, f"Yangi buyurtma #{order_id}\nID: {order_id}\nFoydalanuvchi: {uid}\nSumma: {total}\nLink: {link}")
    bot.send_message(MAIN_CHANNEL, f"Buyurtma #{order_id}\nLink: {link}\nPul ishlash uchun pastdagi tugmani bosing.", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_"))
def cb_earn(call):
    order_id = int(call.data.split("_",1)[1])
    order = orders.get(order_id)
    if not order:
        bot.answer_callback_query(call.id, "Buyurtma topilmadi.")
        return
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "Iltimos, kanalga obuna bo‘ling va tasdiqlang.")
    msg = bot.send_message(uid, f"Buyurtma #{order_id} bo‘yicha kanalga obuna bo‘ling va /tasdiqlash_{order_id} yozing.")
    return

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
        bot.send_message(m.chat.id, "Siz majburiy kanallarga obuna bo‘lmagansiz.")
        return
    order["completed"] += 1
    user_balances[user.id] = user_balances.get(user.id,0) + 100
    bot.send_message(m.chat.id, "Vazifa tasdiqlandi. Hisobingizga 100 so‘m qo‘shildi.")
    owner = order["owner"]
    bot.send_message(owner, f"Sizning buyurtmangiz #{order_id} uchun bitta bajarildi ({order['completed']}/{order['count']})")
    if order["completed"] >= order["count"]:
        bot.send_message(MAIN_CHANNEL, f"Buyurtma #{order_id} bajarildi ✅")
        bot.send_message(owner, f"Sizning buyurtmangiz #{order_id} to‘liq bajarildi ✅")

@bot.message_handler(func=lambda m: m.text == "Hisobni to‘ldirish")
def handle_topup_start(m):
    user_states[m.from_user.id] = {"step":"await_topup_amount"}
    bot.send_message(m.chat.id, "Qancha to‘ldirmoqchisiz? (raqam)")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_topup_amount")
def handle_topup_amount(m):
    try:
        amt = int(m.text.strip())
        if amt <= 0:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Iltimos to‘g‘ri raqam kiriting.")
        return
    user_states[m.from_user.id] = {"step":"await_receipt","amount":amt}
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("To‘lov qildim", callback_data="paid_proceed"))
    bot.send_message(m.chat.id, f"Karta raqam: {CARD_NUMBER}\nPul o‘tkazganingizdan keyin 'To‘lov qildim' tugmasini bosing va chek yuboring.", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "paid_proceed")
def cb_paid_proceed(call):
    uid = call.from_user.id
    state = user_states.get(uid, {})
    if state.get("step") != "await_receipt":
        bot.answer_callback_query(call.id, "Hech nima bekor.")
        return
    bot.answer_callback_query(call.id, "Iltimos to‘lov chekini yuboring (rasm yoki matn).")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id,{}).get("step")=="await_receipt", content_types=['photo','text','document'])
def handle_receipt(m):
    uid = m.from_user.id
    state = user_states.get(uid, {})
    amt = state.get("amount",0)
    pid = len(pending_payments)+1
    pending_payments[pid] = {"user":uid,"amount":amt,"receipt":m}
    user_states.pop(uid, None)
    bot.send_message(uid, "Ariza yaratildi, admin tasdiqlashini kuting.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Tasdiqlash ✅", callback_data=f"approve_pay_{pid}"))
    kb.add(types.InlineKeyboardButton("Bekor qilish ❌", callback_data=f"reject_pay_{pid}"))
    text = f"To‘lov arizasi #{pid}\nFoydalanuvchi: {uid}\nSumma: {amt}"
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
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"Ariza #{pid} tasdiqlandi.")
        bot.send_message(uid, f"Sizning to‘lovingiz {amt} so‘m tasdiqlandi. Hisobingizga qo‘shildi.")
        pending_payments.pop(pid, None)
    else:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"Ariza #{pid} bekor qilindi.")
        bot.send_message(p["user"], "Sizning to‘lov arizangiz bekor qilindi.")
        pending_payments.pop(pid, None)

@bot.message_handler(func=lambda m: m.text == "Vazifalar")
def handle_tasks(m):
    if not daily_tasks:
        bot.send_message(m.chat.id, "Hozircha vazifa yo‘q.")
        return
    lines = []
    for i,t in enumerate(daily_tasks.get("list",[]),1):
        lines.append(f"{i}. {t['text']} - {t['bonus']} so‘m")
    bot.send_message(m.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda m: m.text == "Pul ishlash")
def handle_referral(m):
    me = bot.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Sizning referal havolangiz:\n{link}\nHar bir to‘liq obunadan so‘ng sizga 300 so‘m beriladi.")

@bot.message_handler(func=lambda m: m.text == "Admin panel" and m.from_user.id == ADMIN_ID)
def handle_admin(m):
    bot.send_message(m.chat.id, "Admin panel:", reply_markup=admin_panel_markup())

@bot.message_handler(func=lambda m: m.text == "Bot statistikasi" and m.from_user.id == ADMIN_ID)
def admin_stats(m):
    total_users = len(user_balances)
    active_24h = "N/A"
    text = f"Foydalanuvchilar: {total_users}\nAktiv (24h): {active_24h}\nBuyurtmalar jami: {stats['total_orders']}\nTo‘lovlar jami: {stats['total_payments']}"
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "Karta raqamni o‘zgartirish" and m.from_user.id == ADMIN_ID)
def admin_change_card(m):
    user_states[ADMIN_ID] = {"step":"await_new_card"}
    bot.send_message(m.chat.id, "Yangi karta raqamini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_new_card")
def admin_save_card(m):
    global CARD_NUMBER
    CARD_NUMBER = m.text.strip()
    user_states.pop(ADMIN_ID, None)
    bot.send_message(m.chat.id, "Karta yangilandi.")

@bot.message_handler(func=lambda m: m.text == "Vazifa qo‘shish" and m.from_user.id == ADMIN_ID)
def admin_add_task_start(m):
    user_states[ADMIN_ID] = {"step":"await_task"}
    bot.send_message(m.chat.id, "Vazifa matnini va bonusni kiriting (matn | bonus):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_task")
def admin_add_task_save(m):
    try:
        text,bonus = m.text.split("|",1)
        daily_tasks.setdefault("list",[]).append({"text":text.strip(),"bonus":int(bonus.strip())})
        bot.send_message(m.chat.id, "Vazifa qo‘shildi.")
    except:
        bot.send_message(m.chat.id, "Format xato. Matn | bonus tarzida yuboring.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "Foydalanuvchi hisobiga pul qo‘shish" and m.from_user.id == ADMIN_ID)
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
        bot.send_message(m.chat.id, "Iltimos to‘g‘ri ID kiriting.")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_topup_amount")
def admin_add_balance_finish(m):
    try:
        amt = int(m.text.strip())
        target = user_states[ADMIN_ID]["target"]
        user_balances[target] = user_balances.get(target,0) + amt
        bot.send_message(m.chat.id, f"{target} hisobiga {amt} qo‘shildi.")
        bot.send_message(target, f"Sizning hisobingizga admin tomonidan {amt} so‘m qo‘shildi.")
    except:
        bot.send_message(m.chat.id, "Xato summa.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "Omadli foydalanuvchi" and m.from_user.id == ADMIN_ID)
def admin_lucky(m):
    if not user_balances:
        bot.send_message(m.chat.id, "Foydalanuvchilar yo‘q.")
        return
    lucky = choice(list(user_balances.keys()))
    try:
        u = bot.get_chat(lucky)
        uname = u.username or "Foydalanuvchi"
    except:
        uname = "Foydalanuvchi"
    bot.send_message(m.chat.id, f"Bugungi omadli: ID {lucky} @{uname}")
    for uid in user_balances.keys():
        if uid != lucky:
            bot.send_message(uid, f"🎉 Bugungi omadli foydalanuvchimiz: @{uname}")

@bot.message_handler(func=lambda m: m.text == "Reklama tarqatish" and m.from_user.id == ADMIN_ID)
def admin_broadcast_start(m):
    user_states[ADMIN_ID] = {"step":"await_broadcast"}
    bot.send_message(m.chat.id, "Reklama matnini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID,{}).get("step")=="await_broadcast", content_types=['text','photo','document'])
def admin_broadcast_send(m):
    for uid in list(user_balances.keys()):
        try:
            if m.content_type == "text":
                bot.send_message(uid, f"Reklama:\n{m.text}")
            elif m.content_type == "photo":
                bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption or "")
            else:
                bot.send_document(uid, m.document.file_id, caption=m.caption or "")
        except:
            continue
    bot.send_message(ADMIN_ID, "Reklama yuborildi.")
    user_states.pop(ADMIN_ID, None)

app = Flask('')
@app.route('/')
def home():
    return "Bot ishlayapti"
def run():
    app.run(host="0.0.0.0", port=8080)
def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()
bot.polling(none_stop=True, interval=0, timeout=20)

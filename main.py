import telebot
from telebot import types
import sqlite3
import random
import string
import os
import time

# --- إعداد الثوابت الرئيسية ---
TOKEN = "8019972443:AAHmrS48qvA7QVoJWPUgOznRR_xDz28fFms"
ADMIN_IDS = [7253092491, 6525167572, 7016415874]
REQUIRED_CHANNEL = "@Barq_G"
CUSTOMER_SERVICE = "@Omar_7874"
DEVELOPER = "@VIR_XT"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- إعداد قاعدة البيانات وتوليد الجداول ---
DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0,
        referred_by TEXT,
        is_admin INTEGER DEFAULT 0,
        wallet_number TEXT,
        wallet_type TEXT,
        step TEXT
    )
    """)
    
    # جدول المشرفين الإضافيين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )
    """)
    
    # جدول الجيميلات المتاحة للبيع
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gmails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        status TEXT DEFAULT 'available'
    )
    """)
    
    # جدول المسوقين والبروموكود
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marketers (
        promo_code TEXT PRIMARY KEY,
        marketer_name TEXT,
        password TEXT,
        clicks INTEGER DEFAULT 0,
        earnings REAL DEFAULT 0.0
    )
    """)
    
    # جدول طلبات التسليم المعلقة
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        gmail TEXT,
        gmail_password TEXT,
        progress_msg_id INTEGER,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    # جدول طلبات السحب التلقائي
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        wallet_type TEXT,
        wallet_number TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    # جدول الإعدادات العامة
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # إدخال السعر الافتراضي للجيميل إذا لم يكن موجوداً
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('gmail_price', '7.0')")
    
    conn.commit()
    conn.close()

    
    conn.commit()
    conn.close()

init_db()

# --- دالات قاعدة البيانات المساعدة ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def is_user_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    conn = get_db_connection()
    admin = conn.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return admin is not None

def get_gmail_price():
    conn = get_db_connection()
    price_row = conn.execute("SELECT value FROM settings WHERE key = 'gmail_price'").fetchone()
    conn.close()
    return float(price_row['value']) if price_row else 7.0

def set_gmail_price(price):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('gmail_price', ?)", (str(price),))
    conn.commit()
    conn.close()

def check_channel_member(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception:
        return True

# --- الكيبوردات والواجهات التفاعلية ---

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📬 تسليم الجيميلات")
    btn2 = types.KeyboardButton("📋 الجيميلات المطلوبة اليوم")
    btn3 = types.KeyboardButton("💰 أسعار الجيميلات")
    btn4 = types.KeyboardButton("💳 معلومات الدفع")
    btn5 = types.KeyboardButton("🧑‍💻 المطور")
    btn6 = types.KeyboardButton("💼 التقديم كمسوق بالعمولة")
    btn7 = types.KeyboardButton("🔑 دخول لوحة المسوقين")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    markup.add(btn6, btn7)
    return markup

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💵 تحديد سعر الجيميل", callback_data="admin_set_price"),
        types.InlineKeyboardButton("➕ إضافة جيميل يدوي", callback_data="admin_add_gmail")
    )
    markup.add(
        types.InlineKeyboardButton("🎟️ إنشاء بروموكود مسوق", callback_data="admin_create_promo"),
        types.InlineKeyboardButton("📈 إحصائيات المسوقين", callback_data="admin_marketer_stats")
    )
    markup.add(
        types.InlineKeyboardButton("➕ رفع مشرف جديد", callback_data="admin_add_mod"),
        types.InlineKeyboardButton("💰 إضافة رصيد يدوي", callback_data="admin_add_balance")
    )
    markup.add(
        types.InlineKeyboardButton("📊 إحصائيات البوت الكاملة", callback_data="admin_bot_stats"),
        types.InlineKeyboardButton("📢 قسم الإذاعة الجماعية", callback_data="admin_broadcast_menu")
    )
    return markup

def get_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 اشترك في القناة هنا", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")
    btn_verify = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="verify_subscription")
    markup.add(btn)
    markup.add(btn_verify)
    return markup

def get_broadcast_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 إذاعة نصية عادية", callback_data="admin_cast_text"),
        types.InlineKeyboardButton("🔄 إذاعة بالتوجيه (Forward)", callback_data="admin_cast_forward"),
        types.InlineKeyboardButton("🖼️ إذاعة وسائط (صورة/فيديو) مع نص", callback_data="admin_cast_media"),
        types.InlineKeyboardButton("🔙 عودة للوحة الأدمن", callback_data="admin_back_to_panel")
    )
    return markup

# --- رسالة البدء والتحقق ---

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "مستخدم جديد"
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0.0)", (user_id, username))
        conn.commit()
    conn.close()

    if not check_channel_member(user_id):
        bot.send_message(
            user_id,
            f"⚠️ عذراً عزيزي! يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه:\n{REQUIRED_CHANNEL}",
            reply_markup=get_join_keyboard()
        )
        return

    conn = get_db_connection()
    user_data = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if user_data and user_data['referred_by'] is None:
        markup = types.ForceReply(selective=True)
        msg = bot.send_message(
            user_id,
            "🎁 هل دخلت البوت عن طريق بروموكود (كود تسويقي)؟\n\nإذا كان لديك كود، يرجى كتابته الآن.\nإذا لم يكن لديك كود، أكتب كلمة <b>تخطي</b> لتجاوز هذه الخطوة.",
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_promo_code_input)
        return

    send_welcome_message(message)

def send_welcome_message(message):
    user_id = message.from_user.id
    welcome_text = (
        "✨ <b>أهلاً بك في بوت GMAILs ⇄ TESLA المطور!</b> ✨\n\n"
        "هذا النظام مخصص لشراء وتسليم حسابات الجيميل بشكل فوري وتلقائي مع الحفاظ على أعلى مستويات الأمان والدقة.\n\n"
        "<b>🛡️ نظام العمل وكيفية الاستخدام:</b>\n"
        "• يمكنك تسليم حسابات الجيميل الخاصة بك عبر زر <b>[📬 تسليم الجيميلات]</b>.\n"
        "• يتم مراجعة الحسابات المرسلة فوراً من قبل المشرفين وقبولها أو رفضها يدوياً لتأكيد الأمان.\n"
        "• يمكنك تتبع الجيميلات المطلوبة بشكل يومي والتسعيرة الحالية مباشرة عبر القائمة.\n"
        "• إذا كنت مسوقاً، يمكنك التسجيل والحصول على عمولات ممتازة عبر نظام البروموكود المخصص.\n\n"
        "💡 <i>يرجى استخدام الأزرار أدناه للتحكم في خدمات البوت بكل سهولة وسلاسة!</i>"
    )
    bot.send_message(user_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# --- معالجة مدخلات البروموكود ---

def process_promo_code_input(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text.lower() in ["تخطي", "تخطي ", "skip"]:
        conn = get_db_connection()
        conn.execute("UPDATE users SET referred_by = 'none' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "✅ تم تخطي إدخال البروموكود بنجاح.")
        send_welcome_message(message)
        return

    conn = get_db_connection()
    marketer = conn.execute("SELECT * FROM marketers WHERE promo_code = ?", (text,)).fetchone()
    
    if marketer:
        conn.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (text, user_id))
        conn.execute("UPDATE marketers SET clicks = clicks + 1 WHERE promo_code = ?", (text,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"🎉 تهانينا! تم تسجيل دخولك بنجاح تحت البروموكود للمسوق: <b>{marketer['marketer_name']}</b>", parse_mode="HTML")
        send_welcome_message(message)
    else:
        conn.close()
        markup = types.ForceReply(selective=True)
        msg = bot.send_message(
            user_id,
            "❌ البروموكود الذي أدخلته غير صحيح أو انتهت صلاحيته!\n\nيرجى إعادة إدخال البروموكود الصحيح، أو أرسل كلمة <b>تخطي</b> للمتابعة بدون كود.",
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_promo_code_input)

# --- معالجة زر التحقق والاشتراك الإجباري ---

@bot.callback_query_handler(func=lambda call: call.data == "verify_subscription")
def verify_subscription_callback(call):
    user_id = call.from_user.id
    if check_channel_member(user_id):
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك بنجاح!")
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        conn = get_db_connection()
        user_data = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        
        if user_data and user_data['referred_by'] is None:
            markup = types.ForceReply(selective=True)
            msg = bot.send_message(
                user_id,
                "🎁 هل دخلت البوت عن طريق بروموكود (كود تسويقي)؟\n\nأرسل الكود الآن، أو أكتب كلمة <b>تخطي</b> لتجاوز الخطوة.",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_promo_code_input)
        else:
            send_welcome_message(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد! يرجى الاشتراك أولاً ثم الضغط على تحقق.", show_alert=True)

# --- لوحة التحكم الخاصة بالأدمن ---

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    user_id = message.from_user.id
    if not is_user_admin(user_id):
        bot.send_message(user_id, "⚠️ عذراً، هذا الأمر مخصص للإدارة والمطورين فقط.")
        return
    show_admin_panel(user_id)

def show_admin_panel(user_id):
    conn = get_db_connection()
    total_users = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    total_marketers = conn.execute("SELECT COUNT(*) as count FROM marketers").fetchone()['count']
    available_gmails = conn.execute("SELECT COUNT(*) as count FROM gmails WHERE status = 'available'").fetchone()['count']
    price = get_gmail_price()
    conn.close()

    admin_msg = (
        "👑 <b>أهلاً بك يا مشرف في لوحة التحكم الاحترافية الخاصة بالبوت!</b>\n"
        "───────────────────────\n"
        f"👥 إجمالي المستخدمين: <b>{total_users} مستخدم</b>\n"
        f"💼 إجمالي المسوقين النشطين: <b>{total_marketers} مسوق</b>\n"
        f"📬 الحسابات المتاحة للبيع: <b>{available_gmails} جيميل</b>\n"
        f"💵 سعر شراء الجيميل الحالي: <b>{price} جنيه / دولار</b>\n"
        "───────────────────────\n"
        "⚙️ اختر الإجراء المناسب من الأسفل لإدارة البوت والعمليات يدوياً:"
    )
    bot.send_message(user_id, admin_msg, reply_markup=get_admin_keyboard(), parse_mode="HTML")

# معالجة استدعاءات الأدمن
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback_processor(call):
    user_id = call.from_user.id
    if not is_user_admin(user_id):
        bot.answer_callback_query(call.id, "⚠️ لست مشرفاً!", show_alert=True)
        return

    action = call.data
    
    if action == "admin_back_to_panel":
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        show_admin_panel(user_id)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_set_price":
        msg = bot.send_message(user_id, "💵 يرجى إرسال السعر الجديد للجيميل بصيغة أرقام فقط (مثال: 8.5):")
        bot.register_next_step_handler(msg, process_price_update)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_add_gmail":
        msg = bot.send_message(user_id, "➕ أرسل الجيميل وكلمة المرور بالصيغة التالية تماماً لتسجيلهما:\n<code>email:password</code>")
        bot.register_next_step_handler(msg, process_add_gmail_manual)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_create_promo":
        msg = bot.send_message(user_id, "🎟️ يرجى كتابة تفاصيل المسوق الجديد بالترتيب التالي مفصولاً بشرطة عمودية:\n\n<code>اسم المسوق | الكود المطلوب | كلمة سر المسوق</code>\n\nمثال:\n<code>أحمد | ahmed50 | pass123</code>")
        bot.register_next_step_handler(msg, process_create_promo_code)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_marketer_stats":
        conn = get_db_connection()
        marketers = conn.execute("SELECT * FROM marketers").fetchall()
        conn.close()
        
        if not marketers:
            bot.send_message(user_id, "📭 لا يوجد مسوقين مسجلين حالياً في قاعدة البيانات.")
        else:
            stats_msg = "📈 <b>إحصائيات المسوقين والبروموكودات النشطة:</b>\n\n"
            for m in marketers:
                stats_msg += f"👤 <b>الاسم:</b> {m['marketer_name']}\n🔑 <b>الكود:</b> <code>{m['promo_code']}</code>\n🔑 <b>الباسورد:</b> <code>{m['password']}</code>\n👥 <b>عدد الإحالات:</b> {m['clicks']} مستخدم\n💵 <b>الأرباح:</b> {m['earnings']} \n───────────────────\n"
            bot.send_message(user_id, stats_msg, parse_mode="HTML")
        bot.answer_callback_query(call.id)
        
    elif action == "admin_add_mod":
        msg = bot.send_message(user_id, "➕ يرجى إرسال المعرّف الرقمي (ID) للشخص الذي تريد ترقيته لمشرف:")
        bot.register_next_step_handler(msg, process_add_moderator)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_add_balance":
        msg = bot.send_message(user_id, "💰 أرسل تفاصيل إضافة الرصيد بالشكل التالي:\n\n<code>الـ ID للمستخدم | القيمة المراد إضافتها</code>\n\nمثال:\n<code>7253092491 | 50</code>")
        bot.register_next_step_handler(msg, process_add_balance_manual)
        bot.answer_callback_query(call.id)
        
    elif action == "admin_bot_stats":
        conn = get_db_connection()
        stats = conn.execute("SELECT COUNT(*) as u_count, SUM(balance) as total_bal FROM users").fetchone()
        gmails_count = conn.execute("SELECT COUNT(*) as g_count FROM gmails").fetchone()
        subs_pending = conn.execute("SELECT COUNT(*) as s_count FROM submissions WHERE status = 'pending'").fetchone()
        conn.close()
        
        stats_msg = (
            "📊 <b>إحصائيات النظام التفصيلية:</b>\n\n"
            f"👤 عدد الأعضاء المسجلين: {stats['u_count']}\n"
            f"💰 إجمالي أرصدة المستخدمين: {stats['total_bal'] or 0.0} جنيه/دولار\n"
            f"📧 إجمالي الحسابات بقاعدة البيانات: {gmails_count['g_count']}\n"
            f"⏳ طلبات التسليم المعلقة بانتظار المراجعة: {subs_pending['s_count']}\n"
        )
        bot.send_message(user_id, stats_msg, parse_mode="HTML")
        bot.answer_callback_query(call.id)
        
    elif action == "admin_broadcast_menu":
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text="📢 <b>أهلاً بك في قسم الإذاعة المتطور:</b>\n\nيرجى اختيار نوع الإذاعة التي ترغب في إرسالها لجميع مستخدمي البوت النشطين:",
            reply_markup=get_broadcast_keyboard(),
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)

    elif action == "admin_cast_text":
        msg = bot.send_message(user_id, "📝 يرجى إرسال الرسالة النصية التي ترغب بإذاعتها الآن:")
        bot.register_next_step_handler(msg, process_cast_text_broadcast)
        bot.answer_callback_query(call.id)

    elif action == "admin_cast_forward":
        msg = bot.send_message(user_id, "🔄 قم بعمل توجيه (Forward) لأي رسالة (من قناة أو شات) هنا ليتم إذاعتها وتوجيهها للمستخدمين بنفس هيئتها تماماً:")
        bot.register_next_step_handler(msg, process_cast_forward_broadcast)
        bot.answer_callback_query(call.id)

    elif action == "admin_cast_media":
        msg = bot.send_message(user_id, "🖼️ يرجى إرسال الصورة أو الفيديو مع كتابة النص الإعلاني المرفق أسفل الميديا:")
        bot.register_next_step_handler(msg, process_cast_media_broadcast)
        bot.answer_callback_query(call.id)

# تابع لتعديل السعر من الأدمن
def process_price_update(message):
    user_id = message.from_user.id
    try:
        new_price = float(message.text.strip())
        set_gmail_price(new_price)
        bot.send_message(user_id, f"✅ تم تحديث سعر الجيميل بنجاح إلى: <b>{new_price}</b>", parse_mode="HTML")
    except ValueError:
        bot.send_message(user_id, "❌ خطأ! يرجى إرسال رقم صحيح فقط (أرقام عشرية أو صحيحة).")

# تابع لإضافة جيميل يدوياً
def process_add_gmail_manual(message):
    user_id = message.from_user.id
    data = message.text.strip()
    if ":" not in data:
        bot.send_message(user_id, "❌ خطأ في صيغة الرفع! يرجى كتابة البيانات بالصيغة الصحيحة <code>email:password</code>")
        return
    
    parts = data.split(":")
    email = parts[0].strip()
    password = parts[1].strip()
    
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO gmails (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"✅ تم إضافة الحساب بنجاح!\n📧 الجيميل: {email}\n🔑 الباسورد: {password}")
    except sqlite3.IntegrityError:
        bot.send_message(user_id, "❌ هذا الحساب مضاف مسبقاً في قاعدة البيانات!")

# تابع لإنشاء بروموكود
def process_create_promo_code(message):
    user_id = message.from_user.id
    data = message.text.strip()
    if "|" not in data:
        bot.send_message(user_id, "❌ يرجى اتباع الصيغة المطلوبة والفصل بين المدخلات برمز ( | ).")
        return
    
    try:
        parts = data.split("|")
        name = parts[0].strip()
        code = parts[1].strip()
        pwd = parts[2].strip()
        
        conn = get_db_connection()
        conn.execute("INSERT INTO marketers (promo_code, marketer_name, password) VALUES (?, ?, ?)", (code, name, pwd))
        conn.commit()
        conn.close()
        
        success_msg = (
            "✅ <b>تم إنشاء حساب المسوق والبروموكود بنجاح!</b>\n\n"
            f"👤 اسم المسوق: {name}\n"
            f"🎟️ كود التسويق: <code>{code}</code>\n"
            f"🔑 كلمة سر لوحة التحكم: <code>{pwd}</code>\n\n"
            "💡 يمكن للمسوق الدخول للوحته عبر زر دخول لوحة المسوقين وإدخال هذه البيانات."
        )
        bot.send_message(user_id, success_msg, parse_mode="HTML")
    except sqlite3.IntegrityError:
        bot.send_message(user_id, "❌ كود التسويق هذا مستخدم بالفعل! يرجى اختيار كود آخر فريد.")

# تابع لرفع مشرف جديد
def process_add_moderator(message):
    user_id = message.from_user.id
    try:
        target_id = int(message.text.strip())
        conn = get_db_connection()
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f"✅ تم ترقية المستخدم ذو المعرف <code>{target_id}</code> إلى رتبة مشرف في البوت بنجاح.", parse_mode="HTML")
    except ValueError:
        bot.send_message(user_id, "❌ خطأ! يرجى إرسال أرقام الـ ID فقط.")

# تابع لشحن الرصيد يدوياً للمستخدم
def process_add_balance_manual(message):
    user_id = message.from_user.id
    data = message.text.strip()
    if "|" not in data:
        bot.send_message(user_id, "❌ يرجى استخدام الفاصل ( | ) لفصل المعرف عن قيمة الرصيد.")
        return
    
    try:
        parts = data.split("|")
        target_id = int(parts[0].strip())
        amount = float(parts[1].strip())
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (target_id,)).fetchone()
        if not user:
            conn.close()
            bot.send_message(user_id, "❌ هذا المستخدم غير مسجل بالبوت!")
            return
        
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"✅ تم شحن رصيد إضافي بقيمة {amount} للمستخدم <code>{target_id}</code> بنجاح.", parse_mode="HTML")
        bot.send_message(target_id, f"🎉 تم إضافة رصيد لحسابك من قبل الإدارة!\n➕ القيمة المضافة: <b>{amount}</b>", parse_mode="HTML")
    except Exception:
        bot.send_message(user_id, "❌ حدث خطأ أثناء تنفيذ الإجراء. يرجى التحقق من الأرقام وإعادة المحاولة.")

# --- لوجيك ومعالجة عمليات الإذاعة المتطورة ---

def get_all_users_for_broadcast():
    conn = get_db_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [u['user_id'] for u in users]

def process_cast_text_broadcast(message):
    user_id = message.from_user.id
    text = message.text
    user_ids = get_all_users_for_broadcast()
    
    status_msg = bot.send_message(user_id, "⏳ جاري إرسال الإذاعة النصية لجميع الأعضاء...")
    success = 0
    fail = 0
    
    for uid in user_ids:
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
            
    bot.edit_message_text(
        chat_id=user_id,
        message_id=status_msg.message_id,
        text=f"📢 <b>تم الانتهاء من الإذاعة النصية!</b>\n\n✅ تم الإرسال بنجاح لـ: <code>{success}</code> مستخدم\n❌ فشل الإرسال لـ: <code>{fail}</code> مستخدم",
        parse_mode="HTML"
    )

def process_cast_forward_broadcast(message):
    user_id = message.from_user.id
    user_ids = get_all_users_for_broadcast()
    
    status_msg = bot.send_message(user_id, "⏳ جاري توجيه الرسالة لجميع الأعضاء...")
    success = 0
    fail = 0
    
    for uid in user_ids:
        try:
            bot.forward_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
            
    bot.edit_message_text(
        chat_id=user_id,
        message_id=status_msg.message_id,
        text=f"📢 <b>تم الانتهاء من إذاعة التوجيه!</b>\n\n✅ تم الإرسال بنجاح لـ: <code>{success}</code> مستخدم\n❌ فشل الإرسال لـ: <code>{fail}</code> مستخدم",
        parse_mode="HTML"
    )

def process_cast_media_broadcast(message):
    user_id = message.from_user.id
    user_ids = get_all_users_for_broadcast()
    
    status_msg = bot.send_message(user_id, "⏳ جاري إرسال الإعلان مع الميديا لجميع الأعضاء...")
    success = 0
    fail = 0
    
    file_id = None
    caption = message.caption or ""
    media_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        bot.send_message(user_id, "❌ خطأ! يجب أن ترسل رسالة تحتوي على صورة أو فيديو فقط في هذا الخيار.")
        return

    for uid in user_ids:
        try:
            if media_type == "photo":
                bot.send_photo(uid, file_id, caption=caption, parse_mode="HTML")
            elif media_type == "video":
                bot.send_video(uid, file_id, caption=caption, parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
            
    bot.edit_message_text(
        chat_id=user_id,
        message_id=status_msg.message_id,
        text=f"📢 <b>تم الانتهاء من إذاعة الميديا بنجاح!</b>\n\n✅ تم الإرسال بنجاح لـ: <code>{success}</code> مستخدم\n❌ فشل الإرسال لـ: <code>{fail}</code> مستخدم",
        parse_mode="HTML"
    )

# --- نظام تقديم المسوقين ودخول لوحة المسوق ---

@bot.message_handler(func=lambda msg: msg.text == "💼 التقديم كمسوق بالعمولة")
def apply_marketer_handler(message):
    user_id = message.from_user.id
    info_text = (
        "💼 <b>برنامج التسويق بالعمولة:</b>\n"
        "يمكنك الآن كسب أرباح إضافية ممتازة من خلال جلب بائعين ومستخدمين جدد للبوت!\n\n"
        "<b>المميزات:</b>\n"
        "• كود خصم وترويج خاص بك.\n"
        "• عمولة فورية على كل حساب جيميل يتم تسليمه من قبل إحالاتك وقبوله بنجاح.\n\n"
        "📬 <i>للتقديم، يرجى التواصل مباشرة مع المطور أو خدمة العملاء لتزويدك بالبروموكود والرمز السري الخاص بك.</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💬 خدمة العملاء", url=f"https://t.me/{CUSTOMER_SERVICE.replace('@', '')}"),
        types.InlineKeyboardButton("🧑‍💻 المطور", url=f"https://t.me/{DEVELOPER.replace('@', '')}")
    )
    bot.send_message(user_id, info_text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "🔑 دخول لوحة المسوقين")
def login_marketer_handler(message):
    user_id = message.from_user.id
    markup = types.ForceReply(selective=True)
    msg = bot.send_message(
        user_id,
        "🔐 يرجى تسجيل الدخول إلى لوحة المسوقين.\nأرسل بياناتك الآن مفصولة بشرطة عمودية كالتالي:\n\n<code>البروموكود الخاص بك | كلمة المرور</code>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_marketer_login)

def process_marketer_login(message):
    user_id = message.from_user.id
    data = message.text.strip()
    
    if "|" not in data:
        bot.send_message(user_id, "❌ خطأ في تنسيق المدخلات! يرجى إعادة المحاولة واستخدام الفاصل ( | ).")
        return
        
    parts = data.split("|")
    promo = parts[0].strip()
    pwd = parts[1].strip()
    
    conn = get_db_connection()
    marketer = conn.execute("SELECT * FROM marketers WHERE promo_code = ? AND password = ?", (promo, pwd)).fetchone()
    conn.close()
    
    if marketer:
        m_msg = (
            f"📊 <b>مرحباً بك في لوحة إحصائيات المسوق: {marketer['marketer_name']}</b>\n"
            "───────────────────────────\n"
            f"🎟️ البروموكود النشط: <code>{marketer['promo_code']}</code>\n"
            f"👥 عدد المسجلين عبر كودك: <b>{marketer['clicks']} عضو</b>\n"
            f"💵 أرباحك الحالية المقدرة: <b>{marketer['earnings']} جنيه / دولار</b>\n"
            "───────────────────────────\n"
            "💬 تواصل مع الإدارة لسحب مستحقاتك وأرباحك فوراً."
        )
        bot.send_message(user_id, m_msg, parse_mode="HTML")
    else:
        bot.send_message(user_id, "❌ بيانات الدخول غير صحيحة أو تم إدخال بروموكود خاطئ. يرجى مراجعة الإدارة.")

# --- واجهات المستخدم العامة ومعالجة تسليم الجيميلات ---

@bot.message_handler(func=lambda msg: msg.text == "📬 تسليم الجيميلات")
def deliver_gmail_handler(message):
    user_id = message.from_user.id
    if not check_channel_member(user_id):
        bot.send_message(user_id, "⚠️ يجب عليك الاشتراك في القناة أولاً لتتمكن من التسليم.", reply_markup=get_join_keyboard())
        return
        
    markup = types.ForceReply(selective=True)
    msg = bot.send_message(
        user_id,
        "📬 <b>قسم تسليم الحسابات:</b>\n\nيرجى إرسال عنوان الجيميل وكلمة المرور مفصولين بـ نقطتين كالتالي تماماً:\n\n<code>john.smith@gmail.com:password123</code>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_gmail_submission)

def process_gmail_submission(message):
    user_id = message.from_user.id
    data = message.text.strip()
    
    if ":" not in data:
        bot.send_message(user_id, "❌ صيغة الإدخال خاطئة! يرجى كتابة البريد وكلمة المرور وبينهما الرمز ( : ) فقط دون فراغات إضافية.")
        return
        
    parts = data.split(":")
    email = parts[0].strip()
    pwd = parts[1].strip()
    
    if not email.endswith("@gmail.com"):
        bot.send_message(user_id, "❌ عذراً، نقبل حسابات نطاق الجيميل الرسمية فقط (@gmail.com).")
        return

    # 1. إرسال شريط التقدم المبدئي للمستخدم (10%)
    progress_text = (
        "⏳ <b>جاري فحص الحساب ومراجعته...</b>\n\n"
        "<code>[■□□□□□□□□□] 10%</code>\n\n"
        "⚡ <i>يرجى عدم إرسال الحساب مجدداً، المشرفون يقومون بفحص البيانات الآن.</i>"
    )
    progress_msg = bot.send_message(user_id, progress_text, parse_mode="HTML")

    # 2. حفظ الطلب مع الـ Message ID الخاص بشريط التقدم في قاعدة البيانات
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO submissions (user_id, gmail, gmail_password, progress_msg_id) VALUES (?, ?, ?, ?)", 
        (user_id, email, pwd, progress_msg.message_id)
    )
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 3. إرسال إشعار للمشرفين لمراجعة الحساب واتخاذ إجراء
    notify_admins_new_submission(sub_id, email, pwd, user_id)

def notify_admins_new_submission(sub_id, email, pwd, submitter_id):
    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ قبول الطلب", callback_data=f"sub_approve_{sub_id}")
    btn_reject = types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"sub_reject_{sub_id}")
    markup.add(btn_approve, btn_reject)
    
    msg_text = (
        "🔔 <b>وصول طلب تسليم حساب جيميل جديد!</b>\n"
        "───────────────────────\n"
        f"🆔 معرف المستخدم: <code>{submitter_id}</code>\n"
        f"📧 البريد الإلكتروني: <code>{email}</code>\n"
        f"🔑 كلمة المرور: <code>{pwd}</code>\n"
        "───────────────────────\n"
        "الرجاء التحقق من صحة الحساب ثم اتخاذ القرار بالقبول أو الرفض:"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, msg_text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass

# معالجة قرارات الأدمن (قبول / رفض) وتحريك شريط التقدم تلقائياً
@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def process_submission_action(call):
    admin_id = call.from_user.id
    if not is_user_admin(admin_id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية المشرف للقيام بذلك.", show_alert=True)
        return
        
    parts = call.data.split("_")
    action = parts[1]
    sub_id = int(parts[2])
    
    conn = get_db_connection()
    sub = conn.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,)).fetchone()
    
    if not sub or sub['status'] != 'pending':
        conn.close()
        bot.answer_callback_query(call.id, "⚠️ تم معالجة هذا الطلب مسبقاً أو أنه غير موجود.", show_alert=True)
        bot.delete_message(chat_id=admin_id, message_id=call.message.message_id)
        return
        
    user_id = sub['user_id']
    progress_msg_id = sub['progress_msg_id']
    price = get_gmail_price()
    
    if action == "approve":
        # تحديث حالة الطلب فوراً في الخلفية لتجنب النقرات المكررة
        conn.execute("UPDATE submissions SET status = 'approved' WHERE id = ?", (sub_id,))
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
        
        # مكافأة المسوق إذا وجد
        user_data = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if user_data and user_data['referred_by'] and user_data['referred_by'] != 'none':
            promo = user_data['referred_by']
            marketer_bonus = price * 0.10
            conn.execute("UPDATE marketers SET earnings = earnings + ? WHERE promo_code = ?", (marketer_bonus, promo))
            
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ تم قبول الطلب! جاري معالجة العداد وحساب الرصيد لدى المستخدم...")
        
        # تعديل رسالة الأدمن لتأكيد القبول
        bot.edit_message_text(
            chat_id=admin_id,
            message_id=call.message.message_id,
            text=f"✅ <b>تم قبول الحساب بنجاح!</b>\n📧 البريد: <code>{sub['gmail']}</code>\n👮‍♂️ بواسطة المشرف: <code>{admin_id}</code>\n⏳ شريط التقدم لدى المستخدم قيد التحديث الفوري...",
            parse_mode="HTML"
        )
        
        # --- تحريك شريط التقدم التفاعلي للمستخدم ---
        try:
            # مرحلة 40%
            time.sleep(1.2)
            bot.edit_message_text(
                chat_id=user_id,
                message_id=progress_msg_id,
                text="🔄 <b>جاري التحقق النهائي وصرف المستحقات...</b>\n\n<code>[■■■■□□□□□□] 40%</code>",
                parse_mode="HTML"
            )
            
            # مرحلة 70%
            time.sleep(1.2)
            bot.edit_message_text(
                chat_id=user_id,
                message_id=progress_msg_id,
                text="💳 <b>جاري شحن رصيد المحفظة الخاصة بك...</b>\n\n<code>[■■■■■■■□□□] 70%</code>",
                parse_mode="HTML"
            )
            
            # مرحلة 100% (اكتمال الأوردر)
            time.sleep(1.2)
            complete_text = (
                "<code>[■■■■■■■■■■] 100%</code>\n"
                "<b>تم انتهاء الاوردر✅</b>\n\n"
                "⚡ <i>سيتم اضافه الرصيد من الادمن خلال دقايق.</i>"
            )
            bot.edit_message_text(
                chat_id=user_id,
                message_id=progress_msg_id,
                text=complete_text,
                parse_mode="HTML"
            )
            
            # إرسال الإشعار المالي النهائي بعد اكتمال العداد تماماً بـ 3 ثواني
            time.sleep(3.0)
            bot.send_message(
                user_id, 
                f"🎉 <b>تم تحديث حسابك بنجاح!</b>\n💵 أضيف إلى رصيدك: <b>{price} جنيه / دولار</b>\n📌 رصيدك الحالي أصبح جاهزاً للسحب والاستخدام.", 
                parse_mode="HTML"
            )
            
        except Exception:
            # في حال قام المستخدم بحذف الشات أو حظر البوت أثناء تحريك العداد
            pass
        
    elif action == "reject":
        conn.execute("UPDATE submissions SET status = 'rejected' WHERE id = ?", (sub_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "❌ تم رفض الطلب.")
        
        bot.edit_message_text(
            chat_id=admin_id,
            message_id=call.message.message_id,
            text=f"❌ <b>تم رفض الحساب!</b>\n📧 البريد: <code>{sub['gmail']}</code>\n👮‍♂️ بواسطة المشرف: <code>{admin_id}</code>",
            parse_mode="HTML"
        )
        
        # إشعار المستخدم بالرفض وإلغاء شريط التقدم
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=progress_msg_id,
                text=f"❌ <b>للأسف! تم رفض طلبك للحساب ({sub['gmail']})</b>\n\nالسبب: الحساب غير صالح، أو كلمة المرور خاطئة، أو تم إرساله مسبقاً.\n💬 للمساعدة يرجى مراجعة الدعم الفني.",
                parse_mode="HTML"
            )
        except Exception:
            pass

# --- قسم السحب التلقائي الذكي ---

@bot.message_handler(func=lambda msg: msg.text == "💳 معلومات الدفع")
def payment_info_handler(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    balance = user['balance'] if user else 0.0
    
    pay_msg = (
        "💳 <b>بوابة السحب والرصيد:</b>\n\n"
        f"💰 رصيدك الحالي القابل للسحب: <b>{balance} جنيه / دولار</b>\n───────────────────\n"
        "اضغط على الزر بالأسفل لتقديم طلب سحب أرباحك فوراً:"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn_withdraw = types.InlineKeyboardButton("💵 طلب سحب رصيد", callback_data="user_request_withdraw")
    markup.add(btn_withdraw)
    
    bot.send_message(user_id, pay_msg, reply_markup=markup, parse_mode="HTML")

# عند ضغط المستخدم على "طلب سحب رصيد"
@bot.callback_query_handler(func=lambda call: call.data == "user_request_withdraw")
def start_withdrawal_flow(call):
    user_id = call.from_user.id
    
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    # تحقق مبدئي لو الرصيد 0 أو سالب
    if not user or user['balance'] <= 0:
        bot.answer_callback_query(call.id, "❌ عذراً! رصيدك الحالي 0، لا يوجد ما يمكن سحبه.", show_alert=True)
        return
        
    bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    
    # تخيير المستخدم بين وسائل السحب المتاحة
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_voda = types.InlineKeyboardButton("🔴 فودافون كاش", callback_data="w_type_Vodafone Cash")
    btn_etis = types.InlineKeyboardButton("🟢 اتصالات كاش", callback_data="w_type_Etisalat Cash")
    btn_orange = types.InlineKeyboardButton("🟠 أورنج كاش", callback_data="w_type_Orange Cash")
    btn_usdt = types.InlineKeyboardButton("🪙 USDT (TRC-20)", callback_data="w_type_USDT (TRC-20)")
    markup.add(btn_voda, btn_etis)
    markup.add(btn_orange, btn_usdt)
    
    bot.send_message(user_id, "📌 يرجى اختيار وسيلة السحب المفضلة لديك:", reply_markup=markup)
    bot.answer_callback_query(call.id)

# معالجة نوع المحفظة وطلب رقم المحفظة
@bot.callback_query_handler(func=lambda call: call.data.startswith("w_type_"))
def process_withdrawal_type(call):
    user_id = call.from_user.id
    wallet_type = call.data.replace("w_type_", "")
    
    # حفظ نوع السحب مؤقتاً في جلسة المستخدم أو قاعدة البيانات
    conn = get_db_connection()
    conn.execute("UPDATE users SET wallet_type = ? WHERE user_id = ?", (wallet_type, user_id))
    conn.commit()
    conn.close()
    
    bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    
    markup = types.ForceReply(selective=True)
    msg = bot.send_message(
        user_id, 
        f"📝 لقد اخترت السحب عبر: <b>{wallet_type}</b>\n\nيرجى إرسال رقم المحفظة أو العنوان الذي تريد الاستلام عليه الآن:", 
        reply_markup=markup,
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_withdrawal_number)
    bot.answer_callback_query(call.id)

# استقبال رقم المحفظة ثم طلب تحديد القيمة المراد سحبها
def process_withdrawal_number(message):
    user_id = message.from_user.id
    wallet_number = message.text.strip()
    
    conn = get_db_connection()
    conn.execute("UPDATE users SET wallet_number = ? WHERE user_id = ?", (wallet_number, user_id))
    conn.commit()
    conn.close()
    
    markup = types.ForceReply(selective=True)
    msg = bot.send_message(
        user_id,
        "💰 ممتاز! الآن أرسل المبلغ الذي تريد سحبه بالكامل (أرقام فقط):",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_withdrawal_amount)

# معالجة المبلغ والتحقق من رصيد المستخدم الفعلي
def process_withdrawal_amount(message):
    user_id = message.from_user.id
    amount_text = message.text.strip()
    
    try:
        amount_to_withdraw = float(amount_text)
        if amount_to_withdraw <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(user_id, "❌ خطأ! يرجى كتابة مبلغ صحيح أكبر من الصفر.")
        return

    conn = get_db_connection()
    user = conn.execute("SELECT balance, wallet_type, wallet_number FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return
        
    current_balance = user['balance']
    
    # 🔴 التحقق الفعلي: هل رصيده كافٍ؟
    if current_balance < amount_to_withdraw:
        conn.close()
        bot.send_message(
            user_id,
            f"❌ <b>لقد نفد رصيدك! ليس لديك أموال كافية لإتمام هذه العملية.</b>\n\n"
            f"💸 رصيدك الحالي هو: <b>{current_balance}</b> فقط، بينما طلبت سحب: <b>{amount_to_withdraw}</b>.",
            parse_mode="HTML"
        )
        return

    # 🟢 إذا كان الرصيد كافياً:
    # 1. اخصم المبلغ فوراً من حسابه في قاعدة البيانات
    new_balance = current_balance - amount_to_withdraw
    conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    
    # 2. سجل الطلب في جدول السحوبات
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO withdrawals (user_id, wallet_type, wallet_number, amount) VALUES (?, ?, ?, ?)",
        (user_id, user['wallet_type'], user['wallet_number'], amount_to_withdraw)
    )
    withdraw_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # إشعار نجاح فوري للمستخدم
    success_msg = (
        "⏳ <b>تم تسجيل طلب السحب بنجاح!</b>\n"
        "───────────────────────\n"
        f"📝 نوع السحب: <b>{user['wallet_type']}</b>\n"
        f"📞 الحساب المستلم: <code>{user['wallet_number']}</code>\n"
        f"💵 القيمة المخصومة: <b>{amount_to_withdraw}</b>\n"
        f"💰 رصيدك المتبقي الحالي: <b>{new_balance}</b>\n"
        "───────────────────────\n"
        "⚡ <i>طلبك الآن قيد المعالجة من قبل الإدارة، وسيتم التحويل لك في أقرب وقت.</i>"
    )
    bot.send_message(user_id, success_msg, parse_mode="HTML")
    
    # 3. إرسال إشعار لقروب المشرفين (الأدمن) لتنفيذ السحب يدوياً
    notify_admins_withdrawal(withdraw_id, user_id, user['wallet_type'], user['wallet_number'], amount_to_withdraw)

# إشعار المشرفين بوجود طلب سحب جديد مع أزرار التحكم
def notify_admins_withdrawal(withdraw_id, user_id, wallet_type, wallet_number, amount):
    markup = types.InlineKeyboardMarkup()
    btn_paid = types.InlineKeyboardButton("✅ تم التحويل ودفع الطلب", callback_data=f"with_pay_{withdraw_id}")
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء الطلب وإرجاع الرصيد", callback_data=f"with_cancel_{withdraw_id}")
    markup.add(btn_paid)
    markup.add(btn_cancel)
    
    admin_msg = (
        "🚨 <b>طلب سحب رصيد جديد بانتظار التحويل!</b>\n"
        "───────────────────────\n"
        f"👤 الـ ID للمستخدم: <code>{user_id}</code>\n"
        f"⚙️ طريقة الدفع: <b>{wallet_type}</b>\n"
        f"📞 رقم الاستلام: <code>{wallet_number}</code>\n"
        f"💵 القيمة المطلوبة: <b>{amount} جنيه/دولار</b>\n"
        "───────────────────────\n"
        "بعد تحويل المبلغ يدوياً للمستخدم، يرجى الضغط لتأكيد العملية أو إلغائها:"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, admin_msg, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass

# معالجة قرارات الأدمن بخصوص طلبات السحب
@bot.callback_query_handler(func=lambda call: call.data.startswith("with_"))
def process_withdrawal_admin_action(call):
    admin_id = call.from_user.id
    if not is_user_admin(admin_id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية المشرف للقيام بذلك.", show_alert=True)
        return
        
    parts = call.data.split("_")
    action = parts[1]
    withdraw_id = int(parts[2])
    
    conn = get_db_connection()
    withdraw = conn.execute("SELECT * FROM withdrawals WHERE id = ?", (withdraw_id,)).fetchone()
    
    if not withdraw or withdraw['status'] != 'pending':
        conn.close()
        bot.answer_callback_query(call.id, "⚠️ تم معالجة هذا السحب مسبقاً أو غير موجود.", show_alert=True)
        bot.delete_message(chat_id=admin_id, message_id=call.message.message_id)
        return
        
    user_id = withdraw['user_id']
    amount = withdraw['amount']
    
    if action == "pay":
        conn.execute("UPDATE withdrawals SET status = 'paid' WHERE id = ?", (withdraw_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ تم تأكيد عملية الدفع بنجاح!")
        
        bot.edit_message_text(
            chat_id=admin_id,
            message_id=call.message.message_id,
            text=f"✅ <b>تم إكمال عملية السحب وتأكيد الدفع للمستخدم بنجاح!</b>\n👤 المعرف: <code>{user_id}</code>\n💵 المبلغ: <b>{amount}</b>\n👮‍♂️ بواسطة المشرف: <code>{admin_id}</code>",
            parse_mode="HTML"
        )
        
        try:
            bot.send_message(
                user_id,
                f"🎉 <b>أخبار سعيدة! تم تحويل رصيدك بنجاح!</b>\n\n💵 القيمة المرسلة: <b>{amount}</b> عبر محفظتك المحددة.\n🔒 شكراً لثقتك بنا واستخدمك للبوت!",
                parse_mode="HTML"
            )
        except Exception:
            pass
            
    elif action == "cancel":
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.execute("UPDATE withdrawals SET status = 'cancelled' WHERE id = ?", (withdraw_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "❌ تم إلغاء السحب وإعادة الرصيد للمستخدم.")
        
        bot.edit_message_text(
            chat_id=admin_id,
            message_id=call.message.message_id,
            text=f"❌ <b>تم إلغاء عملية السحب وإعادة الرصيد للمستخدم بنجاح.</b>\n👤 المعرف: <code>{user_id}</code>\n💵 القيمة المسترجعة: <b>{amount}</b>",
            parse_mode="HTML"
        )
        
        try:
            bot.send_message(
                user_id,
                f"⚠️ <b>تنبيه بخصوص طلب السحب الخاص بك:</b>\n\nتم رفض عملية سحب مبلغ <b>{amount}</b> وإرجاعه بالكامل لرصيدك في البوت.\n💬 يرجى مراجعة الدعم الفني أو التأكد من صحة رقم المحفظة والطلب مجدداً.",
                parse_mode="HTML"
            )
        except Exception:
            pass

# باقي أزرار القائمة الرئيسية
@bot.message_handler(func=lambda msg: msg.text == "📋 الجيميلات المطلوبة اليوم")
def required_gmails_handler(message):
    user_id = message.from_user.id
    required_info = (
        "📋 <b>حالة الجيميلات المطلوبة اليوم:</b>\n"
        "───────────────────────\n"
        "📦 <b>الحسابات المطلوبة الكلية:</b> <code>1,500 حساب</code>\n"
        "📥 <b>تم تسليمها حتى الآن:</b> <code>1,180 حساب</code>\n"
        "⏳ <b>المتبقي المطلوب:</b> <code>320 حساب فقط</code>\n"
        "───────────────────────\n"
        "⚡ <i>سارع بتسليم حساباتك الآن للحصول على رصيدك بأسرع وقت ممكن قبل انتهاء الكمية المطلوبة لليوم!</i>"
    )
    bot.send_message(user_id, required_info, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "💰 أسعار الجيميلات")
def price_gmails_handler(message):
    user_id = message.from_user.id
    price = get_gmail_price()
    price_info = (
        "💰 <b>أسعار شراء حسابات الجيميل الحالية:</b>\n\n"
        f"💵 سعر الحساب الواحد: <b>{price}</b>\n\n"
        "⚠️ السعر غير ثابت وقد يتغير من وقت لآخر بحسب طلبات السوق ونوع الحسابات وجودتها."
    )
    bot.send_message(user_id, price_info, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "🧑‍💻 المطور")
def developer_info_handler(message):
    user_id = message.from_user.id
    dev_text = (
        "🧑‍💻 <b>معلومات التطوير والدعم الفني:</b>\n"
        "───────────────────────\n"
        f"👑 مطور البوت المعتمد: {DEVELOPER}\n"
        f"💬 لتقديم الشكاوى وخدمة العملاء: {CUSTOMER_SERVICE}\n"
        "───────────────────────\n"
        "⚡ بوتاتنا مصممة خصيصاً لتوفير الأمان، الفاعلية، والسرعة الفائقة لخدمتكم."
    )
    bot.send_message(user_id, dev_text, parse_mode="HTML")

# فالبك النصوص العشوائية
@bot.message_handler(func=lambda message: True)
def unknown_text_fallback(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "⚠️ عذراً، الرجاء استخدام الأزرار المتاحة في القائمة للتحكم في خدمات البوت بشكل صحيح وتجنب إرسال نصوص عشوائية.")

# تشغيل البوت
if __name__ == "__main__":
    print("[+] البوت يعمل الآن بنجاح...")
    bot.infinity_polling()

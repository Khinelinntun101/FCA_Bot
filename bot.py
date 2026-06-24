import os
import sqlite3
import random
import string
import logging
import csv
import shutil
from datetime import datetime, date

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from openpyxl import Workbook

# =====================================================
# CONFIG
# =====================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = [7242601708]  # Multiple Admins Support
DATABASE = "fca.db"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# =====================================================
# DATABASE
# =====================================================
def db_connect():
    return sqlite3.connect(DATABASE)

def init_database():
    conn = db_connect()
    cur = conn.cursor()

    # Members Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT UNIQUE,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        phone TEXT,
        father_name TEXT,
        mother_name TEXT,
        nrc TEXT,
        address TEXT,
        job TEXT,
        department TEXT,
        join_date TEXT,
        profile_photo_id TEXT,
        status TEXT DEFAULT 'ACTIVE',
        deposit_paid INTEGER DEFAULT 0,
        referrer_id TEXT
    )
    """)

    # Payments Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT,
        amount INTEGER,
        payment_method TEXT, -- CASH or EMONEY
        provider TEXT,
        payment_month TEXT,
        payment_date TEXT,
        proof_photo_id TEXT,
        status TEXT DEFAULT 'PENDING',
        approved_by TEXT
    )
    """)

    # Funds & Expenses Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_type TEXT, -- IN (Income) or OUT (Expense)
        amount INTEGER,
        description TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

# =====================================================
# UTILITIES & VALIDATION
# =====================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_only(update: Update):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin သာလျှင် အသုံးပြုနိုင်ပါသည်။")
        return False
    return True

def generate_member_id():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        member_id = "FCA-" + code
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("SELECT member_id FROM members WHERE member_id=?", (member_id,))
        result = cur.fetchone()
        conn.close()
        if not result:
            return member_id

def calculate_months(join_date_str):
    try:
        start = datetime.strptime(join_date_str, "%d-%m-%Y").date()
        today = date.today()
        return ((today.year - start.year) * 12) + (today.month - start.month)
    except:
        return 0

# =====================================================
# KNOWLEDGE BASE DEFINITIONS
# =====================================================
FCA_RULES = {
    "monthly_fee": "💰 FCA လစဉ်ထည့်ဝင်ကြေး\n\nတစ်လလျှင် 2,000 ကျပ် ဖြစ်ပါသည်။\n\nကြိုတင်ပေးသွင်းနိုင်သောကာလများ\n✅ 3 လစာ\n✅ 6 လစာ\n✅ 1 နှစ်စာ (24,000 ကျပ်)",
    "deposit": "💰 Security Deposit\n\nအဖွဲ့စတင်ဝင်ရောက်ချိန်တွင် 5,000 ကျပ် တစ်ကြိမ်ပေးသွင်းရပါမည်။\n\nအဖွဲ့ဝင်သက်တမ်း 3 လပြည့်လျှင် ပြန်လည်ထုတ်ယူခွင့်ရှိပါသည်။",
    "death_support": "🕊️ သေဆုံးမှုထောက်ပံ့ကြေး\n\nအဖွဲ့ဝင်သက်တမ်း 1 နှစ်ပြည့်ရပါမည်။\n\nတွက်ချက်ပုံ\nအဖွဲ့ဝင်တစ်ဦးစီ 1,000 ကျပ် + Total Fund ၏ 20% ဖြင့် တွက်ချက်ပါသည်။",
    "referral": "🎁 Referral System\n\nMember အသစ် 5 ယောက်ကို အောင်မြင်စွာ မိတ်ဆက်ပေးပြီး ထိုသူများ 3 လဆက်တိုက် ကြေးမှန်မှန်ပေးပြီးပါက လစဉ်ကြေး 2,000 ကျပ် ကင်းလွတ်ခွင့် ရရှိနိုင်ပါသည်။"
}

FCA_KEYWORDS = ["fca", "အဖွဲ့", "ကြေး", "လစဉ်", "deposit", "စပေါ်", "သေဆုံး", "ထောက်ပံ့", "ရန်ပုံငွေ", "member", "အဖွဲ့ဝင်", "မိတ်ဆက်", "referral", "ငွေ", "payment", "သွင်း"]

# =====================================================
# CORE COMMANDS
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🌟 FCA Membership Bot\n\nမင်္ဂလာပါ။\n\nအသုံးပြုနိုင်သော Command များ\n\n/register - အဖွဲ့ဝင်စာရင်းသွင်းရန်\n/view - Profile ကြည့်ရန်\n/eligibility - ခံစားခွင့်အရည်အချင်းစစ်ရန်\n/referral - မိတ်ဆက်မှုအခြေအနေ\n/paymenthistory - မိမိငွေသွင်းမှတ်တမ်း\n/fundstatus - ရန်ပုံငွေအခြေအနေ\n/ask - AI သိလိုသည်များမေးရန်"""
    await update.message.reply_text(text)

# =====================================================
# CONVERSATION 1: MEMBER REGISTER SYSTEM
# =====================================================
REG_NAME, REG_PHONE, REG_FATHER, REG_MOTHER, REG_NRC, REG_ADDRESS, REG_JOB, REG_DEPARTMENT, REG_PHOTO = range(9)

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM members WHERE telegram_id=?", (update.effective_user.id,))
    exists = cur.fetchone()
    conn.close()

    if exists:
        await update.message.reply_text("❌ သင်သည် အဖွဲ့ဝင်စာရင်း သွင်းပြီးသားဖြစ်ပါသည်။")
        return ConversationHandler.END

    await update.message.reply_text("📝 FCA Member Registration\n\nအမည်ကို ရိုက်ထည့်ပေးပါ။")
    return REG_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text
    await update.message.reply_text("📞 ဖုန်းနံပါတ် ထည့်ပါ")
    return REG_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_phone"] = update.message.text
    await update.message.reply_text("👨 ဖခင်အမည် ထည့်ပါ")
    return REG_FATHER

async def get_father(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_father"] = update.message.text
    await update.message.reply_text("👩 မိခင်အမည် ထည့်ပါ")
    return REG_MOTHER

async def get_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_mother"] = update.message.text
    await update.message.reply_text("🪪 မှတ်ပုံတင်အမှတ် ထည့်ပါ")
    return REG_NRC

async def get_nrc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_nrc"] = update.message.text
    await update.message.reply_text("🏠 လက်ရှိလိပ်စာ ထည့်ပါ")
    return REG_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_address"] = update.message.text
    await update.message.reply_text("💼 အလုပ်အကိုင် ထည့်ပါ")
    return REG_JOB

async def get_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_job"] = update.message.text
    await update.message.reply_text("🏢 ဌာန ထည့်ပါ")
    return REG_DEPARTMENT

async def get_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_dept"] = update.message.text
    await update.message.reply_text("📸 Profile Photo ပို့ပေးပါ။ (Telegram Photo အဖြစ် ပို့ရန်)")
    return REG_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ တရားဝင် ဓာတ်ပုံ ပို့ပေးရန် လိုအပ်ပါသည်။")
        return REG_PHOTO

    photo_id = update.message.photo[-1].file_id
    member_id = generate_member_id()
    join_date = datetime.now().strftime("%d-%m-%Y")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO members (member_id, telegram_id, name, phone, father_name, mother_name, nrc, address, job, department, join_date, profile_photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        member_id, update.effective_user.id, context.user_data["reg_name"], context.user_data["reg_phone"],
        context.user_data["reg_father"], context.user_data["reg_mother"], context.user_data["reg_nrc"],
        context.user_data["reg_address"], context.user_data["reg_job"], context.user_data["reg_dept"],
        join_date, photo_id
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎉 FCA Member Registration Complete\n\n🆔 Member ID: {member_id}\n👤 Name: {context.user_data['reg_name']}\n📅 Join Date: {join_date}\n\nအဖွဲ့ဝင်အဖြစ် အောင်မြင်စွာ စာရင်းသွင်းပြီးပါပြီ။")
    return ConversationHandler.END

# =====================================================
# CONVERSATION 2: SMART PAYMENT RECORD SYSTEM (ADMIN)
# =====================================================
PAY_MEMBER, PAY_METHOD, PAY_PROVIDER, PAY_AMOUNT, PAY_MONTH, PAY_PROOF = range(6)

async def add_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return ConversationHandler.END
    await update.message.reply_text("💰 Payment Record System\n\nMember ID ကို ရိုက်ထည့်ပေးပါ (ဥပမာ - FCA-A8K29Z)")
    return PAY_MEMBER

async def payment_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m_id = update.message.text.strip().upper()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT name FROM members WHERE member_id=?", (m_id,))
    member = cur.fetchone()
    conn.close()

    if not member:
        await update.message.reply_text("❌ Member ID မတွေ့ရှိပါ။ ကျေးဇူးပြု၍ ပြန်လည်စစ်ဆေးပါ။")
        return ConversationHandler.END

    context.user_data["pay_member_id"] = m_id
    context.user_data["pay_member_name"] = member[0]

    keyboard = [
        [InlineKeyboardButton("💵 Cash", callback_data="CASH")],
        [InlineKeyboardButton("📱 E-Money", callback_data="EMONEY")]
    ]
    await update.message.reply_text(f"👤 Member: {member[0]}\n\nPayment Type ကို ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(keyboard))
    return PAY_METHOD

async def payment_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data
    context.user_data["pay_method"] = method

    if method == "CASH":
        context.user_data["pay_provider"] = "Cash"
        await query.edit_message_text("💵 Cash Payment\n\nပေးသွင်းငွေ ပမာဏကို ဂဏန်းသီးသန့် ထည့်ပါ (ဥပမာ - 2000)")
        return PAY_AMOUNT
    else:
        await query.edit_message_text("📱 E-Money Payment\n\nအသုံးပြုသော Payment App အမည်ကို ရေးပါ (ဥပမာ - KPay, WavePay)")
        return PAY_PROVIDER

async def payment_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pay_provider"] = update.message.text.strip()
    await update.message.reply_text("💰 ပေးသွင်းငွေ ပမာဏကို ထည့်ပါ (ဥပမာ - 2000)")
    return PAY_AMOUNT

async def payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["pay_amount"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏကို ဂဏန်းသီးသန့်သာ ထည့်သွင်းပေးပါ။")
        return PAY_AMOUNT
        
    await update.message.reply_text("📅 မည်သည့်လအတွက် ပေးသွင်းခြင်းလဲ? (ဥပမာ - August 2026)")
    return PAY_MONTH

async def payment_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pay_month"] = update.message.text.strip()

    if context.user_data["pay_method"] == "CASH":
        # Cash အလိုအလျောက် Approved ဖြစ်စေမည်
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments (member_id, amount, payment_method, provider, payment_month, payment_date, proof_photo_id, status, approved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            context.user_data["pay_member_id"], context.user_data["pay_amount"], "Cash", "Cash",
            context.user_data["pay_month"], datetime.now().strftime("%d-%m-%Y"), None, "APPROVED", str(update.effective_user.id)
        ))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Cash Payment အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။")
        return ConversationHandler.END
    else:
        await update.message.reply_text("📸 ငွေလွှဲ Screenshot ပုံတင်ပေးပါ။")
        return PAY_PROOF

async def payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Screenshot ပုံပို့ရန် လိုအပ်ပါသည်။")
        return PAY_PROOF

    photo_id = update.message.photo[-1].file_id
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO payments (member_id, amount, payment_method, provider, payment_month, payment_date, proof_photo_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        context.user_data["pay_member_id"], context.user_data["pay_amount"], "EMONEY", context.user_data["pay_provider"],
        context.user_data["pay_month"], datetime.now().strftime("%d-%m-%Y"), photo_id, "PENDING"
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text("⏳ Payment Screenshot ရရှိပါပြီ။ Admin အတည်ပြုချက်ရယူရန် စောင့်ဆိုင်းဆဲဖြစ်ပါသည်။")
    return ConversationHandler.END

# =====================================================
# PROFILE & HISTORY VISUALIZATION
# =====================================================
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE telegram_id=?", (update.effective_user.id,))
    m = cur.fetchone()
    conn.close()

    if not m:
        await update.message.reply_text("❌ Member မတွေ့ပါ။ ဦးစွာ /register ပြုလုပ်ပါ။")
        return

    text = f"📋 FCA MEMBER PROFILE\n\n🆔 ID: {m[1]}\n👤 အမည်: {m[3]}\n📞 ဖုန်း: {m[4]}\n👨 ဖခင်: {m[5]}\n👩 မိခင်: {m[6]}\n🪪 NRC: {m[7]}\n🏠 လိပ်စာ: {m[8]}\n💼 အလုပ်အကိုင်: {m[9]}\n🏢 ဌာန: {m[10]}\n📅 Join Date: {m[11]}\n✅ Status: {m[13]}"
    if m[12]:
        await update.message.reply_photo(photo=m[12], caption=text)
    else:
        await update.message.reply_text(text)

async def payment_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM members WHERE telegram_id=?", (update.effective_user.id,))
    res = cur.fetchone()

    if not res:
        await update.message.reply_text("❌ Member မှတ်တမ်း မတွေ့ပါ။")
        conn.close()
        return

    cur.execute("SELECT amount, payment_method, provider, payment_month, payment_date, status FROM payments WHERE member_id=? ORDER BY id DESC", (res[0],))
    payments = cur.fetchall()
    conn.close()

    if not payments:
        await update.message.reply_text("❌ ပေးသွင်းမှုမှတ်တမ်း မရှိသေးပါ။")
        return

    text = "💰 FCA Payment History\n\n"
    for p in payments:
        text += f"📅 {p[3]} ({p[5]})\n💵 {p[0]:,} MMK | {p[1]}-{p[2]}\n🕒 သွင်းသည့်နေ့- {p[4]}\n----------------\n"
    await update.message.reply_text(text)

async def eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT name, join_date FROM members WHERE telegram_id=?", (update.effective_user.id,))
    member = cur.fetchone()
    conn.close()

    if not member:
        await update.message.reply_text("❌ Member မတွေ့ပါ။")
        return

    months = calculate_months(member[1])
    deposit = "✅ ရရှိနိုင်ပါပြီ" if months >= 3 else "❌ မရသေးပါ"
    benefit = "✅ ခံစားခွင့်ရှိပါသည်" if months >= 12 else "❌ မရသေးပါ"

    await update.message.reply_text(f"🔍 FCA Eligibility စစ်ဆေးချက်\n\n👤 Member: {member[0]}\n📅 Join Date: {member[1]}\n⏳ သက်တမ်း: {months} လ\n💰 Security Deposit: {deposit}\n🕊️ Death Support: {benefit}")

async def referral_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM members WHERE telegram_id=?", (update.effective_user.id,))
    member = cur.fetchone()
    if not member:
        await update.message.reply_text("❌ Member မတွေ့ပါ။")
        conn.close()
        return

    cur.execute("SELECT COUNT(*) FROM members WHERE referrer_id=?", (member[0],))
    count = cur.fetchone()[0]
    conn.close()

    status = "✅ Reward ရရှိနိုင်ပါပြီ" if count >= 5 else "❌ မရသေးပါ"
    await update.message.reply_text(f"🎁 Referral Status\n\n🆔 ID: {member[0]}\n👥 မိတ်ဆက်ထားသူ: {count} ယောက်\nStatus: {status}")

# =====================================================
# ADMIN VERIFICATION COMMANDS
# =====================================================
async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, member_id, amount, provider, payment_month FROM payments WHERE status='PENDING'")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("✅ စစ်ဆေးရန်ကျန်သော ပေးသွင်းမှုမရှိပါ။")
        return

    text = "⏳ Pending Payments\n\n"
    for p in rows:
        text += f"🆔 Pay ID: {p[0]}\n👤 Member: {p[1]}\n💰 Amount: {p[2]:,} MMK\n💳 Method: {p[3]} ({p[4]})\nApprove: /approve {p[0]}\nReject: /reject {p[0]}\n----------------\n"
    await update.message.reply_text(text)

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    if not context.args:
        await update.message.reply_text("အသုံးပြုပုံ- /approve [payment_id]")
        return

    pay_id = context.args[0]
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET status='APPROVED', approved_by=? WHERE id=?", (str(update.effective_user.id), pay_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Payment ID: {pay_id} ကို အတည်ပြုပြီးပါပြီ။")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    if not context.args: return
    pay_id = context.args[0]
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET status='REJECTED' WHERE id=?", (pay_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"❌ Payment ID: {pay_id} ကို ငြင်းပယ်ပြီးပါပြီ။")

# =====================================================
# FINANCIALS & MANAGEMENT
# =====================================================
async def add_fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    if len(context.args) < 2:
        await update.message.reply_text("အသုံးပြုပုံ- /fund [amount] [description]")
        return
    try:
        amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ ငွေပမာဏ မှားယွင်းနေပါသည်။")
        return
    desc = " ".join(context.args[1:])
    
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO funds (fund_type, amount, description, created_at) VALUES (?,?,?,?)", ("OUT", amount, desc, datetime.now().strftime("%d-%m-%Y")))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"📉 အသုံးစရိတ် နှုတ်ပြီးပါပြီ-\nပမာဏ: {amount:,} MMK\nအကြောင်းပြချက်: {desc}")

async def fund_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM payments WHERE status='APPROVED'")
    total_in = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(amount) FROM funds WHERE fund_type='OUT'")
    total_out = cur.fetchone()[0] or 0
    conn.close()
    await update.message.reply_text(f"📊 FCA ရန်ပုံငွေအခြေအနေ\n\n💰 လက်ကျန်ရန်ပုံငွေ: {total_in - total_out:,} MMK\n📥 စုစုပေါင်းဝင်ငွေ: {total_in:,} MMK\n📤 စုစုပေါင်းအသုံးစရိတ်: {total_out:,} MMK")

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM members")
    m_count = cur.fetchone()[0]
    cur.execute("SELECT SUM(amount) FROM payments WHERE payment_method='Cash' AND status='APPROVED'")
    cash = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(amount) FROM payments WHERE payment_method='EMONEY' AND status='APPROVED'")
    emoney = cur.fetchone()[0] or 0
    conn.close()
    await update.message.reply_text(f"📊 FCA စာရင်းဇယားများ\n\n👥 စုစုပေါင်းအဖွဲ့ဝင်: {m_count} ဦး\n💵 လက်ငင်းငွေသားစနစ်: {cash:,} MMK\n📱 E-Money စနစ်: {emoney:,} MMK")

async def search_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    keyword = " ".join(context.args).strip()
    if not keyword:
        await update.message.reply_text("ရှာဖွေရန်- /search [Name/Phone/ID]")
        return
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id, name, phone, join_date, status FROM members WHERE name LIKE ? OR member_id LIKE ? OR phone LIKE ?", (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ မည်သည့်အဖွဲ့ဝင်မှ မတွေ့ရှိပါ။")
        return
    text = "🔍 ရှာဖွေတွေ့ရှိမှု ရလဒ်များ-\n\n"
    for r in rows:
        text += f"🆔 {r[0]} | 👤 {r[1]}\n📞 {r[2]} | 📅 {r[3]}\n📌 Status: {r[4]}\n----------------\n"
    await update.message.reply_text(text)

# =====================================================
# DATA MAINTENANCE (BACKUP & EXPORT)
# =====================================================
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    try:
        shutil.copy(DATABASE, "fca_backup.db")
        await update.message.reply_document(document=open("fca_backup.db", "rb"), filename="fca_backup.db", caption="✅ Database Backup အောင်မြင်ပါသည်။")
    except Exception as e:
        await update.message.reply_text(f"❌ Backup Error: {str(e)}")

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    wb = Workbook()
    ws = wb.active
    ws.title = "FCA Members"
    ws.append(["Member ID", "Name", "Phone", "Join Date", "Status"])
    
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id, name, phone, join_date, status FROM members")
    for row in cur.fetchall():
        ws.append(row)
    conn.close()

    file_name = "FCA_Members.xlsx"
    wb.save(file_name)
    await update.message.reply_document(document=open(file_name, "rb"), filename=file_name, caption="📊 Excel ဖိုင် ထုတ်ယူပြီးပါပြီ။")

# =====================================================
# INTENT DETECTOR & KNOWLEDGE SYSTEM (AI)
# =====================================================
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    # FCA နှင့်မဆိုင်လျှင် ရိုးရိုးပဲပြန်မည်
    has_keyword = any(word in question.lower() for word in FCA_KEYWORDS)
    if not has_keyword:
        await update.message.reply_text("🤖 FCA Assistant\n\nဤမေးခွန်းသည် FCA အဖွဲ့နှင့် မသက်ဆိုင်ပါ။ လစဉ်ကြေး၊ စပေါ်ငွေ၊ စည်းမျဉ်းများကိုသာ ဖြေကြားနိုင်ပါသည်။")
        return

    q = question.lower()
    if "လစဉ်" in q or "ကြေး" in q:
        answer = FCA_RULES["monthly_fee"]
    elif "deposit" in q or "စပေါ်" in q or "အရေးပေါ်" in q:
        answer = FCA_RULES["deposit"]
    elif "သေဆုံး" in q or "ထောက်ပံ့" in q:
        answer = FCA_RULES["death_support"]
    elif "မိတ်ဆက်" in q or "referral" in q:
        answer = FCA_RULES["referral"]
    else:
        answer = "🤖 FCA Assistant\n\nမေးခွန်းကို နားမလည်နိုင်သေးပါ။\nဥပမာ- 'လစဉ်ကြေးဘယ်လောက်လဲ' ဟု မေးမြန်းနိုင်ပါသည်။"
    await update.message.reply_text(answer)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception occurred:", exc_info=context.error)

# =====================================================
# INIT & RUN
# =====================================================
def main():
    init_database()
    app = Application.builder().token(BOT_TOKEN).build()

    # Generic Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view_profile))
    app.add_handler(CommandHandler("paymenthistory", payment_history))
    app.add_handler(CommandHandler("eligibility", eligibility))
    app.add_handler(CommandHandler("referral", referral_status))
    app.add_handler(CommandHandler("fundstatus", fund_status))
    
    # Admin Commands
    app.add_handler(CommandHandler("pending", pending_payments))
    app.add_handler(CommandHandler("approve", approve_payment))
    app.add_handler(CommandHandler("reject", reject_payment))
    app.add_handler(CommandHandler("fund", add_fund))
    app.add_handler(CommandHandler("statistics", statistics))
    app.add_handler(CommandHandler("search", search_member))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("export", export_excel))

    # Registration Flow Handler
    register_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            REG_FATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_father)],
            REG_MOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mother)],
            REG_NRC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nrc)],
            REG_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            REG_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_job)],
            REG_DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_department)],
            REG_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[]
    )

    # Admin Payment Flow Handler
    payment_handler = ConversationHandler(
        entry_points=[CommandHandler("addpayment", add_payment_start)],
        states={
            PAY_MEMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_member)],
            PAY_METHOD: [CallbackQueryHandler(payment_method_callback)],
            PAY_PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_provider)],
            PAY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_amount)],
            PAY_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_month)],
            PAY_PROOF: [MessageHandler(filters.PHOTO, payment_proof)],
        },
        fallbacks=[]
    )

    app.add_handler(register_handler)
    app.add_handler(payment_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ai))
    app.add_error_handler(error_handler)

    print("FCA BOT IS SUCCESSFULLY RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
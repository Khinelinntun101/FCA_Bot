import os
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

# DATABASE FUNCTIONS
from database import (
    db_connect,
    init_database,
    get_member_by_telegram_id,
    get_member_by_member_id,
    get_member_by_search_keyword,
    insert_member,
    get_referrer_count,
    get_total_payments,
    get_total_funds_out,
    insert_fund_transaction,
    get_all_members_for_export
)


# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7242601708"))


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# =====================================================
# DATABASE INITIALIZATION
# =====================================================

    

# =====================================================
# UTILITIES
# =====================================================
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
# USER & ADMIN ACCESS CONTROL PANEL
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        # Admin Menu
        text = """👑 FCA Bot Admin Control Panel

မင်္ဂလာပါ အက်ဒမင်။ စနစ်ကို ထိန်းချုပ်ရန် အောက်ပါ Command များကို အသုံးပြုနိုင်ပါသည်။

📊 စာရင်းဇယားနှင့် ဒေတာစုဆောင်းမှု
/admin_menu - လုပ်ဆောင်ချက်များ လမ်းညွှန်ကြည့်ရန်
/pending - စိစစ်ရန်ကျန်ရှိသော ငွေသွင်းမှုမှတ်တမ်းများ ကြည့်ရန်
/backup - လက်ရှိ Database File ကို Backup ဆွဲယူရန်
/export - အဖွဲ့ဝင်စာရင်းအားလုံးကို CSV Excel ထုတ်ယူရန်
/fund_in <amount> <desc> - အဖွဲ့တွင်း အထွေထွေဝင်ငွေ ထည့်ရန်
/fund_out <amount> <desc> - အဖွဲ့တွင်း အသုံးစရိတ်/ထောက်ပံ့ငွေ ထုတ်ရန်

📌 Member တစ်ဦးချင်းစီအား ရှာဖွေရန်
/search_member <စာသား/ဖုန်း/ID> - အဖွဲ့ဝင် ရှာဖွေရန်
"""
        await update.message.reply_text(text)
    else:
        # Member Menu
        text = """🌟 FCA မတည်ရန်ပုံငွေအဖွဲ့မှ ကြိုဆိုပါသည်

တစ်ဦးကိုတစ်ဦး ဖေးမကူညီနိုင်ရန် ရည်ရွယ်သော "အပြန်အလှန် အကျိုးပြုစုပေါင်းစနစ်" Bot ဖြစ်ပါသည်။

📝 အဖွဲ့ဝင်သစ် စာရင်းသွင်းရန်:
/register - ကိုယ်ရေးအချက်အလက်များ တင်သွင်းရန်

📋 မိမိအချက်အလက်နှင့် ခံစားခွင့်များ စစ်ဆေးရန်:
/view - မိမိ၏ Profile ကို ပြန်လည်ကြည့်ရှုရန်
/eligibility - စပေါ်ငွေနှင့် နာရေးထောက်ပံ့ကြေး ခံစားခွင့် ရှိ/မရှိ စစ်ဆေးရန်
/referral - မိမိမိတ်ဆက်ထားသော အဖွဲ့ဝင်ဦးရေနှင့် Reward အခြေအနေ
/fundstatus - အဖွဲ့၏ လက်ရှိ စုစုပေါင်း ရန်ပုံငွေ အခြေအနေ

🤖 FCA AI Assistant:
Bot ထံသို့ စည်းမျဉ်းစည်းကမ်းများနှင့် ပတ်သက်၍ သိလိုသည်များကို တိုက်ရိုက် ရိုက်နှိပ်မေးမြန်းနိုင်ပါသည်။"""
        await update.message.reply_text(text)

# =====================================================
# MEMBER REGISTRATION CONVERSATION Flow
# =====================================================
NAME, PHONE, FATHER, MOTHER, NRC, ADDRESS, JOB, DEPARTMENT, PHOTO = range(9)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("❌ Admin သည် ရုံးလုပ်ငန်းစာရင်းများသာ ကိုင်တွယ်ရန်ဖြစ်သဖြင့် Register လုပ်ရန်မလိုပါ။")
        return ConversationHandler.END
        
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM members WHERE telegram_id=?", (update.effective_user.id,))
    exists = cur.fetchone()
    conn.close()

    if exists:
        await update.message.reply_text("❌ သင်သည် အဖွဲ့ဝင်စာရင်း သွင်းပြီးသားဖြစ်နေပါသည်။ /view ဖြင့် Profile ပြန်ကြည့်နိုင်ပါသည်။")
        return ConversationHandler.END

    await update.message.reply_text("📝 FCA Member Registration\n\nအဖွဲ့ဝင်အဖြစ် ပါဝင်လိုသူ၏ 'အမည်' ကို ရိုက်ထည့်ပေးပါ။")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("📞 ဆက်သွယ်ရန် 'ဖုန်းနံပါတ်' ထည့်ပေးပါ။")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("👨 'ဖခင်အမည်' ကို ထည့်ပေးပါ။")
    return FATHER

async def get_father(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["father_name"] = update.message.text
    await update.message.reply_text("👩 'မိခင်အမည်' ကို ထည့်ပေးပါ။")
    return MOTHER

async def get_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mother_name"] = update.message.text
    await update.message.reply_text("🪪 'မှတ်ပုံတင်အမှတ် (NRC)' ကို ထည့်ပေးပါ။")
    return NRC

async def get_nrc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nrc"] = update.message.text
    await update.message.reply_text("🏠 'လက်ရှိနေရပ်လိပ်စာ' အပြည့်အစုံကို ထည့်ပေးပါ။")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("💼 'အလုပ်အကိုင်' ကို ရိုက်ထည့်ပေးပါ။")
    return JOB

async def get_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"] = update.message.text
    await update.message.reply_text("🏢 မိမိလုပ်ကိုင်နေသော 'ဌာန' ကို ရိုက်ထည့်ပေးပါ။")
    return DEPARTMENT

async def get_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["department"] = update.message.text
    await update.message.reply_text("📸 Profile Photo ပို့ပေးပါ။\n\nမိမိပုံကို Telegram Photo (ဓာတ်ပုံအစစ်) အဖြစ် တိုက်ရိုက်တင်ပေးပါ။ File အနေဖြင့် မပို့ပါနှင့်။")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ လုံခြုံရေးအရ ဓာတ်ပုံ တင်ပေးရန် လိုအပ်ပါသည်။ ဓာတ်ပုံပြန်ပို့ပေးပါ။")
        return PHOTO

    photo_id = update.message.photo[-1].file_id
    member_id = generate_member_id()
    join_date_str = datetime.now().strftime("%d-%m-%Y")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO members (member_id, telegram_id, name, phone, father_name, mother_name, nrc, address, job, department, join_date, profile_photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        member_id, update.effective_user.id, context.user_data["name"], context.user_data["phone"],
        context.user_data["father_name"], context.user_data["mother_name"], context.user_data["nrc"],
        context.user_data["address"], context.user_data["job"], context.user_data["department"],
        join_date_str, photo_id
    ))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎉 FCA Member Registration Complete\n\n🆔 မိတ်ဆွေ၏ Member ID မှာ: {member_id} ဖြစ်ပါသည်။\n👤 အမည်: {context.user_data['name']}\n📅 စတင်ဝင်ရောက်သည့်နေ့: {join_date_str}\n\nလက်စွဲစာစောင်ပါ အပိုင်း (၁၀) အရ ဤစနစ်ကို အသုံးပြုခြင်းသည် စည်းကမ်းချက်များကို နှစ်ဦးသဘောတူ ဝန်ခံကတိပြုပြီးဖြစ်သည်ဟု မှတ်ယူပါသည်။")
    return ConversationHandler.END

# =====================================================
# MEMBER UTILITIES
# =====================================================
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE telegram_id=?", (update.effective_user.id,))
    m = cur.fetchone()
    conn.close()

    if not m:
        await update.message.reply_text("❌ အဖွဲ့ဝင်စာရင်း မတွေ့ပါ။ ကျေးဇူးပြု၍ ဦးစွာ /register ပြုလုပ်ပေးပါ။")
        return

    text = f"📋 FCA MEMBER PROFILE\n\n🆔 ID: {m[1]}\n👤 အမည်: {m[3]}\n📞 ဖုန်း: {m[4]}\n👨 ဖခင်: {m[5]}\n👩 မိခင်: {m[6]}\n🪪 NRC: {m[7]}\n🏠 လိပ်စာ: {m[8]}\n💼 အလုပ်အကိုင်: {m[9]}\n🏢 ဌာန: {m[10]}\n📅 Join Date: {m[11]}\n📌 အခြေအနေ: {m[13]}"
    await update.message.reply_photo(photo=m[12], caption=text)

async def eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id, name, join_date FROM members WHERE telegram_id=?", (update.effective_user.id,))
    member = cur.fetchone()
    conn.close()

    if not member:
        await update.message.reply_text("❌ အဖွဲ့ဝင်စာရင်း မတွေ့ပါ။")
        return

    months = calculate_months(member[2])
    
    # Waiting Period Rule (3 Months for deposit, 12 Months for Death Benefit)
    deposit = "✅ (၃) လပြည့်ပြီးသဖြင့် ပြန်လည်ထုတ်ယူခွင့် ရှိပါသည်" if months >= 3 else f"❌ စောင့်ဆိုင်းဆဲ (ကျန်ရှိသက်တမ်း: {3 - months} လ)"
    benefit = "✅ (၁) နှစ်ပြည့်ပြီးသဖြင့် သေဆုံးမှုထောက်ပံ့ကြေး အပြည့်အဝ ခံစားခွင့်ရှိပါသည်" if months >= 12 else f"❌ စောင့်ဆိုင်းကာလမပြည့်သေးပါ (သွင်းငွေများကိုသာ အတိုးမဲ့ ပြန်ထုတ်ပိုင်ခွင့်ရှိသည်)"

    await update.message.reply_text(f"🔍 FCA ခံစားခွင့်ဆိုင်ရာ စစ်ဆေးချက်\n\n👤 အဖွဲ့ဝင်အမည်: {member[1]}\n📅 စတင်ဝင်ရောက်သည့်နေ့: {member[2]}\n⏳ လက်ရှိအဖွဲ့ဝင်သက်တမ်း: {months} လ\n\n💰 စပေါ်ငွေ (၅,၀၀၀ ကျပ်) အခြေအနေ:\n{deposit}\n\n🕊️ နာရေးထောက်ပံ့ကြေး ခံစားခွင့်အခြေအနေ:\n{benefit}")

async def referral_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM members WHERE telegram_id=?", (update.effective_user.id,))
    member = cur.fetchone()
    
    if not member:
        await update.message.reply_text("❌ အဖွဲ့ဝင်စာရင်း မတွေ့ပါ။")
        conn.close()
        return

    cur.execute("SELECT COUNT(*) FROM members WHERE referrer_id=?", (member[0],))
    count = cur.fetchone()[0]
    conn.close()

    # Referral Reward Rule (5 Active members)
    status = "✅ သတ်မှတ်ချက်ပြည့်မီသဖြင့် လစဉ်ကြေး ၂,၀၀၀ ကျပ် ကင်းလွတ်ခွင့် ရရှိပါသည်" if count >= 5 else f"❌ မပြည့်သေးပါ (ယခု မိတ်ဆက်ပြီးသူ: {count}/၅ ဦး)"
    
    await update.message.reply_text(f"🎁 Referral ဆုလာဘ် အခြေအနေ\n\n🆔 မိမိ၏ ID: {member[0]}\n👥 အောင်မြင်စွာ မိတ်ဆက်ထားသူ: {count} ဦး\n\n📌 ဆုလာဘ်ရရှိမှု: {status}\n\n⚠️ စည်းကမ်းချက်- ခေါ်ယူလာသူ ၅ ဦးစလုံး ၃ လဆက်တိုက် ကြေးမှန်မှန်သွင်းမှသာ အတည်ပြုမည်ဖြစ်ပြီး၊ တစ်ဦးဦးပျက်ကွက်ပါက ပုံမှန်အတိုင်း လစဉ်ကြေး ပြန်သွင်းရပါမည်။ သေဆုံးမှုထည့်ဝင်ငွေ ၁,၀၀0 ကျပ်ကိုမူ ပုံမှန်ထည့်ရပါမည်။")

async def fund_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM payments WHERE status='APPROVED'")
    total_in = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(amount) FROM funds WHERE fund_type='OUT'")
    total_out = cur.fetchone()[0] or 0
    conn.close()

    # Base Reserve Fund is 200,000 MMK
    reserve_fund = 200000
    current_pool = reserve_fund + total_in - total_out

    await update.message.reply_text(f"📊 FCA စုစုပေါင်း ရန်ပုံငွေထုတ်ပြန်ချက်\n\n🧱 စတင်မတည်ငွေ (Reserve Fund): {reserve_fund:,} MMK\n📥 စုစုပေါင်း ဝင်ငွေမှတ်တမ်း: {total_in:,} MMK\n📤 စုစုပေါင်း အသုံးပြုမှု/ထောက်ပံ့မှု: {total_out:,} MMK\n\n💰 လက်ရှိဗဟိုရန်ပုံငွေ လက်ကျန်: {current_pool:,} MMK\n\n🤝 စနစ်သည် ပွင့်လင်းမြင်သာမှုရှိစွာ စာရင်းဇယားများကို စက္ကန့်နှင့်အမျှ တိကျစွာ မှတ်တမ်းတင်ထားပါသည်။")

# =====================================================
# HAND-BOOK BASED SMART AI ASSISTANT (12 SECTIONS LOGIC)
# =====================================================
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        return # Admin text messages are ignored by AI responses
        
    question = update.message.text.lower()
    reply = ""

    # Section 1: Intro & Purpose
    if any(x in question for x in ["နိဒါန်း", "ရည်ရွယ်ချက်", "vision", "အာမခံလုပ်ငန်း", "reserve fund", "မတည်ငွေ"]):
        reply = "🤝 **အပိုင်း (၁) - ရန်ပုံငွေအဖွဲ့၏ မူဝါဒနှင့် ရည်ရွယ်ချက်များ**\n\nဤအဖွဲ့သည် စီးပွားဖြစ်အာမခံလုပ်ငန်းမဟုတ်ဘဲ တစ်ဦးကိုတစ်ဦး ဖေးမကူညီရန် 'အပြန်အလှန် အကျိုးပြုစုပေါင်းစနစ်' ဖြစ်သည်။ ကျွန်ုပ်တို့အဖွဲ့သည် စီမံခန့်ခွဲသူ၏ မတည်ရင်းနှီးငွေ (Reserve Fund) **၂ သိန်းကျပ်** ဖြင့် အခိုင်အမာ စတင်ထားခြင်း ဖြစ်သဖြင့် ယုံကြည်စိတ်ချစွာ ပါဝင်နိုင်ပါသည်။"

    # Section 2 & 8: Fees, contribution & Referral Rewards
    elif any(x in question for x in ["လစဉ်ကြေး", "စပေါ်ငွေ", "ငွေသွင်း", "security deposit", "ဘယ်လောက်သွင်း", "ကြိုတင်ပေး"]):
        reply = "💰 **အပိုင်း (၂) - ထည့်ဝင်ကြေးဆိုင်ရာ စည်းမျဉ်းများ**\n\n• **အာမခံစပေါ်ငွေ (Security Deposit):** စတင်ဝင်ရောက်ချိန်တွင် ၅,၀၀၀ ကျပ် တစ်ကြိမ်တည်း ပေးသွင်းရမည်။ (၃ လပြည့်လျှင် ပြန်ထုတ်နိုင်သည်။ ၃ လမပြည့်ဘဲ ထွက်ပါက ပြန်မရပါ)\n• **လစဉ်ထည့်ဝင်ကြေး:** တစ်လလျှင် ၂,၀၀၀ ကျပ် တိတိ ဖြစ်ပြီး၊ ၃ လစာ၊ ၆ လစာ သို့မဟုတ် ၁ နှစ်စာ (၂၄,၀၀၀ ကျပ်) ကြိုတင်ပေးသွင်းနိုင်ပါသည်။"
        
    elif any(x in question for x in ["မိတ်ဆက်", "referral", "reward", "၅ ယောက်", "ဆုလာဘ်"]):
        reply = "🎁 **အပိုင်း (၂/၈) - မိတ်ဆက်သူများအတွက် အထူးခံစားခွင့်**\n\nအဖွဲ့ဝင်သစ် (၅) ဦးအား အောင်မြင်စွာ မိတ်ဆက်ပေးနိုင်သူသည် ထိုသူများ ၃ လဆက်တိုက် လစဉ်ကြေးမှန်မှန် သွင်းပြီးသည့် နောက်လမှစ၍ လစဉ်ကြေး ၂,၀၀၀ ကျပ် ကင်းလွတ်ခွင့်ရမည်။ သို့သော် တစ်ဦးဦး ပျက်ကွက်ပါက ပုံမှန်အတိုင်း ပြန်ဆောင်ရမည်ဖြစ်ပြီး၊ သေဆုံးမှုထည့်ဝင်ကြေး ၁,၀၀၀ ကျပ်ကိုမူ ကင်းလွတ်ခွင့်မရှိဘဲ အားလုံးနည်းတူ ထည့်ဝင်ရပါမည်။"

    # Section 3 & 12: Payout Formula & Multiple Claims
    elif any(x in question for x in ["သေဆုံး", "ထောက်ပံ့ကြေး", "နာရေး", "တွက်ချက်ပုံ", "လျော်ကြေး"]):
        reply = "🕊️ **အပိုင်း (၃) - ထောက်ပံ့ငွေ တွက်ချက်ပုံစနစ်**\n\nပုံသေ လျော်ကြေးငွေ ပေးအပ်ခြင်းမဟုတ်ဘဲ အချိုးကျစနစ်ကို ကျင့်သုံးသည်။ အဖွဲ့ဝင်တစ်ဦး သေဆုံးပါက (သက်တမ်း ၁ နှစ်ပြည့်ပြီးသူဖြစ်လျှင်):\n\n၁။ အဖွဲ့ဝင်တစ်ဦးစီမှ **၁,၀၀၀ ကျပ်စီ** ထည့်ဝင်သော စုစုပေါင်းငွေ\n+\n၂။ ဗဟိုရန်ပုံငွေ လက်ကျန် (Total Fund) ၏ **၂၀% တိတိ**\n\nတို့ကို ပေါင်းစပ်ထောက်ပံ့မည်ဖြစ်သည်။ စောင့်ဆိုင်းကာလ ၁ နှစ်မပြည့်မီ သေဆုံးပါက သွင်းထားသောငွေများကိုသာ အတိုးမဲ့ ပြန်လည်ထုတ်ယူခွင့်ရှိသည်။"

    elif any(x in question for x in ["တစ်လအတွင်း", "၂ ယောက်သေ", "ပြတ်လပ်", "split"]):
        reply = "🔄 **အပိုင်း (၃) - တစ်လအတွင်း သေဆုံးမှု တစ်ခုထက်ပိုရှိခြင်း**\n\nအကယ်၍ တစ်လအတွင်း အဖွဲ့ဝင် ၂ ဦးနှင့်အထက် သေဆုံးမှုရှိပါက၊ စုစုပေါင်းရရှိသော ထောက်ပံ့ငွေ (၁,၀၀၀ စီကောက်ငွေ + ရန်ပုံငွေ၏ ၂၀%) အား သေဆုံးသူများအကြား ညီတူညီမျှ ခွဲဝေ (Split) ပေးအပ်မည် ဖြစ်သည်။ ထောက်ပံ့ကြေးကို စိစစ်မှုများပြုလုပ်ပြီး 'လကုန်ရက်' တွင်သာ စုပေါင်းထုတ်ပေးသည်။"

    # Section 4 & 6: Management & Transparency & Asset
    elif any(x in question for x in ["စီမံခန့်ခွဲမှု", "ဖြတ်တောက်", "ရွှေဝယ်", "ရင်းနှီးမြှုပ်နှံ", "စာရင်းထုတ်"]):
        reply = "🛠️ **အပိုင်း (၄/၆) - စီမံခန့်ခွဲမှုနှင့် ရန်ပုံငွေထိန်းသိမ်းခြင်း**\n\nအဖွဲ့ဝင်အရေအတွက် (၂၀) ဦး ပြည့်မြောက်သည့်နေ့မှစ၍ လစဉ်ရရှိသော ရန်ပုံငွေစုစုပေါင်း၏ (၁၀%) အား လည်ပတ်မှုစရိတ်အဖြစ် ဖြတ်တောက်မည်။ ငွေကြေးဖောင်းပွမှုဒဏ်မှ ကာကွယ်ရန် ရန်ပုံငွေများကို ခိုင်မာသော ပိုင်ဆိုင်မှုများ (ဥပမာ- ရွှေ) အဖြစ် ပြောင်းလဲသိမ်းဆည်းပိုင်ခွင့် စီမံခန့်ခွဲသူတွင် ရှိသည်။ စာရင်းဇယားများကို လစဉ် လူမှုကွန်ရက်တွင် ပွင့်လင်းမြင်သာစွာ အမြဲထုတ်ပြန်ပေးမည်။"

    # Section 4 & 7: Obligations, Withdrawal & Dismissal
    elif any(x in question for x in ["နုတ်ထွက်", "ထွက်ချင်", "ပြန်အမ်း", "ပျက်ကွက်", "ထုတ်ပယ်"]):
        reply = "🚪 **အပိုင်း (၄/၇) - နုတ်ထွက်ခြင်းနှင့် ရပ်စဲခံရခြင်း မူဝါဒ**\n\n• **၁ နှစ်အတွင်းနုတ်ထွက်ပါက:** မိမိပေးသွင်းထားသော လစဉ်ကြေးစုစုပေါင်းအား အတိုးမဲ့ ပြန်ထုတ်ယူခွင့်ရှိသည်။\n• **၁ နှစ်ကျော်မှနုတ်ထွက်ပါက:** အကျိုးခံစားခွင့်များ ရယူထားပြီးဖြစ်၍ ငွေပြန်ထုတ်ပိုင်ခွင့် မရှိပါ။\n⚠️ **သတိပြုရန်:** သေဆုံးမှု ထပ်ဆောင်းငွေ ၁,၀၀၀ ကျပ်အား ၃ ရက်အတွင်း သွင်းရမည်။ သတ်မှတ်ထားသောငွေများကို (၃) ကြိမ်နှင့်အထက် ပျက်ကွက်ပါက အဖွဲ့ဝင်အဖြစ်မှ အလိုအလျောက် ရပ်စဲခံရမည်ဖြစ်ပြီး ငွေပြန်တောင်းပိုင်ခွင့် မရှိပါ။"

    # Section 5: Exclusions (When they don't get paid)
    elif any(x in question for x in ["မရနိုင်သော", "ချွင်းချက်", "သတ်သေ", "ရာဇဝတ်မှု", "မူးယစ်ဆေး"]):
        reply = "🚫 **အပိုင်း (၅) - ထောက်ပံ့ကြေးမရနိုင်သော ချွင်းချက်များ**\n\nအောက်ပါအခြေအနေများကြောင့် သေဆုံးခြင်းဖြစ်ပါက ထောက်ပံ့ကြေး လုံးဝ ပေးအပ်မည်မဟုတ်ပါ -\n၁။ မိမိကိုယ်ကိုယ် အဆုံးစီရင်ခြင်း (Suicide)\n၂။ ရာဇဝတ်မှု ကျူးလွန်နေစဉ်အတွင်း သေဆုံးခြင်း\n၃။ မူးယစ်ဆေးဝါး အလွန်အကျွံသုံးစွဲခြင်းကြောင့် သေဆုံးခြင်း\n၄။ အဖွဲ့ဝင်ဝင်စဉ်ကတည်းက ကျန်းမာရေးအခြေအနေအား လိမ်လည်ဖုံးကွယ်ခြင်း။"

    # Section 11: Internal Credit & Bonus
    elif any(x in question for x in ["အကြွေး", "ကုန်ပစ္စည်း", "bonus", "အမြတ်ခွဲဝေ"]):
        reply = "🏦 **အပိုင်း (၁၁) - အသေးစား အကြွေးဝယ်စနစ်နှင့် ရန်ပုံငွေ**\n\nအဖွဲ့ဝင်သက်တမ်းရင့်ပြီး စနစ်တကျရှိသူများအား အဖွဲ့၏ရန်ပုံငွေကို အခြေခံ၍ အိမ်သုံးကုန်ပစ္စည်းများ အကြွေးဝယ်ယူခွင့် သို့မဟုတ် လူမှုဖူလုံရေး ကြိုတင်ထုတ်ယူခွင့်ကို ရန်ပုံငွေ၏ (၃၀%) ထက်မပိုသော ကန့်သတ်ချက်ဖြင့် စီမံခန့်ခွဲသူမှ ခွင့်ပြုပေးနိုင်သည်။ အမြတ်များပြားလာပါက နှစ်ပတ်လည်လက်ဆောင်များ ပေးအပ်သွားမည်ဖြစ်သည်။"

    # Section 12: Claim Process
    elif any(x in question for x in ["တောင်းခံ", "လုံခြုံရေး", "အထောက်အထား", "ဆေးရုံမှတ်တမ်း"]):
        reply = "🚨 **အပိုင်း (၁၂) - ထောက်ပံ့ကြေး တောင်းခံခြင်း လုပ်ငန်းစဉ်**\n\nအဖွဲ့ဝင်တစ်ဦး ကွယ်လွန်ပါက ကျန်ရစ်သူမိသားစုသည် (၂၄) နာရီအတွင်း စီမံခန့်ခွဲသူထံ ချက်ချင်းအကြောင်းကြားရမည်။ သေဆုံးကြောင်းအထောက်အထား (ဆေးရုံမှတ်တမ်း သို့မဟုတ် ရပ်ကွက်ထောက်ခံချက် မူရင်း) ကို တင်ပြရမည်ဖြစ်ပြီး စီမံခန့်ခွဲသူမှ (၃) ရက်အတွင်း စိစစ်ကာ ကျန်အဖွဲ့ဝင်များထံမှ ကောက်ခံခြင်းလုပ်ငန်းစဉ် စတင်ပါမည်။\n📞 အရေးပေါ်ဖုန်း - 09685247040"

    else:
        reply = "🤖 **FCA AI Assistant**\n\nမင်္ဂလာပါ၊ မေးခွန်းကို ရှာမတွေ့ပါ။ FCA စည်းမျဉ်းအဖွဲ့ဝင်လက်စွဲပါ အောက်ပါအကြောင်းအရာများကို တိုက်ရိုက် မေးမြန်းနိုင်ပါသည်။\n\nဥပမာ -\n• 'လစဉ်ကြေးနဲ့ စပေါ်ငွေ ဘယ်လောက်လဲ?'\n• 'နာရေးထောက်ပံ့ကြေး ဘယ်လိုတွက်လဲ?'\n• '၁ နှစ်မပြည့်ခင် နုတ်ထွက်ရင် ငွေပြန်ရလား?'\n• '၅ ယောက်ခေါ်ရင် တကယ်လစဉ်ကြေး အလကားရတာလား?'"

    await update.message.reply_text(reply, parse_mode="Markdown")

# =====================================================
# ADMIN ONLY COMMANDS
# =====================================================
async def search_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if not context.args:
        await update.message.reply_text("အသုံးပြုပုံ: /search_member <အမည် သို့မဟုတ် ဖုန်း သို့မဟုတ် ID>")
        return

    keyword = " ".join(context.args)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT member_id, name, phone, join_date, status 
        FROM members 
        WHERE name LIKE ? OR member_id LIKE ? OR phone LIKE ?
    """, ("%"+keyword+"%", "%"+keyword+"%", "%"+keyword+"%"))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ မည်သည့် Member အချက်အလက်မှ ရှာမတွေ့ပါ။")
        return

    text = f"🔍 Search Results ({len(rows)} ဦးတွေ့ရှိ):\n\n"
    for m in rows:
        text += f"🆔 ID: {m[0]}\n👤 အမည်: {m[1]}\n📞 ဖုန်း: {m[2]}\n📅 ဝင်သည့်နေ့: {m[3]}\n📌 Status: {m[4]}\n----------------\n"
    await update.message.reply_text(text)

async def fund_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("အသုံးပြုပုံ: /fund_in <ပမာဏ> <အကြောင်းအရာ>")
        return
    
    amount = int(context.args[0])
    desc = " ".join(context.args[1:])
    date_str = datetime.now().strftime("%d-%m-%Y")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO funds (fund_type, amount, description, created_at) VALUES ('IN', ?, ?, ?)", (amount, desc, date_str))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ ရန်ပုံငွေထဲသို့ ဝင်ငွေစာရင်းသွင်းပြီးပါပြီ။\n💰 ပမာဏ: {amount:,} MMK\n📝 အကြောင်းအရာ: {desc}")

async def fund_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("အသုံးပြုပုံ: /fund_out <ပမာဏ> <အကြောင်းအရာ/နာရေးထောက်ပံ့မှု>")
        return
    
    amount = int(context.args[0])
    desc = " ".join(context.args[1:])
    date_str = datetime.now().strftime("%d-%m-%Y")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO funds (fund_type, amount, description, created_at) VALUES ('OUT', ?, ?, ?)", (amount, desc, date_str))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"💸 ရန်ပုံငွေထဲမှ အသုံးစရိတ်/ထောက်ပံ့ငွေ ထုတ်ယူမှု သွင်းပြီးပါပြီ။\n💰 ပမာဏ: {amount:,} MMK\n📝 အကြောင်းအရာ: {desc}")

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        shutil.copy("fca.db", "fca_backup.db")
        await update.message.reply_document(document=open("fca_backup.db", "rb"), filename=f"fca_backup_{datetime.now().strftime('%Y%m%d')}.db", caption="✅ လက်ရှိ Database အား Backup ထုတ်ယူပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"Backup Error: {str(e)}")

async def export_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    filename = "members_export.csv"
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT member_id, name, phone, join_date, status FROM members")
    rows = cur.fetchall()
    conn.close()

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Member ID", "Name", "Phone", "Join Date", "Status"])
        writer.writerows(rows)

    await update.message.reply_document(document=open(filename, "rb"), filename=filename, caption="📊 FCA အဖွဲ့ဝင်တစ်ဦးချင်းစီ၏ စာရင်းဇယား Excel/CSV ဖိုင်ထုတ်ယူမှု။")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# =====================================================
# MAIN APPLICATION RUNNER
# =====================================================
def main():
    init_database()

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands Base Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view_profile))
    app.add_handler(CommandHandler("eligibility", eligibility))
    app.add_handler(CommandHandler("referral", referral_status))
    app.add_handler(CommandHandler("fundstatus", fund_status))

    # Admin Handlers
    app.add_handler(CommandHandler("search_member", search_member))
    app.add_handler(CommandHandler("fund_in", fund_in))
    app.add_handler(CommandHandler("fund_out", fund_out))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("export", export_members))

    # Conversation Registration Handler
    register_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            FATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_father)],
            MOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mother)],
            NRC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nrc)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_job)],
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_department)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[]
    )
    app.add_handler(register_handler)

    # General Member Messages route to Handbook AI
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ai))
    
    app.add_error_handler(error_handler)

    print("FCA BOT IS FULLY DEPLOYED & RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
import os
import sqlite3
import random
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# ENV
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7242601708"))

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("fca.db", check_same_thread=False)
cur = conn.cursor()

# Members Table
cur.execute("""
CREATE TABLE IF NOT EXISTS members (
    member_id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT,
    telegram_id INTEGER,
    approved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Profiles Table (confirmed column ကိုပါ ထည့်သွင်းတည်ဆောက်ထားသည်)
cur.execute("""
CREATE TABLE IF NOT EXISTS profiles (
    member_id TEXT PRIMARY KEY,
    photo_id TEXT,
    full_name TEXT,
    father_name TEXT,
    mother_name TEXT,
    nrc TEXT,
    phone TEXT,
    current_address TEXT,
    permanent_address TEXT,
    occupation TEXT,
    department TEXT,
    position TEXT,
    join_date TEXT,
    beneficiary_name TEXT,
    beneficiary_relationship TEXT,
    beneficiary_phone TEXT,
    beneficiary_address TEXT,
    confirmed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Settings Table
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# =========================
# MEMORY
# =========================
user_sessions = {}
user_profile_progress = {}
user_profile_data = {}
user_waiting_photo = {}

# =========================
# PROFILE STEPS & LABELS
# =========================
profile_steps = [
    "full_name", "father_name", "mother_name", "nrc", "phone",
    "current_address", "permanent_address", "occupation", "department",
    "position", "join_date", "beneficiary_name", "beneficiary_relationship",
    "beneficiary_phone", "beneficiary_address"
]

profile_labels = {
    "full_name": "အမည်",
    "father_name": "ဖခင်အမည်",
    "mother_name": "မိခင်အမည်",
    "nrc": "မှတ်ပုံတင်အမှတ်",
    "phone": "ဖုန်းနံပါတ်",
    "current_address": "လက်ရှိနေရပ်လိပ်စာ",
    "permanent_address": "အမြဲတမ်းနေရပ်လိပ်စာ",
    "occupation": "အလုပ်အကိုင်",
    "department": "ဌာန",
    "position": "ရာထူး",
    "join_date": "FCA စတင်ဝင်ရောက်သည့်ရက်စွဲ",
    "beneficiary_name": "အကျိုးခံစားခွင့်ရှိသူ အမည်",
    "beneficiary_relationship": "တော်စပ်ပုံ",
    "beneficiary_phone": "အကျိုးခံစားခွင့်ရှိသူ ဖုန်း",
    "beneficiary_address": "အကျိုးခံစားခွင့်ရှိသူ လိပ်စာ"
}

# =========================
# HELPERS
# =========================
def is_admin(user_id):
    return user_id == ADMIN_ID

def generate_member_id():
    while True:
        member_id = f"FCA-{random.randint(10000, 99999)}"
        cur.execute("SELECT member_id FROM members WHERE member_id=?", (member_id,))
        if not cur.fetchone():
            return member_id

def get_member(username, password):
    cur.execute(
        "SELECT member_id, approved FROM members WHERE username=? AND password=?",
        (username, password)
    )
    return cur.fetchone()

def is_logged_in(user_id):
    return user_id in user_sessions

# =========================
# COMMAND HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            "🔐 FCA Admin Panel\n\n"
            "/addmember username password\n"
            "/approve FCA-12345\n"
            "/members — စာရင်းကြည့်ရန်\n"
            "/viewmember FCA-12345 — Profile ကြည့်ရန်\n"
            "/setfund 500000 — ရန်ပုံငွေသတ်မှတ်ရန်\n"
            "/broadcast စာသား — အသိပေးချက်ပို့ရန်\n"
            "/confirm FCA-12345 — Profile အတည်ပြုရန်\n"
            "/deletemember MEMBER_ID\n"
            "/stats"
        )
        return

    await update.message.reply_text(
        "🏢 FCA Membership Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "Login ဝင်ရန်\n"
        "/login username password"
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("အသုံးပြုပုံ - /login username password")
        return

    username, password = context.args, context.args
    data = get_member(username, password)

    if not data:
        await update.message.reply_text("❌ Username သို့ Password မှားနေပါသည်")
        return

    member_id, approved = data
    if approved == 0:
        await update.message.reply_text("⏳ Admin Approval မရသေးပါ")
        return

    user_id = update.effective_user.id
    user_sessions[user_id] = member_id

    cur.execute(
        "UPDATE members SET telegram_id=? WHERE member_id=?",
        (user_id, member_id)
    )
    conn.commit()

    await update.message.reply_text(
        f"✅ Login အောင်မြင်ပါသည်\n\n🆔 Member ID : {member_id}\n\n/profile ကိုနှိပ်ပြီး Profile ဖြည့်နိုင်ပါသည်"
    )

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_logged_in(user_id):
        await update.message.reply_text("❌ Login မဝင်ရသေးပါ")
        return

    del user_sessions[user_id]
    await update.message.reply_text("✅ Logout ပြီးပါပြီ")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_logged_in(user_id):
        await update.message.reply_text("❌ အရင်ဆုံး /login ဝင်ပါ")
        return

    user_profile_progress[user_id] = -1
    user_profile_data[user_id] = {}
    user_waiting_photo[user_id] = True

    await update.message.reply_text("📸 Profile Photo (ဓာတ်ပုံ) ပို့ပေးပါ။")

# =========================
# PHOTO & TEXT HANDLERS
# =========================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_waiting_photo:
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    user_profile_data[user_id]["photo_id"] = file_id

    os.makedirs("photos", exist_ok=True)
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(f"photos/{user_id}.jpg")

    del user_waiting_photo[user_id]
    user_profile_progress[user_id] = 0
    first_field = profile_steps

    await update.message.reply_text(
        f"✅ ဓာတ်ပုံလက်ခံရရှိပါပြီ။\n\n1️⃣ {profile_labels[first_field]} ကို ထည့်သွင်းပေးပါ။"
    )

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_profile_progress:
        return

    step = user_profile_progress[user_id]
    if step < 0:
        return

    current_field = profile_steps[step]
    user_profile_data[user_id][current_field] = update.message.text

    step += 1
    user_profile_progress[user_id] = step

    if step < len(profile_steps):
        next_field = profile_steps[step]
        await update.message.reply_text(f"{step+1}️⃣ {profile_labels[next_field]} ကို ထည့်သွင်းပေးပါ။")
    else:
        await save_profile(user_id)
        member_id = user_sessions[user_id]
        await update.message.reply_text(
            f"🎉 FCA Membership Profile ဖြည့်စွက်ခြင်း အောင်မြင်စွာ ပြီးဆုံးပါပြီ။\n\n🆔 {member_id}"
        )
        user_profile_progress.pop(user_id, None)
        user_profile_data.pop(user_id, None)

async def save_profile(user_id):
    member_id = user_sessions[user_id]
    d = user_profile_data[user_id]

    cur.execute("""
        INSERT OR REPLACE INTO profiles (
            member_id, photo_id, full_name, father_name, mother_name, nrc, phone,
            current_address, permanent_address, occupation, department, position,
            join_date, beneficiary_name, beneficiary_relationship, beneficiary_phone, beneficiary_address, confirmed
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
    """, (
        member_id, d.get("photo_id", ""), d.get("full_name", ""), d.get("father_name", ""),
        d.get("mother_name", ""), d.get("nrc", ""), d.get("phone", ""), d.get("current_address", ""),
        d.get("permanent_address", ""), d.get("occupation", ""), d.get("department", ""),
        d.get("position", ""), d.get("join_date", ""), d.get("beneficiary_name", ""),
        d.get("beneficiary_relationship", ""), d.get("beneficiary_phone", ""), d.get("beneficiary_address", "")
    ))
    conn.commit()

# =========================
# USER COMMANDS
# =========================

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_logged_in(user_id):
        await update.message.reply_text("❌ အရင်ဆုံး /login ဝင်ပါ")
        return

    member_id = user_sessions[user_id]
    cur.execute("SELECT full_name, phone, position FROM profiles WHERE member_id=?", (member_id,))
    data = cur.fetchone()

    if not data:
        await update.message.reply_text("❌ Profile မဖြည့်ရသေးပါ")
        return

    await update.message.reply_text(f"👤 အမည်: {data}\n📞 ဖုန်း: {data}\n🏅 ရာထူး: {data}")

async def myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_logged_in(user_id):
        await update.message.reply_text("❌ အရင်ဆုံး /login ဝင်ပါ")
        return

    member_id = user_sessions[user_id]
    cur.execute("SELECT * FROM profiles WHERE member_id=?", (member_id,))
    row = cur.fetchone()

    if not row:
        await update.message.reply_text("❌ Profile မရှိသေးပါ")
        return

    status = "✅ Confirmed" if row == 1 else "⏳ Waiting Confirmation"

    msg = f"""
🆔 ID: {row} [Status: {status}]
👤 အမည်: {row}
👨 အဖအမည်: {row}
👩 အမိအမည်: {row}
🪪 မှတ်ပုံတင်: {row}
📞 ဖုန်း: {row}
🏠 လက်ရှိလိပ်စာ: {row}
🏡 အမြဲတမ်းလိပ်စာ: {row}
💼 အလုပ်အကိုင်: {row}
🏢 ဌာန: {row}
🏅 ရာထူး: {row}
📅 FCA ဝင်ရောက်သည့်နေ့: {row}

👨‍👩‍👧 အကျိုးခံစားခွင့်ရှိသူ
👤 အမည်: {row}
🔗 တော်စပ်ပုံ: {row}
📞 ဖုန်း: {row}
🏠 လိပ်စာ: {row}
"""
    if row:  # Photo ID ရှိလျှင် ပုံပါတွဲပို့ပေးမည်
        await update.message.reply_photo(photo=row, caption=msg)
    else:
        await update.message.reply_text(msg)

async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT value FROM settings WHERE key='fund'")
    row = cur.fetchone()
    amount = row if row else "0"
    await update.message.reply_text(f"💰 FCA Fund\n\n{amount} MMK")

# =========================
# ADMIN COMMANDS (တောင်းဆိုထားသော Function များ ဖြည့်စွက်ထားသည်)
# =========================

async def addmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 2:
        await update.message.reply_text("အသုံးပြုပုံ - /addmember username password")
        return
    
    username, password = context.args, context.args
    member_id = generate_member_id()
    
    try:
        cur.execute(
            "INSERT INTO members (member_id, username, password, approved) VALUES (?, ?, ?, 0)",
            (member_id, username, password)
        )
        conn.commit()
        await update.message.reply_text(f"✅ Member ကို စာရင်းသွင်းပြီးပါပြီ။\n🆔 ID: {member_id}\n👤 User: {username}\n(မှတ်ချက် - /approve ဖြင့် approval ပေးရန် လိုအပ်ပါသည်)")
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ ဒီ Username က ရှိပြီးသားဖြစ်နေပါသည်။")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 1:
        await update.message.reply_text("အသုံးပြုပုံ - /approve MEMBER_ID")
        return
    
    member_id = context.args
    cur.execute("UPDATE members SET approved=1 WHERE member_id=?", (member_id,))
    conn.commit()
    await update.message.reply_text(f"✅ {member_id} အား Login ဝင်ခွင့် ပြုလိုက်ပါပြီ (Approved)။")

async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    cur.execute("SELECT member_id, username, approved FROM members")
    rows = cur.fetchall()
    
    if not rows:
        await update.message.reply_text("အဖွဲ့ဝင် မရှိသေးပါ။")
        return
        
    msg = "👥 FCA Members List:\n\n"
    for row in rows:
        status = "Approved" if row == 1 else "Pending"
        msg += f"🆔 {row} | 👤 {row} | [{status}]\n"
    await update.message.reply_text(msg)

# အသစ်ထည့်ထားသော FUNCTION: /viewmember MEMBER_ID
async def viewmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 1:
        await update.message.reply_text("အသုံးပြုပုံ - /viewmember MEMBER_ID")
        return

    member_id = context.args
    cur.execute("SELECT * FROM profiles WHERE member_id=?", (member_id,))
    row = cur.fetchone()

    if not row:
        await update.message.reply_text(f"❌ {member_id} ၏ Profile စာရင်း မရှိသေးပါ။")
        return

    status = "Confirmed" if row == 1 else "Waiting Confirm"
    msg = f"📋 Member Profile ({member_id})\nStatus: {status}\n\n" \
          f"👤 အမည်: {row}\n👨 အဖအမည်: {row}\n👩 အမိအမည်: {row}\n" \
          f"🪪 မှတ်ပုံတင်: {row}\n📞 ဖုန်း: {row}\n🏠 လိပ်စာ: {row}\n" \
          f"💼 ရာထူး: {row}\n📅 ဝင်ရောက်သည့်ရက်: {row}"

    if row:
        await update.message.reply_photo(photo=row, caption=msg)
    else:
        await update.message.reply_text(msg)

# အသစ်ထည့်ထားသော FUNCTION: /confirm MEMBER_ID
async def confirm_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 1:
        await update.message.reply_text("အသုံးပြုပုံ - /confirm MEMBER_ID")
        return

    member_id = context.args
    cur.execute("UPDATE profiles SET confirmed=1 WHERE member_id=?", (member_id,))
    conn.commit()
    
    # သက်ဆိုင်ရာ Member ရဲ့ Telegram ID ကိုရှာပြီး အကြောင်းကြားစာပို့ပေးခြင်း
    cur.execute("SELECT telegram_id FROM members WHERE member_id=?", (member_id,))
    user_row = cur.fetchone()
    if user_row and user_row:
        try:
            await context.bot.send_message(chat_id=user_row, text="🎉 သင်၏ Profile ကို Admin မှ အတည်ပြု (Confirm) ပေးလိုက်ပါပြီ။")
        except Exception:
            pass

    await update.message.reply_text(f"✅ {member_id} ၏ Profile ကို Confirm လုပ်ပြီးပါပြီ။")

# အသစ်ထည့်ထားသော FUNCTION: /broadcast စာသား
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("အသုံးပြုပုံ - /broadcast သင်ပြောချင်သောစာသား")
        return

    text_to_send = "📢 **FCA Admin အသိပေးချက်**\n\n" + " ".join(context.args)
    cur.execute("SELECT telegram_id FROM members WHERE telegram_id IS NOT NULL")
    users = cur.fetchall()

    success_count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=text_to_send, parse_mode="Markdown")
            success_count += 1
        except Exception:
            continue

    await update.message.reply_text(f"📢 Broadcast ပြီးပါပြီ။ အဖွဲ့ဝင် {success_count} ဦးထံ ပေးပို့အောင်မြင်သည်။")

async def setfund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 1:
        await update.message.reply_text("/setfund amount")
        return

    amount = context.args
    cur.execute("INSERT OR REPLACE INTO settings VALUES('fund',?)", (amount,))
    conn.commit()
    await update.message.reply_text(f"✅ Fund Updated\n{amount} MMK")

async def deletemember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) != 1:
        await update.message.reply_text("/deletemember MEMBER_ID")
        return

    member_id = context.args
    cur.execute("DELETE FROM members WHERE member_id=?", (member_id,))
    cur.execute("DELETE FROM profiles WHERE member_id=?", (member_id,))
    conn.commit()
    await update.message.reply_text("🗑 Member Deleted")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT COUNT(*) FROM members")
    members_count = cur.fetchone()

    cur.execute("SELECT value FROM settings WHERE key='fund'")
    row = cur.fetchone()
    fund_amount = row if row else "0"

    await update.message.reply_text(f"📊 FCA Statistics\n\n👥 Members : {members_count}\n💰 Fund : {fund_amount} MMK")

# =========================
# APPLICATION SETUP
# =========================
def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing in .env file")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Register Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("myprofile", myprofile))
    app.add_handler(CommandHandler("fund", fund))
    
    # Admin Handlers
    app.add_handler(CommandHandler("addmember", addmember))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("viewmember", viewmember))     # <--- ဖြည့်စွက်ချက်
    app.add_handler(CommandHandler("confirm", confirm_profile))   # <--- ဖြည့်စွက်ချက်
    app.add_handler(CommandHandler("broadcast", broadcast))       # <--- ဖြည့်စွက်ချက်
    app.add_handler(CommandHandler("setfund", setfund))
    app.add_handler(CommandHandler("deletemember", deletemember))
    app.add_handler(CommandHandler("stats", stats))

    # Message Handlers
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
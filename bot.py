import os
import sqlite3
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7242601708

# Session and Progress trackers
user_sessions = {}
user_profile_progress = {}
user_profile_data = {}

# Profile fields (မြန်မာဘာသာ label တွေ)
profile_steps = [
    "အမည်",
    "ဖခင်အမည်",
    "မိခင်အမည်",
    "မှတ်ပုံတင်အမှတ်",
    "ဖုန်းနံပါတ်",
    "လက်ရှိနေရပ်လိပ်စာ",
    "အမြဲတမ်းနေရပ်လိပ်စာ",
    "အလုပ်အကိုင်",
    "ဌာန",
    "ရာထူး",
    "FCA စတင်ဝင်ရောက်သည့်ရက်စွဲ",
    "အကျိုးခံစားခွင့်ရှိသူ အမည်",
    "တော်စပ်ပုံ (ဆက်သွယ်မှု)",
    "အကျိုးခံစားခွင့်ရှိသူ ဖုန်းနံပါတ်",
    "အကျိုးခံစားခွင့်ရှိသူ လိပ်စာ"
]

# ─── Database Setup ───────────────────────────────────────────
conn = sqlite3.connect("fca.db", check_same_thread=False)
cur = conn.cursor()

# Members table
cur.execute("""
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id TEXT UNIQUE,
    username TEXT UNIQUE,
    password TEXT,
    telegram_id INTEGER,
    approved INTEGER DEFAULT 0
)
""")

# Profiles table (proper columns)
cur.execute("""
CREATE TABLE IF NOT EXISTS profiles (
    member_id TEXT PRIMARY KEY,
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
    created_at TEXT DEFAULT (datetime('now','localtime'))
)
""")
conn.commit()


# ─── Helper Functions ─────────────────────────────────────────
def is_admin(user_id):
    return user_id == ADMIN_ID


def generate_member_id():
    cur.execute("SELECT COUNT(*) FROM members")
    count = cur.fetchone()[0] + 1          # ✅ Bug 1 fix
    return f"FCA-{count:04d}"


# ─── /start ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            "🔐 FCA Admin Panel\n\n"
            "/addmember username password — Member ဖန်တီးရန်\n"
            "/approve FCA-0001 — Member Approve လုပ်ရန်\n"
            "/members — Member စာရင်းကြည့်ရန်"
        )
    else:
        await update.message.reply_text(
            "🏢 FCA Membership Bot မှ ကြိုဆိုပါတယ်။\n\n"
            "/login username password ဖြင့် Login ဝင်ပါ။"
        )


# ─── /addmember ──────────────────────────────────────────────
async def addmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin သာ အသုံးပြုနိုင်သည်")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "အသုံးပြုပုံ:\n/addmember username password"
        )
        return

    username = context.args[0]             # ✅ Bug 2 fix
    password = context.args[1]             # ✅ Bug 2 fix
    member_id = generate_member_id()

    try:
        cur.execute(
            "INSERT INTO members (member_id, username, password, telegram_id) VALUES (?, ?, ?, ?)",
            (member_id, username, password, 0)
        )
        conn.commit()
        await update.message.reply_text(
            f"✅ Member ဖန်တီးပြီးပါပြီ\n\n"
            f"🆔 ID: {member_id}\n"
            f"👤 Username: {username}\n"
            f"🔑 Password: {password}\n\n"
            f"⏳ Approve လုပ်ရန်: /approve {member_id}"
        )
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"❌ '{username}' သည် ရှိပြီးသား Username ဖြစ်သည်")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /approve ────────────────────────────────────────────────
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin သာ အသုံးပြုနိုင်သည်")
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "အသုံးပြုပုံ:\n/approve FCA-0001"
        )
        return

    member_id = context.args[0]            # ✅ Bug 3 fix

    # Member ရှိမရှိ စစ်ဆေး
    cur.execute("SELECT member_id FROM members WHERE member_id=?", (member_id,))
    found = cur.fetchone()

    if not found:
        await update.message.reply_text(f"❌ {member_id} မတွေ့ပါ")
        return

    cur.execute("UPDATE members SET approved=1 WHERE member_id=?", (member_id,))
    conn.commit()

    await update.message.reply_text(f"✅ {member_id} ကို Approve လုပ်ပြီးပါပြီ")


# ─── /members ────────────────────────────────────────────────
async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin သာ အသုံးပြုနိုင်သည်")
        return

    cur.execute("SELECT member_id, username, approved FROM members")
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Member မရှိသေးပါ")
        return

    text = "📋 Member List\n\n"
    for row in rows:
        status = "✅" if row[2] == 1 else "⏳"   # ✅ Bug 4 fix
        text += f"{row[0]} | {row[1]} | {status}\n"

    await update.message.reply_text(text)


# ─── /login ──────────────────────────────────────────────────
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "အသုံးပြုပုံ:\n/login username password"
        )
        return

    username = context.args[0]
    password = context.args[1]

    cur.execute(
        "SELECT member_id, approved FROM members WHERE username=? AND password=?",
        (username, password)
    )
    data = cur.fetchone()

    if not data:
        await update.message.reply_text("❌ Username သို့ Password မှားနေပါသည်")
        return

    member_id, approved = data

    if approved == 0:
        await update.message.reply_text(
            "⏳ Admin approval မရသေးပါ\n"
            "Admin မှ Approve ပြီးမှ Login ဝင်နိုင်မည်"
        )
        return

    user_sessions[update.effective_user.id] = member_id

    await update.message.reply_text(
        f"✅ Login အောင်မြင်ပါသည်\n\n"
        f"🆔 Member ID: {member_id}\n\n"
        f"Profile ဖြည့်ရန် /profile နှိပ်ပါ"
    )


# ─── /profile ────────────────────────────────────────────────
async def start_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_sessions:
        await update.message.reply_text("❌ အရင်ဆုံး /login ဝင်ပါ")
        return

    user_profile_progress[user_id] = 0
    user_profile_data[user_id] = {}

    await update.message.reply_text(
        f"📋 Profile Registration စတင်သည်\n"
        f"မေးခွန်း {len(profile_steps)} ခု ဖြေရမည်\n\n"
        f"1️⃣ {profile_steps[0]} ကို ရိုက်ထည့်ပေးပါ"   # ✅ Bug 5 fix
    )


# ─── Profile Message Handler ──────────────────────────────────
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_profile_progress:
        return

    step = user_profile_progress[user_id]
    current_field = profile_steps[step]

    # လက်ရှိ field သိမ်း
    user_profile_data[user_id][current_field] = update.message.text
    user_profile_progress[user_id] += 1

    # အားလုံးပြည့်ပြီ
    if user_profile_progress[user_id] >= len(profile_steps):
        member_id = user_sessions.get(user_id)
        d = user_profile_data[user_id]

        try:
            # ✅ Bug 6 fix — DB ထဲ သိမ်းသည်
            cur.execute("""
                INSERT OR REPLACE INTO profiles (
                    member_id, full_name, father_name, mother_name,
                    nrc, phone, current_address, permanent_address,
                    occupation, department, position, join_date,
                    beneficiary_name, beneficiary_relationship,
                    beneficiary_phone, beneficiary_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member_id,
                d.get("အမည်", ""),
                d.get("ဖခင်အမည်", ""),
                d.get("မိခင်အမည်", ""),
                d.get("မှတ်ပုံတင်အမှတ်", ""),
                d.get("ဖုန်းနံပါတ်", ""),
                d.get("လက်ရှိနေရပ်လိပ်စာ", ""),
                d.get("အမြဲတမ်းနေရပ်လိပ်စာ", ""),
                d.get("အလုပ်အကိုင်", ""),
                d.get("ဌာန", ""),
                d.get("ရာထူး", ""),
                d.get("FCA စတင်ဝင်ရောက်သည့်ရက်စွဲ", ""),
                d.get("အကျိုးခံစားခွင့်ရှိသူ အမည်", ""),
                d.get("တော်စပ်ပုံ (ဆက်သွယ်မှု)", ""),
                d.get("အကျိုးခံစားခွင့်ရှိသူ ဖုန်းနံပါတ်", ""),
                d.get("အကျိုးခံစားခွင့်ရှိသူ လိပ်စာ", "")
            ))
            conn.commit()

            await update.message.reply_text(
                "✅ Profile Registration ပြီးဆုံးပါပြီ\n\n"
                f"🆔 Member ID: {member_id}\n"
                f"👤 အမည်: {d.get('အမည်', '')}\n"
                f"📞 ဖုန်း: {d.get('ဖုန်းနံပါတ်', '')}\n\n"
                "ကျေးဇူးတင်ပါသည် 🙏"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ သိမ်းဆည်းရာတွင် Error ဖြစ်ပါသည်: {e}")

        # Memory clear
        del user_profile_progress[user_id]
        del user_profile_data[user_id]
        return

    # နောက် question မေးသည်
    next_step = user_profile_progress[user_id]
    next_field = profile_steps[next_step]
    await update.message.reply_text(
        f"{next_step + 1}️⃣ {next_field} ကို ရိုက်ထည့်ပေးပါ"
    )


# ─── Main ─────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addmember", addmember))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("profile", start_profile))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler)
    )

    print("FCA Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
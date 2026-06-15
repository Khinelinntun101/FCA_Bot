import os
import sqlite3
import bcrypt
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    PicklePersistence
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "20061027")

# States for ConversationHandler
LOGIN_USERNAME, LOGIN_PASSWORD = range(2)
PROFILE_PHOTO, PROFILE_INPUT = range(2, 4)
ADMIN_ADD_USERNAME, ADMIN_ADD_PASSWORD, ADMIN_SET_FUND, ADMIN_BROADCAST = range(4, 8)

PROFILE_STEPS = [
    "အမည်", "ဖခင်အမည်", "မိခင်အမည်", "မှတ်ပုံတင်အမှတ်", "ဖုန်းနံပါတ်",
    "လက်ရှိနေရပ်လိပ်စာ", "အမြဲတမ်းနေရပ်လိပ်စာ", "အလုပ်အကိုင်", "ဌာန", "ရာထူး",
    "FCA စတင်ဝင်ရောက်သည့်ရက်စွဲ", "အမွေစားအမွေခံသူ အမည်", "တော်စပ်ပုံ",
    "အမွေစားအမွေခံသူ ဖုန်းနံပါတ်", "အမွေစားအမွေခံသူ လိပ်စာ"
]

# ── Database Setup ──────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("fca.db", check_same_thread=False)
    cur = conn.cursor()
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        member_id TEXT PRIMARY KEY,
        full_name TEXT, father_name TEXT, mother_name TEXT,
        nrc TEXT, phone TEXT, current_address TEXT, permanent_address TEXT,
        occupation TEXT, department TEXT, position TEXT, join_date TEXT,
        beneficiary_name TEXT, beneficiary_relationship TEXT,
        beneficiary_phone TEXT, beneficiary_address TEXT,
        photo_file_id TEXT, confirmed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS fund (id INTEGER PRIMARY KEY, total_amount REAL DEFAULT 0)")
    cur.execute("INSERT OR IGNORE INTO fund (id, total_amount) VALUES (1, 0)")
    
    # Admin setup
    cur.execute("SELECT member_id FROM members WHERE username='admin'")
    if not cur.fetchone():
        hashed_admin_pwd = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO members (member_id, username, password, telegram_id, approved) VALUES ('FCA-ADMIN', 'admin', ?, ?, 1)", (hashed_admin_pwd, ADMIN_ID))
    
    conn.commit()
    return conn

conn = init_db()
cur = conn.cursor()

# ── Keyboards ────────────────────────────────────────────────
def get_main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("👤 My Profile", callback_data="view_my_profile"), InlineKeyboardButton("📝 Edit Profile", callback_data="start_profile")],
        [InlineKeyboardButton("💰 Fund Status", callback_data="view_fund"), InlineKeyboardButton("👥 Members List", callback_data="view_members_list")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Add Member", callback_data="admin_add_member"), InlineKeyboardButton("⏳ Pending", callback_data="admin_pending")],
        [InlineKeyboardButton("📊 Manage Fund", callback_data="admin_fund"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ── Handlers ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if "member_id" not in context.user_data:
        keyboard = [[InlineKeyboardButton("🔑 Login", callback_data="login_start")]]
        await update.message.reply_text(
            "🏢 *FCA Membership System* မှ ကြိုဆိုပါတယ်။\n\nကျေးဇူးပြု၍ အောက်ပါခလုတ်ကိုနှိပ်ပြီး Login ဝင်ပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        member_id = context.user_data["member_id"]
        await update.message.reply_text(
            f"👋 မင်္ဂလာပါ *{member_id}*!\n\nသင်လုပ်ဆောင်လိုသည်ကို ရွေးချယ်ပါ။",
            reply_markup=get_main_menu(is_admin),
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if query.data == "main_menu":
        await query.edit_message_text(f"👋 မင်္ဂလာပါ!\nသင်လုပ်ဆောင်လိုသည်ကို ရွေးချယ်ပါ။", reply_markup=get_main_menu(is_admin))
    
    elif query.data == "admin_panel":
        if not is_admin: return
        await query.edit_message_text("🔐 *Admin Control Panel*\n\nလုပ်ဆောင်ချက်တစ်ခုကို ရွေးချယ်ပါ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
    
    elif query.data == "view_fund":
        cur.execute("SELECT total_amount FROM fund WHERE id=1")
        amount = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM members WHERE approved=1 AND member_id != 'FCA-ADMIN'")
        count = cur.fetchone()[0]
        text = f"💰 *FCA ရန်ပုံငွေ အခြေအနေ*\n\n💵 စုစုပေါင်း: {amount:,.0f} ကျပ်\n👥 အဖွဲ့ဝင်ဦးရေ: {count} ယောက်"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]), parse_mode="Markdown")

    elif query.data == "view_members_list":
        cur.execute("SELECT member_id, username, approved FROM members WHERE member_id != 'FCA-ADMIN' LIMIT 20")
        rows = cur.fetchall()
        if not rows:
            text = "📋 Member မရှိသေးပါ။"
        else:
            text = "📋 *Member List (Top 20)*\n\n"
            for r in rows:
                status = "✅" if r[2] == 1 else "⏳"
                text += f"{status} `{r[0]}` | {r[1]}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]), parse_mode="Markdown")

    elif query.data == "view_my_profile":
        member_id = context.user_data.get("member_id")
        if not member_id: return
        cur.execute("SELECT * FROM profiles WHERE member_id=?", (member_id,))
        p = cur.fetchone()
        if not p:
            await query.edit_message_text("❌ Profile မဖြည့်ရသေးပါ။", reply_markup=get_main_menu(is_admin))
            return
        
        text = (
            f"👤 *FCA MEMBER PROFILE*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 *ID:* `{member_id}`\n"
            f"👤 *အမည်:* {p[1]}\n"
            f"👨‍💼 *ဖခင်:* {p[2]}\n"
            f"👩‍💼 *မိခင်:* {p[3]}\n"
            f"🆔 *NRC:* `{p[4]}`\n"
            f"📞 *ဖုန်း:* `{p[5]}`\n"
            f"🏠 *နေရပ်:* {p[6]}\n"
            f"💼 *ရာထူး:* {p[10]} ({p[9]})\n"
            f"📅 *ဝင်ရောက်သည့်နေ့:* {p[11]}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🤝 *အမွေစားအမွေခံ:* {p[12]}\n"
            f"📞 *ဆက်သွယ်ရန်:* `{p[14]}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ *အခြေအနေ:* {'အတည်ပြုပြီး' if p[17] == 1 else 'စစ်ဆေးဆဲ'}"
        )
        
        if p[16]: # photo_file_id
            await query.message.reply_photo(p[16], caption=text, parse_mode="Markdown", reply_markup=get_main_menu(is_admin))
            await query.message.delete()
        else:
            await query.edit_message_text(text, reply_markup=get_main_menu(is_admin), parse_mode="Markdown")

    elif query.data == "admin_add_member":
        await query.edit_message_text("👤 အသစ်ထည့်မည့် Member ၏ *Username* ကို ရိုက်ထည့်ပါ။", parse_mode="Markdown")
        return ADMIN_ADD_USERNAME

    elif query.data == "admin_fund":
        await query.edit_message_text("💰 သတ်မှတ်လိုသော *ရန်ပုံငွေ ပမာဏ* ကို ရိုက်ထည့်ပါ။", parse_mode="Markdown")
        return ADMIN_SET_FUND

    elif query.data == "admin_broadcast":
        await query.edit_message_text("📢 အဖွဲ့ဝင်အားလုံးကို ပို့လိုသော *စာသား* ကို ရိုက်ထည့်ပါ။", parse_mode="Markdown")
        return ADMIN_BROADCAST

    elif query.data == "admin_pending":
        cur.execute("SELECT member_id, username FROM members WHERE approved=0")
        rows = cur.fetchall()
        if not rows:
            await query.edit_message_text("⏳ Pending Member မရှိပါ။", reply_markup=get_admin_menu())
        else:
            text = "⏳ *Pending Approvals*\n\n"
            keyboard = []
            for r in rows:
                keyboard.append([InlineKeyboardButton(f"✅ Approve {r[1]} ({r[0]})", callback_data=f"approve_{r[0]}")])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("approve_"):
        mid = query.data.split("_")[1]
        cur.execute("UPDATE members SET approved=1 WHERE member_id=?", (mid,))
        conn.commit()
        await query.edit_message_text(f"✅ {mid} ကို Approve လုပ်ပြီးပါပြီ။", reply_markup=get_admin_menu())

# ── Conversations ───────────────────────────────────────────
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👤 ကျေးဇူးပြု၍ သင်၏ *Username* ကို ရိုက်ထည့်ပေးပါ။", parse_mode="Markdown")
    return LOGIN_USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_user"] = update.message.text
    await update.message.reply_text("🔑 ကျေးဇူးပြု၍ *Password* ကို ရိုက်ထည့်ပေးပါ။", parse_mode="Markdown")
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("login_user")
    password = update.message.text
    cur.execute("SELECT member_id, password, approved FROM members WHERE username=?", (username,))
    row = cur.fetchone()
    if row and bcrypt.checkpw(password.encode('utf-8'), row[1].encode('utf-8')):
        if row[2] == 0:
            await update.message.reply_text("⏳ သင်၏အကောင့်မှာ အတည်ပြုရန် စောင့်ဆိုင်းနေဆဲ ဖြစ်သည်။")
            return ConversationHandler.END
        context.user_data["member_id"] = row[0]
        cur.execute("UPDATE members SET telegram_id=? WHERE member_id=?", (update.effective_user.id, row[0]))
        conn.commit()
        await update.message.reply_text(f"✅ Login အောင်မြင်ပါသည်။\n🆔 ID: {row[0]}", reply_markup=get_main_menu(update.effective_user.id == ADMIN_ID))
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်။ /start ဖြင့် ပြန်စပါ။")
        return ConversationHandler.END

# ── Profile Flow ────────────────────────────────────────────
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    member_id = context.user_data.get("member_id")
    cur.execute("SELECT confirmed FROM profiles WHERE member_id=?", (member_id,))
    row = cur.fetchone()
    if row and row[0] == 1:
        await query.edit_message_text("✅ သင်၏ Profile မှာ အတည်ပြုပြီးဖြစ်၍ ပြင်ဆင်၍မရတော့ပါ။")
        return ConversationHandler.END
    
    await query.edit_message_text("📸 အရင်ဆုံး သင်၏ *Selfie ဓာတ်ပုံ* ပို့ပေးပါ။", parse_mode="Markdown")
    context.user_data["profile_step"] = 0
    context.user_data["profile_temp"] = {}
    return PROFILE_PHOTO

async def profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profile_temp"]["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text(f"1️⃣ {PROFILE_STEPS[0]} ကို ရိုက်ထည့်ပါ။")
    return PROFILE_INPUT

async def profile_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("profile_step", 0)
    context.user_data["profile_temp"][PROFILE_STEPS[step]] = update.message.text
    
    if step + 1 < len(PROFILE_STEPS):
        context.user_data["profile_step"] = step + 1
        await update.message.reply_text(f"{step + 2}️⃣ {PROFILE_STEPS[step+1]} ကို ရိုက်ထည့်ပါ။")
        return PROFILE_INPUT
    else:
        # Save to DB
        d = context.user_data["profile_temp"]
        mid = context.user_data["member_id"]
        cur.execute("""
            INSERT OR REPLACE INTO profiles (member_id, full_name, father_name, mother_name, nrc, phone, current_address, permanent_address, occupation, department, position, join_date, beneficiary_name, beneficiary_relationship, beneficiary_phone, beneficiary_address, photo_file_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (mid, d[PROFILE_STEPS[0]], d[PROFILE_STEPS[1]], d[PROFILE_STEPS[2]], d[PROFILE_STEPS[3]], d[PROFILE_STEPS[4]], d[PROFILE_STEPS[5]], d[PROFILE_STEPS[6]], d[PROFILE_STEPS[7]], d[PROFILE_STEPS[8]], d[PROFILE_STEPS[9]], d[PROFILE_STEPS[10]], d[PROFILE_STEPS[11]], d[PROFILE_STEPS[12]], d[PROFILE_STEPS[13]], d[PROFILE_STEPS[14]], d["photo"]))
        conn.commit()
        await update.message.reply_text("🎉 Profile ဖြည့်သွင်းမှု အောင်မြင်ပါသည်။ Admin အတည်ပြုချက်ကို စောင့်ပါ။", reply_markup=get_main_menu(update.effective_user.id == ADMIN_ID))
        return ConversationHandler.END

# ── Main ─────────────────────────────────────────────────────
def main():
    persistence = PicklePersistence(filepath="fca_bot_data")
    app = Application.builder().token(TOKEN).persistence(persistence).build()

    # Conversation Handlers
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern="^login_start$")],
        states={
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )

    profile_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profile_start, pattern="^start_profile$")],
        states={
            PROFILE_PHOTO: [MessageHandler(filters.PHOTO, profile_photo)],
            PROFILE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_input)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )

    admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern="^admin_add_member$"),
            CallbackQueryHandler(button_handler, pattern="^admin_fund$"),
            CallbackQueryHandler(button_handler, pattern="^admin_broadcast$"),
        ],
        states={
            ADMIN_ADD_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_username)],
            ADMIN_ADD_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_password)],
            ADMIN_SET_FUND: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_fund)],
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(profile_conv)
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("FCA Pro Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

# ── Admin Handlers ──────────────────────────────────────────
async def admin_add_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_temp_user"] = update.message.text
    await update.message.reply_text("🔑 အသစ်ထည့်မည့် Member ၏ *Password* ကို ရိုက်ထည့်ပါ။", parse_mode="Markdown")
    return ADMIN_ADD_PASSWORD

async def admin_add_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("admin_temp_user")
    password = update.message.text
    
    cur.execute("SELECT COUNT(*) FROM members WHERE member_id != 'FCA-ADMIN'")
    count = cur.fetchone()[0] + 1
    member_id = f"FCA-{count:04d}"
    hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        cur.execute("INSERT INTO members (member_id, username, password, telegram_id) VALUES (?, ?, ?, 0)", (member_id, username, hashed_pwd))
        conn.commit()
        await update.message.reply_text(f"✅ Member အသစ် ထည့်သွင်းပြီးပါပြီ။\n🆔 ID: `{member_id}`\n👤 User: `{username}`", parse_mode="Markdown", reply_markup=get_admin_menu())
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ Username ရှိပြီးသားဖြစ်နေပါသည်။ ပြန်စမ်းကြည့်ပါ။")
    return ConversationHandler.END

async def admin_set_fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        cur.execute("UPDATE fund SET total_amount=? WHERE id=1", (amount,))
        conn.commit()
        await update.message.reply_text(f"✅ ရန်ပုံငွေကို {amount:,.0f} ကျပ် သတ်မှတ်ပြီးပါပြီ။", reply_markup=get_admin_menu())
    except ValueError:
        await update.message.reply_text("❌ ဂဏန်းများသာ ရိုက်ထည့်ပါ။")
    return ConversationHandler.END

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📢 *FCA အသိပေးချက်*\n\n" + update.message.text
    cur.execute("SELECT telegram_id FROM members WHERE telegram_id != 0")
    rows = cur.fetchall()
    for r in rows:
        try:
            await context.bot.send_message(chat_id=r[0], text=text, parse_mode="Markdown")
        except: pass
    await update.message.reply_text("✅ အဖွဲ့ဝင်အားလုံးကို ပို့ပြီးပါပြီ။", reply_markup=get_admin_menu())
    return ConversationHandler.END
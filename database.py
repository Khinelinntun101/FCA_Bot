import sqlite3
from config import DATABASE_NAME


def db_connect():
    return sqlite3.connect(DATABASE_NAME)


def init_database():
    conn = db_connect()
    cur = conn.cursor()

    # Members
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


    # Payments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT,
        amount INTEGER,
        payment_method TEXT,
        provider TEXT,
        payment_month TEXT,
        payment_date TEXT,
        proof_photo_id TEXT,
        status TEXT DEFAULT 'PENDING',
        approved_by TEXT
    )
    """)


    # Funds
    cur.execute("""
    CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_type TEXT,
        amount INTEGER,
        description TEXT,
        created_at TEXT
    )
    """)


    # Admin Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        action TEXT,
        created_at TEXT
    )
    """)


    conn.commit()
    conn.close()



def get_member_by_telegram_id(telegram_id):

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM members WHERE telegram_id=?",
        (telegram_id,)
    )

    data = cur.fetchone()

    conn.close()

    return data



def get_member_by_member_id(member_id):

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM members WHERE member_id=?",
        (member_id,)
    )

    data = cur.fetchone()

    conn.close()

    return data



def get_member_by_search_keyword(keyword):

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
    SELECT member_id,name,phone,join_date,status
    FROM members
    WHERE name LIKE ?
    OR member_id LIKE ?
    OR phone LIKE ?
    """,
    (
        f"%{keyword}%",
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    data = cur.fetchall()

    conn.close()

    return data



def insert_member(member_data):

    conn = db_connect()
    cur = conn.cursor()

    try:

        cur.execute("""
        INSERT INTO members
        (
        member_id,
        telegram_id,
        name,
        phone,
        father_name,
        mother_name,
        nrc,
        address,
        job,
        department,
        join_date,
        profile_photo_id,
        referrer_id
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, member_data)

        conn.commit()

        return True


    except sqlite3.IntegrityError:

        return False


    finally:

        conn.close()



def get_referrer_count(referrer_id):

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM members WHERE referrer_id=?",
        (referrer_id,)
    )

    count = cur.fetchone()[0]

    conn.close()

    return count



def get_total_payments():

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT SUM(amount) FROM payments WHERE status='APPROVED'"
    )

    total = cur.fetchone()[0] or 0

    conn.close()

    return total



def get_total_funds_out():

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT SUM(amount) FROM funds WHERE fund_type='OUT'"
    )

    total = cur.fetchone()[0] or 0

    conn.close()

    return total



def insert_fund_transaction(
        fund_type,
        amount,
        description,
        created_at):

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO funds
    (fund_type,amount,description,created_at)
    VALUES (?,?,?,?)
    """,
    (
        fund_type,
        amount,
        description,
        created_at
    ))

    conn.commit()
    conn.close()



def get_all_members_for_export():

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
    member_id,
    name,
    phone,
    join_date,
    status
    FROM members
    """)

    rows = cur.fetchall()

    conn.close()

    return rows
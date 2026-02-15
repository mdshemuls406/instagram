#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot (Fixed Admin Commands)
Features:
- Fixed: Admin commands now work perfectly
- Time-Based Access (Days, Hours, Minutes)
- Auto-Expiry & Real-time Verification
- 20-Thread Chrome Engine with Proxy
"""

import os
import sys
import asyncio
import logging
import sqlite3
import subprocess
import time
import re
import uuid
import secrets
import string
import random
from datetime import datetime, timedelta
from pathlib import Path

# ============================================
# SECTION 1: DEPENDENCIES & CONFIG
# ============================================
def install_dependencies():
    required = ['pyrogram', 'tgcrypto', 'instaloader', 'pyotp', 'requests']
    for pkg in required:
        try: __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_dependencies()

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import instaloader
from instaloader import TwoFactorAuthRequiredException, BadCredentialsException
import pyotp

class Config:
    API_ID = 36021238
    API_HASH = "8f9bf7770e5b58b550030bcbaa0ec7d7"
    BOT_TOKEN = "8274795288:AAHDbqKWe1XpM4_xJppY9PED_1TtmAeCX1o"
    
    # আপনার অ্যাডমিন আইডি সঠিকভাবে চেক করুন
    ADMIN_ID = 6323050876
    
    CHANNEL_ID = -1003375283491
    CHANNEL_LINK = "https://t.me/Sheet_short_update"
    
    SESSION_NAME = "ig_premium_bot_fixed"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    MAX_THREADS = 20
    DB_FILE = "premium_users.db"

logging.basicConfig(level=logging.ERROR)

# ============================================
# SECTION 2: DATABASE & TIME LOGIC
# ============================================
def init_db():
    conn = sqlite3.connect(Config.DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS access_users 
                 (user_id INTEGER PRIMARY KEY, expiry_time REAL)''')
    conn.commit()
    conn.close()

def set_access(user_id, seconds):
    expiry = time.time() + seconds
    conn = sqlite3.connect(Config.DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO access_users VALUES (?, ?)", (user_id, expiry))
    conn.commit()
    conn.close()

def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin"
    
    conn = sqlite3.connect(Config.DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry_time FROM access_users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False, "No Access"
        
    expiry_time = result[0]
    remaining = expiry_time - time.time()
    
    if remaining > 0:
        return True, format_remaining_time(remaining)
    else:
        remove_user(user_id)
        return False, "Expired"

def remove_user(user_id):
    conn = sqlite3.connect(Config.DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM access_users WHERE user_id=?", (user_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_all_users_info():
    conn = sqlite3.connect(Config.DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, expiry_time FROM access_users")
    data = c.fetchall()
    conn.close()
    return data

def format_remaining_time(seconds):
    if seconds < 0: return "Expired"
    td = timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "< 1m"

init_db()

# ============================================
# SECTION 3: PROXY & ENGINE
# ============================================
def load_proxies():
    p_file = Path("proxies.txt")
    if not p_file.exists(): return []
    proxies = []
    with open(p_file, "r") as f:
        for line in f:
            l = line.strip()
            if not l: continue
            if '@' in l or l.startswith('http'): proxies.append(f"http://{l}")
            elif len(l.split(':')) == 2: proxies.append(f"http://{l}")
            elif len(l.split(':')) == 4:
                p = l.split(':')
                proxies.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
    return proxies

PROXY_LIST = load_proxies()

def get_headers():
    return {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(120, 124)}.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
        'Sec-Fetch-Site': 'none',
        'Upgrade-Insecure-Requests': '1'
    }

def process_account(u, p, k):
    L = instaloader.Instaloader(quiet=True, user_agent=get_headers()['User-Agent'], max_connection_attempts=1)
    L.context._session.headers.update(get_headers())
    if PROXY_LIST:
        prx = random.choice(PROXY_LIST)
        L.context._session.proxies = {"http": prx, "https": prx}

    try:
        k = str(k).replace(" ", "").strip().upper()
        try:
            time.sleep(random.uniform(1.5, 3.5))
            L.login(u, p)
        except TwoFactorAuthRequiredException:
            try: L.two_factor_login(pyotp.TOTP(k).now())
            except: return False, "2FA_FAIL"
        except BadCredentialsException: return False, "BAD_PASS"
        except: return False, "ERROR"
        
        try: L.context._session.get("https://www.instagram.com/")
        except: pass
        
        cookies = L.context._session.cookies.get_dict()
        cookies.update({'ig_did': str(uuid.uuid4()).upper(), 'datr': secrets.token_hex(12)})
        parts = []
        prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid']
        for key in prio:
            if key in cookies: parts.append(f"{key}={cookies[key]}")
        for k,v in cookies.items():
            if k not in prio: parts.append(f"{k}={v}")
        return True, f"{u}|{p}|{'; '.join(parts)}"
    except: return False, "UNKNOWN"

# ============================================
# SECTION 4: BOT COMMANDS (PRIORITY FIXED)
# ============================================
app = Client(Config.SESSION_NAME, api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

async def check_permissions(client, user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin"
    has_access, expiry = check_access(user_id)
    if not has_access: return False, "expired"
    try:
        await client.get_chat_member(Config.CHANNEL_ID, user_id)
        return True, expiry
    except: return False, "not_joined"

# --- 1. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    # Debug Message for Admin Check
    if user_id == Config.ADMIN_ID:
        admin_status = "👑 **Admin Detected**"
    else:
        admin_status = f"👤 User ID: `{user_id}`"

    is_valid, status = await check_permissions(client, user_id)
    global PROXY_LIST
    PROXY_LIST = load_proxies()
    
    if is_valid:
        expiry_text = "♾️ Unlimited (Admin)" if status == "Admin" else f"⏳ Expires in: `{status}`"
        await message.reply_text(
            f"💠 **PREMIUM IG TOOL** 💠\n\n"
            f"👋 Hello, **{message.from_user.first_name}**\n"
            f"{admin_status}\n"
            f"🛡️ **Status:** `Active` ✅\n"
            f"{expiry_text}\n"
            f"🌐 **Proxies:** `{len(PROXY_LIST)}` Connected\n\n"
            f"📝 **To Use:** Send account list below.\n"
            f"`User` `Pass` `Key`"
        )
    elif status == "not_joined":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=Config.CHANNEL_LINK)]])
        await message.reply_text("🚫 **Join Channel First**", reply_markup=btn)
    else:
        await message.reply_text(f"🔒 **Access Denied**\nYour ID: `{user_id}`\nContact Admin.")

# --- 2. ADMIN COMMANDS (MUST BE ABOVE TEXT HANDLER) ---

@app.on_message(filters.command("access") & filters.user(Config.ADMIN_ID))
async def give_access(client, message):
    try:
        # Format: /access 12345 3days
        args = message.command
        if len(args) != 3:
            await message.reply_text("⚠️ **Format:** `/access ID Duration`\nEx: `/access 1234 3days`")
            return
        
        target_id = int(args[1])
        duration_str = args[2].lower()
        
        seconds = 0
        match = re.match(r"(\d+)([a-z]+)", duration_str)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if 'day' in unit: seconds = val * 86400
            elif 'hr' in unit or 'hour' in unit: seconds = val * 3600
            elif 'min' in unit: seconds = val * 60
            else: raise ValueError
        else: raise ValueError

        set_access(target_id, seconds)
        expiry_date = (datetime.now() + timedelta(seconds=seconds)).strftime("%d-%b %H:%M")
        
        await message.reply_text(f"✅ **Granted!**\nID: `{target_id}`\nTime: `{duration_str}`")
        try: await client.send_message(target_id, f"🎉 **Access Granted!**\nTime: {duration_str}")
        except: pass
        
    except Exception as e:
        await message.reply_text(f"❌ Error: Invalid Format or ID\nError: {e}")

@app.on_message(filters.command("ban") & filters.user(Config.ADMIN_ID))
async def ban_user(client, message):
    try:
        target_id = int(message.command[1])
        if remove_user(target_id):
            await message.reply_text(f"🚫 Banned `{target_id}`")
            try: await client.send_message(target_id, "🚫 **Access Revoked**")
            except: pass
        else:
            await message.reply_text("⚠️ ID not found.")
    except:
        await message.reply_text("❌ Use: `/ban 12345`")

@app.on_message(filters.command("users") & filters.user(Config.ADMIN_ID))
async def user_list(client, message):
    users = get_all_users_info()
    if not users:
        await message.reply_text("📂 No active users.")
        return
    text = f"👥 **Users ({len(users)})**\n\n"
    now = time.time()
    for uid, expiry in users:
        remaining = expiry - now
        if remaining > 0:
            text += f"🆔 `{uid}` | ⏳ `{format_remaining_time(remaining)}`\n"
        else:
            remove_user(uid)
    await message.reply_text(text)

@app.on_message(filters.command("id"))
async def get_my_id(client, message):
    await message.reply_text(f"🆔 Your ID: `{message.from_user.id}`")

# --- 3. TEXT HANDLER (MUST BE LAST) ---
@app.on_message(filters.text & filters.private)
async def handle_files(client, message):
    # Ignore any command that slipped through (Just in case)
    if message.text.startswith("/"): return
    
    user_id = message.from_user.id
    is_valid, status = await check_permissions(client, user_id)
    
    if not is_valid:
        if status == "not_joined":
            await message.reply_text("❌ **Join Channel First!**")
        else:
            await message.reply_text("⛔ **Access Expired**\nContact Admin.")
        return

    lines = [l for l in message.text.split('\n') if l.strip()]
    if not lines: return
    if not PROXY_LIST:
        await message.reply_text("⚠️ **Proxies Offline!** Contact Admin.")
        return

    msg = await message.reply_text(
        f"💎 **Job Started**\n📂 Accounts: `{len(lines)}`\n🚀 Status: `Initializing...`"
    )
    
    valid_results = []
    processed = 0
    total = len(lines)
    sem = asyncio.Semaphore(Config.MAX_THREADS)
    loop = asyncio.get_running_loop()
    last_update = time.time()

    async def worker(line):
        nonlocal processed, last_update
        async with sem:
            try:
                parts = line.strip().split(None, 2)
                if len(parts) >= 3:
                    u, p, k = parts[0], parts[1], parts[2]
                    ok, res = await loop.run_in_executor(None, process_account, u, p, k)
                    if ok: valid_results.append(res)
                processed += 1
                if time.time() - last_update > 2.5 or processed == total:
                    perc = int((processed/total)*10)
                    bar = "■" * perc + "□" * (10-perc)
                    try:
                        await msg.edit_text(
                            f"💎 **Running...**\n"
                            f"📊 `{bar}` {int((processed/total)*100)}%\n"
                            f"✅ Success: `{len(valid_results)}`\n"
                            f"🔄 Done: `{processed}/{total}`"
                        )
                        last_update = time.time()
                    except: pass
            except: processed += 1

    await asyncio.gather(*[worker(line) for line in lines])

    if valid_results:
        fname = f"Cookies_{datetime.now().strftime('%H%M')}.txt"
        with open(fname, "w") as f: f.write("\n".join(valid_results))
        await message.reply_document(fname, caption=f"✅ **Done**\n🍪 Valid: {len(valid_results)}")
        os.remove(fname)
    else:
        await msg.edit_text("❌ **Failed:** No valid accounts.")

if __name__ == "__main__":
    print("🔥 Fixed Bot Started...")
    app.run()

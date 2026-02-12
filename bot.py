#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot (GitHub Persistence Edition)
Features:
- Permanent Database on GitHub (No Data Loss on Restart)
- Multi-User Concurrency
- Admin Commands & Time Access
- 20-Thread Chrome Engine
"""

import os
import sys
import asyncio
import logging
import subprocess
import time
import re
import uuid
import secrets
import random
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path

# ============================================
# SECTION 1: DEPENDENCIES & CONFIG
# ============================================

def install_dependencies():
    required = ['pyrogram', 'tgcrypto', 'instaloader', 'pyotp', 'requests']
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_dependencies()

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from instaloader import TwoFactorAuthRequiredException, BadCredentialsException
import pyotp
import requests

class Config:
    API_ID = 36021238
    API_HASH = "8f9bf7770e5b58b550030bcbaa0ec7d7"
    BOT_TOKEN = "8274795288:AAHDbqKWe1XpM4_xJppY9PED_1TtmAeCX1o"
    
    # Admin ID
    ADMIN_ID = 6323050876
    
    CHANNEL_ID = -1003375283491
    CHANNEL_LINK = "https://t.me/Sheet_short_update"
    
    SESSION_NAME = "ig_premium_bot_github"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    MAX_THREADS = 20
    
    # ---------------------------------------------------------
    # GITHUB DATABASE CONFIGURATION (EDIT THIS CAREFULLY)
    # ---------------------------------------------------------
    # আপনার গিটহাব টোকেন এখানে দিন (Railway variables এ রাখাই ভালো)
    GITHUB_TOKEN = "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" 
    
    # আপনার রিপোসিটরি নাম (Username/RepoName)
    GITHUB_REPO = "mdshemuls406/instagram" 
    
    # ফাইলের নাম (এটা পরিবর্তন করার দরকার নেই)
    DB_FILENAME = "users_db.json"
    # ---------------------------------------------------------

logging.basicConfig(level=logging.ERROR)

# ============================================
# SECTION 2: GITHUB DATABASE LOGIC
# ============================================

class GitHubDB:
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{Config.GITHUB_REPO}/contents/{Config.DB_FILENAME}"
        self.headers = {
            "Authorization": f"token {Config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.local_cache = {}
        self.load_from_github()

    def load_from_github(self):
        """Load DB from GitHub on Startup"""
        try:
            r = requests.get(self.api_url, headers=self.headers)
            if r.status_code == 200:
                content = r.json().get("content", "")
                if content:
                    decoded = base64.b64decode(content).decode("utf-8")
                    self.local_cache = json.loads(decoded)
                    print("✅ Database loaded from GitHub.")
                else:
                    self.local_cache = {}
            else:
                print("⚠️ No database found on GitHub. Creating new one.")
                self.local_cache = {}
        except Exception as e:
            print(f"❌ Error loading DB: {e}")
            self.local_cache = {}

    def save_to_github(self):
        """Push Local Cache to GitHub"""
        try:
            # 1. Get current SHA (Required for update)
            r = requests.get(self.api_url, headers=self.headers)
            sha = r.json().get("sha") if r.status_code == 200 else None
            
            # 2. Prepare Payload
            json_str = json.dumps(self.local_cache, indent=2)
            b64_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
            
            data = {
                "message": "Update User DB",
                "content": b64_content
            }
            if sha:
                data["sha"] = sha
            
            # 3. Push Update
            requests.put(self.api_url, headers=self.headers, json=data)
            
        except Exception as e:
            print(f"❌ Failed to sync with GitHub: {e}")

    def set_access(self, user_id, seconds, limit):
        expiry = time.time() + seconds
        # Store as string key because JSON requires string keys
        self.local_cache[str(user_id)] = {
            "expiry": expiry,
            "limit": limit
        }
        # Push changes to GitHub
        self.save_to_github()

    def get_user(self, user_id):
        return self.local_cache.get(str(user_id))

    def remove_user(self, user_id):
        if str(user_id) in self.local_cache:
            del self.local_cache[str(user_id)]
            self.save_to_github()
            return True
        return False

    def get_all(self):
        return self.local_cache

# Initialize Database Instance
db = GitHubDB()

# --- Access Logic Wrappers ---

def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    
    user_data = db.get_user(user_id)
    
    if not user_data:
        return False, "No Access", 0
        
    expiry_time = user_data.get("expiry", 0)
    limit = user_data.get("limit", 100)
    
    remaining = expiry_time - time.time()
    
    if remaining > 0:
        return True, format_remaining_time(remaining), limit
    else:
        db.remove_user(user_id)
        return False, "Expired", 0

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
# SECTION 4: BOT COMMANDS
# ============================================

app = Client(Config.SESSION_NAME, api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

async def check_permissions(client, user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    
    has_access, expiry, limit = check_access(user_id)
    if not has_access: return False, "expired", 0
    
    try:
        await client.get_chat_member(Config.CHANNEL_ID, user_id)
        return True, expiry, limit
    except: return False, "not_joined", 0

# --- 1. START COMMAND ---

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    if user_id == Config.ADMIN_ID:
        admin_status = "👑 **Admin Detected**"
    else:
        admin_status = f"👤 User ID: `{user_id}`"

    is_valid, status, limit = await check_permissions(client, user_id)
    global PROXY_LIST
    PROXY_LIST = load_proxies()
    
    if is_valid:
        expiry_text = "♾️ Unlimited (Admin)" if status == "Admin" else f"⏳ Expires in: `{status}`"
        limit_text = "♾️ No Limit" if status == "Admin" else f"🔢 Account Limit: `{limit}`"
        
        await message.reply_text(
            f"💠 **PREMIUM IG TOOL** 💠\n\n"
            f"👋 Hello, **{message.from_user.first_name}**\n"
            f"{admin_status}\n"
            f"🛡️ **Status:** `Active` ✅\n"
            f"{expiry_text}\n"
            f"{limit_text}\n"
            f"🌐 **Proxies:** `{len(PROXY_LIST)}` Connected\n\n"
            f"📝 **To Use:** Send account list below.\n"
            f"`User` `Pass` `Key`"
        )
    elif status == "not_joined":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=Config.CHANNEL_LINK)]])
        await message.reply_text("🚫 **Join Channel First**", reply_markup=btn)
    else:
        await message.reply_text(f"🔒 **Access Denied**\nYour ID: `{user_id}`\nContact Admin.")

# --- 2. ADMIN COMMANDS (GITHUB SYNCED) ---

@app.on_message(filters.command("access") & filters.user(Config.ADMIN_ID))
async def give_access(client, message):
    try:
        args = message.command
        if len(args) != 4:
            await message.reply_text("⚠️ Format: `/access ID Time Limit`\nEx: `/access 1234 3days 1000`")
            return
        
        target_id = int(args[1])
        duration_str = args[2].lower()
        limit = int(args[3])
        
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

        # Saving to GitHub DB
        db.set_access(target_id, seconds, limit)
        
        await message.reply_text(f"✅ **Granted!**\nID: `{target_id}`\nTime: `{duration_str}`\nLimit: `{limit}`\n_Synced with GitHub_")
        try: await client.send_message(target_id, f"🎉 **Access Granted!**\nTime: {duration_str}\nLimit: {limit}")
        except: pass
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("ban") & filters.user(Config.ADMIN_ID))
async def ban_user(client, message):
    try:
        target_id = int(message.command[1])
        if db.remove_user(target_id):
            await message.reply_text(f"🚫 Banned {target_id}\n_Synced with GitHub_")
            try: await client.send_message(target_id, "🚫 Access Revoked")
            except: pass
        else:
            await message.reply_text("⚠️ ID not found.")
    except:
        await message.reply_text("❌ Use: /ban 12345")

@app.on_message(filters.command("users") & filters.user(Config.ADMIN_ID))
async def user_list(client, message):
    users = db.get_all()
    if not users:
        await message.reply_text("📂 No active users.")
        return
        
    text = f"👥 Users ({len(users)})\n\n"
    now = time.time()
    
    # Iterate through dict
    for uid, data in list(users.items()):
        expiry = data.get("expiry", 0)
        limit = data.get("limit", 100)
        remaining = expiry - now
        
        if remaining > 0:
            text += f"🆔 `{uid}` | ⏳ `{format_remaining_time(remaining)}` | 🔢 `{limit}`\n"
        else:
            db.remove_user(uid)
            
    await message.reply_text(text)

# --- 3. TEXT HANDLER ---

@app.on_message(filters.text & filters.private)
async def handle_files(client, message):
    if message.text.startswith("/"): return
    
    user_id = message.from_user.id
    is_valid, status, limit = await check_permissions(client, user_id)
    
    if not is_valid:
        if status == "not_joined":
            await message.reply_text("❌ **Join Channel First!**")
        else:
            await message.reply_text("⛔ **Access Expired**\nContact Admin.")
        return

    lines = [l for l in message.text.split('\n') if l.strip()]
    if not lines: return
    
    if len(lines) > limit:
        await message.reply_text(
            f"⛔ **Limit Exceeded!**\n"
            f"Allowed: `{limit}` accounts\n"
            f"You sent: `{len(lines)}` accounts"
        )
        return

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
    print("🔥 GitHub DB Bot Started...")
    app.run()

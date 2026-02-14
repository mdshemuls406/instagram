#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot V8 (Proxy Toggle Edition)
Features:
- Commands: /on proxies & /off proxies
- Dynamic Threading (20 for Proxy, 5 for Direct)
- GitHub Database Persistence
- Browser-Like Login & Solver
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
    
    SESSION_NAME = "ig_proxy_toggle_v8"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    
    # ---------------------------------------------
    # GITHUB CONFIG
    # ---------------------------------------------
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    GITHUB_REPO = "YourUsername/YourRepoName" 
    DB_FILENAME = "users_db.json"
    # ---------------------------------------------

    # DYNAMIC SETTINGS (DO NOT EDIT HERE)
    MAX_THREADS = 20
    USE_PROXY = True

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
                    print("✅ Database loaded from GitHub.")
                else:
                    self.local_cache = {}
            else:
                self.local_cache = {}
        except Exception as e:
            print(f"❌ Error loading DB: {e}")
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
        except Exception as e:
            print(f"❌ Sync Error: {e}")

    def set_access(self, user_id, seconds, limit):
        expiry = time.time() + seconds
        self.local_cache[str(user_id)] = {"expiry": expiry, "limit": limit}
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

db = GitHubDB()

# --- Access Logic ---
def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    user_data = db.get_user(user_id)
    if not user_data: return False, "No Access", 0
    
    expiry = user_data.get("expiry", 0)
    limit = user_data.get("limit", 100)
    remaining = expiry - time.time()
    
    if remaining > 0: return True, format_time(remaining), limit
    else:
        db.remove_user(user_id)
        return False, "Expired", 0

def format_time(seconds):
    td = timedelta(seconds=seconds)
    return f"{td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m"

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

def get_headers(mobile=False):
    if mobile:
        return {
            'User-Agent': 'Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Samsung; SM-G973F; beyond1; exynos9820; en_US; 314665256)',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-IG-App-ID': '936619743392459',
        }
    else:
        return {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(120, 125)}.0.0.0 Safari/537.36',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        }

# --- Login Logic ---
def process_account(line):
    parts = line.strip().split(None, 2)
    username = parts[0]
    password = parts[1]
    key = parts[2] if len(parts) > 2 else None

    L = instaloader.Instaloader(quiet=True, user_agent=get_headers()['User-Agent'], max_connection_attempts=1)
    L.context._session.headers.update(get_headers())
    
    # 🔴 DYNAMIC PROXY CHECK
    if Config.USE_PROXY and PROXY_LIST:
        prx = random.choice(PROXY_LIST)
        L.context._session.proxies = {"http": prx, "https": prx}

    try:
        time.sleep(random.uniform(2, 4))
        try:
            L.login(username, password)
        except TwoFactorAuthRequiredException:
            if key:
                try: L.two_factor_login(pyotp.TOTP(str(key).replace(" ", "").upper()).now())
                except: return False, f"{username}|{password}|2FA_KEY_INVALID"
            else: return False, f"{username}|{password}|NEEDS_2FA_CODE"
        except BadCredentialsException: return False, f"{username}|{password}|WRONG_PASS"
        except Exception: return False, f"{username}|{password}|ERROR"

        try: L.context._session.get("https://www.instagram.com/")
        except: pass
        
        cookies = L.context._session.cookies.get_dict()
        if 'sessionid' not in cookies: return False, f"{username}|{password}|NO_SESSION"

        cookies.update({'ig_did': str(uuid.uuid4()).upper(), 'datr': secrets.token_hex(12)})
        prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid']
        parts = [f"{k}={cookies[k]}" for k in prio if k in cookies]
        for k,v in cookies.items():
            if k not in prio: parts.append(f"{k}={v}")
            
        return True, f"{username}|{password}|{'; '.join(parts)}"
        
    except: return False, f"{username}|{password}|UNKNOWN_ERROR"

# --- Solver Logic ---
def solve_checkpoint_logic(line):
    try:
        parts = line.strip().split('|')
        u, p, c_str = parts[0], parts[1], parts[2]
        
        cookie_dict = {}
        for item in c_str.split(';'):
            if '=' in item: k, v = item.strip().split('=', 1); cookie_dict[k.strip()] = v.strip()

        L = instaloader.Instaloader(quiet=True, user_agent=get_headers(mobile=True)['User-Agent'])
        
        # 🔴 DYNAMIC PROXY CHECK
        if Config.USE_PROXY and PROXY_LIST:
            prx = random.choice(PROXY_LIST)
            L.context._session.proxies = {"http": prx, "https": prx}
            
        L.context._session.cookies.update(cookie_dict)
        
        try:
            resp = L.context._session.get("https://www.instagram.com/")
            if "accounts/login" in resp.url: return False, f"{u}|{p}|SESSION_EXPIRED"
            instaloader.Profile.from_username(L.context, u)
            
            new_cookies = L.context._session.cookies.get_dict()
            if 'sessionid' not in new_cookies:
                 if 'sessionid' in cookie_dict: new_cookies['sessionid'] = cookie_dict['sessionid']
                 else: return False, f"{u}|{p}|REVOKED"

            prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid']
            parts = [f"{k}={new_cookies[k]}" for k in prio if k in new_cookies]
            for k,v in new_cookies.items():
                if k not in prio: parts.append(f"{k}={v}")
                
            return True, f"{u}|{p}|{'; '.join(parts)}"
        except: return False, f"{u}|{p}|LOCKED"
    except: return False, "ERROR"

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

# --- PROXY TOGGLE COMMANDS (NEW) ---

@app.on_message(filters.command(["on", "off"]) & filters.user(Config.ADMIN_ID))
async def toggle_proxy(client, message):
    cmd = message.command[0] # on or off
    target = message.command[1] if len(message.command) > 1 else ""
    
    if target.lower() == "proxies":
        if cmd == "on":
            Config.USE_PROXY = True
            Config.MAX_THREADS = 20
            await message.reply_text("🟢 **Proxies Enabled!**\n🚀 Threads increased to 20.")
        else:
            Config.USE_PROXY = False
            Config.MAX_THREADS = 5
            await message.reply_text("🔴 **Proxies Disabled!**\n⚠️ Threads reduced to 5 (Direct IP Mode).")
    else:
        await message.reply_text("Usage: `/on proxies` or `/off proxies`")

# --- ADMIN COMMANDS ---

@app.on_message(filters.command("access") & filters.user(Config.ADMIN_ID))
async def give_access(c, m):
    try:
        a = m.command; t, d, l = int(a[1]), a[2].lower(), int(a[3])
        sec = int(re.match(r"(\d+)", d).group(1)) * (86400 if 'd' in d else 3600 if 'h' in d else 60)
        db.set_access(t, sec, l)
        await m.reply_text(f"✅ Access: `{t}` | Limit: `{l}` | GitHub Synced")
    except: await m.reply_text("❌ Usage: `/access ID 3days 1000`")

@app.on_message(filters.command("ban") & filters.user(Config.ADMIN_ID))
async def ban(c, m):
    try: 
        db.remove_user(int(m.command[1]))
        await m.reply_text("🚫 Banned & Synced")
    except: pass

@app.on_message(filters.command("users") & filters.user(Config.ADMIN_ID))
async def ulist(c, m):
    u = db.get_all()
    txt = "\n".join([f"`{k}` ⏳ {format_time(v['expiry']-time.time())}" for k,v in u.items() if v['expiry']>time.time()])
    await m.reply_text(f"👥 Users:\n{txt}" if txt else "Empty")

# --- START & HANDLERS ---

@app.on_message(filters.command("start"))
async def start(c, m):
    u = m.from_user.id
    ok, st, lim = await check_permissions(c, u)
    global PROXY_LIST; PROXY_LIST = load_proxies()
    
    proxy_status = "✅ ON (20 Threads)" if Config.USE_PROXY else "❌ OFF (5 Threads)"
    
    if ok:
        await m.reply_text(
            f"💠 **IG PREMIUM BOT V8** 💠\n\n"
            f"👋 User: **{m.from_user.first_name}**\n"
            f"🛡️ Status: `{st}`\n"
            f"🔢 Limit: `{lim}`\n"
            f"🌐 Proxies: `{proxy_status}`\n\n"
            f"🛠️ **Commands:**\n"
            f"1️⃣ Login: `User Pass` or `User Pass Key`\n"
            f"2️⃣ Solve: `/solve`"
        )
    elif st == "not_joined":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]])
        await m.reply_text("🚫 **Join Channel First**", reply_markup=btn)
    else: await m.reply_text("🔒 **No Access**")

@app.on_callback_query(filters.regex("verify_join"))
async def verify(c, q):
    ok, st, _ = await check_permissions(c, q.from_user.id)
    if ok: await q.message.delete(); await start(c, q.message)
    else: await q.answer("❌ Not Joined!", show_alert=True)

@app.on_message(filters.command("solve"))
async def solve(c, m):
    u = m.from_user.id
    ok, _, _ = await check_permissions(c, u)
    if not ok: return await m.reply("⛔ No Access")
    
    txt = m.text.split(None, 1)[1] if len(m.command)>1 else m.reply_to_message.text if m.reply_to_message else None
    if not txt: return await m.reply("⚠️ Format: `/solve list`")
    
    lines = [l for l in txt.split('\n') if l.strip()]
    msg = await m.reply(f"🔧 **Solving...**\nTarget: `{len(lines)}`")
    
    solved, failed, proc = [], [], 0
    sem = asyncio.Semaphore(Config.MAX_THREADS) # Uses Dynamic Threads
    last = time.time()

    async def w(l):
        nonlocal proc, last
        async with sem:
            res, val = await asyncio.get_running_loop().run_in_executor(None, solve_checkpoint_logic, l)
            if res: solved.append(val)
            else: failed.append(l)
            proc += 1
            if time.time()-last > 3 or proc==len(lines):
                try: await msg.edit(f"🔧 **Solving...**\n✅: {len(solved)} | ❌: {len(failed)} | ⚙️: {proc}/{len(lines)}")
                except: pass; last = time.time()

    await asyncio.gather(*[w(l) for l in lines])
    
    if solved:
        f = f"Fixed_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(solved))
        await m.reply_document(f, caption=f"✅ **Fixed:** {len(solved)}"); os.remove(f)
    else: await msg.edit("❌ Failed.")

@app.on_message(filters.text & filters.private)
async def main(c, m):
    if m.text.startswith("/"): return
    u = m.from_user.id
    ok, st, lim = await check_permissions(c, u)
    
    if not ok: return await m.reply("⛔ Access Denied")
    lines = [l for l in m.text.split('\n') if l.strip()]
    if len(lines) > lim: return await m.reply(f"⛔ Limit Exceeded: `{lim}`")
    
    # PROXY CHECK
    if Config.USE_PROXY and not PROXY_LIST:
        return await m.reply("⚠️ **Proxies ON but list empty!**\nAdmin must add proxies or turn mode OFF.")

    msg = await m.reply(f"💎 **Processing...**\nThreads: `{Config.MAX_THREADS}`")
    
    succ, fail, proc = [], [], 0
    sem = asyncio.Semaphore(Config.MAX_THREADS) # Dynamic Limit
    last = time.time()

    async def w(l):
        nonlocal proc, last
        async with sem:
            res, val = await asyncio.get_running_loop().run_in_executor(None, process_account, l)
            if res: succ.append(val)
            else: fail.append(val)
            proc += 1
            if time.time()-last > 3 or proc==len(lines):
                try: await msg.edit(f"💎 **Running...**\n✅: {len(succ)} | ❌: {len(fail)} | ⚙️: {proc}/{len(lines)}")
                except: pass; last = time.time()

    await asyncio.gather(*[w(l) for l in lines])
    
    if succ:
        f = f"Success_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(succ))
        await m.reply_document(f, caption=f"✅ **Success:** {len(succ)}"); os.remove(f)
    if fail:
        f = f"Failed_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(fail))
        await m.reply_document(f, caption=f"❌ **Failed:** {len(fail)}"); os.remove(f)

if __name__ == "__main__":
    print("💎 Bot V8 Started...")
    app.run()

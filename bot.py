#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot V9 (Hardcore Login + GitHub DB + Admin Contact)
Features:
- UI Update: Contact Admin button for non-access users
- Login Logic: Hardcore (3x Retry, IP Rotation, RUR/SHBID Extraction)
- Database: GitHub Persistence
- Controls: /on, /off, /access, /ban
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
    
    # Admin ID
    ADMIN_ID = 6323050876
    
    CHANNEL_ID = -1003375283491
    CHANNEL_LINK = "https://t.me/Sheet_short_update"
    
    SESSION_NAME = "ig_premium_v9"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    
    # ---------------------------------------------------------
    # GITHUB DATABASE CONFIGURATION
    # ---------------------------------------------------------
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    GITHUB_REPO = "YourUsername/YourRepoName" 
    DB_FILENAME = "users_db.json"
    # ---------------------------------------------------------

# Global State for Switch
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
                else: self.local_cache = {}
            else: self.local_cache = {}
        except: self.local_cache = {}

    def save_to_github(self):
        try:
            r = requests.get(self.api_url, headers=self.headers)
            sha = r.json().get("sha") if r.status_code == 200 else None
            json_str = json.dumps(self.local_cache, indent=2)
            b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
            data = {"message": "Update DB", "content": b64}
            if sha: data["sha"] = sha
            requests.put(self.api_url, headers=self.headers, json=data)
        except: pass

    def set_access(self, uid, sec, lim):
        self.local_cache[str(uid)] = {"expiry": time.time() + sec, "limit": lim}
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
    u = db.get_user(user_id)
    if not u: return False, "No Access", 0
    rem = u.get("expiry", 0) - time.time()
    if rem > 0: return True, format_time(rem), u.get("limit", 100)
    else: db.remove_user(user_id); return False, "Expired", 0

def format_time(s):
    td = timedelta(seconds=s)
    return f"{td.days}d {td.seconds//3600}h"

# ============================================
# SECTION 3: PROXY & HARDCORE ENGINE
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

# --- Hardcore Login Logic ---
def attempt_login(u, p, k, use_mobile_ua=False):
    ua = get_headers(mobile=use_mobile_ua)
    L = instaloader.Instaloader(quiet=True, user_agent=ua['User-Agent'], max_connection_attempts=1)
    L.context._session.headers.update(ua)
    
    if PROXY_LIST and GlobalState.USE_PROXY:
        prx = random.choice(PROXY_LIST)
        L.context._session.proxies = {"http": prx, "https": prx}

    try:
        try: L.login(u, p)
        except TwoFactorAuthRequiredException:
            if k:
                try: L.two_factor_login(pyotp.TOTP(str(k).replace(" ", "").strip().upper()).now())
                except: return False, "2FA_FAIL"
            else: return False, "NEEDS_2FA"
        except BadCredentialsException: return False, "WRONG_PASS"
        except ConnectionException: return False, "PROXY_ERROR"
        except Exception as e:
            if "checkpoint" in str(e).lower(): return False, "CHECKPOINT"
            return False, "ERROR"

        # Force Full Cookie Generation
        try: L.context._session.get("https://www.instagram.com/")
        except: pass
        
        cookies = L.context._session.cookies.get_dict()
        if 'sessionid' not in cookies: return False, "NO_SESSION"

        # Extras
        if 'ig_did' not in cookies: cookies['ig_did'] = str(uuid.uuid4()).upper()
        if 'datr' not in cookies: cookies['datr'] = secrets.token_hex(12)
        if 'rur' not in cookies: cookies['rur'] = "NA"

        prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid', 'rur', 'shbid', 'shbts']
        parts = [f"{k}={cookies[k]}" for k in prio if k in cookies]
        for k,v in cookies.items():
            if k not in prio: parts.append(f"{k}={v}")
            
        return True, f"{u}|{p}|{'; '.join(parts)}"
    except: return False, "UNKNOWN"

def process_account_hardcore(u, p, k):
    # Retry 3 times with different proxies
    for i in range(3):
        use_mobile = (i % 2 != 0) 
        success, res = attempt_login(u, p, k, use_mobile_ua=use_mobile)
        if success: return True, res
        if "WRONG_PASS" in res or "NEEDS_2FA" in res or "2FA_FAIL" in res:
            return False, f"{u}|{p}|{res}"
        time.sleep(random.uniform(1, 2))
    return False, f"{u}|{p}|FAILED"

# --- Solver Logic ---
def solve_checkpoint_logic(line):
    try:
        parts = line.strip().split('|')
        if len(parts) < 3: return False, "FORMAT_ERROR"
        u, p, c_str = parts[0], parts[1], parts[2]
        
        cookie_dict = {}
        for item in c_str.split(';'):
            if '=' in item: k, v = item.strip().split('=', 1); cookie_dict[k.strip()] = v.strip()

        L = instaloader.Instaloader(quiet=True, user_agent=get_headers(mobile=True)['User-Agent'])
        if PROXY_LIST and GlobalState.USE_PROXY: 
            prx = random.choice(PROXY_LIST)
            L.context._session.proxies = {"http": prx, "https": prx}
        
        L.context._session.cookies.update(cookie_dict)
        
        try:
            resp = L.context._session.get("https://www.instagram.com/")
            if "accounts/login" in resp.url: return False, f"{u}|{p}|EXPIRED"
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
            f"💠 **IG PREMIUM BOT V9** 💠\n\n"
            f"👋 Hello, **{message.from_user.first_name}**\n"
            f"🛡️ Status: `Active`\n"
            f"⏳ Expiry: `{status}`\n"
            f"🔢 Limit: `{limit}`\n"
            f"🌐 Proxies: `{len(PROXY_LIST)}` ({pmode})\n\n"
            f"📝 **To Use:** Send account list below.\n"
            f"`User` `Pass` `Key`"
        )
    elif status == "not_joined":
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=Config.CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
        ])
        await message.reply_text("🚫 **Access Denied**\n\nYou must join our channel to use this bot.", reply_markup=btn)
    else:
        # NEW: Contact Admin Button for Expired/No Access Users
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={Config.ADMIN_ID}")]
        ])
        await message.reply_text(
            f"🔒 **Access Denied**\n\n"
            f"🆔 Your ID: `{user_id}`\n"
            f"⚠️ You do not have permission or your access has expired.\n"
            f"Please contact the admin to buy access.",
            reply_markup=btn
        )

@app.on_callback_query(filters.regex("verify_join"))
async def verify(c, q):
    v, s, l = await check_permissions(c, q.from_user.id)
    if v: await q.message.delete(); await start(c, q.message)
    elif s == "not_joined": await q.answer("❌ Not Joined!", show_alert=True)
    else: await q.answer("❌ Joined but Expired!", show_alert=True)

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

@app.on_message(filters.command("solve"))
async def solve(c, m):
    uid = m.from_user.id
    v, s, l = await check_permissions(c, uid)
    if not v: return await m.reply("🚫 No Access")
    
    if len(m.command) < 2 and not m.reply_to_message: return await m.reply("⚠️ Reply to file or text")
    text = m.text.split(None, 1)[1] if len(m.command) > 1 else m.reply_to_message.text
    lines = [l for l in text.split('\n') if l.strip()]
    
    msg = await m.reply(f"🔧 **Solving...**\nTarget: `{len(lines)}`")
    solved, failed, processed = [], [], 0
    sem = asyncio.Semaphore(GlobalState.THREADS)
    loop = asyncio.get_running_loop()
    last = time.time()

    async def worker(line):
        nonlocal processed, last
        async with sem:
            ok, res = await loop.run_in_executor(None, solve_checkpoint_logic, line)
            if ok: solved.append(res)
            else: failed.append(line)
            processed += 1
            if time.time() - last > 3 or processed == len(lines):
                try: await msg.edit(f"🔧 **Running...**\n✅ Valid: {len(solved)}\n❌ Dead: {len(failed)}\n⚙️ Done: {processed}/{len(lines)}"); last = time.time()
                except: pass

    await asyncio.gather(*[worker(l) for l in lines])
    
    if solved:
        f = f"Fixed_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(solved))
        await m.reply_document(f, caption=f"✅ **Fixed:** {len(solved)}")
        os.remove(f)
    else: await msg.edit("❌ No cookies refreshed.")

@app.on_message(filters.text & filters.private)
async def handle(c, m):
    if m.text.startswith("/"): return
    uid = m.from_user.id
    v, s, lim = await check_permissions(c, uid)
    
    if not v:
        # UI for Access Denied in Text Handler
        if s == "not_joined":
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join", url=Config.CHANNEL_LINK)],[InlineKeyboardButton("✅ Verify", callback_data="verify_join")]])
            await m.reply("❌ Join Channel First", reply_markup=btn)
        else:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={Config.ADMIN_ID}")]])
            await m.reply(f"🔒 **Access Denied**\n🆔 `{uid}`\nContact Admin.", reply_markup=btn)
        return

    lines = [l for l in m.text.split('\n') if l.strip()]
    if len(lines) > lim: return await m.reply(f"⛔ Limit: {lim}")
    if not PROXY_LIST and GlobalState.USE_PROXY: return await m.reply("⚠️ Proxies Offline")

    msg = await m.reply(f"💎 **Processing...**\nTarget: `{len(lines)}`\nMode: Hardcore (3x Retry)")
    
    valid, failed, processed = [], [], 0
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
                    else: failed.append(res)
                processed += 1
                if time.time() - last > 2.5 or processed == len(lines):
                    try: await msg.edit(f"💎 **Running...**\n📊 {int((processed/len(lines))*100)}%\n✅ Valid: {len(valid)}\n❌ Failed: {len(failed)}\n🔄 Done: {processed}/{len(lines)}"); last = time.time()
                    except: pass
            except: processed += 1

    await asyncio.gather(*[worker(l) for l in lines])
    
    if valid:
        f = f"Cookies_{datetime.now().strftime('%H%M')}.txt"
        with open(f, "w") as fl: fl.write("\n".join(valid))
        await m.reply_document(f, caption=f"✅ **Success:** {len(valid)}")
        os.remove(f)
    if failed:
        f2 = f"Failed_{datetime.now().strftime('%H%M')}.txt"
        with open(f2, "w") as fl: fl.write("\n".join(failed))
        await m.reply_document(f2, caption=f"❌ **Failed:** {len(failed)}")
        os.remove(f2)

if __name__ == "__main__":
    print("🔥 Hardcore Bot V9 Started...")
    app.run()

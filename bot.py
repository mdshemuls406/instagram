#!/data/data/com.termux/files/usr/bin/python3
"""
Instagram Premium Bot V11 (Pure Web-Flow Login)
Features:
- Pure Web Requests (Simulates Browser AJAX Calls)
- Manual Password Encryption & 2FA Handling
- Single Thread & 10x Retry
- GitHub Database & Admin Controls
"""

import os
import sys
import asyncio
import logging
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

import requests
import pyotp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import instaloader # Still used for profile fetching if needed

class Config:
    API_ID = 36021238
    API_HASH = "8f9bf7770e5b58b550030bcbaa0ec7d7"
    BOT_TOKEN = "8274795288:AAHDbqKWe1XpM4_xJppY9PED_1TtmAeCX1o"
    
    ADMIN_ID = 6323050876
    CHANNEL_ID = -1003375283491
    CHANNEL_LINK = "https://t.me/Sheet_short_update"
    
    SESSION_NAME = "ig_pure_web_v11"
    WORKDIR = Path("ig_data")
    WORKDIR.mkdir(exist_ok=True)
    
    # GITHUB CONFIG
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    GITHUB_REPO = "YourUsername/YourRepoName" 
    DB_FILENAME = "users_db.json"

# Global State
class GlobalState:
    USE_PROXY = True
    THREADS = 1

logging.basicConfig(level=logging.ERROR)

# ============================================
# SECTION 2: GITHUB DATABASE LOGIC
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
                self.local_cache = json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
            else: self.local_cache = {}
        except: self.local_cache = {}

    def save_to_github(self):
        try:
            r = requests.get(self.api_url, headers=self.headers)
            sha = r.json().get("sha") if r.status_code == 200 else None
            data = {
                "message": "Update DB",
                "content": base64.b64encode(json.dumps(self.local_cache, indent=2).encode("utf-8")).decode("utf-8")
            }
            if sha: data["sha"] = sha
            requests.put(self.api_url, headers=self.headers, json=data)
        except: pass

    def set_access(self, uid, sec, lim):
        self.local_cache[str(uid)] = {"expiry": time.time() + sec, "limit": lim}
        self.save_to_github()

    def get_user(self, uid): return self.local_cache.get(str(uid))
    def remove_user(self, uid): 
        if str(uid) in self.local_cache: del self.local_cache[str(uid)]; self.save_to_github(); return True
        return False
    def get_all(self): return self.local_cache

db = GitHubDB()

def check_access(user_id):
    if user_id == Config.ADMIN_ID: return True, "Admin", 999999
    u = db.get_user(user_id)
    if not u: return False, "No Access", 0
    rem = u.get("expiry", 0) - time.time()
    if rem > 0: return True, f"{int(rem//3600)}h {int((rem%3600)//60)}m", u.get("limit", 100)
    else: db.remove_user(user_id); return False, "Expired", 0

# ============================================
# SECTION 3: PURE WEB LOGIN ENGINE
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
        'User-Agent': f'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120, 130)}.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.instagram.com',
        'Referer': 'https://www.instagram.com/accounts/login/',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
    }

def enc_password(password):
    # Simulate Instagram Web Password Encryption (#PWD_INSTAGRAM_BROWSER:10:TIME:PASS)
    t = int(time.time())
    return f"#PWD_INSTAGRAM_BROWSER:10:{t}:{password}"

def pure_web_login(username, password, key):
    s = requests.Session()
    s.headers.update(get_headers())
    
    # 1. Proxy Setup
    if PROXY_LIST and GlobalState.USE_PROXY:
        prx = random.choice(PROXY_LIST)
        s.proxies = {"http": prx, "https": prx}

    try:
        # 2. Get CSRF Token (Home Page Load)
        r1 = s.get('https://www.instagram.com/accounts/login/')
        csrf = r1.cookies.get('csrftoken')
        if not csrf: return False, "NO_CSRF_INIT"
        
        s.headers.update({'X-CSRFToken': csrf})
        
        # 3. Perform Login (POST)
        login_url = 'https://www.instagram.com/accounts/login/ajax/'
        payload = {
            'enc_password': enc_password(password),
            'username': username,
            'queryParams': '{}',
            'optIntoOneTap': 'false'
        }
        
        time.sleep(random.uniform(2, 4))
        r2 = s.post(login_url, data=payload)
        resp_json = r2.json()
        
        # 4. Handle Response
        if resp_json.get('authenticated') is True:
            # Direct Login Success
            pass
            
        elif resp_json.get('two_factor_required'):
            # 2FA Handling
            if not key: return False, "NEEDS_2FA_NO_KEY"
            
            # Generate Code
            try:
                totp_code = pyotp.TOTP(str(key).replace(" ", "").strip().upper()).now()
            except: return False, "INVALID_2FA_KEY"
            
            identifier = resp_json.get('two_factor_info', {}).get('two_factor_identifier')
            
            # Submit 2FA Code
            two_factor_url = 'https://www.instagram.com/accounts/login/ajax/two_factor/'
            tf_payload = {
                'verificationCode': totp_code,
                'identifier': identifier,
                'queryParams': '{}',
                'trust_this_device': '1'
            }
            
            time.sleep(random.uniform(2, 3))
            r3 = s.post(two_factor_url, data=tf_payload)
            r3_json = r3.json()
            
            if r3_json.get('authenticated') is not True:
                return False, "2FA_FAILED_OR_WRONG"
                
        elif 'message' in resp_json and 'checkpoint' in resp_json.get('message', ''):
            return False, "CHECKPOINT"
        elif resp_json.get('user') is False:
            return False, "WRONG_PASS"
        else:
            return False, f"LOGIN_ERR: {resp_json.get('message', 'Unknown')}"

        # 5. Finalize Session (Hit Home Page to populate cookies)
        s.get('https://www.instagram.com/')
        
        cookies = s.cookies.get_dict()
        if 'sessionid' not in cookies: return False, "NO_SESSION_COOKIE"
        
        # Add Extras
        if 'ig_did' not in cookies: cookies['ig_did'] = str(uuid.uuid4()).upper()
        if 'datr' not in cookies: cookies['datr'] = secrets.token_hex(12)
        if 'rur' not in cookies: cookies['rur'] = "NA"

        prio = ['csrftoken', 'datr', 'ig_did', 'mid', 'ds_user_id', 'sessionid', 'rur', 'shbid', 'shbts']
        parts = [f"{k}={cookies[k]}" for k in prio if k in cookies]
        for k,v in cookies.items():
            if k not in prio: parts.append(f"{k}={v}")
            
        return True, f"{username}|{password}|{'; '.join(parts)}"

    except Exception as e:
        return False, "NET_ERROR"

def process_account_hardcore(u, p, k):
    # 10 Retries with Proxy Rotation
    for i in range(10):
        success, res = pure_web_login(u, p, k)
        if success: return True, res
        
        # Stop on fatal errors
        if "WRONG_PASS" in res or "NEEDS_2FA" in res or "INVALID_2FA_KEY" in res:
            return False, f"{u}|{p}|{res}"
            
        time.sleep(random.uniform(1, 3))
    return False, f"{u}|{p}|FAILED_10_RETRIES"

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
            f"💠 **IG PURE WEB BOT V11** 💠\n\n"
            f"👋 Hello, **{message.from_user.first_name}**\n"
            f"🛡️ Status: `Active`\n"
            f"⏳ Expiry: `{status}`\n"
            f"🌐 Proxies: `{len(PROXY_LIST)}` ({pmode})\n\n"
            f"⚡ **Mode:** Web Request (Auto 2FA)\n"
            f"📝 **To Use:** Send account list below.\n"
            f"`User` `Pass` `Key`"
        )
    elif status == "not_joined":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=Config.CHANNEL_LINK)],[InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]])
        await message.reply_text("🚫 **Access Denied**\n\nYou must join our channel to use this bot.", reply_markup=btn)
    else:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact Admin", url=f"tg://user?id={Config.ADMIN_ID}")]])
        await message.reply_text(f"🔒 **Access Denied**\n\n🆔 Your ID: `{user_id}`\n⚠️ No Permission.", reply_markup=btn)

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
        GlobalState.THREADS = 1 # Always 1 Thread requested
        await m.reply(f"✅ Proxies: {GlobalState.USE_PROXY} | Threads: 1")

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
    
    if not v:
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

    msg = await m.reply(f"💎 **Processing...**\nTarget: `{len(lines)}`\nMode: Web Flow (10x Retry)")
    
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
                if time.time() - last > 3 or processed == len(lines):
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
    print("🔥 Pure Web Bot V11 Started...")
    app.run()

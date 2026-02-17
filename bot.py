import sys
import subprocess
import logging
import asyncio
import re
import random
import string
from typing import Dict, Set, Optional, Tuple
from datetime import datetime
import httpx
import os
import shutil
# -----------------------------------------------------------
# 1. AUTO DEPENDENCY INSTALLER (httpx এবং playwright দুটোই)
# -----------------------------------------------------------
def run(cmd, sudo=False):
    try:
        if sudo and os.geteuid() != 0:
            cmd = ["sudo"] + cmd
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        return None

def command_exists(cmd):
    return shutil.which(cmd) is not None

def install_apt_packages():
    # Only if server actually has apt (Ubuntu/Debian VPS)
    if not command_exists("apt"):
        print("APT not available on this hosting. Skipping system library install.")
        return

    print("Installing Linux browser libraries...")

    packages = [
        "libatk-bridge2.0-0","libatk1.0-0","libgtk-3-0","libnss3",
        "libx11-xcb1","libxcomposite1","libxdamage1","libxrandr2",
        "libgbm1","libasound2","libpangocairo-1.0-0","libpango-1.0-0",
        "libcairo2","libcups2","libdrm2","libxkbcommon0","libxfixes3",
        "libxext6","libxrender1","libxcb1","libxshmfence1",
        "fonts-liberation","libappindicator3-1","ca-certificates",
        "wget","curl","xdg-utils"
    ]

    run(["apt","update"], sudo=True)
    run(["apt","install","-y"] + packages, sudo=True)

def install_pip_packages():
    print("Installing Python packages...")

    required = [
        "python-telegram-bot==20.7",
        "httpx",
        "playwright"
    ]

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + required)

def install_playwright():
    print("Installing Playwright Chromium...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    subprocess.run([sys.executable, "-m", "playwright", "install-deps"])

def full_install():
    marker = ".deps_installed"

    # Already installed once
    if os.path.exists(marker):
        return

    print("=== FIRST RUN SETUP STARTED ===")

    install_apt_packages()
    install_pip_packages()
    install_playwright()

    # create marker so it never repeats
    with open(marker, "w") as f:
        f.write("ok")

    print("Setup completed. Restarting script...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# run automatically
full_install()

# -----------------------------------------------------------
# 2. BOT CODE
# -----------------------------------------------------------
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from playwright.async_api import async_playwright, Page
import httpx

# --- CONFIGURATION ---
BOT_TOKEN = "7810230703:AAGdoQpT0ECgiDoRhBwZiOGUPp1w814ynE0"
API_BASE_URL = "https://tempmail.plus/api"
MAIL_VIEW_URL = "https://tempmail.plus/en/#!mail/{mail_id}"
DOMAINS = [
    "mailto.plus", "fexpost.com", "fexbox.org", "chitthi.in",
    "rover.info", "fextemp.com", "any.pink", "merepost.com"
]

# --- LOGGING & STATE SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
CHOOSING_DOMAIN, MAIL_ACTIVE = range(2)

# --- SESSION MANAGEMENT ---
class UserSession:
    def __init__(self, email: str, domain: str):
        self.email = email
        self.domain = domain
        self.active = True
        self.seen_mail_ids: Set[str] = set()
        # Browser objects
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        
    async def cleanup(self):
        self.active = False
        if self.page: await self.page.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()


user_sessions: Dict[int, UserSession] = {}


# --- KEYBOARD LAYOUTS ---
def get_main_keyboard():
    return ReplyKeyboardMarkup([["📧 TEMPMAIL PLUS"]], resize_keyboard=True)

def get_domain_keyboard():
    keyboard = [DOMAINS[i:i + 2] for i in range(0, len(DOMAINS), 2)]
    keyboard.append(["⬅️ Back", "🏠 Home"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --- BOT HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 Welcome! Click the button below to choose a domain.",
        reply_markup=get_main_keyboard()
    )
    return CHOOSING_DOMAIN

async def show_domains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please select a domain:", reply_markup=get_domain_keyboard())
    return CHOOSING_DOMAIN

async def generate_email_from_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    domain = update.message.text
    await update.message.reply_text(f"Generating email with domain `{domain}`...", parse_mode='Markdown')
    await create_new_email(update, context, domain)
    return MAIL_ACTIVE

async def create_new_email(update: Update, context: ContextTypes.DEFAULT_TYPE, domain: str):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        await user_sessions[user_id].cleanup()

    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{name}@{domain}"
    
    session = UserSession(email, domain)
    user_sessions[user_id] = session

    # Launch browser for this session
    try:
        session.playwright = await async_playwright().start()
        session.browser = await session.playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        session.page = await session.browser.new_page()
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        await update.message.reply_text("Error: Could not start the browser service. Please try again later.")
        return

    inline_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Change Mail", callback_data=f"change:{domain}")]])
    await update.message.reply_text(
        f"✅ **Email Ready!**\n\n📧 `{email}`\n\nMonitoring inbox...",
        reply_markup=inline_keyboard, parse_mode='Markdown'
    )
    context.application.create_task(monitor_inbox_task(user_id, context.application))

async def change_mail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    domain = query.data.split(":")[1]
    await create_new_email(query, context, domain)


async def monitor_inbox_task(user_id: int, app: Application):
    """
    (চূড়ান্ত হাইব্রিড মডেল)
    প্রথমে API দিয়ে সাবজেক্ট চেক করে, না পেলে ব্রাউজার দিয়ে বডি স্ক্র্যাপ করে।
    """
    session = user_sessions.get(user_id)
    if not session or not session.page: return

    logger.info(f"Starting HYBRID monitor for {session.email}")

    async with httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0'}) as client:
        for _ in range(90):
            if not session.active: break
            try:
                list_response = await client.get(
                    f"{API_BASE_URL}/mails", params={'email': session.email}, timeout=20
                )
                if list_response.status_code == 200:
                    mail_list = list_response.json().get('mail_list', [])
                    for mail_summary in mail_list:
                        mail_id = mail_summary.get('mail_id')
                        if mail_id and mail_id not in session.seen_mail_ids:
                            session.seen_mail_ids.add(mail_id)
                            
                            subject = mail_summary.get('subject', '')
                            sender = mail_summary.get('from_name', 'Unknown')
                            otp = extract_otp_from_text(subject)

                            if otp:
                                # পদ্ধতি ১: সাবজেক্ট থেকেই কোড পাওয়া গেছে
                                logger.info(f"OTP found in subject for mail {mail_id}")
                                await process_and_send_email(user_id, otp, sender, subject, "---", app, session.email)
                            else:
                                # পদ্ধতি ২: সাবজেক্টে কোড নেই, ব্রাউজার দিয়ে বডি স্ক্র্যাপ করতে হবে
                                logger.info(f"OTP not in subject. Scraping body for mail {mail_id}")
                                scraped_otp, body_text = await scrape_mail_content(session.page, mail_id)
                                await process_and_send_email(user_id, scraped_otp, sender, subject, body_text, app, session.email)
            except Exception as e:
                logger.error(f"Monitor task error: {e}")
            await asyncio.sleep(10)

    if user_id in user_sessions and user_sessions.get(user_id) == session:
        await session.cleanup()
        del user_sessions[user_id]
        await app.bot.send_message(user_id, "⏰ Your email session has expired.")


async def scrape_mail_content(page: Page, mail_id: str) -> Tuple[Optional[str], str]:
    """Navigates to the mail page and scrapes its content."""
    try:
        url = MAIL_VIEW_URL.format(mail_id=mail_id)
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # অপেক্ষা করার জন্য একটি নির্ভরযোগ্য সিলেক্টর
        content_selector = ".overflow-auto, .mail-content"
        await page.wait_for_selector(content_selector, timeout=15000)
        
        body_element = await page.query_selector(content_selector)
        body_text = await body_element.inner_text() if body_element else "--- No Content ---"
        
        otp = extract_otp_from_text(body_text)
        return otp, body_text
    except Exception as e:
        logger.error(f"Failed to scrape mail {mail_id}: {e}")
        return None, "--- Failed to load content ---"

def extract_otp_from_text(text: str) -> Optional[str]:
    matches = re.findall(r'\b\d+\b', text)
    return matches[0] if matches else None

async def process_and_send_email(
    user_id: int, otp: Optional[str], sender: str, subject: str, body: str, 
    app: Application, recipient_email: str
):
    """Formats and sends the final message to the user."""
    if otp:
        current_time = datetime.now().strftime('%I:%M:%S %p')
        appendix = f"# {otp} is your {sender} code. Don't share it"
        message_text = (
            f"✨ **SheetShort OTP Received** ✨\n\n"
            f"⚙️ **Service:** {sender}\n"
            f"📧 **Mail:** `{recipient_email}`\n"
            f"🕒 **Time:** {current_time}\n\n"
            f"🔐 **Code:** `{otp}`\n\n"
            f"{appendix}"
        )
    else:
        full_body = body[:3500] + "..." if len(body) > 3500 else body
        message_text = (
            f"📧 **New Email Received**\n\n"
            f"**From:** `{sender}`\n"
            f"**Subject:** `{subject}`\n"
            f"------------------------------------\n\n"
            f"{full_body}"
        )
    await app.bot.send_message(user_id, message_text, parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        await user_sessions[user_id].cleanup()
        del user_sessions[user_id]
    await update.message.reply_text("🛑 Session stopped.", reply_markup=get_main_keyboard())
    return CHOOSING_DOMAIN

def main():
    install_dependencies()
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            CHOOSING_DOMAIN: [
                MessageHandler(filters.Regex("^📧 TEMPMAIL PLUS$"), show_domains),
                MessageHandler(filters.Regex("^(" + "|".join(re.escape(d) for d in DOMAINS) + ")$"), generate_email_from_domain),
                MessageHandler(filters.Regex("^🏠 Home$|^⬅️ Back$"), start_command),
            ],
            MAIL_ACTIVE: []
        },
        fallbacks=[CommandHandler("stop", stop_command), CommandHandler("start", start_command)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(change_mail_callback, pattern="^change:"))
    
    print("Bot is running with Hybrid (API + Browser) Model...")
    app.run_polling()

if __name__ == "__main__":
    main()

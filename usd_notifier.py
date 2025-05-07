import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configs
BOT_TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "/data/users.txt"  # Persistent storage path
URL = "https://sp-today.com/en/currency/us_dollar/city/damascus"
CHECK_INTERVAL = 3600  # 1 hour

# Global state
active = True
users_cache = set()  # In-memory cache of users

def load_users():
    """Load users from file into memory"""
    global users_cache
    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w'): pass
            return set()
        
        with open(USERS_FILE, 'r') as f:
            users_cache = set(line.strip() for line in f if line.strip())
            return users_cache
    except Exception as e:
        print(f"Error loading users: {e}")
        return set()

def save_user(user_id):
    """Save user to both file and memory cache"""
    global users_cache
    try:
        user_id = str(user_id)
        if user_id not in users_cache:
            with open(USERS_FILE, 'a') as f:
                f.write(f"{user_id}\n")
            users_cache.add(user_id)
            print(f"New user added: {user_id}")
            return True
        return False
    except Exception as e:
        print(f"Error saving user: {e}")
        return False

async def send_notification(rate):
    if not users_cache:
        print("No users to notify")
        return
        
    bot = Bot(token=BOT_TOKEN)
    message = f"💰 USD Rate: {rate} SYP"
    
    for user_id in users_cache:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            print(f"Sent to {user_id}")
        except Exception as e:
            print(f"Error sending to {user_id}: {e}")

def get_usd_rate():
    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rate_divs = soup.find_all("div", class_="col-xs-2 col-md-1 item-data")
            for div in rate_divs:
                if "usd damas" in div.text.lower():
                    return div.find("span", class_="value").text.strip()
    except Exception as e:
        print(f"Error getting USD rate: {e}")
    return None

async def check_rates_periodically():
    global active
    while True:
        if active:
            rate = get_usd_rate()
            if rate:
                await send_notification(rate)
        await asyncio.sleep(CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if save_user(user_id):
        await update.message.reply_text("✅ You've been subscribed to USD rate updates!")
    else:
        await update.message.reply_text("ℹ️ You're already subscribed!")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active
    active = False
    await update.message.reply_text("⏸ Notifications paused. Use /reset to restart.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active
    active = True
    rate = get_usd_rate()
    if rate:
        await send_notification(rate)
    await update.message.reply_text("▶️ Notifications resumed!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error occurred: {context.error}")

async def post_init(application: Application):
    # Initialize user cache
    load_users()
    # Start background tasks
    asyncio.create_task(check_rates_periodically())

def main():
    # Create the Application
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .concurrent_updates(True) \
        .build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("reset", reset))
    application.add_error_handler(error_handler)

    # Start polling
    print("Bot is running with users:", users_cache)
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()

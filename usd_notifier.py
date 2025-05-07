import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configs
BOT_TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.txt"
URL = "https://sp-today.com/en/currency/us_dollar/city/damascus"
CHECK_INTERVAL = 3600  # 1 hour

# Global state
active = True

def load_users():
    """Load users from file, create file if missing"""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            pass  # Create empty file
        return set()
    
    with open(USERS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_user(user_id):
    """Add a new user to the file if not already present"""
    users = load_users()
    user_id = str(user_id)
    if user_id not in users:
        with open(USERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")
        return True
    return False

async def send_notification(rate):
    users = load_users()
    if not users:
        print("No users to notify")
        return
        
    bot = Bot(token=BOT_TOKEN)
    message = f"💰 USD Rate: {rate} SYP"
    
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            print(f"Sent to {user_id}")
        except Exception as e:
            print(f"Error sending to {user_id}: {e}")

def get_usd_rate():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        rate_divs = soup.find_all("div", class_="col-xs-2 col-md-1 item-data")
        for div in rate_divs:
            if "usd damas" in div.text.lower():
                return div.find("span", class_="value").text.strip()
    return None

async def check_rates_periodically():
    global active
    while True:
        if active:
            rate = get_usd_rate()
            if rate:
                await send_notification(rate)
        await asyncio.sleep(CHECK_INTERVAL)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if save_user(user_id):
        await update.message.reply_text("✅ You've been subscribed to USD rate updates!\n\n"
                                      "Use /stop to pause notifications\n"
                                      "Use /reset to resume")
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

async def post_init(application: Application):
    asyncio.create_task(check_rates_periodically())

def main():
    # Initialize users file if missing
    load_users()
    
    # Create the Application
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("reset", reset))

    # Start polling
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()

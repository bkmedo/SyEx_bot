import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot, Update, Message
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, time

# Configs
BOT_TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "/data/users.txt"
URL = "https://sp-today.com/en/currency/us_dollar/city/damascus"
UPDATE_INTERVAL = 5  # Seconds between rate checks
DAILY_RESET_TIME = time(0, 0)  # Midnight reset (adjust as needed)

# Global state
active = True
users_cache = set()
current_rate = None
live_messages = {}  # {user_id: message_id}
daily_rates = []  # Stores today's rates

async def update_live_message(user_id):
    bot = Bot(token=BOT_TOKEN)
    message_text = f"💵 LIVE USD Rate: {current_rate} SYP\n(Updates every {UPDATE_INTERVAL}s)"
    
    if user_id in live_messages:
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=live_messages[user_id],
                text=message_text
            )
        except:
            # If message editing fails, send new one
            msg = await bot.send_message(chat_id=user_id, text=message_text)
            live_messages[user_id] = msg.message_id
    else:
        msg = await bot.send_message(chat_id=user_id, text=message_text)
        live_messages[user_id] = msg.message_id

async def send_daily_summary():
    if not daily_rates:
        return
        
    bot = Bot(token=BOT_TOKEN)
    avg_rate = sum(float(r) for r in daily_rates)/len(daily_rates)
    message_text = (
        "📊 Daily Summary\n"
        f"• Final Rate: {daily_rates[-1]} SYP\n"
        f"• Average Rate: {avg_rate:.2f} SYP\n"
        "New live update will appear tomorrow"
    )
    
    for user_id in users_cache:
        try:
            await bot.send_message(chat_id=user_id, text=message_text)
            live_messages.pop(user_id, None)  # Clear old live message
        except Exception as e:
            print(f"Error sending summary to {user_id}: {e}")
    
    daily_rates.clear()

async def check_rates():
    global current_rate, daily_rates
    while True:
        if active:
            rate = get_usd_rate()
            if rate and rate != current_rate:
                current_rate = rate
                daily_rates.append(rate)
                print(f"Rate updated: {rate}")
                
                # Update all live messages
                for user_id in users_cache.copy():
                    try:
                        await update_live_message(user_id)
                    except Exception as e:
                        print(f"Error updating {user_id}: {e}")
                        
                # Check for daily reset
                if datetime.now().time() >= DAILY_RESET_TIME:
                    await send_daily_summary()
                    await asyncio.sleep(1)  # Ensure midnight passes
                    
        await asyncio.sleep(UPDATE_INTERVAL)

# [Previous load_users(), save_user(), get_usd_rate() functions remain the same]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if save_user(user_id):
        await update_live_message(user_id)
        await update.message.reply_text("✅ Live tracking started!")
    else:
        await update_live_message(user_id)
        await update.message.reply_text("ℹ️ Welcome back!")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active
    active = False
    user_id = update.effective_user.id
    live_messages.pop(user_id, None)
    await update.message.reply_text("⏸ Stopped live updates")

# [Rest of the bot setup remains same as previous example]

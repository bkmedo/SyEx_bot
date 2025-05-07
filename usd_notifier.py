import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# Configs
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Get from Railway environment
USERS_FILE = "users.txt"
URL = "https://sp-today.com/en/currency/us_dollar/city/damascus"

async def send_notification(rate, chat_id=None):
    bot = Bot(token=BOT_TOKEN)
    users = [chat_id] if chat_id else load_users()
    message = f"💰 USD Rate: {rate} SYP"
    
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            print(f"Sent to {user_id}")
        except Exception as e:
            print(f"Error sending to {user_id}: {e}")

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def get_usd_rate():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        rate_divs = soup.find_all("div", class_="col-xs-2 col-md-1 item-data")
        for div in rate_divs:
            if "usd damas" in div.text.lower():
                return div.find("span", class_="value").text.strip()
    return None

if __name__ == "__main__":
    rate = get_usd_rate()
    if rate:
        asyncio.run(send_notification(rate))

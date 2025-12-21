import requests
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Notifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.token or not self.chat_id:
            print("⚠️ [Warning] Telegram credentials not found in .env file.")

    def send(self, message):
        """Send a message to the Telegram chat"""
        if not self.token or not self.chat_id:
            print(f"[LOG ONLY] {message}") # If no token, just print to console
            return
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message
        }

        try:
            response = requests.post(url, data=data, timeout=5)
            if response.status_code != 200:
                print(f"⚠️ Telegram Error: {response.text}")
        except Exception as e:
            print(f"⚠️ Failed to send Telegram message: {e}")
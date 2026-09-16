import os
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_API_KEY = os.getenv("GCP_API_KEY")  # если используешь
ADMIN_CHAT_ID = os.getenv("ADMIN_ID")

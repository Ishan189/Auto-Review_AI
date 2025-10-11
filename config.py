"""
Configuration loader - loads settings from .env file
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
API_KEY = os.getenv("API_KEY")
ORG_ID = os.getenv("ORG_ID")
BASE_URL = os.getenv("BASE_URL")

# AI Review API Key (Google Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Rate Limiting Settings (with safe defaults)
MIN_DELAY_BETWEEN_REQUESTS = float(os.getenv("MIN_DELAY_BETWEEN_REQUESTS", "2"))
MAX_DELAY_BETWEEN_REQUESTS = float(os.getenv("MAX_DELAY_BETWEEN_REQUESTS", "5"))
MIN_DELAY_BETWEEN_BATCHES = float(os.getenv("MIN_DELAY_BETWEEN_BATCHES", "5"))
MAX_DELAY_BETWEEN_BATCHES = float(os.getenv("MAX_DELAY_BETWEEN_BATCHES", "10"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
RETRY_BASE_DELAY = int(os.getenv("RETRY_BASE_DELAY", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# HTTP Headers
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-IN;q=0.9,en-US;q=0.8,en;q=0.7",
    "apikey": API_KEY,
    "dnt": "1",
    "orgid": ORG_ID,
    "origin": "https://lms.tutort.net",
    "priority": "u=1, i",
    "referer": "https://lms.tutort.net/",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}


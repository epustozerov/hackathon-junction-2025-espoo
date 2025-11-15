import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

ASSISTANT_ID = os.getenv("ASSISTANT_ID")
if not ASSISTANT_ID:
    raise ValueError("ASSISTANT_ID environment variable is not set")

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
if not SMTP_USERNAME:
    raise ValueError("SMTP_USERNAME environment variable is not set")

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
if not SMTP_PASSWORD:
    raise ValueError("SMTP_PASSWORD environment variable is not set")

SMTP_SERVER = os.getenv("SMTP_SERVER")
if not SMTP_SERVER:
    raise ValueError("SMTP_SERVER environment variable is not set")

SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

FROM_EMAIL = os.getenv("FROM_EMAIL")
if not FROM_EMAIL:
    raise ValueError("FROM_EMAIL environment variable is not set")

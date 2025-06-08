import os
import sys
import time
import datetime
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Bot start time for uptime tracking
START_TIME = time.time()

#Preferences os >> env >> default

API_KEY = os.environ.get('API_ID') or os.getenv('API_ID') or "API_KEY"
API_HASH = os.environ.get('API_HASH') or os.getenv("API_HASH")   or "API_HASH"
BOT_TOKEN = os.environ.get('BOT_TOKEN ') or os.getenv("BOT_TOKEN") or   "BOT_TOKEN"
ADMINS=[]
ADMINS = os.environ.get('ADMIN_IDS') or os.getenv("ADMIN_IDS") or "123456789"
ADMINS = ADMINS.split(",") # Split the string and convert it to list
OWNER_ID = os.environ.get('OWNER_ID') or os.getenv("OWNER_ID") or "123456789" # Owner ID
ADMINS+=[OWNER_ID] # Add the owner ID to the list
LOG_CHANNEL = os.environ.get('LOG_CHANNEL') or os.getenv("LOG_CHANNEL") or "advchatgptlogs" # Log Channel username preferance
DATABASE_URL=os.environ.get('DATABASE_URL') or os.getenv("DATABASE_URL") or "DATABASE_URL"
BING_COOKIE = os.environ.get('BING_COOKIE') or os.getenv("BING_COOKIE") or "BING_COOKIE"
OCR_KEY = os.environ.get('OCR_KEY') or os.getenv("OCR_KEY") or "OCR_KEY"

MULTIPLE_BOTS = os.environ.get('MULTIPLE_BOTS') or os.getenv("MULTIPLE_BOTS") or "false"
MULTIPLE_BOTS = MULTIPLE_BOTS.lower() in ["true", "1", "yes", "y"]
NUM_OF_BOTS = int(os.environ.get('NUM_OF_BOTS')) or int(os.getenv("NUM_OF_BOTS")) or 1


# Function to get all bot tokens

def get_bot_tokens():
    if MULTIPLE_BOTS:
        tokens = []
        for i in range(1, NUM_OF_BOTS + 1):
            token = os.environ.get(f'BOT_TOKEN{i}') or os.getenv(f'BOT_TOKEN{i}')
            if not token:
                sys.exit(f"BOT_TOKEN{i} is required when MULTIPLE_BOTS is true.")
            tokens.append(token)
        return tokens
    else:
        return [BOT_TOKEN]
#check if all ids are int or not
for x in ADMINS:
    x = str(x)
    if not x.isdigit():
        sys.exit("Please enter a valid integer ID value, Check your ADMINS list")
    else:
        pass

if not OWNER_ID.isdigit():  
    sys.exit("Please enter a valid integer ID value, Check your OWNER_ID")

ADMINS = list(map(int, ADMINS))
OWNER_ID = int(OWNER_ID)
BOT_NAME = os.environ.get('BOT_NAME') or os.getenv("BOT_NAME") or "Adance AI ChatBot"
ADMIN_CONTACT_MENTION = os.environ.get('ADMIN_CONTACT_MENTION') or os.getenv("ADMIN_CONTACT_MENTION") or "@techycsr"




import os
import sys
import logging
import logging.config
import json

import time
import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get('API_KEY') or os.getenv('API_ID') or "API_KEY"
API_HASH = os.environ.get('API_HASH') or os.getenv("API_HASH")   or "API_HASH"
BOT_TOKEN = os.environ.get('BOT_TOKEN ') or os.getenv("BOT_TOKEN") or   "BOT_TOKEN"
ADMINS=[]
ADMINS = os.environ.get('ADMINS') or os.getenv("ADMIN_IDS") or "123456789"
ADMINS = ADMINS.split(",") # Split the string and convert it to list
OWNER_ID = os.environ.get('OWNER_ID') or os.getenv("OWNER_ID") or "123456789" # Owner ID


#check if all ids are int or not
for x in ADMINS:
    x = str(x)
    if not x.isdigit():
        sys.exit("Please enter a valid integer ID value, Check your ADMINS list")
    else:
        pass

if not OWNER_ID.isdigit():  
    sys.exit("Please enter a valid integer ID value, Check your OWNER_ID")



BOT_NAME = os.environ.get('BOT_NAME') or os.getenv("BOT_NAME") or "Adance AI ChatBot"


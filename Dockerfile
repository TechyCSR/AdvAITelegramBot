FROM python:3.11-slim

WORKDIR /AdvAITelegramBot

COPY . /AdvAITelegramBot


API_ID=17071638
API_HASH="ce2045280ff29d36ff9a4daf1c84c975"
BOT_TOKEN="6228771089:AAGMvlMEmXuL4K-xCpbU0rDV-fKUniPVfDY"
OWNER_ID=5293138954
ADMIN_IDS=123456789,987654321,123456789
BOT_NAME=BotName
LOG_CHANNEL=-1002245598026
DATABASE_URL="mongodb+srv://techycsr:techycsr@cluster0.vo3t2jk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BING_COOKIE="1CigBFEeLqnRY90U1ZGeNakvClOBQ7uf3RpVPUs8xKBqBB2aOvy_J42K8uqn5YF9cRZuH4EWVixUfyJuNWxvei1U7U-Ie544u_pJQeDs69k9L2XQjQU5paR8mSh1WDoEW0rrH5MJ3BGegigoRDXt8ZBcPkiYwwTDVKhWpeR0l3VoMMoe6Y_KD-Mo6lnr31cqQfH2YVQbqEi-9oZo0k2BMOA"
OCR_KEY="K87615743688957"

RUN apt-get update \
    && apt-get install -y libsndfile1 \
    && apt-get install -y --no-install-recommends gcc libffi-dev curl \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "run.py"]

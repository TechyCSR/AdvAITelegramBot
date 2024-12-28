FROM python:3.11-slim

WORKDIR /AdvAITelegramBot

COPY . /AdvAITelegramBot


RUN apt-get update \
    && apt-get install -y libsndfile1 \
    && apt-get install -y --no-install-recommends gcc libffi-dev curl \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "run.py"]

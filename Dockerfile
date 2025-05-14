FROM python:3.11-slim

WORKDIR /AdvAITelegramBot

# Copy requirements first for better layer caching
COPY requirements.txt /AdvAITelegramBot/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    gcc \
    libffi-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /AdvAITelegramBot/

# Create directories if they don't exist
RUN mkdir -p sessions

# Expose port if needed for web interface or health checks
EXPOSE 8080

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "run.py"]

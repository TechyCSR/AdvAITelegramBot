#!/bin/bash

# AdvAI Image Generator Web App Startup Script

echo "🚀 Starting AdvAI Image Generator Web App..."

# Set default environment variables
export PORT=${PORT:-5000}
export DEBUG=${DEBUG:-false}
export FLASK_ENV=${FLASK_ENV:-production}

# Create necessary directories
mkdir -p static/uploads
mkdir -p static/generated

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if running in production
if [ "$FLASK_ENV" = "production" ]; then
    echo "🌐 Starting production server with Gunicorn..."
    gunicorn -w 4 -b 0.0.0.0:$PORT app:app --access-logfile - --error-logfile -
else
    echo "🛠️ Starting development server..."
    python app.py
fi 
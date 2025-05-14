# Advanced AI Telegram Bot

A powerful Telegram bot built with Python that leverages cutting-edge AI technologies to provide a rich interactive experience.

## Features

- **AI Chat**: Natural conversation with GPT-4o
- **Image Generation**: Create high-quality images from text descriptions
- **Voice Processing**: Two-way conversion between voice messages and text
- **Text Extraction**: Extract text from images
- **Multi-language Support**: Communicate in multiple languages
- **Group Support**: AI functionality in group chats

## Project Structure

```
AdvAITelegramBot/
├── modules/                  # Core application modules
│   ├── core/                 # Core infrastructure components
│   │   ├── database.py       # DatabaseService with connection pooling
│   │   └── service_container.py # Dependency injection container
│   ├── models/               # Data models and services
│   │   ├── ai_res.py         # AI conversation functionality
│   │   ├── user_db.py        # User data operations
│   │   └── image_service.py  # Image generation and management
│   ├── user/                 # User interaction modules
│   ├── group/                # Group chat functionality
│   ├── image/                # Image processing components
│   └── speech/               # Voice processing components
├── database/                 # Database configuration
├── generated_images/         # Local storage for generated images
├── run.py                    # Main application entry point
├── config.py                 # Configuration settings
└── logs/                     # Application logs
```

## Architectural Pattern

The bot uses a modular architecture with dependency injection:

- **Service Container**: Centralized dependency management
- **Singleton Database Service**: Connection pooling for MongoDB
- **Model-View Pattern**: Clean separation of data and presentation

## Setup and Installation

### Prerequisites

- Python 3.8+
- MongoDB
- Telegram Bot Token (from BotFather)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AdvAITelegramBot.git
   cd AdvAITelegramBot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `config.py` file with your tokens and settings:
   ```python
   BOT_TOKEN = "your_telegram_bot_token"
   API_KEY = "your_telegram_api_key"
   API_HASH = "your_telegram_api_hash"
   DATABASE_URL = "mongodb://localhost:27017/"
   ADMINS = [123456789]  # List of admin user IDs
   ```

5. Run the bot:
   ```bash
   python run.py
   ```

## Commands

- `/start` - Start a conversation and see welcome message
- `/help` - Show available commands and help information
- `/generate [prompt]` - Generate an image from text prompt
- `/newchat` - Clear conversation history and start fresh
- `/settings` - Adjust bot settings
- `/rate` - Rate the bot
- `/clear_cache` - Clear your stored image cache

## Technologies Used

- **Pyrogram**: Telegram client library
- **MongoDB**: Database storage
- **GPT-4o**: Advanced language model for AI responses
- **Image Generation**: Multiple AI image generators
- **Speech Recognition**: Voice-to-text processing
- **Text-to-Speech**: Text-to-voice conversion

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
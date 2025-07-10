# 🤖 AdvAI Image Generator - Telegram Mini App

A powerful AI image generation web application designed to work as a **Telegram Mini App** with seamless authentication and user management.

## ✨ Features

- 🔐 **Telegram Mini App Authentication** - Secure login through Telegram
- 🎨 **AI Image Generation** - Multiple models (Flux, DALL-E 3) with style options
- ✨ **Prompt Enhancement** - AI-powered prompt improvement
- 👤 **User Management** - Premium features and permission-based access
- 🌙 **Theme Support** - Dark/Light modes that sync with Telegram
- 📱 **Mobile Responsive** - Optimized for mobile and desktop
- 🎯 **Real-time Generation** - Progress tracking and status updates

## 🚀 Quick Start

### Prerequisites

1. **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
2. **Pollinations API Key** - Get from [Pollinations.ai](https://pollinations.ai/)
3. **Python 3.8+** - For local development

### Installation

1. **Clone and navigate to webapp directory:**
   ```bash
   cd webapp
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp config.example.py config.py
   # Edit config.py with your API keys
   ```

4. **Set environment variables:**
   ```bash
   export BOT_TOKEN="your_telegram_bot_token"
   export POLLINATIONS_KEY="your_pollinations_api_key"
   export FLASK_SECRET_KEY="your_secure_secret_key"
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | ✅ Yes |
| `POLLINATIONS_KEY` | API key for image generation | ✅ Yes |
| `FLASK_SECRET_KEY` | Secret key for session management | ✅ Yes |
| `TELEGRAM_MINI_APP_REQUIRED` | Enable/disable Telegram auth | ❌ No (default: True) |
| `SESSION_TIMEOUT` | Session timeout in seconds | ❌ No (default: 86400) |
| `FLASK_DEBUG` | Enable debug mode | ❌ No (default: False) |

### Configuration File Example

```python
# config.py
BOT_TOKEN = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
POLLINATIONS_KEY = "your_pollinations_api_key"
FLASK_SECRET_KEY = "your-cryptographically-secure-secret-key"

# Optional settings
TELEGRAM_MINI_APP_REQUIRED = True
SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours
MAX_IMAGES_PER_REQUEST = 4
```

## 📱 Telegram Mini App Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save your bot token securely

### 2. Configure Mini App

1. Send `/setmenubutton` to @BotFather
2. Select your bot
3. Provide your webapp URL (e.g., `https://your-domain.com`)
4. Set button text (e.g., "🎨 Generate Images")

### 3. Set Bot Commands (Optional)

```
/start - Start the bot
/help - Get help information  
/settings - Open image generator
```

### 4. Test Your Mini App

1. Open your bot in Telegram
2. Tap the menu button or send `/start`
3. The webapp should open with authentication

## 🚀 Deployment Options

### Option 1: Vercel (Recommended)

1. **Fork this repository**

2. **Deploy to Vercel:**
   [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/TechyCSR/AdvAITelegramBot&project-name=advai-image-generator&repository-name=advai-image-generator&root-directory=webapp)

3. **Set environment variables in Vercel dashboard:**
   ```
   BOT_TOKEN=your_telegram_bot_token
   POLLINATIONS_KEY=your_pollinations_api_key
   FLASK_SECRET_KEY=your_secure_secret_key
   ```

4. **Update bot settings in @BotFather with your Vercel URL**

### Option 2: Heroku

1. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables:**
   ```bash
   heroku config:set BOT_TOKEN=your_telegram_bot_token
   heroku config:set POLLINATIONS_KEY=your_pollinations_api_key
   heroku config:set FLASK_SECRET_KEY=your_secure_secret_key
   ```

3. **Deploy:**
   ```bash
   git subtree push --prefix webapp heroku main
   ```

### Option 3: Docker

1. **Build Docker image:**
   ```bash
   docker build -t advai-webapp .
   ```

2. **Run container:**
   ```bash
   docker run -p 5000:5000 \
     -e BOT_TOKEN=your_telegram_bot_token \
     -e POLLINATIONS_KEY=your_pollinations_api_key \
     -e FLASK_SECRET_KEY=your_secure_secret_key \
     advai-webapp
   ```

## 🔐 Security Features

### Authentication Flow

1. **Telegram Verification** - Validates initData from Telegram WebApp
2. **Hash Validation** - Ensures data integrity using HMAC-SHA256
3. **Session Management** - Secure session handling with timeout
4. **Permission System** - Role-based access to features

### Security Best Practices

- ✅ HTTPS required for production
- ✅ Secure session cookies
- ✅ CSRF protection via Telegram authentication
- ✅ Rate limiting on generation endpoints
- ✅ Input validation and sanitization

## 🎨 Customization

### Themes

The app automatically adapts to Telegram's theme:
- 🌙 **Dark Mode** - For dark Telegram themes
- ☀️ **Light Mode** - For light Telegram themes

### User Permissions

```python
# Example permission system
{
    'can_generate_images': True,
    'can_enhance_prompts': True,
    'can_access_premium_models': user.is_premium,
    'max_images_per_request': 4 if user.is_premium else 2
}
```

## 🛠️ Development

### Project Structure

```
webapp/
├── app.py                 # Main Flask application
├── telegram_auth.py       # Telegram authentication module
├── config.py             # Configuration file
├── requirements.txt      # Python dependencies
├── static/
│   ├── css/style.css     # Styles with Telegram theme support
│   └── js/app.js         # Frontend with Telegram WebApp integration
├── index.html            # Main webpage
└── vercel.json          # Vercel deployment config
```

### Local Development

1. **Enable debug mode:**
   ```bash
   export FLASK_DEBUG=True
   ```

2. **Disable Telegram auth for testing:**
   ```python
   # config.py
   TELEGRAM_MINI_APP_REQUIRED = False
   ```

3. **Run with auto-reload:**
   ```bash
   python app.py
   ```

### API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/auth/telegram` | POST | Authenticate with Telegram |
| `/api/auth/status` | GET | Check authentication status |
| `/api/auth/logout` | POST | Logout user |
| `/api/generate` | POST | Generate images |
| `/api/enhance-prompt` | POST | Enhance text prompt |
| `/api/health` | GET | Health check |

## 🐛 Troubleshooting

### Common Issues

**Q: Authentication fails with "No initialization data"**
A: Ensure the app is opened through Telegram, not directly in browser

**Q: Images fail to generate**
A: Check your Pollinations API key and ensure it's valid

**Q: Session expires quickly**
A: Increase `SESSION_TIMEOUT` in configuration

**Q: Mini App doesn't open**
A: Verify your webapp URL is correct in @BotFather settings

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Authentication

Use browser developer tools to check:
- Telegram WebApp object is available
- initData is being sent correctly
- Authentication API responses

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

- 📧 **Issues**: [GitHub Issues](https://github.com/TechyCSR/AdvAITelegramBot/issues)
- 💬 **Telegram**: [@TechyCSR](https://t.me/TechyCSR)
- 🤖 **Bot**: [@AdvChatGptBot](https://t.me/AdvChatGptBot)

---

<div align="center">

**Made with ❤️ by [@TechyCSR](https://github.com/TechyCSR)**

[🚀 Deploy Now](https://vercel.com/new/clone?repository-url=https://github.com/TechyCSR/AdvAITelegramBot&project-name=advai-image-generator&repository-name=advai-image-generator&root-directory=webapp) • [📖 Documentation](../README.md) • [🐛 Report Bug](https://github.com/TechyCSR/AdvAITelegramBot/issues)

</div> 
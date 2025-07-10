# 🔗 Connecting Your Existing Telegram Bot to the Mini App

This guide will help you connect your existing `@AdvChatGptBot` to the new image generator Mini App.

## 📋 Prerequisites

- ✅ Your existing Telegram bot token (from `config.py`)
- ✅ Deployed webapp URL (Vercel, Heroku, etc.)
- ✅ Access to [@BotFather](https://t.me/BotFather)

## 🚀 Step-by-Step Setup

### Step 1: Deploy the WebApp

First, deploy your webapp to a public URL:

**Option A: Deploy to Vercel (Fastest)**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "New Project" → Import your repository
3. Set root directory to `webapp`
4. Add environment variables:
   ```
   BOT_TOKEN=your_existing_bot_token_from_config.py
   POLLINATIONS_KEY=your_pollinations_api_key
   FLASK_SECRET_KEY=generate_a_secure_random_string
   ```
5. Deploy and copy the URL (e.g., `https://your-app.vercel.app`)

**Option B: Deploy to Heroku**
1. Create new Heroku app
2. Connect GitHub repository
3. Set environment variables in settings
4. Deploy from `webapp` directory

### Step 2: Configure Bot with @BotFather

1. **Open [@BotFather](https://t.me/BotFather)** in Telegram

2. **Set the Menu Button:**
   ```
   /setmenubutton
   → Select: @AdvChatGptBot
   → Button URL: https://your-app.vercel.app
   → Button Text: 🎨 Generate Images
   ```

3. **Set Web App (Alternative method):**
   ```
   /newapp
   → Select: @AdvChatGptBot
   → App name: AdvAI Image Generator
   → Description: AI-powered image generation
   → Photo: Upload your logo
   → Web App URL: https://your-app.vercel.app
   ```

4. **Update Bot Commands:**
   ```
   /setcommands
   → Select: @AdvChatGptBot
   → Commands:
   start - Start the bot
   help - Get help information
   settings - Bot settings
   img - Generate images
   generate - Generate images
   webapp - Open image generator
   ```

### Step 3: Test the Integration

1. **Open your bot** in Telegram: [@AdvChatGptBot](https://t.me/AdvChatGptBot)

2. **Test the menu button** - You should see a "🎨 Generate Images" button

3. **Click the button** - The webapp should open with authentication

4. **Verify authentication** - You should see your Telegram name and profile

### Step 4: Update Your Main Bot (Optional)

Add a command to your main bot to open the webapp:

```python
# In your main bot code (run.py)
@advAiBot.on_message(filters.command("webapp"))
async def webapp_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Open Image Generator", web_app=WebAppInfo(url="https://your-app.vercel.app"))]
    ])
    await message.reply_text(
        "🚀 **Open the Advanced Image Generator**\n\n"
        "Generate stunning AI images with advanced features:\n"
        "• Multiple AI models (Flux, DALL-E 3)\n"
        "• Style options and customization\n"
        "• Prompt enhancement\n"
        "• History and management\n\n"
        "Click the button below to get started!",
        reply_markup=keyboard
    )
```

## 🔧 Configuration Options

### Environment Variables

Set these in your deployment platform:

```bash
# Required
BOT_TOKEN=your_existing_bot_token              # From your config.py
POLLINATIONS_KEY=your_pollinations_api_key     # From your config.py
FLASK_SECRET_KEY=secure_random_string          # Generate a new one

# Optional
TELEGRAM_MINI_APP_REQUIRED=True                # Enable Telegram auth
SESSION_TIMEOUT=86400                          # 24 hours
FLASK_DEBUG=False                              # Production mode
```

### Generating a Secure Secret Key

```python
# Run this in Python to generate a secure key
import secrets
print(secrets.token_urlsafe(32))
```

## ✅ Verification Checklist

After setup, verify these work:

- [ ] Menu button appears in your bot
- [ ] Clicking menu button opens the webapp
- [ ] Authentication works (shows your Telegram info)
- [ ] Image generation works
- [ ] Theme matches your Telegram theme
- [ ] Mobile responsive design works

## 🎯 User Experience

### How Users Will Access the Mini App:

1. **Via Menu Button** - Most common way
   - Users see the button at bottom of chat
   - Single tap opens the webapp

2. **Via Commands** - Traditional way
   - `/webapp` command opens the mini app
   - `/img` or `/generate` can also redirect

3. **Via Inline Keyboard** - In messages
   - Bot can send messages with webapp buttons
   - Contextual access to image generation

### Expected User Flow:

```
User opens @AdvChatGptBot
         ↓
Sees menu button "🎨 Generate Images"
         ↓
Taps button → Webapp opens
         ↓
Automatic authentication with Telegram
         ↓
User generates images seamlessly
```

## 🐛 Troubleshooting

### Common Issues:

**❌ "Authentication Required" Error**
- Ensure `BOT_TOKEN` matches your actual bot token
- Check webapp is accessed through Telegram, not browser

**❌ Menu Button Not Showing**
- Check @BotFather configuration
- Ensure webapp URL is correct and accessible

**❌ 500 Server Error**
- Check environment variables are set correctly
- Verify `POLLINATIONS_KEY` is valid

**❌ Theme Not Working**
- Ensure webapp is opened in Telegram app
- Check browser developer tools for errors

### Debug Mode:

For testing, you can disable Telegram authentication:

```python
# In webapp/config.py
TELEGRAM_MINI_APP_REQUIRED = False
```

This allows testing the webapp directly in browser.

## 📞 Support

If you encounter issues:

1. **Check the logs** in your deployment platform
2. **Test in browser** with auth disabled
3. **Verify environment variables** are set correctly
4. **Create an issue** on GitHub with error details

---

🎉 **Congratulations!** Your Telegram bot now has a powerful Mini App for image generation!

Your users can now generate images directly within Telegram with a seamless, authenticated experience. 
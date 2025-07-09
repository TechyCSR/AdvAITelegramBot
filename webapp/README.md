# AdvAI Image Generator Web App

A modern web application for AI image generation using the same technology as the AdvAI Telegram Bot. Features a beautiful interface similar to gpt1image.exomlapi.com with full integration to g4f and advanced AI models.

## ✨ Features

- **Modern UI**: Clean, responsive design with beautiful animations
- **AI Image Generation**: Powered by g4f with multiple AI models (DALL-E 3, Flux, Stable Diffusion)
- **Multiple Formats**: Support for Square (1024×1024), Wide (1536×1024), and Tall (1024×1536) images
- **Batch Generation**: Generate 1, 2, or 4 images at once
- **Style Options**: Multiple artistic styles (Photorealistic, Artistic, Anime, Cartoon, etc.)
- **Prompt Enhancement**: AI-powered prompt optimization
- **Reference Images**: Upload up to 5 reference images (optional)
- **Download Support**: Download individual images or all at once
- **History Management**: Save, view, and export generation history
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Navigate to the webapp directory**:
   ```bash
   cd webapp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser**:
   Visit `http://localhost:5000`

## 🛠️ Development

### Environment Variables

Create a `.env` file in the webapp directory:

```env
DEBUG=true
PORT=5000
MAX_CONTENT_LENGTH=52428800
FLASK_ENV=development
```

### Running in Development Mode

```bash
export DEBUG=true
python app.py
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t advai-webapp .
```

### Run Container

```bash
docker run -p 5000:5000 advai-webapp
```

## 🌐 Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using uWSGI

```bash
uwsgi --http :5000 --wsgi-file app.py --callable app --processes 4 --threads 2
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/webapp/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📡 API Endpoints

### Generate Images
```http
POST /api/generate
Content-Type: multipart/form-data

description: "Your image description"
size: "1024x1024" | "1536x1024" | "1024x1536"
variants: 1 | 2 | 4
style: "default" | "photorealistic" | "artistic" | "anime" | etc.
reference_image_0: [file] (optional)
reference_image_1: [file] (optional)
...
```

### Enhance Prompt
```http
POST /api/enhance-prompt
Content-Type: application/json

{
  "prompt": "Your original prompt"
}
```

### Health Check
```http
GET /api/health
```

### Service Stats
```http
GET /api/stats
```

## 🎨 Customization

### Styling

Edit `static/css/style.css` to customize:
- Colors and themes
- Layout and spacing
- Animations and effects
- Responsive breakpoints

### Functionality

Edit `static/js/app.js` to customize:
- Generation settings
- UI behavior
- API interactions
- Local storage

## 🔧 Configuration

### Image Generation Settings

```python
# In app.py
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
MAX_REFERENCE_IMAGES = 5
```

### Style Presets

```python
# In app.py - clean_prompt() function
style_prefixes = {
    'photorealistic': 'photorealistic, highly detailed, professional photography, ',
    'artistic': 'artistic, creative, expressive, ',
    'anime': 'anime style, manga style, ',
    # Add more styles...
}
```

## 📱 Mobile Support

The webapp is fully responsive and optimized for:
- ✅ iOS Safari
- ✅ Android Chrome
- ✅ Mobile Firefox
- ✅ Touch interactions
- ✅ Mobile file uploads

## 🛡️ Security Features

- File type validation
- File size limits
- Input sanitization
- CORS protection
- Rate limiting ready
- XSS protection

## 🐛 Troubleshooting

### Common Issues

1. **Images not generating**:
   - Check g4f service status
   - Verify internet connection
   - Check logs for API errors

2. **File upload fails**:
   - Check file size (max 10MB per file)
   - Verify file type is supported
   - Ensure upload directory permissions

3. **Prompt enhancement not working**:
   - Check AI service availability
   - Verify API key configuration
   - Check network connectivity

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
python app.py
```

View logs:
```bash
tail -f webapp.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the AdvAI Telegram Bot ecosystem.

## 🔗 Related

- [AdvAI Telegram Bot](https://t.me/AdvChatGptBot)
- [Main Bot Repository](../)
- [g4f Library](https://github.com/xtekky/gpt4free)

## 📞 Support

For support and questions:
- Telegram: [@techycsr](https://t.me/techycsr)
- Bot: [@AdvChatGptBot](https://t.me/AdvChatGptBot)

---

Made with ❤️ for the AI community 
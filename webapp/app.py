#!/usr/bin/env python3
"""
AdvAI Image Generator Web Application
Flask backend server with Groq for AI and g4f for images - Serverless Compatible
Now with Telegram Mini App Authentication
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

# Import config for API keys with fallback
try:
    from config import FLASK_SECRET_KEY, SESSION_TIMEOUT, TELEGRAM_MINI_APP_REQUIRED, GROQ_API_KEY
except ImportError:
    # Fallback for Vercel deployment - get from environment variables
    FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this')
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '86400'))
    TELEGRAM_MINI_APP_REQUIRED = os.environ.get('TELEGRAM_MINI_APP_REQUIRED', 'True').lower() == 'true'
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

from flask import Flask, request, jsonify, send_from_directory, Response, session, redirect, url_for
from flask_cors import CORS

# Import Multi-Platform authentication
from telegram_auth import (
    require_auth,
    require_telegram_auth,  # Backward compatibility
    authenticate_telegram_user,
    authenticate_google_user,
    get_current_user,
    clear_user_session,
    get_user_permissions,
    get_auth_config,
    is_google_auth_available,
    create_google_oauth_flow,
    generate_state_token,
    User,
    TelegramUser  # Backward compatibility alias
)

# Import Telegram logging system
from telegram_logging import log_image_generation, log_error, log_user_activity

# Import Groq for AI text generation (prompt enhancement)
from groq import Groq

# Import g4f for image generation with multi-provider support
from g4f.client import Client, AsyncClient
from g4f.Provider import (
    BlackForestLabs_Flux1Dev,
    StabilityAI_SD35Large,
    HuggingFaceInference,
    DeepseekAI_JanusPro7b,
    AnyProvider,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client for prompt enhancement
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

# Configure Flask session
app.secret_key = FLASK_SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_TIMEOUT)
app.config['SESSION_COOKIE_SECURE'] = True  # Enable in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for Telegram Mini Apps

# Serverless-friendly configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

def generate_ai_response(prompt: str) -> str:
    """Generate AI response using Groq with llama-3.3-70b-versatile"""
    try:
        if not groq_client:
            raise Exception("Groq client not configured. Please set GROQ_API_KEY.")
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        raise

async def generate_images_standalone(prompt: str, style: str = None, max_images: int = 1, width: int = 1024, height: int = 1024, model: str = "flux-dev") -> tuple:
    """Generate images using multi-provider system (async version)"""
    return await generate_images_multi_provider(prompt, style, max_images, width, height, model)

def generate_images_sync(prompt: str, style: str = None, max_images: int = 1, width: int = 1024, height: int = 1024, model: str = "flux-dev") -> tuple:
    """Generate images using multi-provider system (sync wrapper)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            generate_images_multi_provider(prompt, style, max_images, width, height, model)
        )
    finally:
        loop.close()


# =============================================================================
# MULTI-PROVIDER IMAGE GENERATION SYSTEM
# =============================================================================

# Provider configurations - auth-free providers only
IMAGE_PROVIDERS = [
    {
        "name": "BlackForestLabs_Flux1Dev",
        "provider": BlackForestLabs_Flux1Dev,
        "models": ["flux-dev", "flux"],
        "priority": 1,
        "timeout": 60,
    },
    {
        "name": "AnyProvider",
        "provider": AnyProvider,
        "models": ["flux", "flux-dev", "sdxl-turbo", "sd-3.5-large", "flux-schnell"],
        "priority": 1,
        "timeout": 60,
    },
    {
        "name": "StabilityAI_SD35Large",
        "provider": StabilityAI_SD35Large,
        "models": ["sd-3.5-large"],
        "priority": 2,
        "timeout": 60,
    },
    {
        "name": "HuggingFaceInference",
        "provider": HuggingFaceInference,
        "models": ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"],
        "priority": 2,
        "timeout": 90,
    },
    {
        "name": "DeepseekAI_JanusPro7b",
        "provider": DeepseekAI_JanusPro7b,
        "models": ["janus-pro-7b-image"],
        "priority": 3,
        "timeout": 90,
    },
]

# Model mapping for legacy and alternative names
MODEL_PROVIDER_MAP = {
    "flux": ["BlackForestLabs_Flux1Dev", "AnyProvider"],
    "flux-dev": ["BlackForestLabs_Flux1Dev", "AnyProvider"],
    "sd-3.5-large": ["StabilityAI_SD35Large", "AnyProvider"],
    "sdxl-turbo": ["AnyProvider"],
    "flux-schnell": ["AnyProvider"],
}

# Legacy model mapping
LEGACY_MODEL_MAP = {
    "dall-e3": "flux-dev",
    "dall-e-3": "flux-dev",
    "flux-pro": "flux-dev",
    "sdxl-1.0": "sd-3.5-large",
    "turbo": "flux",
}

# Fallback chains
MODEL_FALLBACK_CHAIN = {
    "flux": ["flux-dev", "sd-3.5-large", "flux-schnell"],
    "flux-dev": ["flux", "sd-3.5-large", "flux-schnell"],
    "sd-3.5-large": ["flux-dev", "flux", "sdxl-turbo"],
}

DEFAULT_IMAGE_MODEL = "flux-dev"


def normalize_model_name(model: str) -> str:
    """Convert legacy model names to current equivalents"""
    if model in LEGACY_MODEL_MAP:
        new_model = LEGACY_MODEL_MAP[model]
        logger.info(f"Mapping legacy model '{model}' to '{new_model}'")
        return new_model
    return model


def get_providers_for_model(model: str) -> list:
    """Get all provider configs that support a given model"""
    provider_names = MODEL_PROVIDER_MAP.get(model, [])
    providers = []
    for p in IMAGE_PROVIDERS:
        if p["name"] in provider_names:
            providers.append(p)
    return sorted(providers, key=lambda x: x["priority"])


async def generate_with_single_provider(provider_config: dict, prompt: str, model: str, width: int, height: int) -> tuple:
    """Generate image with a single provider"""
    provider_name = provider_config["name"]
    provider_class = provider_config["provider"]
    timeout = provider_config["timeout"]
    
    logger.info(f"Trying provider: {provider_name} with model {model}")
    
    try:
        client = AsyncClient(image_provider=provider_class)
        
        # Build generation kwargs
        kwargs = {
            "prompt": prompt,
            "model": model,
            "response_format": "url",
        }
        
        # Add dimensions for providers that support them
        if provider_name not in ["DeepseekAI_JanusPro7b"]:
            kwargs["width"] = width
            kwargs["height"] = height
        
        # Generate with timeout
        response = await asyncio.wait_for(
            client.images.generate(**kwargs),
            timeout=timeout
        )
        
        if not response or not response.data:
            return None, f"{provider_name} returned empty response"
        
        # Extract URLs
        image_urls = []
        for img_data in response.data:
            if hasattr(img_data, 'url') and img_data.url:
                url = img_data.url
                if url.startswith("http://") or url.startswith("https://"):
                    image_urls.append(url)
        
        if image_urls:
            logger.info(f"{provider_name} generated {len(image_urls)} images successfully")
            return image_urls, None
        else:
            return None, f"{provider_name} returned no valid URLs"
            
    except asyncio.TimeoutError:
        logger.warning(f"{provider_name} timed out after {timeout}s")
        return None, f"{provider_name} timed out"
    except Exception as e:
        logger.error(f"{provider_name} failed: {str(e)}")
        return None, f"{provider_name} error: {str(e)}"


async def generate_images_multi_provider(prompt: str, style: str = None, max_images: int = 1, width: int = 1024, height: int = 1024, model: str = "flux-dev") -> tuple:
    """
    Generate images using multi-provider system with automatic fallback.
    Tries multiple providers concurrently for maximum success rate.
    """
    start_time = time.time()
    
    # Style definitions
    style_definitions = {
        "default": {"prompt_additions": "ultra realistic, detailed, photographic quality"},
        "photorealistic": {"prompt_additions": "photorealistic, ultra realistic, detailed, professional photography"},
        "artistic": {"prompt_additions": "artistic, creative, expressive, painterly style"},
        "anime": {"prompt_additions": "anime style, manga style, vibrant colors"},
        "cartoon": {"prompt_additions": "cartoon style, animated, colorful, stylized"},
        "digital-art": {"prompt_additions": "digital art, concept art, trending on artstation"},
        "painting": {"prompt_additions": "oil painting, traditional art, brushstrokes, artistic"},
        "sketch": {"prompt_additions": "pencil sketch, hand drawn, artistic sketch, detailed drawing"}
    }
    
    # Enhance prompt with style
    style_info = style_definitions.get(style or "default", style_definitions["default"])
    enhanced_prompt = f"{prompt}, {style_info['prompt_additions']}"
    
    # Normalize model name (handle legacy models)
    model = normalize_model_name(model)
    
    logger.info(f"Generating {max_images} images with model '{model}', prompt: {enhanced_prompt[:100]}...")
    
    # Build list of models to try
    models_to_try = [model]
    fallbacks = MODEL_FALLBACK_CHAIN.get(model, [])
    if not fallbacks and model != DEFAULT_IMAGE_MODEL:
        models_to_try.append(DEFAULT_IMAGE_MODEL)
        fallbacks = MODEL_FALLBACK_CHAIN.get(DEFAULT_IMAGE_MODEL, [])
    models_to_try.extend(fallbacks)
    
    all_errors = []
    
    for try_model in models_to_try:
        logger.info(f"Trying model: {try_model}")
        
        # Get providers for this model
        providers = get_providers_for_model(try_model)
        
        if not providers:
            logger.warning(f"No providers available for model {try_model}")
            continue
        
        # Try providers concurrently
        tasks = []
        for provider_config in providers:
            use_model = try_model if try_model in provider_config["models"] else provider_config["models"][0]
            task = asyncio.create_task(
                generate_with_single_provider(provider_config, enhanced_prompt, use_model, width, height)
            )
            tasks.append((provider_config["name"], task))
        
        # Wait for first successful result
        pending_tasks = [t[1] for t in tasks]
        task_to_name = {t[1]: t[0] for t in tasks}
        
        while pending_tasks:
            done, pending_tasks = await asyncio.wait(
                pending_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            pending_tasks = list(pending_tasks)
            
            for completed_task in done:
                provider_name = task_to_name.get(completed_task, "Unknown")
                try:
                    urls, error = completed_task.result()
                    if urls:
                        # Cancel remaining tasks
                        for task in pending_tasks:
                            task.cancel()
                        elapsed = time.time() - start_time
                        logger.info(f"Success with {provider_name} in {elapsed:.2f}s")
                        return urls, None
                    else:
                        all_errors.append(f"{provider_name}: {error}")
                except Exception as e:
                    all_errors.append(f"{provider_name}: {str(e)}")
    
    # All providers failed
    elapsed = time.time() - start_time
    error_msg = f"All providers failed after {elapsed:.2f}s"
    if all_errors:
        error_msg += f". Errors: {'; '.join(all_errors[:3])}"
    logger.error(error_msg)
    return [], error_msg

def clean_prompt(prompt: str, style: str = 'default') -> str:
    """Clean and enhance the prompt based on style"""
    prompt = prompt.strip()
    
    # Style-specific enhancements
    style_prefixes = {
        'photorealistic': 'photorealistic, highly detailed, professional photography, ',
        'artistic': 'artistic, creative, expressive, ',
        'anime': 'anime style, manga style, ',
        'cartoon': 'cartoon style, animated, colorful, ',
        'digital-art': 'digital art, concept art, trending on artstation, ',
        'painting': 'oil painting, traditional art, brushstrokes, ',
        'sketch': 'pencil sketch, hand drawn, artistic sketch, '
    }
    
    if style in style_prefixes:
        prompt = style_prefixes[style] + prompt
    
    # Add quality enhancers
    quality_suffix = ', high quality, detailed, 4k resolution'
    if not any(term in prompt.lower() for term in ['quality', 'detailed', '4k', 'hd']):
        prompt += quality_suffix
    
    return prompt

# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/api/auth/telegram', methods=['POST'])
def telegram_auth():
    """Authenticate user with Telegram Web App data"""
    try:
        data = request.get_json()
        init_data = data.get('initData', '').strip()
        
        if not init_data:
            return jsonify({'error': 'No initialization data provided'}), 400
        
        # Authenticate user
        success, user, error = authenticate_telegram_user(init_data)
        
        if not success:
            logger.warning(f"Authentication failed: {error}")
            return jsonify({'error': error}), 401
        
        # Load premium status from database immediately after authentication
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                premium_info = loop.run_until_complete(user.get_premium_status())
                image_limit = loop.run_until_complete(user.get_image_limit())
            finally:
                loop.close()
            
            # Update user object with real premium status
            user.is_premium = premium_info.get('has_premium_access', False)
            user.premium_info = premium_info
            
            # Update session with new premium info
            from telegram_auth import update_user_session
            update_user_session(user)
            
            premium_status = {
                'is_premium': premium_info.get('is_premium', False),
                'is_admin': premium_info.get('is_admin', False),
                'has_premium_access': premium_info.get('has_premium_access', False),
                'remaining_days': premium_info.get('remaining_days', 0),
                'image_limit': image_limit,
                'expires_at': premium_info.get('expires_at')
            }
            
        except Exception as e:
            logger.error(f"Error loading premium status during Telegram auth: {e}")
            # Fallback to basic status
            premium_status = {
                'is_premium': False,
                'is_admin': False,
                'has_premium_access': False,
                'remaining_days': 0,
                'image_limit': 1,
                'expires_at': None
            }
        
        # Get user permissions (now with premium status loaded)
        permissions = get_user_permissions(user)
        
        logger.info(f"User authenticated: {user.display_name} (ID: {user.id}) - Premium: {premium_status['has_premium_access']}")
        
        # Log user authentication to Telegram channel
        try:
            log_user_activity(user, "Authentication", f"Telegram auth - Premium: {premium_status['has_premium_access']}")
        except Exception as log_error_ex:
            logger.error(f"Failed to log user authentication: {str(log_error_ex)}")
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'permissions': permissions,
            'premium': premium_status,
            'message': f'Welcome, {user.display_name}!'
        })
        
    except Exception as e:
        logger.error(f"Error in Telegram authentication: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check current authentication status"""
    user = get_current_user()
    
    if not user:
        return jsonify({
            'authenticated': False,
            'message': 'Not authenticated'
        })
    
    # Get REAL premium information from database (same as /api/auth/premium)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            premium_info = loop.run_until_complete(user.get_premium_status())
            image_limit = loop.run_until_complete(user.get_image_limit())
        finally:
            loop.close()
        
        # Update user object with real premium status
        user.is_premium = premium_info.get('has_premium_access', False)
        user.premium_info = premium_info
        user.premium_info['image_limit'] = image_limit  # Add image limit to premium info
        
        # Update session with new premium info
        from telegram_auth import update_user_session
        update_user_session(user)
        
        premium_status = {
            'is_premium': premium_info.get('is_premium', False),
            'is_admin': premium_info.get('is_admin', False),
            'has_premium_access': premium_info.get('has_premium_access', False),
            'remaining_days': premium_info.get('remaining_days', 0),
            'image_limit': image_limit,
            'expires_at': premium_info.get('expires_at')
        }
        
    except Exception as e:
        logger.error(f"Error getting premium status in auth_status: {e}")
        # Fallback to basic check if database fails
        premium_status = {
            'is_premium': user.auth_type == 'google',
            'is_admin': False,
            'has_premium_access': user.auth_type == 'google',
            'remaining_days': 0,
            'image_limit': 4 if user.auth_type == 'google' else 1,
            'expires_at': None
        }
        # Also update user object with fallback info
        user.is_premium = premium_status['has_premium_access']
        user.premium_info = premium_status
    
    # Get permissions AFTER updating premium info
    permissions = get_user_permissions(user)
    
    return jsonify({
        'authenticated': True,
        'user': user.to_dict(),
        'permissions': permissions,
        'premium': premium_status
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout current user"""
    clear_user_session()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/config', methods=['GET'])
def auth_config():
    """Get authentication configuration for frontend"""
    return jsonify(get_auth_config())

@app.route('/api/auth/premium', methods=['GET'])
@require_auth
def get_premium_status():
    """Get user's premium status information"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get premium status asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            premium_info = loop.run_until_complete(user.get_premium_status())
            available_models = loop.run_until_complete(user.get_available_models())
            image_limit = loop.run_until_complete(user.get_image_limit())
        finally:
            loop.close()
        
        # Structure response
        response_data = {
            'premium_info': premium_info,
            'available_models': {
                'text_models': available_models[0],
                'image_models': available_models[1]
            },
            'image_limit': image_limit,
            'is_admin': user.is_admin()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting premium status: {e}")
        return jsonify({'error': 'Failed to get premium status'}), 500

@app.route('/api/auth/google', methods=['GET'])
def google_auth():
    """Initiate Google OAuth flow"""
    try:
        if not is_google_auth_available():
            return jsonify({'error': 'Google authentication not available'}), 503
        
        # Generate state token for security
        state = generate_state_token()
        session['oauth_state'] = state
        
        # Create OAuth flow
        flow = create_google_oauth_flow()
        
        # Get authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return jsonify({
            'authorization_url': authorization_url,
            'state': state
        })
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        return jsonify({'error': 'Failed to initiate Google login'}), 500

@app.route('/api/auth/google/callback', methods=['GET', 'POST'])
def auth_google_callback():
    """Handle Google OAuth callback"""
    try:
        if not is_google_auth_available():
            return jsonify({'error': 'Google authentication not available'}), 503
        
        # Verify state parameter to prevent CSRF
        state = request.args.get('state')
        if not state or state != session.get('oauth_state'):
            return jsonify({'error': 'Invalid state parameter'}), 400
        
        # Clear the state from session
        session.pop('oauth_state', None)
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error')
            return jsonify({'error': f'OAuth failed: {error}'}), 400
        
        # Exchange code for tokens
        flow = create_google_oauth_flow()
        flow.fetch_token(code=code)
        
        # Get user info from ID token
        credentials = flow.credentials
        id_token_jwt = credentials.id_token
        
        # Authenticate user with the token
        success, user, error = authenticate_google_user(id_token_jwt)
        
        if not success:
            logger.warning(f"Google authentication failed: {error}")
            return jsonify({'error': error}), 401
        
        # Google users are premium by default - set premium status
        premium_status = {
            'is_premium': True,
            'is_admin': user.is_admin(),
            'has_premium_access': True,
            'remaining_days': 0,  # Unlimited for Google users
            'image_limit': 4,
            'expires_at': None  # Never expires for Google users
        }
        
        # Update user object
        user.is_premium = True
        user.premium_info = premium_status
        
        # Get user permissions
        permissions = get_user_permissions(user)
        
        logger.info(f"Google user authenticated: {user.display_name} (ID: {user.id}) - Premium: True")
        
        # Log Google authentication to Telegram channel
        try:
            log_user_activity(user, "Authentication", f"Google OAuth - Premium: True")
        except Exception as log_error_ex:
            logger.error(f"Failed to log Google authentication: {str(log_error_ex)}")
        
        # Check if this is a direct API call or browser redirect
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            # API call - return JSON
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'permissions': permissions,
                'premium': premium_status,
                'message': f'Welcome, {user.display_name}!'
            })
        else:
            # Browser redirect - redirect to main page with success
            return redirect('/?auth=success')
            
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({'error': 'Authentication failed'}), 500
        else:
            return redirect('/?auth=error')

@app.route('/api/auth/google/token', methods=['POST'])
def google_token_auth():
    """Authenticate with Google ID token directly"""
    try:
        if not is_google_auth_available():
            return jsonify({'error': 'Google authentication not available'}), 503
        
        data = request.get_json()
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'error': 'No token provided'}), 400
        
        # Authenticate user with the token
        success, user, error = authenticate_google_user(token)
        
        if not success:
            logger.warning(f"Google token authentication failed: {error}")
            return jsonify({'error': error}), 401
        
        # Google users are premium by default - set premium status
        premium_status = {
            'is_premium': True,
            'is_admin': user.is_admin(),
            'has_premium_access': True,
            'remaining_days': 0,  # Unlimited for Google users
            'image_limit': 4,
            'expires_at': None  # Never expires for Google users
        }
        
        # Update user object
        user.is_premium = True
        user.premium_info = premium_status
        
        # Get user permissions
        permissions = get_user_permissions(user)
        
        logger.info(f"Google user authenticated via token: {user.display_name} (ID: {user.id}) - Premium: True")
        
        # Log Google token authentication to Telegram channel
        try:
            log_user_activity(user, "Authentication", f"Google Token - Premium: True")
        except Exception as log_error_ex:
            logger.error(f"Failed to log Google token authentication: {str(log_error_ex)}")
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'permissions': permissions,
            'premium': premium_status,
            'message': f'Welcome, {user.display_name}!'
        })
        
    except Exception as e:
        logger.error(f"Error in Google token authentication: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/auth/update-premium', methods=['POST'])
@require_auth
def update_user_premium_status():
    """Update user's premium status in session (for frontend-detected premium status)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401
        
        data = request.get_json()
        is_premium = data.get('is_premium', False)
        
        # Only allow updating to premium for Telegram users who are verified as premium
        if user.auth_type == 'telegram' and is_premium:
            # Update user object
            user.is_premium = True
            
            # Update session
            from telegram_auth import update_user_session
            update_user_session(user)
            
            # Get updated permissions
            permissions = get_user_permissions(user)
            
            return jsonify({
                'success': True,
                'message': 'Premium status updated',
                'user': user.to_dict(),
                'permissions': permissions
            })
        else:
            return jsonify({'error': 'Invalid premium status update request'}), 400
            
    except Exception as e:
        logger.error(f"Error updating premium status: {e}")
        return jsonify({'error': 'Failed to update premium status'}), 500

# =============================================================================
# PROTECTED ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return f"<h1>AdvAI Image Generator</h1><p>Service starting...</p><p>Error: {str(e)}</p>", 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {e}")
        return "File not found", 404

@app.route('/api/enhance-prompt', methods=['POST'])
@require_auth
def enhance_prompt():
    """Enhance a user prompt using AI"""
    try:
        user = get_current_user()
        permissions = get_user_permissions(user)
        
        if not permissions.get('can_enhance_prompts'):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        original_prompt = data.get('prompt', '').strip()
        
        if not original_prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        if len(original_prompt) > 700:
            return jsonify({'error': 'Prompt is too long'}), 400
        
        # AI prompt enhancement
        enhancement_prompt = f"""
        You are an expert at creating detailed, creative image generation prompts. 
        Enhance the following prompt to be more detailed, vivid, and likely to produce a stunning AI-generated image.
        
        Original prompt: "{original_prompt}"
        
        Please provide an enhanced version that:
        - Adds more visual details and descriptions
        - Adds lighting, mood, and atmosphere details
        - Keeps the core concept intact
        - Is suitable for AI image generation
        - Keep it detailed and comprehensive
        
        Enhanced prompt:"""
        
        try:
            enhanced = generate_ai_response(enhancement_prompt)
            
            # Clean up the response
            enhanced = enhanced.strip()
            if enhanced.startswith('"') and enhanced.endswith('"'):
                enhanced = enhanced[1:-1]
            
            # Only trim if longer than 700 characters
            if len(enhanced) > 700:
                enhanced = enhanced[:697] + "..."
            
            logger.info(f"Enhanced prompt for user {user.id}: {original_prompt[:50]}... -> {enhanced[:50]}...")
            
            # Log prompt enhancement to Telegram channel
            try:
                log_user_activity(user, "PromptEnhancement", f"Original: {original_prompt[:100]}... -> Enhanced: {enhanced[:100]}...")
            except Exception as log_error_ex:
                logger.error(f"Failed to log prompt enhancement: {str(log_error_ex)}")
            
            return jsonify({
                'original_prompt': original_prompt,
                'enhanced_prompt': enhanced,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return jsonify({'error': 'Failed to enhance prompt'}), 500
        
    except Exception as e:
        logger.error(f"Error in enhance_prompt: {e}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/api/generate', methods=['POST'])
@require_auth
def generate_images_api():
    """Generate images using AI"""
    try:
        user = get_current_user()
        permissions = get_user_permissions(user)
        
        if not permissions.get('can_generate_images'):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Validate input
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        if len(prompt) > 1000:
            return jsonify({'error': 'Prompt is too long (max 1000 characters)'}), 400
        
        # Get generation parameters
        style = data.get('style', 'default')
        model = data.get('model', 'flux')
        requested_images = int(data.get('num_images', 1))
        
        # Use requested images directly (frontend UI already handles limits)
        num_images = max(1, min(requested_images, 4))  # Cap at 4 images max
        
        # Parse image size
        size = data.get('size', '1024x1024')
        try:
            if 'x' in size:
                width, height = map(int, size.split('x'))
            else:
                width = height = 1024
            
            # Validate dimensions
            width = max(256, min(2048, width))
            height = max(256, min(2048, height))
            
        except (ValueError, TypeError):
            width = height = 1024
        
        logger.info(f"Generating {num_images} images for user {user.id}: {prompt[:50]}...")
        
        # Generate images
        try:
            image_urls, error = generate_images_sync(
                prompt=prompt,
                style=style,
                max_images=num_images,
                width=width,
                height=height,
                model=model
            )
            
            if error or not image_urls:
                # Log error to Telegram channel
                try:
                    log_error("ImageGeneration", error or 'Failed to generate images', user.id, f"Prompt: {prompt[:100]}")
                except Exception as log_error_ex:
                    logger.error(f"Failed to log image generation error: {str(log_error_ex)}")
                
                return jsonify({
                    'error': error or 'Failed to generate images',
                    'success': False
                }), 500
            
            # Log successful generation
            logger.info(f"Successfully generated {len(image_urls)} images for user {user.id}")
            
            # Log to Telegram channel (async)
            generation_data = {
                'size': f"{width}x{height}",
                'model': model,
                'count': len(image_urls)
            }
            
            # Run logging in background to avoid blocking the response
            try:
                log_image_generation(user, prompt, style, image_urls, generation_data)
            except Exception as log_error_ex:
                logger.error(f"Failed to log image generation: {str(log_error_ex)}")
            
            return jsonify({
                'success': True,
                'images': image_urls,
                'prompt': prompt,
                'style': style,
                'model': model,
                'size': f"{width}x{height}",
                'count': len(image_urls)
            })
            
        except Exception as e:
            logger.error(f"Error generating images: {e}")
            return jsonify({'error': 'Image generation failed'}), 500
        
    except Exception as e:
        logger.error(f"Error in generate_images_api: {e}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'telegram_auth_required': TELEGRAM_MINI_APP_REQUIRED
    })

@app.route('/api/debug/premium', methods=['GET'])
@require_auth
def debug_premium():
    """Debug premium system (temporary endpoint)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Check if premium system is available
        from telegram_auth import PREMIUM_SYSTEM_AVAILABLE
        
        debug_info = {
            'user_auth_type': user.auth_type,
            'user_telegram_id': getattr(user, 'telegram_id', None),
            'user_telegram_id_type': type(getattr(user, 'telegram_id', None)).__name__,
            'premium_system_available': PREMIUM_SYSTEM_AVAILABLE,
            'user_id_for_premium': user.get_user_id_for_premium(),
        }
        
                # Test database connection
        try:
            from database_service import webapp_db_service
            db_test = webapp_db_service.test_connection()
            debug_info['database_connection'] = db_test
            
            # Test premium collection access
            from database_service import get_premium_users_collection
            premium_collection = get_premium_users_collection()
            
            # Get count of premium users
            premium_count = premium_collection.count_documents({"is_premium": True})
            debug_info['total_premium_users'] = premium_count
            
            # If this is a Telegram user, check if there's ANY record for this user
            if user.auth_type == 'telegram' and user.telegram_id:
                any_record = premium_collection.find_one({"user_id": user.telegram_id})
                debug_info['user_record_in_db'] = any_record is not None
                if any_record:
                    debug_info['user_record_details'] = {
                        'user_id': any_record.get('user_id'),
                        'is_premium': any_record.get('is_premium'),
                        'premium_expires_at': str(any_record.get('premium_expires_at')),
                        'premium_since': str(any_record.get('premium_since'))
                    }
                
        except Exception as e:
            debug_info['database_error'] = str(e)
            import traceback
            debug_info['database_traceback'] = traceback.format_exc()
        
        # Try to check premium status with detailed logging
        if user.auth_type == 'telegram' and user.telegram_id:
            try:
                from premium_management import is_user_premium
                debug_info['import_success'] = True
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    premium_result = loop.run_until_complete(is_user_premium(user.telegram_id))
                    debug_info['premium_check_result'] = premium_result
                finally:
                    loop.close()
            except ImportError as e:
                debug_info['import_error'] = str(e)
            except Exception as e:
                debug_info['premium_check_error'] = str(e)
                import traceback
                debug_info['premium_check_traceback'] = traceback.format_exc()
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Error in debug premium: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/premium-users', methods=['GET'])
def get_all_premium_users():
    """Get all premium user IDs for testing purposes."""
    try:
        from database_service import get_premium_users_collection
        premium_collection = get_premium_users_collection()
        
        # Get all premium users that are currently active
        premium_users = list(premium_collection.find(
            {"is_premium": True}, 
            {"user_id": 1, "_id": 0}
        ))
        
        # Extract just the user IDs as integers
        premium_user_ids = [user["user_id"] for user in premium_users if isinstance(user.get("user_id"), int)]
        
        return jsonify({
            'success': True,
            'premium_user_ids': premium_user_ids,
            'total_count': len(premium_user_ids)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get user statistics"""
    user = get_current_user()
    
    return jsonify({
        'user_id': user.id if user else None,
        'display_name': user.display_name if user else None,
        'is_premium': user.is_premium if user else False,
        'permissions': get_user_permissions(user)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# APP STARTUP
# =============================================================================

def run_app():
    """Run the Flask application"""
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting AdvAI Image Generator WebApp on port {port}")
    logger.info(f"Telegram Mini App authentication: {'Enabled' if TELEGRAM_MINI_APP_REQUIRED else 'Disabled'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == '__main__':
    run_app() 
#!/usr/bin/env python3
"""
Multi-Platform Authentication Module
Handles validation of Telegram Web App data, Google OAuth, and user sessions
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
import secrets
import string

# Google OAuth imports
try:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    from google_auth_oauthlib.flow import Flow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

try:
    from config import BOT_TOKEN, SESSION_TIMEOUT, TELEGRAM_MINI_APP_REQUIRED, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ADMINS
except ImportError:
    # Fallback for environment variables
    import os
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '86400'))  # 24 hours
    TELEGRAM_MINI_APP_REQUIRED = os.environ.get('TELEGRAM_MINI_APP_REQUIRED', 'True').lower() == 'true'
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    ADMINS = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',') if x.strip().isdigit()]

# Import premium management functions
try:
    from premium_management import (
        is_user_premium, 
        get_premium_status_info,
        is_admin_user,
        get_user_image_limit,
        get_available_models
    )
    PREMIUM_SYSTEM_AVAILABLE = True
except ImportError:
    PREMIUM_SYSTEM_AVAILABLE = False

class User:
    """Represents a user with their data from either Telegram or Google"""
    
    def __init__(self, user_data: Dict[str, Any], auth_type: str = 'telegram'):
        self.auth_type = auth_type  # 'telegram' or 'google'
        
        if auth_type == 'telegram':
            self.id = f"tg_{user_data.get('id')}"
            self.telegram_id = user_data.get('id')
            self.first_name = user_data.get('first_name', '')
            self.last_name = user_data.get('last_name', '')
            self.username = user_data.get('username', '')
            self.language_code = user_data.get('language_code', 'en')
            # Note: is_premium from Telegram data is not reliable for our premium system
            # We'll check the database for actual premium status
            self.allows_write_to_pm = user_data.get('allows_write_to_pm', False)
            self.photo_url = user_data.get('photo_url', '')
            self.email = None
        elif auth_type == 'google':
            self.id = f"g_{user_data.get('sub')}"  # Google user ID
            self.google_id = user_data.get('sub')
            self.first_name = user_data.get('given_name', '')
            self.last_name = user_data.get('family_name', '')
            self.username = None
            self.language_code = user_data.get('locale', 'en')
            # Google users get premium status by default
            self.allows_write_to_pm = True
            self.photo_url = user_data.get('picture', '')
            self.email = user_data.get('email', '')
            self.telegram_id = None
        
        # Initialize premium status (will be updated by get_premium_status)
        self.is_premium = False
        self.premium_info = None
        
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        name_parts = [self.first_name, self.last_name]
        return ' '.join(part for part in name_parts if part).strip()
    
    @property
    def display_name(self) -> str:
        """Get user's display name (full name, username, or email)"""
        if self.full_name:
            return self.full_name
        elif self.username:
            return f"@{self.username}"
        elif self.email:
            return self.email
        else:
            return f"User {self.id}"
    
    def get_user_id_for_premium(self) -> Optional[int]:
        """Get the user ID to use for premium checking (only Telegram users have premium system)"""
        if self.auth_type == 'telegram' and self.telegram_id:
            return self.telegram_id
        return None
    
    async def get_premium_status(self) -> Dict[str, Any]:
        """Get comprehensive premium status information from database"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            return {
                "is_premium": self.auth_type == 'google',  # Google users are premium
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 4 if self.auth_type == 'google' else 1,
                "has_premium_access": self.auth_type == 'google'
            }
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            # Non-Telegram users (Google) get premium status
            return {
                "is_premium": self.auth_type == 'google',
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 4 if self.auth_type == 'google' else 1,
                "has_premium_access": self.auth_type == 'google'
            }
        
        try:
            premium_info = await get_premium_status_info(user_id)
            self.is_premium = premium_info['has_premium_access']
            self.premium_info = premium_info
            return premium_info
        except Exception as e:
            print(f"Error getting premium status for user {user_id}: {e}")
            return {
                "is_premium": False,
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 1,
                "has_premium_access": False
            }
    
    async def get_image_limit(self) -> int:
        """Get the maximum number of images this user can generate per request"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            return 4 if self.auth_type == 'google' else 1
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            return 4 if self.auth_type == 'google' else 1
        
        try:
            return await get_user_image_limit(user_id)
        except Exception:
            return 1
    
    async def get_available_models(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Get available AI models for this user"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            # Default models for non-premium users
            text_models = {"gpt-4o": "GPT-4o"}
            image_models = {"dall-e3": "DALL-E 3", "flux": "Flux"}
            if self.auth_type == 'google':
                # Google users get all models
                text_models.update({"gpt-4.1": "GPT-4.1", "qwen3": "Qwen3"})
                image_models.update({"flux-pro": "Flux Pro"})
            return text_models, image_models
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            # Non-Telegram users (Google) get all models
            from premium_management import TEXT_MODELS, IMAGE_MODELS
            return TEXT_MODELS, IMAGE_MODELS
        
        try:
            return await get_available_models(user_id)
        except Exception:
            # Fallback to basic models
            return {"gpt-4o": "GPT-4o"}, {"dall-e3": "DALL-E 3", "flux": "Flux"}
    
    def is_admin(self) -> bool:
        """Check if user is an admin"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            return False
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            return False
        
        try:
            return is_admin_user(user_id)
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'auth_type': self.auth_type,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'language_code': self.language_code,
            'is_premium': self.is_premium,
            'allows_write_to_pm': self.allows_write_to_pm,
            'photo_url': self.photo_url,
            'email': self.email,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'telegram_id': getattr(self, 'telegram_id', None),
            'google_id': getattr(self, 'google_id', None),
            'premium_info': getattr(self, 'premium_info', None)
        }

# Backward compatibility - alias for existing code
TelegramUser = User

def validate_telegram_webapp_data(init_data: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate Telegram Web App initialization data
    
    Args:
        init_data: The initData string from Telegram Web App
        
    Returns:
        Tuple of (is_valid, parsed_data, error_message)
    """
    if not BOT_TOKEN:
        return False, None, "Bot token not configured"
    
    if not init_data:
        return False, None, "No initialization data provided"
    
    try:
        # Parse the URL-encoded data
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        
        # Extract hash from data
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return False, None, "No hash found in initialization data"
        
        # Check auth_date to prevent replay attacks
        auth_date = parsed_data.get('auth_date')
        if not auth_date:
            return False, None, "No auth_date found in initialization data"
        
        try:
            auth_timestamp = int(auth_date)
            current_timestamp = int(time.time())
            
            # Allow 24 hours window for auth_date (adjust as needed)
            if current_timestamp - auth_timestamp > SESSION_TIMEOUT:
                return False, None, "Initialization data is too old"
        except (ValueError, TypeError):
            return False, None, "Invalid auth_date format"
        
        # Create data check string according to Telegram specs
        data_check_arr = []
        for key, value in sorted(parsed_data.items()):
            data_check_arr.append(f"{key}={value}")
        data_check_string = "\n".join(data_check_arr)
        
        # Generate secret key from bot token
        secret_key = hmac.new(
            "WebAppData".encode(),
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate expected hash
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare hashes
        if not hmac.compare_digest(received_hash, expected_hash):
            return False, None, "Invalid hash - data may be tampered with"
        
        # Parse user data if present
        user_data = None
        if 'user' in parsed_data:
            try:
                user_data = json.loads(parsed_data['user'])
            except json.JSONDecodeError:
                return False, None, "Invalid user data format"
        
        return True, {
            'user': user_data,
            'auth_date': auth_timestamp,
            'query_id': parsed_data.get('query_id'),
            'start_param': parsed_data.get('start_param'),
            'chat_type': parsed_data.get('chat_type'),
            'chat_instance': parsed_data.get('chat_instance')
        }, None
        
    except Exception as e:
        return False, None, f"Error validating data: {str(e)}"

def create_google_oauth_flow(redirect_uri: str = None):
    """Create Google OAuth flow"""
    if not GOOGLE_AUTH_AVAILABLE:
        raise ImportError("Google auth libraries not installed")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth not configured")
    
    if not redirect_uri:
        redirect_uri = url_for('auth_google_callback', _external=True)
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=['openid', 'email', 'profile']
    )
    flow.redirect_uri = redirect_uri
    return flow

def validate_google_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate Google ID token
    
    Args:
        token: Google ID token
        
    Returns:
        Tuple of (is_valid, user_data, error_message)
    """
    if not GOOGLE_AUTH_AVAILABLE:
        return False, None, "Google auth not available"
    
    if not GOOGLE_CLIENT_ID:
        return False, None, "Google OAuth not configured"
    
    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Check if the token is valid
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return False, None, "Invalid token issuer"
        
        return True, id_info, None
        
    except ValueError as e:
        return False, None, f"Invalid token: {str(e)}"
    except Exception as e:
        return False, None, f"Error validating token: {str(e)}"

def create_user_session(user_data: Dict[str, Any], auth_type: str = 'telegram') -> User:
    """
    Create a user session from validated data
    
    Args:
        user_data: Validated user data from Telegram or Google
        auth_type: Authentication type ('telegram' or 'google')
        
    Returns:
        User object
    """
    user = User(user_data, auth_type)
    
    # Store user data in Flask session
    session['user'] = user.to_dict()
    session['authenticated'] = True
    session['auth_time'] = time.time()
    session['user_id'] = user.id
    session['auth_type'] = auth_type
    
    # Set session to be permanent and configure timeout
    session.permanent = True
    
    return user

def get_current_user() -> Optional[User]:
    """
    Get current authenticated user from session
    
    Returns:
        User object if authenticated, None otherwise
    """
    if not session.get('authenticated'):
        return None
    
    # Check session timeout
    auth_time = session.get('auth_time', 0)
    if time.time() - auth_time > SESSION_TIMEOUT:
        clear_user_session()
        return None
    
    user_data = session.get('user')
    if not user_data:
        return None
    
    # Handle session restoration properly
    auth_type = user_data.get('auth_type', 'telegram')
    
    # If this is a restored session, recreate the user object properly
    if auth_type == 'google' and 'given_name' not in user_data and 'first_name' in user_data:
        # Convert stored session data back to Google token format for proper User construction
        google_user_data = {
            'sub': user_data.get('google_id', ''),
            'given_name': user_data.get('first_name', ''),
            'family_name': user_data.get('last_name', ''),
            'email': user_data.get('email', ''),
            'picture': user_data.get('photo_url', ''),
            'locale': user_data.get('language_code', 'en')
        }
        return User(google_user_data, auth_type)
    elif auth_type == 'telegram' and 'id' not in user_data and 'telegram_id' in user_data:
        # Convert stored session data back to Telegram format for proper User construction
        telegram_user_data = {
            'id': user_data.get('telegram_id', ''),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username', ''),
            'language_code': user_data.get('language_code', 'en'),
            'is_premium': user_data.get('is_premium', False),
            'allows_write_to_pm': user_data.get('allows_write_to_pm', False),
            'photo_url': user_data.get('photo_url', '')
        }
        return User(telegram_user_data, auth_type)
    else:
        # This is fresh session data, use as-is
        return User(user_data, auth_type)

def clear_user_session():
    """Clear user session data"""
    session.pop('user', None)
    session.pop('telegram_user', None)  # Backward compatibility
    session.pop('authenticated', None)
    session.pop('auth_time', None)
    session.pop('user_id', None)
    session.pop('auth_type', None)

def generate_state_token() -> str:
    """Generate a secure state token for OAuth"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(32))

def require_auth(f):
    """
    Decorator to require authentication for routes (Telegram or Google)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not TELEGRAM_MINI_APP_REQUIRED and not GOOGLE_CLIENT_ID:
            # Authentication disabled, proceed without user
            return f(*args, **kwargs)
        
        user = get_current_user()
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please login to access this feature',
                'auth_options': {
                    'telegram': bool(BOT_TOKEN and TELEGRAM_MINI_APP_REQUIRED),
                    'google': bool(GOOGLE_CLIENT_ID and GOOGLE_AUTH_AVAILABLE)
                }
            }), 401
        
        # Add user to request context
        request.user = user
        request.telegram_user = user  # Backward compatibility
        return f(*args, **kwargs)
    
    return decorated_function

# Backward compatibility
require_telegram_auth = require_auth

def authenticate_telegram_user(init_data: str) -> Tuple[bool, Optional[User], Optional[str]]:
    """
    Complete authentication flow for Telegram user
    
    Args:
        init_data: Telegram Web App initialization data
        
    Returns:
        Tuple of (success, user_object, error_message)
    """
    # Validate the initialization data
    is_valid, parsed_data, error = validate_telegram_webapp_data(init_data)
    
    if not is_valid:
        return False, None, error
    
    if not parsed_data or not parsed_data.get('user'):
        return False, None, "No user data found in initialization data"
    
    # Create user session
    try:
        user = create_user_session(parsed_data['user'], 'telegram')
        return True, user, None
    except Exception as e:
        return False, None, f"Error creating user session: {str(e)}"

def authenticate_google_user(token: str) -> Tuple[bool, Optional[User], Optional[str]]:
    """
    Complete authentication flow for Google user
    
    Args:
        token: Google ID token
        
    Returns:
        Tuple of (success, user_object, error_message)
    """
    # Validate the token
    is_valid, user_data, error = validate_google_token(token)
    
    if not is_valid:
        return False, None, error
    
    if not user_data:
        return False, None, "No user data found in token"
    
    # Create user session
    try:
        user = create_user_session(user_data, 'google')
        return True, user, None
    except Exception as e:
        return False, None, f"Error creating user session: {str(e)}"

def get_user_permissions(user: User) -> Dict[str, bool]:
    """
    Get user permissions based on their status
    
    Args:
        user: User object
        
    Returns:
        Dictionary of permissions
    """
    if not user:
        return {
            'can_generate_images': False,
            'can_enhance_prompts': False,
            'can_access_premium_models': False,
            'can_generate_multiple_images': False,
            'max_images_per_request': 0
        }
    
    return {
        'can_generate_images': True,
        'can_enhance_prompts': True,
        'can_access_premium_models': user.is_premium,
        'can_generate_multiple_images': True,
        'max_images_per_request': 4 if user.is_premium else 2
    }

def is_google_auth_available() -> bool:
    """Check if Google authentication is available and configured"""
    return GOOGLE_AUTH_AVAILABLE and bool(GOOGLE_CLIENT_ID) and bool(GOOGLE_CLIENT_SECRET)

def get_auth_config() -> Dict[str, Any]:
    """Get authentication configuration for frontend"""
    return {
        'telegram_enabled': bool(BOT_TOKEN and TELEGRAM_MINI_APP_REQUIRED),
        'google_enabled': is_google_auth_available(),
        'google_client_id': GOOGLE_CLIENT_ID if is_google_auth_available() else None,
        'session_timeout': SESSION_TIMEOUT
    } 
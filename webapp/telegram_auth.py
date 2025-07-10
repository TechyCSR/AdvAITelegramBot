#!/usr/bin/env python3
"""
Telegram Mini App Authentication Module
Handles validation of Telegram Web App data and user sessions
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session

try:
    from config import BOT_TOKEN, SESSION_TIMEOUT, TELEGRAM_MINI_APP_REQUIRED
except ImportError:
    # Fallback for environment variables
    import os
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '86400'))  # 24 hours
    TELEGRAM_MINI_APP_REQUIRED = os.environ.get('TELEGRAM_MINI_APP_REQUIRED', 'True').lower() == 'true'

class TelegramUser:
    """Represents a Telegram user with their data"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get('id')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.username = user_data.get('username', '')
        self.language_code = user_data.get('language_code', 'en')
        self.is_premium = user_data.get('is_premium', False)
        self.allows_write_to_pm = user_data.get('allows_write_to_pm', False)
        self.photo_url = user_data.get('photo_url', '')
        
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        name_parts = [self.first_name, self.last_name]
        return ' '.join(part for part in name_parts if part).strip()
    
    @property
    def display_name(self) -> str:
        """Get user's display name (full name or username)"""
        return self.full_name or f"@{self.username}" if self.username else f"User {self.id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'language_code': self.language_code,
            'is_premium': self.is_premium,
            'allows_write_to_pm': self.allows_write_to_pm,
            'photo_url': self.photo_url,
            'full_name': self.full_name,
            'display_name': self.display_name
        }

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

def create_user_session(user_data: Dict[str, Any]) -> TelegramUser:
    """
    Create a user session from validated Telegram data
    
    Args:
        user_data: Validated user data from Telegram
        
    Returns:
        TelegramUser object
    """
    telegram_user = TelegramUser(user_data)
    
    # Store user data in Flask session
    session['telegram_user'] = telegram_user.to_dict()
    session['authenticated'] = True
    session['auth_time'] = time.time()
    session['user_id'] = telegram_user.id
    
    # Set session to be permanent and configure timeout
    session.permanent = True
    
    return telegram_user

def get_current_user() -> Optional[TelegramUser]:
    """
    Get current authenticated user from session
    
    Returns:
        TelegramUser object if authenticated, None otherwise
    """
    if not session.get('authenticated'):
        return None
    
    # Check session timeout
    auth_time = session.get('auth_time', 0)
    if time.time() - auth_time > SESSION_TIMEOUT:
        clear_user_session()
        return None
    
    user_data = session.get('telegram_user')
    if not user_data:
        return None
    
    return TelegramUser(user_data)

def clear_user_session():
    """Clear user session data"""
    session.pop('telegram_user', None)
    session.pop('authenticated', None)
    session.pop('auth_time', None)
    session.pop('user_id', None)

def require_telegram_auth(f):
    """
    Decorator to require Telegram authentication for routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not TELEGRAM_MINI_APP_REQUIRED:
            # Authentication disabled, proceed with dummy user
            return f(*args, **kwargs)
        
        user = get_current_user()
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please open this app through Telegram'
            }), 401
        
        # Add user to request context
        request.telegram_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def authenticate_telegram_user(init_data: str) -> Tuple[bool, Optional[TelegramUser], Optional[str]]:
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
        user = create_user_session(parsed_data['user'])
        return True, user, None
    except Exception as e:
        return False, None, f"Error creating user session: {str(e)}"

def get_user_permissions(user: TelegramUser) -> Dict[str, bool]:
    """
    Get user permissions based on their Telegram status
    
    Args:
        user: TelegramUser object
        
    Returns:
        Dictionary of permissions
    """
    return {
        'can_generate_images': True,
        'can_enhance_prompts': True,
        'can_access_premium_models': user.is_premium if user else False,
        'can_generate_multiple_images': True,
        'max_images_per_request': 4 if user and user.is_premium else 2
    } 
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

# Import premium management
try:
    from premium_management import PremiumManager
    PREMIUM_SYSTEM_AVAILABLE = True
except ImportError:
    PREMIUM_SYSTEM_AVAILABLE = False

class User:
    """Represents a user with their data from either Telegram or Google"""
    
    def __init__(self, user_data: Dict[str, Any], auth_type: str = 'telegram'):
        self.auth_type = auth_type  # 'telegram' or 'google'
        
        if auth_type == 'telegram':
            # Convert telegram ID to integer for database compatibility
            telegram_id_raw = user_data.get('id')
            try:
                self.telegram_id = int(telegram_id_raw) if telegram_id_raw else None
            except (ValueError, TypeError):
                self.telegram_id = None
                print(f"[ERROR] Failed to convert Telegram ID to int: {telegram_id_raw}")
            
            self.id = f"tg_{telegram_id_raw}"
            self.first_name = user_data.get('first_name', '')
            self.last_name = user_data.get('last_name', '')
            self.username = user_data.get('username', '')
            self.language_code = user_data.get('language_code', 'en')
            self.allows_write_to_pm = user_data.get('allows_write_to_pm', False)
            self.photo_url = user_data.get('photo_url', '')
            self.email = None
            
            print(f"[USER-DEBUG] Created Telegram user: ID={self.telegram_id}, raw_id={telegram_id_raw}, type={type(self.telegram_id)}")
            
        elif auth_type == 'google':
            self.id = f"g_{user_data.get('sub')}"  # Google user ID
            self.google_id = user_data.get('sub')
            self.first_name = user_data.get('given_name', '')
            self.last_name = user_data.get('family_name', '')
            self.username = None
            self.language_code = user_data.get('locale', 'en')
            self.allows_write_to_pm = True
            self.photo_url = user_data.get('picture', '')
            self.email = user_data.get('email', '')
            self.telegram_id = None
            
            print(f"[USER-DEBUG] Created Google user: ID={self.id}")
        
        # Initialize premium status (will be loaded separately)
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
            print(f"[USER-DEBUG] Premium user ID: {self.telegram_id}")
            return self.telegram_id
        print(f"[USER-DEBUG] No premium user ID available for {self.auth_type} user")
        return None
    
    async def get_premium_status(self) -> Dict[str, Any]:
        """Get comprehensive premium status information from database using new system"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            print("[USER-DEBUG] Premium system not available, using fallback")
            return {
                "is_premium": self.auth_type == 'google',
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 4 if self.auth_type == 'google' else 1,
                "has_premium_access": self.auth_type == 'google'
            }
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            # Non-Telegram users (Google) get premium status
            print(f"[USER-DEBUG] Google user gets premium by default")
            return {
                "is_premium": self.auth_type == 'google',
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 4 if self.auth_type == 'google' else 1,
                "has_premium_access": self.auth_type == 'google'
            }
        
        try:
            print(f"[USER-DEBUG] Getting comprehensive status for Telegram user: {user_id}")
            premium_info = await PremiumManager.get_comprehensive_status(user_id)
            print(f"[USER-DEBUG] Premium info result: {premium_info}")
            
            # Update user object
            self.is_premium = premium_info.get('has_premium_access', False)
            self.premium_info = premium_info
            
            return premium_info
        except Exception as e:
            print(f"[USER-ERROR] Error getting premium status for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "is_premium": False,
                "is_admin": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": 1,
                "has_premium_access": False,
                "error": str(e)
            }
    
    async def get_image_limit(self) -> int:
        """Get the maximum number of images this user can generate per request"""
        if not PREMIUM_SYSTEM_AVAILABLE:
            return 4 if self.auth_type == 'google' else 1
        
        user_id = self.get_user_id_for_premium()
        if not user_id:
            return 4 if self.auth_type == 'google' else 1
        
        try:
            status = await PremiumManager.get_comprehensive_status(user_id)
            return status["image_limit"]
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
            status = await PremiumManager.get_comprehensive_status(user_id)
            return status["available_text_models"], status["available_image_models"]
        except Exception:
            # Fallback to basic models
            return {"gpt-4o": "GPT-4o"}, {"dall-e3": "DALL-E 3", "flux": "Flux"}
    
    def is_admin(self) -> bool:
        """Check if this user is an admin"""
        if self.auth_type == 'telegram' and self.telegram_id:
            return self.telegram_id in ADMINS
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'auth_type': self.auth_type,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'username': self.username,
            'email': self.email,
            'language_code': self.language_code,
            'photo_url': self.photo_url,
            'is_premium': self.is_premium,
            'telegram_id': self.telegram_id,
            'google_id': getattr(self, 'google_id', None),
            'allows_write_to_pm': self.allows_write_to_pm,
            'is_admin': self.is_admin()
        }

# Backward compatibility - alias for existing code
TelegramUser = User

def validate_telegram_webapp_data(init_data: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate Telegram Web App initialization data
    Returns: (is_valid, user_data, error_message)
    """
    try:
        # Parse the init data
        parsed_data = urllib.parse.parse_qs(init_data, keep_blank_values=True)
        
        # Extract user data
        if 'user' not in parsed_data:
            return False, None, "No user data in initialization string"
        
        user_json = parsed_data['user'][0]
        user_data = json.loads(user_json)
        
        # Extract hash for validation
        if 'hash' not in parsed_data:
            return False, None, "No hash in initialization string"
        
        provided_hash = parsed_data['hash'][0]
        
        # Create validation string (excluding hash)
        validation_parts = []
        for key in sorted(parsed_data.keys()):
            if key != 'hash':
                value = parsed_data[key][0]
                validation_parts.append(f"{key}={value}")
        
        validation_string = '\n'.join(validation_parts)
        
        # Create HMAC key
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Calculate expected hash
        expected_hash = hmac.new(secret_key, validation_string.encode(), hashlib.sha256).hexdigest()
        
        # Verify hash
        if not hmac.compare_digest(provided_hash, expected_hash):
            return False, None, "Invalid hash - data may be tampered"
        
        # Check data age (optional - comment out if causing issues)
        # if 'auth_date' in parsed_data:
        #     auth_date = int(parsed_data['auth_date'][0])
        #     current_time = int(time.time())
        #     if current_time - auth_date > 86400:  # 24 hours
        #         return False, None, "Initialization data is too old"
        
        return True, user_data, None
        
    except json.JSONDecodeError:
        return False, None, "Invalid JSON in user data"
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"

def create_google_oauth_flow(redirect_uri: str = None):
    """Create Google OAuth flow"""
    if not GOOGLE_AUTH_AVAILABLE:
        return None
        
    if not redirect_uri:
        redirect_uri = url_for('auth_google_callback', _external=True)
    
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=['openid', 'email', 'profile'],
        redirect_uri=redirect_uri
    )

def validate_google_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate Google ID token
    Returns: (is_valid, user_data, error_message)
    """
    if not GOOGLE_AUTH_AVAILABLE:
        return False, None, "Google authentication not available"
    
    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Token is valid, extract user information
        return True, id_info, None
        
    except ValueError as e:
        return False, None, f"Invalid token: {str(e)}"
    except Exception as e:
        return False, None, f"Token validation error: {str(e)}"

def create_user_session(user_data: Dict[str, Any], auth_type: str = 'telegram') -> User:
    """Create a new user session"""
    user = User(user_data, auth_type)
    
    # Store in session
    session['user_id'] = user.id
    session['auth_type'] = auth_type
    session['user_data'] = user.to_dict()
    session['login_time'] = datetime.now().isoformat()
    session.permanent = True
    
    print(f"[SESSION-DEBUG] Created session for {auth_type} user: {user.id}")
    return user

def update_user_session(user: User):
    """Update user session with new information"""
    session['user_data'] = user.to_dict()
    session['last_update'] = datetime.now().isoformat()
    print(f"[SESSION-DEBUG] Updated session for user: {user.id}")

def get_current_user() -> Optional[User]:
    """Get current user from session"""
    if 'user_id' not in session or 'user_data' not in session:
        return None
    
    try:
        # Check if session is still valid
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > timedelta(seconds=SESSION_TIMEOUT):
                clear_user_session()
                return None
        
        # Recreate user from session data
        user_data = session['user_data']
        auth_type = session.get('auth_type', 'telegram')
        
        # Create user object
        if auth_type == 'telegram':
            # Extract original telegram data for User constructor
            telegram_data = {
                'id': user_data.get('telegram_id'),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'username': user_data.get('username', ''),
                'language_code': user_data.get('language_code', 'en'),
                'allows_write_to_pm': user_data.get('allows_write_to_pm', False),
                'photo_url': user_data.get('photo_url', '')
            }
            user = User(telegram_data, 'telegram')
        else:  # google
            google_data = {
                'sub': user_data.get('google_id'),
                'given_name': user_data.get('first_name', ''),
                'family_name': user_data.get('last_name', ''),
                'locale': user_data.get('language_code', 'en'),
                'picture': user_data.get('photo_url', ''),
                'email': user_data.get('email', '')
            }
            user = User(google_data, 'google')
        
        # Restore premium info if available
        user.is_premium = user_data.get('is_premium', False)
        
        return user
        
    except Exception as e:
        print(f"[SESSION-ERROR] Error getting current user: {e}")
        clear_user_session()
        return None

def clear_user_session():
    """Clear user session"""
    keys_to_remove = ['user_id', 'auth_type', 'user_data', 'login_time', 'last_update']
    for key in keys_to_remove:
        session.pop(key, None)
    print("[SESSION-DEBUG] Session cleared")

def generate_state_token() -> str:
    """Generate a secure state token for OAuth"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def authenticate_telegram_user(init_data: str) -> Tuple[bool, Optional[User], Optional[str]]:
    """
    Authenticate a Telegram user and create session
    Returns: (success, user, error_message)
    """
    print(f"[AUTH-DEBUG] Authenticating Telegram user with init_data length: {len(init_data)}")
    
    # Validate the initialization data
    is_valid, user_data, error = validate_telegram_webapp_data(init_data)
    
    if not is_valid:
        print(f"[AUTH-ERROR] Telegram validation failed: {error}")
        return False, None, error
    
    # Create user session
    try:
        user = create_user_session(user_data, 'telegram')
        print(f"[AUTH-DEBUG] Telegram user authenticated successfully: {user.telegram_id}")
        return True, user, None
    except Exception as e:
        print(f"[AUTH-ERROR] Error creating Telegram user session: {e}")
        return False, None, f"Session creation failed: {str(e)}"

def authenticate_google_user(token: str) -> Tuple[bool, Optional[User], Optional[str]]:
    """
    Authenticate a Google user and create session
    Returns: (success, user, error_message)  
    """
    # Validate the token
    is_valid, user_data, error = validate_google_token(token)
    
    if not is_valid:
        return False, None, error
    
    # Create user session
    try:
        user = create_user_session(user_data, 'google')
        return True, user, None
    except Exception as e:
        return False, None, f"Session creation failed: {str(e)}"

def get_user_permissions(user: User) -> Dict[str, bool]:
    """Get user permissions based on their status"""
    base_permissions = {
        'can_generate_images': True,
        'can_use_ai': True,
        'can_enhance_prompts': True,
        'can_view_stats': False,
        'can_access_admin': False,
        'can_use_premium_models': False,
        'can_generate_multiple_images': False
    }
    
    # Admin permissions
    if user.is_admin():
        base_permissions.update({
            'can_view_stats': True,
            'can_access_admin': True,
            'can_use_premium_models': True,
            'can_generate_multiple_images': True
        })
    
    # Premium permissions (will be updated when premium status is loaded)
    if user.is_premium:
        base_permissions.update({
            'can_use_premium_models': True,
            'can_generate_multiple_images': True
        })
    
    # Google users get premium features
    if user.auth_type == 'google':
        base_permissions.update({
            'can_use_premium_models': True,
            'can_generate_multiple_images': True
        })
    
    return base_permissions

def is_google_auth_available() -> bool:
    """Check if Google authentication is available"""
    return GOOGLE_AUTH_AVAILABLE and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

def get_auth_config() -> Dict[str, Any]:
    """Get authentication configuration for frontend"""
    return {
        'telegram_required': TELEGRAM_MINI_APP_REQUIRED,
        'google_available': is_google_auth_available(),
        'google_client_id': GOOGLE_CLIENT_ID if is_google_auth_available() else None
    } 
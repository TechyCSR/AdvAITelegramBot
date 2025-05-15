"""
UI Theme Module - Centralized UI theming system for consistent button styles

This module provides standardized button styles, layouts, and UI elements
to ensure a consistent modern appearance throughout the bot.
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any, Union, Optional, Tuple
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Color Theme (using Telegram emoji indicators)
class Colors:
    PRIMARY = "🔵"    # Blue - Primary actions
    SUCCESS = "✅"    # Green - Success/Enabled
    DANGER = "❌"     # Red - Danger/Disabled
    WARNING = "⚠️"    # Yellow - Warning/Caution
    INFO = "ℹ️"       # Info
    SETTINGS = "⚙️"   # Settings
    BACK = "🔙"       # Back navigation
    NEXT = "➡️"       # Next/Forward
    HOME = "🏠"       # Home
    PREMIUM = "💎"    # Premium feature
    IMAGE = "🖼️"      # Image related
    VOICE = "🎙️"      # Voice related
    AI = "🤖"         # AI related
    HELP = "❓"       # Help
    ADMIN = "🔑"      # Admin functions
    STATS = "📊"      # Statistics
    USER = "👤"       # User
    SEARCH = "🔍"     # Search
    NEW = "🆕"        # New
    FAVORITE = "⭐"   # Favorite/Star
    EDIT = "✏️"       # Edit
    DELETE = "🗑️"     # Delete
    CUSTOM = "🎨"     # Customization
    HEART = "❤️"      # Like/Love
    COMMAND = "🛠️"    # Commands
    SUPPORT = "📞"    # Support/Contact
    GROUP = "👥"      # Group
    DONATE = "💰"     # Donation
    LINK = "🔗"       # External link

# Theme configuration
class Theme:
    """Modern UI Theme for Telegram Bot"""
    
    # Spacing and Layout
    MAX_BUTTONS_PER_ROW = 2     # Default max buttons per row
    HEADER_FOOTER_FULL_WIDTH = True  # Headers/footers take full width
    
    # Standard Button Types
    @staticmethod
    def primary_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Primary action button"""
        return InlineKeyboardButton(f"{Colors.PRIMARY} {text}", callback_data=callback_data)
        
    @staticmethod
    def success_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Success/enabled button"""
        return InlineKeyboardButton(f"{Colors.SUCCESS} {text}", callback_data=callback_data)
    
    @staticmethod
    def danger_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Danger/disabled button"""
        return InlineKeyboardButton(f"{Colors.DANGER} {text}", callback_data=callback_data)
    
    @staticmethod
    def toggle_button(text: str, is_enabled: bool, callback_data: str) -> InlineKeyboardButton:
        """Toggle button that shows enabled/disabled state"""
        emoji = Colors.SUCCESS if is_enabled else Colors.DANGER
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)
    
    @staticmethod
    def back_button(callback_data: str = "back") -> InlineKeyboardButton:
        """Standard back navigation button"""
        return InlineKeyboardButton(f"{Colors.BACK} Back", callback_data=callback_data)
    
    @staticmethod
    def settings_button(callback_data: str = "settings") -> InlineKeyboardButton:
        """Standard settings button"""
        return InlineKeyboardButton(f"{Colors.SETTINGS} Settings", callback_data=callback_data)
    
    @staticmethod
    def help_button(callback_data: str = "help") -> InlineKeyboardButton:
        """Standard help button"""
        return InlineKeyboardButton(f"{Colors.HELP} Help", callback_data=callback_data)
    
    @staticmethod
    def link_button(text: str, url: str) -> InlineKeyboardButton:
        """External link button"""
        return InlineKeyboardButton(f"{Colors.LINK} {text}", url=url)
    
    @staticmethod
    def command_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Command button"""
        return InlineKeyboardButton(f"{Colors.COMMAND} {text}", callback_data=callback_data)
    
    @staticmethod
    def admin_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Admin action button"""
        return InlineKeyboardButton(f"{Colors.ADMIN} {text}", callback_data=callback_data)
    
    # Layout Helpers
    @staticmethod
    def create_button_row(buttons: List[InlineKeyboardButton], max_per_row: int = None) -> List[List[InlineKeyboardButton]]:
        """Create rows of buttons with specified maximum per row"""
        max_per_row = max_per_row or Theme.MAX_BUTTONS_PER_ROW
        rows = []
        current_row = []
        
        for button in buttons:
            if len(current_row) >= max_per_row:
                rows.append(current_row)
                current_row = []
            current_row.append(button)
            
        if current_row:
            rows.append(current_row)
            
        return rows
    
    @staticmethod
    def create_keyboard(buttons: List[InlineKeyboardButton], 
                        max_per_row: int = None,
                        add_back: bool = False,
                        back_callback: str = "back") -> InlineKeyboardMarkup:
        """Create a keyboard from buttons with automatic row handling"""
        rows = Theme.create_button_row(buttons, max_per_row)
        
        # Add back button if requested
        if add_back:
            rows.append([Theme.back_button(back_callback)])
            
        return InlineKeyboardMarkup(rows)
    
    @staticmethod
    def create_menu(items: List[Tuple[str, str, str]], add_back: bool = True) -> InlineKeyboardMarkup:
        """
        Create a menu with emojis and consistent styling
        
        Args:
            items: List of (emoji, text, callback_data) tuples
            add_back: Whether to add a back button
            
        Returns:
            Formatted InlineKeyboardMarkup
        """
        buttons = []
        for emoji, text, callback_data in items:
            buttons.append(InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data))
            
        return Theme.create_keyboard(buttons, add_back=add_back)
    
    # Special Layouts
    @staticmethod
    def toggle_control_layout(feature_name: str, emoji: str, is_enabled: bool, 
                             feature_id: str) -> List[List[InlineKeyboardButton]]:
        """
        Standard layout for a feature toggle with ON/OFF buttons
        
        Args:
            feature_name: Display name of the feature
            emoji: Emoji indicator for the feature
            is_enabled: Current state of the feature
            feature_id: ID used in callback_data
            
        Returns:
            List of rows (each row is a list of buttons)
        """
        status = "✅" if is_enabled else "❌"
        
        # Create two separate rows (header and controls)
        header_row = [InlineKeyboardButton(f"{emoji} {feature_name}: {status}", 
                             callback_data=f"feature_info_{feature_id}")]
                             
        controls_row = [
            InlineKeyboardButton("✅ ON", callback_data=f"toggle_{feature_id}_true"),
            InlineKeyboardButton("❌ OFF", callback_data=f"toggle_{feature_id}_false"),
            InlineKeyboardButton("ℹ️", callback_data=f"feature_info_{feature_id}")
        ]
        
        # Return as a list of rows (list of lists of buttons)
        return [header_row, controls_row]

# Common button sets
class CommonButtons:
    """Pre-defined common button configurations"""
    
    @staticmethod
    def yes_no_buttons(yes_callback: str, no_callback: str) -> List[InlineKeyboardButton]:
        """Standard Yes/No button pair"""
        return [
            InlineKeyboardButton(f"{Colors.SUCCESS} Yes", callback_data=yes_callback),
            InlineKeyboardButton(f"{Colors.DANGER} No", callback_data=no_callback)
        ]
    
    @staticmethod
    def feedback_buttons(user_id: int, item_id: str) -> List[List[InlineKeyboardButton]]:
        """Standard feedback buttons (like/dislike + regenerate)"""
        return [
            [
                InlineKeyboardButton(f"{Colors.HEART} Love it", 
                                    callback_data=f"img_feedback_positive_{user_id}_{item_id}"),
                InlineKeyboardButton(f"{Colors.DANGER} Not good", 
                                    callback_data=f"img_feedback_negative_{user_id}_{item_id}")
            ],
            [InlineKeyboardButton(f"{Colors.NEW} Regenerate", 
                                 callback_data=f"img_regenerate_{user_id}_{item_id}")]
        ]
    
    @staticmethod
    def main_menu_buttons(bot_username: str) -> List[List[InlineKeyboardButton]]:
        """Standard main menu buttons"""
        return [
            [InlineKeyboardButton(f"{Colors.GROUP} Add to Group", 
                                 url=f"https://t.me/{bot_username}?startgroup=true")],
            [
                InlineKeyboardButton(f"{Colors.COMMAND} Commands", callback_data="commands"),
                InlineKeyboardButton(f"{Colors.HELP} Help", callback_data="help")
            ],
            [
                InlineKeyboardButton(f"{Colors.SETTINGS} Settings", callback_data="settings"),
                InlineKeyboardButton(f"{Colors.SUPPORT} Support", callback_data="support")
            ]
        ]
    
    @staticmethod
    def admin_menu_buttons() -> List[List[InlineKeyboardButton]]:
        """Standard admin menu buttons"""
        return [
            [InlineKeyboardButton(f"{Colors.ADMIN} Admin Panel", callback_data="admin_panel")],
            [
                InlineKeyboardButton(f"{Colors.STATS} Statistics", callback_data="admin_stats"),
                InlineKeyboardButton(f"{Colors.USER} User Manager", callback_data="admin_users")
            ],
            [Theme.back_button()]
        ] 
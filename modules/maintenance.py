from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang
from modules.core.database import get_feature_settings_collection
from config import ADMINS, OWNER_ID
from modules.admin.statistics import get_bot_statistics
from modules.ui.theme import Theme, Colors

# Default feature states
DEFAULT_FEATURE_STATES = {
    "maintenance_mode": False,
    "image_generation": True,
    "voice_features": True,
    "ai_response": True
}

# Cache for feature states to avoid frequent DB access
_feature_states_cache = None
_cache_initialized = False

async def get_feature_states() -> dict:
    """
    Get the current feature states from the database or initialize with defaults
    
    Returns:
        Dictionary of feature states
    """
    global _feature_states_cache, _cache_initialized
    
    # Return cached states if available
    if _cache_initialized:
        return _feature_states_cache
    
    # Get the feature settings collection
    feature_settings = get_feature_settings_collection()
    
    # Try to get the current settings
    settings_doc = feature_settings.find_one({"settings_id": "global"})
    
    if not settings_doc:
        # Initialize with defaults
        feature_settings.insert_one({
            "settings_id": "global",
            **DEFAULT_FEATURE_STATES
        })
        _feature_states_cache = DEFAULT_FEATURE_STATES.copy()
    else:
        # Remove _id and settings_id
        settings = settings_doc.copy()
        if "_id" in settings:
            del settings["_id"]
        if "settings_id" in settings:
            del settings["settings_id"]
        _feature_states_cache = settings
    
    _cache_initialized = True
    return _feature_states_cache

async def set_feature_state(feature: str, state: bool) -> None:
    """
    Set the state of a feature in the database
    
    Args:
        feature: Feature name
        state: New state (True/False)
    """
    global _feature_states_cache, _cache_initialized
    
    # Update the cache
    if _cache_initialized and _feature_states_cache:
        _feature_states_cache[feature] = state
    
    # Get the feature settings collection
    feature_settings = get_feature_settings_collection()
    
    # Update the feature state
    feature_settings.update_one(
        {"settings_id": "global"}, 
        {"$set": {feature: state}},
        upsert=True
    )

async def is_feature_enabled(feature: str) -> bool:
    """
    Check if a feature is enabled
    
    Args:
        feature: Feature name
        
    Returns:
        True if feature is enabled, False otherwise
    """
    states = await get_feature_states()
    return states.get(feature, DEFAULT_FEATURE_STATES.get(feature, False))

async def is_admin_user(user_id: int) -> bool:
    """
    Check if a user is an admin or owner
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if user is admin or owner, False otherwise
    """
    return user_id in ADMINS or user_id == OWNER_ID

async def maintenance_check(user_id: int) -> bool:
    """
    Check if the bot is in maintenance mode and the user is not an admin
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if bot is in maintenance AND user is not admin
    """
    if await is_admin_user(user_id):
        return False
        
    return await is_feature_enabled("maintenance_mode")

async def maintenance_message(user_id: int) -> str:
    """
    Get the maintenance message translated to the user's language
    
    Args:
        user_id: User ID for translation
        
    Returns:
        Translated maintenance message
    """
    maintenance_text = """
🚧 **Bot Maintenance in Progress** 🚧

Our bot is currently undergoing maintenance to improve its performance and features.
We apologize for any inconvenience and appreciate your patience.

The system will be back online as soon as possible.

For urgent inquiries, please contact:
• Developer: @techycsr
• Website: techycsr.me
"""
    return await async_translate_to_lang(maintenance_text, user_id)

async def settings_others_callback(client, callback: CallbackQuery):
    """Handle settings_others callback - show enhanced system status for users"""
    await show_user_system_status(client, callback)

async def show_user_system_status(client, callback: CallbackQuery):
    """Show system status (uptime, CPU, memory, features) for regular users with refresh"""
    user_id = callback.from_user.id
    # Get translations
    sysinfo_title = await async_translate_to_lang("⚙️ **System Information**", user_id)
    sysinfo_desc = await async_translate_to_lang(
        "This section shows the current status of the bot's features and system health.", user_id)
    uptime_text = await async_translate_to_lang("Uptime", user_id)
    cpu_text = await async_translate_to_lang("CPU", user_id)
    mem_text = await async_translate_to_lang("Memory", user_id)
    feature_status_text = await async_translate_to_lang("Current Feature Status", user_id)
    enabled_text = await async_translate_to_lang("✅ Enabled", user_id)
    disabled_text = await async_translate_to_lang("❌ Disabled", user_id)
    back_text = await async_translate_to_lang("🔙 Back", user_id)
    refresh_text = await async_translate_to_lang("🔄 Refresh", user_id)
    # Feature names
    ai_text = await async_translate_to_lang("AI Response", user_id)
    img_text = await async_translate_to_lang("Image Generation", user_id)
    voice_text = await async_translate_to_lang("Voice Features", user_id)

    # Get system stats (reuse admin code, but only show system+feature status)
    stats = await get_bot_statistics()
    # Build system status message
    sys_status = f"\n\n**{feature_status_text}:**\n\n"
    sys_status += f"• {ai_text}: {enabled_text if stats.get('ai_response_enabled', True) else disabled_text}\n"
    sys_status += f"• {img_text}: {enabled_text if stats.get('image_generation_enabled', True) else disabled_text}\n"
    sys_status += f"• {voice_text}: {enabled_text if stats.get('voice_features_enabled', True) else disabled_text}\n"
    # Maintenance mode
    if stats.get('maintenance_mode', False):
        sys_status += f"\n⚠️ <b>The bot is currently in maintenance mode.</b>\nSome features may be unavailable.\n"
    # System metrics
    sys_metrics = (
        f"\n<b>{uptime_text}:</b> {stats.get('uptime','?')}\n"
        f"<b>{cpu_text}:</b> {stats.get('cpu_usage','?')}%\n"
        f"<b>{mem_text}:</b> {stats.get('memory_usage','?')}%\n"
    )
    # Compose message
    message = f"{sysinfo_title}\n\n{sysinfo_desc}{sys_metrics}{sys_status}"
    # Modern keyboard: Refresh + Back
    keyboard = Theme.create_keyboard([
        Theme.primary_button(refresh_text, "settings_others_refresh"),
        Theme.back_button("support")
    ], max_per_row=2)
    await callback.message.edit(
        text=message,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Add a refresh handler for the user system status
async def settings_others_refresh_callback(client, callback: CallbackQuery):
    await show_user_system_status(client, callback)

async def maintenance_settings(client, callback: CallbackQuery):
    """Display maintenance settings page with admin options if applicable"""
    user_id = callback.from_user.id
    
    if await is_admin_user(user_id):
        # User is admin, show admin panel
        await show_admin_panel(client, callback)
    else:
        # Regular user, show maintenance info
        message = await async_translate_to_lang(
            "⚙️ **System Information**\n\n"
            "This section shows the current status of the bot's features. "
            "If features are disabled, please check back later or contact support.", 
            user_id
        )
        
        # Show current feature states
        states = await get_feature_states()
        
        # Translate status texts
        enabled_text = await async_translate_to_lang("✅ Enabled", user_id)
        disabled_text = await async_translate_to_lang("❌ Disabled", user_id)
        back_text = await async_translate_to_lang("🔙 Back", user_id)
        
        # Feature texts
        ai_text = await async_translate_to_lang("AI Response", user_id)
        img_text = await async_translate_to_lang("Image Generation", user_id)
        voice_text = await async_translate_to_lang("Voice Features", user_id)
        
        # Build status message
        status_message = f"\n\n**Current Feature Status:**\n\n"
        status_message += f"• {ai_text}: {enabled_text if states.get('ai_response', True) else disabled_text}\n"
        status_message += f"• {img_text}: {enabled_text if states.get('image_generation', True) else disabled_text}\n"
        status_message += f"• {voice_text}: {enabled_text if states.get('voice_features', True) else disabled_text}\n"
        
        # Add maintenance mode message if enabled
        if states.get('maintenance_mode', False):
            maintenance_info = await async_translate_to_lang(
                "\n⚠️ **The bot is currently in maintenance mode.**\n"
                "Some features may be unavailable.", 
                user_id
            )
            status_message += maintenance_info
        
        # Build keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_text, callback_data="support")]
        ])
        
        await callback.message.edit(
            text=message + status_message,
            reply_markup=keyboard
        )
        
async def show_admin_panel(client, callback: CallbackQuery):
    """Show the admin panel with feature toggle options"""
    user_id = callback.from_user.id
    
    # Get current states
    states = await get_feature_states()
    
    # Translate UI elements
    admin_title = await async_translate_to_lang("⚙️ **Advanced Admin Control Panel**", user_id)
    admin_desc = await async_translate_to_lang(
        "Control your bot's features and maintenance settings from this centralized dashboard.\n\n"
        "Toggle features on/off with a single click. Changes take effect immediately.", 
        user_id
    )
    
    # Feature labels
    maint_label = await async_translate_to_lang("🚧 Maintenance Mode", user_id)
    img_label = await async_translate_to_lang("🖼️ Image Generation", user_id)
    voice_label = await async_translate_to_lang("🎙️ Voice Features", user_id)
    ai_label = await async_translate_to_lang("🤖 AI Response", user_id)
    
    # Status indicators
    maint_status = "✅" if states.get("maintenance_mode", False) else "❌"
    img_status = "✅" if states.get("image_generation", True) else "❌"
    voice_status = "✅" if states.get("voice_features", True) else "❌"
    ai_status = "✅" if states.get("ai_response", True) else "❌"
    
    # Button labels
    toggle_text = await async_translate_to_lang("Toggle", user_id)
    info_text = await async_translate_to_lang("Info", user_id)
    back_text = await async_translate_to_lang("🔙 Back", user_id)
    stats_text = await async_translate_to_lang("📊 Statistics", user_id)
    users_text = await async_translate_to_lang("👥 Users", user_id)
    donate_text = await async_translate_to_lang("💰 Donations", user_id)
    
    # Create modern control panel - flat list of rows
    keyboard = []
    
    # Header section
    keyboard.append([InlineKeyboardButton(f"{Colors.ADMIN} System Controls", callback_data="admin_header")])
    
    # Get toggle layouts and add each row separately
    maintenance_toggle_rows = Theme.toggle_control_layout(
        feature_name=maint_label,
        emoji=Colors.WARNING,
        is_enabled=states.get("maintenance_mode", False),
        feature_id="maintenance_mode"
    )
    for row in maintenance_toggle_rows:
        keyboard.append(row)
    
    # Feature Controls header
    keyboard.append([InlineKeyboardButton(f"{Colors.SETTINGS} Feature Controls", callback_data="features_header")])
    
    # Image generation toggle
    image_toggle_rows = Theme.toggle_control_layout(
        feature_name=img_label,
        emoji=Colors.IMAGE,
        is_enabled=states.get("image_generation", True),
        feature_id="image_generation"
    )
    for row in image_toggle_rows:
        keyboard.append(row)
    
    # Voice features toggle
    voice_toggle_rows = Theme.toggle_control_layout(
        feature_name=voice_label,
        emoji=Colors.VOICE,
        is_enabled=states.get("voice_features", True),
        feature_id="voice_features"
    )
    for row in voice_toggle_rows:
        keyboard.append(row)
    
    # AI response toggle
    ai_toggle_rows = Theme.toggle_control_layout(
        feature_name=ai_label,
        emoji=Colors.AI,
        is_enabled=states.get("ai_response", True),
        feature_id="ai_response"
    )
    for row in ai_toggle_rows:
        keyboard.append(row)
    
    # Advanced Admin Tools
    keyboard.append([InlineKeyboardButton(f"{Colors.STATS} Admin Tools", callback_data="admin_tools_header")])
    
    # Stats and Users buttons row
    keyboard.append([
        Theme.admin_button(stats_text, "admin_view_stats"),
        Theme.admin_button(users_text, "admin_users")
    ])
    
    # Donation button row
    keyboard.append([
        Theme.admin_button(donate_text, "support_donate")
    ])
    
    # Back button
    keyboard.append([Theme.back_button("support")])
    
    # Create status summary
    status_summary = "\n\n**Current Status:**\n"
    status_summary += f"• {maint_label}: {maint_status}\n"
    status_summary += f"• {img_label}: {img_status}\n"
    status_summary += f"• {voice_label}: {voice_status}\n"
    status_summary += f"• {ai_label}: {ai_status}\n"
    
    message_text = f"{admin_title}\n\n{admin_desc}{status_summary}"
    
    try:
        await callback.message.edit(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        # Handle MessageNotModified error by silently ignoring it
        if "MESSAGE_NOT_MODIFIED" in str(e):
            # Just acknowledge the callback instead
            await callback.answer("Panel already up to date")
            pass
        else:
            # For other errors, log and notify
            # logger.error(f"Error showing admin panel: {str(e)}")
            await callback.answer(f"Error: {str(e)[:20]}...", show_alert=True)

async def handle_feature_toggle(client, callback: CallbackQuery):
    """Handle feature toggle callback"""
    if not await is_admin_user(callback.from_user.id):
        await callback.answer("You don't have permission to change settings.", show_alert=True)
        return
    
    # Extract feature and state from callback data
    # Format: toggle_FEATURE_STATE
    parts = callback.data.split('_')
    feature = '_'.join(parts[1:-1])  # Handle feature names with underscores
    state = parts[-1].lower() == 'true'
    
    # Update feature state
    await set_feature_state(feature, state)
    
    # Show confirmation
    feature_name = feature.replace('_', ' ').title()
    state_text = "enabled" if state else "disabled"
    await callback.answer(f"{feature_name} {state_text}", show_alert=True)
    
    # Refresh admin panel
    await show_admin_panel(client, callback)

async def handle_feature_info(client, callback: CallbackQuery):
    """Show information about a specific feature"""
    user_id = callback.from_user.id
    
    # Extract feature from callback data
    # Format: feature_info_FEATURE
    feature = callback.data.replace('feature_info_', '')
    
    # Feature descriptions - SHORTENED to avoid MESSAGE_TOO_LONG errors
    descriptions = {
        "maintenance_mode": "When enabled, shows maintenance message to regular users. Only admins can use the bot.",
        "image_generation": "Controls image generation commands (/generate, /img). Disable if service has issues.",
        "voice_features": "Controls voice message processing. Can be disabled to reduce server load.",
        "ai_response": "Controls bot's ability to respond to text messages. Core functionality."
    }
    
    # Get current state
    states = await get_feature_states()
    current_state = states.get(feature, DEFAULT_FEATURE_STATES.get(feature, False))
    state_text = "✅ Enabled" if current_state else "❌ Disabled"
    
    description = descriptions.get(feature, "No info available.")
    feature_name = feature.replace('_', ' ').title()
    
    # Translate the message - kept very short for alert
    info_text = await async_translate_to_lang(
        f"{feature_name}: {description}\nState: {state_text}", 
        user_id
    )
    
    try:
        await callback.answer(info_text, show_alert=True)
    except Exception as e:
        # If too long, try an even shorter version
        short_info = await async_translate_to_lang(
            f"{feature_name}\nState: {state_text}", 
            user_id
        )
        await callback.answer(short_info, show_alert=True)

async def handle_donation(client, callback: CallbackQuery):
    """Show donation options with UPI ID"""
    user_id = callback.from_user.id
    
    # Create donation message
    donation_text = """
💰 **Support Bot Development**

Your donations help maintain and improve this bot with new features and better performance.

Developed by Chandan Singh (@techycsr), a tech enthusiast and student developer passionate about AI/ML and Telegram bots.

**UPI Payment Option:**
• UPI ID: `csr.info.in@oksbi`
• Scan QR code or use any UPI app like Google Pay, PhonePe, Paytm, etc.

**After donating:**
Please message @techycsr with your donation details to get premium features activated.

Thank you for your support! 🙏
"""
    
    # Translate the message and button
    translated_donation = await async_translate_to_lang(donation_text, user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    
    # Create keyboard with back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(back_btn, callback_data="support_developers")]
    ])
    
    # Show donation message
    await callback.message.edit(
        text=translated_donation,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


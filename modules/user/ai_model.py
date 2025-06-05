import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import MongoClient
from config import DATABASE_URL, ADMINS
from modules.lang import async_translate_to_lang, batch_translate
from typing import Tuple
import asyncio

# --- Constants ---
TEXT_MODEL_HEADING = "AI Text Generation Model"
IMAGE_MODEL_HEADING = "Image Generation Model"

TEXT_MODELS = {
    "gpt-4o": "GPT-4o",
    "gpt-4.1": "GPT-4.1",
    "qwen3": "Qwen3",
    "deepseek-r1": "DeepSeek-R1"
}

IMAGE_MODELS = {
    "dall-e3": "DALL-E 3",
    "flux": "Flux",
    "flux-pro": "Flux Pro"
}

DEFAULT_TEXT_MODEL = "gpt-4o"
DEFAULT_IMAGE_MODEL = "dall-e3"

# --- Restricted Models ---
RESTRICTED_TEXT_MODELS = {"gpt-4.1", "qwen3"}
RESTRICTED_IMAGE_MODELS = {"flux-pro"}

# --- Database Setup ---
client = MongoClient(DATABASE_URL)
db = client["aibotdb"]
user_ai_model_settings_collection = db["user_ai_model_settings"]
user_lang_collection = db['user_lang'] # Assuming this is used for language preference

# --- Helper Functions ---
async def get_user_ai_models(user_id: int) -> Tuple[str, str]:
    """Fetches the user's selected AI models, returning defaults if not set. Enforces fallback for restricted models if user is not premium/admin."""
    settings = user_ai_model_settings_collection.find_one({"user_id": user_id})
    text_model = settings.get("text_model", DEFAULT_TEXT_MODEL) if settings else DEFAULT_TEXT_MODEL
    image_model = settings.get("image_model", DEFAULT_IMAGE_MODEL) if settings else DEFAULT_IMAGE_MODEL

    # Enforce fallback for restricted models at runtime
    from modules.user.premium_management import is_user_premium
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = user_id in ADMINS
    if not is_premium and not is_admin:
        if text_model in RESTRICTED_TEXT_MODELS:
            text_model = DEFAULT_TEXT_MODEL
        if image_model in RESTRICTED_IMAGE_MODELS:
            image_model = DEFAULT_IMAGE_MODEL
    return text_model, image_model

async def set_user_ai_model(user_id: int, model_type: str, model_name: str):
    """Sets the user's selected AI model for a given type (text or image)."""
    user_ai_model_settings_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"{model_type}_model": model_name}},
        upsert=True
    )

async def get_current_lang(user_id: int) -> str:
    """Gets the user's current language preference."""
    lang_doc = user_lang_collection.find_one({"user_id": user_id})
    return lang_doc["language"] if lang_doc else "en"

async def revert_restricted_models_if_needed(user_id: int):
    from modules.user.premium_management import is_user_premium
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = user_id in ADMINS
    text_model, image_model = await get_user_ai_models(user_id)
    changed = False
    if (not is_premium and not is_admin):
        if text_model in RESTRICTED_TEXT_MODELS:
            await set_user_ai_model(user_id, "text", DEFAULT_TEXT_MODEL)
            changed = True
        if image_model in RESTRICTED_IMAGE_MODELS:
            await set_user_ai_model(user_id, "image", DEFAULT_IMAGE_MODEL)
            changed = True
    return changed

# --- Main Panel Function ---
async def ai_model_settings_panel(client_obj, callback: CallbackQuery):
    """Displays the AI Model settings panel."""
    user_id = callback.from_user.id
    user_mention = callback.from_user.mention
    current_lang = await get_current_lang(user_id)
    current_text_model, current_image_model = await get_user_ai_models(user_id)

    # --- Translations ---
    panel_title_text = await async_translate_to_lang("🧠 AI Model Settings", current_lang)
    
    text_model_heading_display = await async_translate_to_lang(TEXT_MODEL_HEADING, current_lang)
    image_model_heading_display = await async_translate_to_lang(IMAGE_MODEL_HEADING, current_lang)
    
    back_button_text = await async_translate_to_lang("🔙 Back to Settings", current_lang)
    
    # Translate model display names
    translated_text_models = {k: await async_translate_to_lang(v, current_lang) for k, v in TEXT_MODELS.items()}
    translated_image_models = {k: await async_translate_to_lang(v, current_lang) for k, v in IMAGE_MODELS.items()}

    # --- Keyboard Construction ---
    keyboard = []

    # Text Model Heading
    keyboard.append([InlineKeyboardButton(f"🔶 {text_model_heading_display} 🔶", callback_data="ai_model_heading_text")])
    
    # Text Model Buttons
    text_model_buttons = []
    for model_key, model_display_name in translated_text_models.items():
        text = f"✅ {model_display_name}" if model_key == current_text_model else model_display_name
        text_model_buttons.append(InlineKeyboardButton(text, callback_data=f"set_text_model_{model_key}"))
    
    # Arrange text model buttons in rows of 2
    for i in range(0, len(text_model_buttons), 2):
        keyboard.append(text_model_buttons[i:i+2])

    # Image Model Heading
    keyboard.append([InlineKeyboardButton(f"🔷 {image_model_heading_display} 🔷", callback_data="ai_model_heading_image")])

    # Image Model Buttons
    image_model_buttons = []
    for model_key, model_display_name in translated_image_models.items():
        text = f"✅ {model_display_name}" if model_key == current_image_model else model_display_name
        image_model_buttons.append(InlineKeyboardButton(text, callback_data=f"set_image_model_{model_key}"))
        
    # Arrange image model buttons in rows of 2 (or 3 if preferred)
    for i in range(0, len(image_model_buttons), 2): # Adjust 2 to 3 if more space
        keyboard.append(image_model_buttons[i:i+2])

    # Back Button
    keyboard.append([InlineKeyboardButton(back_button_text, callback_data="settings")]) # Assuming "settings" takes back to main settings

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show user's current models at the top
    current_text_model_label = translated_text_models.get(current_text_model, current_text_model)
    current_image_model_label = translated_image_models.get(current_image_model, current_image_model)
    current_models_text = f"👤 {user_mention}\n" \
                        f"Current Text Model: <b>{current_text_model_label}</b>\n" \
                        f"Current Image Model: <b>{current_image_model_label}</b>\n\n"

    panel_text = current_models_text
    panel_text += f"<b>{panel_title_text}</b>\n\n"
    panel_text += await async_translate_to_lang("Please select your preferred AI models for text and image generation.", current_lang)

    await callback.message.edit_text(
        text=panel_text,
        reply_markup=reply_markup,
        parse_mode=pyrogram.enums.ParseMode.HTML
    )
    await callback.answer()

# --- Callback Handlers for Model Changes ---
async def handle_set_text_model(client_obj, callback: CallbackQuery):
    from modules.user.premium_management import is_user_premium
    user_id = callback.from_user.id
    current_lang = await get_current_lang(user_id)
    model_key = callback.data.split("_")[-1]
    current_text_model, _ = await get_user_ai_models(user_id)
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = user_id in ADMINS
    if model_key == current_text_model:
        alert_text = await async_translate_to_lang("This is already your selected text model.", current_lang)
        await callback.answer(alert_text, show_alert=True)
    elif (model_key in RESTRICTED_TEXT_MODELS) and (not is_premium and not is_admin):
        alert_text = await async_translate_to_lang("You need to upgrade to Premium to use this model.", current_lang)
        await callback.answer(alert_text, show_alert=True)
    else:
        await set_user_ai_model(user_id, "text", model_key)
        await ai_model_settings_panel(client_obj, callback)
        alert_text_template = await async_translate_to_lang("Text model set to: {model_name}", current_lang)
        model_display_name = await async_translate_to_lang(TEXT_MODELS.get(model_key, model_key), current_lang)
        await callback.answer(alert_text_template.format(model_name=model_display_name), show_alert=False)

async def handle_set_image_model(client_obj, callback: CallbackQuery):
    from modules.user.premium_management import is_user_premium
    user_id = callback.from_user.id
    current_lang = await get_current_lang(user_id)
    model_key = callback.data.split("_")[-1]
    _, current_image_model = await get_user_ai_models(user_id)
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = user_id in ADMINS
    if model_key == current_image_model:
        alert_text = await async_translate_to_lang("This is already your selected image model.", current_lang)
        await callback.answer(alert_text, show_alert=True)
    elif (model_key in RESTRICTED_IMAGE_MODELS) and (not is_premium and not is_admin):
        alert_text = await async_translate_to_lang("You need to upgrade to Premium to use this model.", current_lang)
        await callback.answer(alert_text, show_alert=True)
    else:
        await set_user_ai_model(user_id, "image", model_key)
        await ai_model_settings_panel(client_obj, callback)
        alert_text_template = await async_translate_to_lang("Image model set to: {model_name}", current_lang)
        model_display_name = await async_translate_to_lang(IMAGE_MODELS.get(model_key, model_key), current_lang)
        await callback.answer(alert_text_template.format(model_name=model_display_name), show_alert=False)

# --- Callback Handlers for Heading Clicks ---
async def handle_ai_model_heading_click(client_obj, callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = await get_current_lang(user_id)
    
    heading_type = callback.data.split("_")[-1] # "text" or "image"
    
    if heading_type == "text":
        alert_text = await async_translate_to_lang("Choose the AI Text Generation Model from the options below.", current_lang)
    elif heading_type == "image":
        alert_text = await async_translate_to_lang("Choose the Image Generation Model from the options below.", current_lang)
    else:
        alert_text = await async_translate_to_lang("Invalid selection.", current_lang) # Should not happen
        
    await callback.answer(alert_text, show_alert=True)

"""
Supported AI Text Models: """ + ", ".join(TEXT_MODELS.values()) + """
Supported Image Generation Models: """ + ", ".join(IMAGE_MODELS.values()) + """
Multi-Model Support: Users can choose their preferred models in the AI Model Panel (Settings).
""" 
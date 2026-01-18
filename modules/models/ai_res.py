import os
import asyncio
import time
import re
import html

from typing import List, Dict, Any, Optional, Generator, Union, Tuple
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# Import multi-provider text generation system
from modules.models.multi_provider_text import (
    generate_text_sync,
    generate_text_multi_provider,
    get_streaming_response_multi_provider,
    normalize_model_name,
    DEFAULT_TEXT_MODEL as MULTI_PROVIDER_DEFAULT_MODEL,
)

from modules.core.database import get_history_collection
from modules.chatlogs import user_log, error_log
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled
from modules.user.ai_model import get_user_ai_models, DEFAULT_TEXT_MODEL, RESTRICTED_TEXT_MODELS
from modules.user.premium_management import is_user_premium
from config import ADMINS
from pyrogram.errors import MessageTooLong
from modules.image.image_generation import generate_images
from pyrogram.types import InputMediaPhoto
from modules.core.request_queue import (
    can_start_text_request, 
    start_text_request, 
    finish_text_request,
    get_user_request_status
)
import uuid
import random


async def send_interactive_waiting_message(message: Message) -> Message:
    """
    Send an engaging, interactive waiting message that cycles through different statuses
    to show what's happening in the backend while processing the AI response.
    Also continuously shows "typing" action to indicate active processing.
    
    Args:
        message: The user's message to reply to
        
    Returns:
        The waiting message object that can be edited/deleted later
    """
    from pyrogram.enums import ChatAction
    
    # Creative status messages that explain what's happening
    status_messages = [
        "🔍 Reading your message...",
        "🧠 Understanding your request...",
        "💭 Thinking about the best response...",
        "✨ Crafting something helpful...",
        "📝 Putting thoughts into words...",
        "🎯 Almost ready with your answer..."
    ]
    
    # Send initial typing action
    try:
        await message._client.send_chat_action(message.chat.id, ChatAction.TYPING)
    except Exception:
        pass
    
    # Send initial message
    temp_msg = await message.reply_text(status_messages[0])
    
    # Create background task to cycle through messages and keep typing action
    async def cycle_messages():
        try:
            for i in range(1, len(status_messages)):
                await asyncio.sleep(1.5)  # Wait 1.5 seconds between each update
                try:
                    # Send typing action to keep it visible
                    await message._client.send_chat_action(message.chat.id, ChatAction.TYPING)
                    await temp_msg.edit_text(status_messages[i])
                except Exception:
                    # Message might be deleted if response is ready
                    break
            
            # Continue sending typing action every 4 seconds until response is ready
            while True:
                await asyncio.sleep(4)
                try:
                    await message._client.send_chat_action(message.chat.id, ChatAction.TYPING)
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            # Silently handle any errors (message might be deleted)
            pass
    
    # Start the cycling task in background (non-blocking)
    typing_task = asyncio.create_task(cycle_messages())
    
    # Store the task reference on the message for later cancellation
    temp_msg._typing_task = typing_task
    
    return temp_msg


def get_response(history: List[Dict[str, str]], model: str = "gpt-4o") -> str:
    """
    Get a non-streaming response from the AI model using multi-provider system
    
    Args:
        history: Conversation history in the format expected by the AI model
        model: The user's selected model
        
    Returns:
        String response from the AI model
    """
    try:
        # Validate and prepare history
        if not isinstance(history, list):
            history = [history]
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
        
        print(f"Using multi-provider system for model: {model}")
        
        response, error = generate_text_sync(
            messages=history,
            model=model,
            temperature=0.7,
            max_tokens=4096,
        )
        
        if error:
            raise Exception(error)
        
        return response
            
    except Exception as e:
        print(f"Error generating response with model {model}: {e}")
        raise


def get_streaming_response(history: List[Dict[str, str]], model: str = "gpt-4o") -> Optional[Generator]:
    """
    Get a streaming response from the AI model using multi-provider system
    
    Args:
        history: Conversation history in the format expected by the AI model
        model: The model to use for generating the response
        
    Returns:
        Generator yielding response chunks or None if there's an error
    """
    try:
        # Ensure history is a list
        if not isinstance(history, list):
            history = [history]
            
        # If history is empty, use the default system message
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
            
        # Ensure each message in history is a dictionary
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
        
        print(f"Streaming with multi-provider system for model: {model}")
        
        response = get_streaming_response_multi_provider(
            messages=history,
            model=model,
            temperature=0.7,
            max_tokens=4096,
        )
        return response
            
    except Exception as e:
        print(f"Error generating streaming response: {e}")
        return None


def sanitize_markdown(text: str) -> str:
    """
    Ensures proper markdown formatting in streaming responses
    
    Args:
        text: Raw text that may contain incomplete markdown
        
    Returns:
        Text with proper markdown formatting
    """
    # Count opening and closing backticks to handle code blocks
    backticks_opened = text.count('```')
    if backticks_opened % 2 != 0:
        text += '\n```'  # Close incomplete code block
    
    # Handle inline code (single backtick)
    single_backticks = text.count('`') - (backticks_opened * 3)
    if single_backticks % 2 != 0:
        text += '`'  # Close incomplete inline code
    
    # Handle markdown bold/italic
    asterisks_count = text.count('*')
    if asterisks_count % 2 != 0:
        text += '*'  # Close incomplete bold/italic
    
    # Handle incomplete links or formatting
    if text.count('[') > text.count(']'):
        text += ']'
    
    if text.count('(') > text.count(')'):
        text += ')'
    
    return text

def markdown_to_html(text):
    """
    Convert markdown formatting to Telegram-compatible HTML.
    Handles: code blocks, inline code, bold, italic, strikethrough, headers, links
    """
    if not text or not isinstance(text, str):
        return text or ""
    
    # First, protect code blocks (triple backticks) by replacing with placeholders
    # Use angle brackets that won't conflict with any markdown patterns
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"<<<CODEBLOCK{len(code_blocks) - 1}>>>"
    
    text = re.sub(r'```[\s\S]*?```', save_code_block, text)
    
    # Protect inline code (single backticks)
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f"<<<INLINECODE{len(inline_codes) - 1}>>>"
    
    text = re.sub(r'`[^`]+`', save_inline_code, text)
    
    # Escape HTML special characters in the main text
    text = html.escape(text)
    
    # Convert headers (### Header -> <b>Header</b>)
    text = re.sub(r'^#{1,6}\s*(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    # Convert bold (**text** or __text__ -> <b>text</b>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Convert italic (*text* or _text_ -> <i>text</i>) - be careful not to match bold
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    
    # Convert strikethrough (~~text~~ -> <s>text</s>)
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    # Convert links [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Restore inline code - need to handle both escaped and unescaped versions
    for i, code in enumerate(inline_codes):
        # Extract just the code (remove backticks)
        code_content = code[1:-1]
        html_code = f"<code>{html.escape(code_content)}</code>"
        # Replace both escaped version (after html.escape) and original
        text = text.replace(f"&lt;&lt;&lt;INLINECODE{i}&gt;&gt;&gt;", html_code)
        text = text.replace(f"<<<INLINECODE{i}>>>", html_code)
    
    # Restore code blocks - need to handle both escaped and unescaped versions
    for i, block in enumerate(code_blocks):
        # Extract the code (remove triple backticks and optional language)
        match = re.match(r'```(?:\w+)?\n?([\s\S]*?)```', block)
        if match:
            code_content = match.group(1).strip()
        else:
            code_content = block[3:-3].strip()
        html_code = f"<pre><code>{html.escape(code_content)}</code></pre>"
        # Replace both escaped version (after html.escape) and original
        text = text.replace(f"&lt;&lt;&lt;CODEBLOCK{i}&gt;&gt;&gt;", html_code)
        text = text.replace(f"<<<CODEBLOCK{i}>>>", html_code)
    
    return text

def markdown_code_to_html(text):
    """Legacy function - now calls the full markdown_to_html converter"""
    return markdown_to_html(text)

def validate_image_url(url: str) -> bool:
    """Validate if the URL is a proper image URL"""
    if not url or not isinstance(url, str):
        return False
    return url.startswith(('http://', 'https://')) or url.startswith('/')

def analyze_user_intent_for_images(user_message: str) -> dict:
    """
    Advanced intent analysis to determine if user wants image generation
    
    Args:
        user_message: User's message text
        
    Returns:
        Dictionary with intent analysis results
    """
    # Ensure we have a string to work with
    if not user_message or not isinstance(user_message, str):
        user_message = str(user_message) if user_message else ""
    
    user_msg_lower = user_message.lower()
    
    # Strong image intent indicators (high confidence) - Enhanced
    strong_indicators = [
        "create image", "generate image", "make image", "draw image", "create picture",
        "generate picture", "make picture", "draw picture", "show me image", "show me picture",
        "i want image", "i want picture", "i need image", "i need picture",
        "can you create", "can you generate", "can you make", "can you draw", "can you show",
        "please create", "please generate", "please make", "please draw", "please show",
        "create for me", "generate for me", "make for me", "draw for me", "show for me",
        # Enhanced patterns for better detection
        "create such", "generate such", "make such", "draw such", "show such",
        "create some", "generate some", "make some", "show some",
        "create a few", "generate a few", "make a few", "show a few"
    ]
    
    # Medium image intent indicators
    medium_indicators = [
        "show me", "let me see", "i want to see", "i would like to see", "display",
        "visualize", "illustrate", "design", "artwork", "sketch", "paint", "render",
        "how does", "what does", "what would", "how would", "imagine", "picture this"
    ]
    
    # Visual subject keywords (things that are typically visualized)
    visual_subjects = [
        "cat", "dog", "animal", "flower", "tree", "house", "car", "landscape", "sunset",
        "dragon", "robot", "castle", "forest", "mountain", "ocean", "space", "planet",
        "character", "person", "food", "building", "city", "nature", "art", "painting",
        "drawing", "scene", "view", "background", "wallpaper", "design", "logo", "icon",
        "image", "images", "picture", "pictures", "photo", "photos"
    ]
    
    # Multiple image indicators
    multiple_indicators = [
        "multiple", "several", "few", "some", "many", "different", "various", "bunch of",
        "collection of", "set of", "group of", "types of", "kinds of", "examples of"
    ]
    
    # Number patterns (2, 3, 4, etc.) - Enhanced
    import re
    number_patterns = [
        r'\b(\d+)\s+(?:different|various|multiple|types?|kinds?|examples?)',
        r'\b(\d+)\s+(?:image|images|picture|pictures|photo|photos)',
        r'(?:create|generate|make|draw|show)\s+(?:such\s+)?(\d+)',
        r'(\d+)\s+(?:of|such)'
    ]
    
    requested_count = 1
    for pattern in number_patterns:
        match = re.search(pattern, user_msg_lower)
        if match:
            try:
                requested_count = int(match.group(1))
                break
            except (ValueError, IndexError):
                continue
    
    # Calculate confidence scores
    strong_score = sum(1 for indicator in strong_indicators if indicator in user_msg_lower)
    medium_score = sum(1 for indicator in medium_indicators if indicator in user_msg_lower) * 0.7
    visual_score = sum(1 for subject in visual_subjects if subject in user_msg_lower) * 0.8
    multiple_score = sum(1 for indicator in multiple_indicators if indicator in user_msg_lower) * 0.6
    
    total_score = strong_score + medium_score + visual_score + multiple_score
    
    # Determine intent
    if strong_score > 0:
        confidence = "high"
        intent = "definite_image_request"
    elif total_score >= 1.5:
        confidence = "medium"
        intent = "likely_image_request"
    elif total_score >= 0.8:
        confidence = "low"
        intent = "possible_image_request"
    else:
        confidence = "none"
        intent = "no_image_request"
    
    return {
        "intent": intent,
        "confidence": confidence,
        "score": total_score,
        "requested_count": min(requested_count, 4),  # Cap at 4
        "has_visual_subjects": visual_score > 0,
        "wants_multiple": multiple_score > 0 or requested_count > 1,
        "detected_subjects": [subject for subject in visual_subjects if subject in user_msg_lower]
    }

def extract_visual_concepts_from_response(ai_response: str, user_intent: dict) -> list:
    """
    Extract visual concepts from AI response for fallback image generation
    
    Args:
        ai_response: AI's response text
        user_intent: Intent analysis from user message
        
    Returns:
        List of potential image prompts
    """
    response_lower = ai_response.lower()
    extracted_concepts = []
    
    # Look for descriptive phrases that could be images
    descriptive_patterns = [
        r'(?:beautiful|stunning|amazing|gorgeous|magnificent|spectacular|breathtaking|majestic|elegant|graceful)\s+([^.!?]*?)(?:\.|!|\?|$)',
        r'(?:imagine|picture|visualize|think of|envision)\s+([^.!?]*?)(?:\.|!|\?|$)',
        r'(?:like|such as|for example|including)\s+([^.!?]*?)(?:\.|!|\?|$)',
        r'(?:a|an|the)\s+([^.!?]*?(?:landscape|scene|view|sight|image|picture|photo))(?:\.|!|\?|$)'
    ]
    
    import re
    for pattern in descriptive_patterns:
        matches = re.findall(pattern, response_lower, re.IGNORECASE)
        for match in matches:
            # Clean and validate the concept
            concept = match.strip()
            concept = re.sub(r'\s+', ' ', concept)
            if len(concept) > 10 and len(concept) < 100:  # Reasonable length
                extracted_concepts.append(concept)
    
    # If user mentioned specific subjects, prioritize those
    if user_intent.get("detected_subjects"):
        for subject in user_intent["detected_subjects"]:
            if subject in response_lower:
                # Create a prompt around the subject
                context_match = re.search(rf'.{{0,50}}{subject}.{{0,50}}', response_lower)
                if context_match:
                    context = context_match.group().strip()
                    # Clean up the context to make a good prompt
                    context = re.sub(r'\b(?:the|a|an|is|are|was|were|will|would|could|should|might|may)\b', '', context)
                    context = re.sub(r'\s+', ' ', context).strip()
                    if len(context) > 5:
                        extracted_concepts.append(context)
    
    return extracted_concepts[:3]  # Return top 3 concepts

def smart_response_analysis(ai_response: str, user_intent: dict) -> tuple:
    """
    Intelligent analysis of AI response to determine if image generation should be triggered
    
    Args:
        ai_response: AI's response text
        user_intent: Intent analysis from user message
        
    Returns:
        Tuple of (should_generate_images, suggested_prompts, suggested_count)
    """
    # If user intent is clear but AI didn't generate patterns, we should intervene
    should_generate = False
    suggested_prompts = []
    suggested_count = 1
    
    # Check if AI response already has generation patterns
    existing_patterns = [
        r'\[GENERATE_IMAGE:', r'\[GENERATE_IMAGES:', r'\[IMAGE:', r'\[IMAGES:',
        r'\[CREATE_IMAGE:', r'\[CREATE_IMAGES:', r'\[DRAW:', r'\[DRAW_IMAGES:'
    ]
    
    import re
    has_existing_patterns = any(re.search(pattern, ai_response, re.IGNORECASE) for pattern in existing_patterns)
    
    if has_existing_patterns:
        return False, [], 1  # AI already handled it
    
    # Determine if we should generate based on user intent
    if user_intent["intent"] == "definite_image_request":
        should_generate = True
        suggested_count = user_intent["requested_count"]
    elif user_intent["intent"] == "likely_image_request" and user_intent["has_visual_subjects"]:
        should_generate = True
        suggested_count = user_intent["requested_count"]
    elif user_intent["intent"] == "possible_image_request" and user_intent["confidence"] != "none":
        # Check if AI response seems to be describing something visual
        visual_response_indicators = [
            "beautiful", "stunning", "amazing", "gorgeous", "magnificent", "spectacular",
            "breathtaking", "majestic", "elegant", "graceful", "colorful", "vibrant",
            "imagine", "picture", "visualize", "looks like", "appears", "resembles"
        ]
        
        response_visual_score = sum(1 for indicator in visual_response_indicators if indicator in ai_response.lower())
        if response_visual_score >= 2:
            should_generate = True
    
    # Extract potential prompts from the response
    if should_generate:
        extracted_concepts = extract_visual_concepts_from_response(ai_response, user_intent)
        
        if extracted_concepts:
            suggested_prompts = extracted_concepts
        elif user_intent.get("detected_subjects"):
            # Use detected subjects as prompts
            suggested_prompts = [f"{', '.join(user_intent['detected_subjects'][:3])}, detailed and beautiful"]
        else:
            # Fallback: try to extract any descriptive content
            # Look for sentences that might describe something visual
            sentences = re.split(r'[.!?]+', ai_response)
            descriptive_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 150:
                    # Check if sentence has descriptive content
                    descriptive_words = ["beautiful", "amazing", "stunning", "colorful", "bright", "dark", "large", "small", "tall", "short"]
                    if any(word in sentence.lower() for word in descriptive_words):
                        # Clean sentence to make it a good prompt
                        clean_sentence = re.sub(r'\b(?:it|this|that|there|here|they|them|these|those)\b', '', sentence, flags=re.IGNORECASE)
                        clean_sentence = re.sub(r'\s+', ' ', clean_sentence).strip()
                        if len(clean_sentence) > 10:
                            descriptive_sentences.append(clean_sentence)
            
            if descriptive_sentences:
                suggested_prompts = descriptive_sentences[:2]  # Take top 2
    
    return should_generate, suggested_prompts, suggested_count

async def process_auto_image_generation_async(client: Client, message: Message, ai_response: str, user_id: int) -> Tuple[str, List[Dict]]:
    """
    Process AI response for automatic image generation requests (Advanced Enhanced version)
    
    Args:
        client: Pyrogram client instance
        message: Original user message
        ai_response: AI's response text
        user_id: User ID
        
    Returns:
        Tuple of (cleaned_response_text, list_of_image_generation_tasks)
    """
    image_tasks = []
    
    # Step 1: Analyze user intent
    user_intent = analyze_user_intent_for_images(message.text or "")
    print(f"[DEBUG] User intent analysis: {user_intent}")
    
    # Enhanced pattern to capture multiple images and count - using DOTALL to capture complete prompts
    primary_patterns = [
        r'\[GENERATE_IMAGE:\s*(.*?)\]',
        r'\[GENERATE_IMAGES:\s*(\d+)\s*:\s*(.*?)\]',  # [GENERATE_IMAGES: 3: cats playing]
        r'\[MULTI_IMAGE:\s*(.*?)\]'
    ]
    
    # Additional flexible patterns for variations the AI might generate
    flexible_patterns = [
        r'\[IMAGE:\s*(.*?)\]',
        r'\[IMAGES:\s*(\d+)\s*:\s*(.*?)\]',
        r'\[GEN_IMAGE:\s*(.*?)\]',
        r'\[GEN_IMAGES:\s*(\d+)\s*:\s*(.*?)\]',
        r'\[CREATE_IMAGE:\s*(.*?)\]',
        r'\[CREATE_IMAGES:\s*(\d+)\s*:\s*(.*?)\]',
        r'\[DRAW:\s*(.*?)\]',
        r'\[DRAW_IMAGES:\s*(\d+)\s*:\s*(.*?)\]'
    ]
    
    all_matches = []
    all_patterns = primary_patterns + flexible_patterns
    
    # Step 2: Process existing patterns in AI response
    for pattern in all_patterns:
        try:
            matches = re.findall(pattern, ai_response, re.IGNORECASE | re.DOTALL)
            
            # Check if this is a multiple images pattern (has 2 capture groups)
            is_multiple_pattern = pattern.count('(') == 2 and '\\d+' in pattern
            
            for match in matches:
                try:
                    if is_multiple_pattern:
                        # Pattern like [GENERATE_IMAGES: 3: cats] returns tuple (count, prompt)
                        if isinstance(match, tuple) and len(match) == 2:
                            count_str, prompt = match
                            # Ensure both are strings
                            count_str = str(count_str).strip()
                            prompt = str(prompt).strip()
                            
                            # Clean and validate the prompt
                            clean_prompt = prompt.replace('\n', ' ').replace('\r', ' ')
                            clean_prompt = ' '.join(clean_prompt.split())  # Remove extra whitespace
                            
                            if clean_prompt and len(clean_prompt) > 3:  # Only add if not empty and meaningful
                                count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 1
                                all_matches.append((clean_prompt, count))
                                print(f"[DEBUG] Multiple pattern match: '{clean_prompt}' x{count}")
                        else:
                            print(f"[DEBUG] Unexpected tuple format for multiple pattern: {match}")
                    else:
                        # Pattern like [GENERATE_IMAGE: cats] returns string
                        if isinstance(match, tuple):
                            # If it's a tuple, take the first element
                            prompt = str(match[0]) if match else ""
                        else:
                            # If it's a string, use it directly
                            prompt = str(match)
                        
                        # Clean and validate the prompt
                        clean_prompt = prompt.strip().replace('\n', ' ').replace('\r', ' ')
                        clean_prompt = ' '.join(clean_prompt.split())  # Remove extra whitespace
                        
                        if clean_prompt and len(clean_prompt) > 3:  # Only add if not empty and meaningful
                            all_matches.append((clean_prompt, 1))
                            print(f"[DEBUG] Single pattern match: '{clean_prompt}'")
                            
                except Exception as match_error:
                    print(f"[DEBUG] Error processing match {match}: {match_error}")
                    continue
                    
        except Exception as pattern_error:
            print(f"[DEBUG] Error processing pattern {pattern}: {pattern_error}")
            continue
    
    # Step 3: Smart fallback analysis (most important improvement)
    if not all_matches:
        try:
            should_generate, suggested_prompts, suggested_count = smart_response_analysis(ai_response, user_intent)
            
            if should_generate and suggested_prompts:
                print(f"[DEBUG] Smart fallback triggered: {len(suggested_prompts)} prompts, count: {suggested_count}")
                
                # Add suggested prompts with proper string handling
                if suggested_count > 1 and len(suggested_prompts) == 1:
                    # Multiple images of the same concept
                    prompt = str(suggested_prompts[0]) if suggested_prompts[0] else "beautiful artwork"
                    all_matches.append((prompt, suggested_count))
                else:
                    # Multiple different concepts or single concept
                    for prompt in suggested_prompts:
                        clean_prompt = str(prompt) if prompt else "beautiful artwork"
                        all_matches.append((clean_prompt, 1))
        except Exception as fallback_error:
            print(f"[DEBUG] Error in smart fallback analysis: {fallback_error}")
    
    # Step 4: Natural language fallback (existing logic, but enhanced)
    if not all_matches and user_intent["confidence"] != "none":
        try:
            print(f"[DEBUG] Applying natural language fallback for user intent: {user_intent['intent']}")
            
            # Extract potential image requests from the AI response
            natural_patterns = [
                r'(?:here\'s|i\'ll create|i\'ll generate|i\'ll make|i\'ll show|i\'ll draw).*?(?:image|picture|visual|artwork|illustration).*?(?:of|for|with|featuring)?\s*([^.!?]*?)(?:\.|!|\?|$)',
                r'(?:creating|generating|making|showing|drawing|designing).*?(?:image|picture|visual|artwork|illustration).*?(?:of|for|with|featuring)?\s*([^.!?]*?)(?:\.|!|\?|$)',
                r'(?:perfect|great|wonderful|amazing|beautiful|stunning|gorgeous).*?(?:image|picture|visual|artwork|illustration).*?(?:of|for|with|featuring)?\s*([^.!?]*?)(?:\.|!|\?|$)',
                r'(?:would|could|might)\s+(?:be|look|appear).*?(?:like|as)\s+([^.!?]*?)(?:\.|!|\?|$)'
            ]
            
            for pattern in natural_patterns:
                try:
                    matches = re.findall(pattern, ai_response, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        # Ensure match is a string
                        if isinstance(match, tuple):
                            match = str(match[0]) if match else ""
                        else:
                            match = str(match)
                            
                        clean_prompt = match.strip().replace('\n', ' ').replace('\r', ' ')
                        clean_prompt = ' '.join(clean_prompt.split())
                        if clean_prompt and len(clean_prompt) > 5:
                            count = user_intent["requested_count"]
                            all_matches.append((clean_prompt, count))
                            print(f"[DEBUG] Natural language fallback detected: '{clean_prompt}' (count: {count})")
                            break  # Only take the first good match from natural language
                except Exception as natural_error:
                    print(f"[DEBUG] Error in natural pattern {pattern}: {natural_error}")
                    continue
        except Exception as natural_fallback_error:
            print(f"[DEBUG] Error in natural language fallback: {natural_fallback_error}")
    
    # Enhanced debugging
    if all_matches:
        print(f"[DEBUG] Auto-image detection successful for user {user_id}")
        print(f"[DEBUG] User intent: {user_intent['intent']} (confidence: {user_intent['confidence']})")
        print(f"[DEBUG] Extracted {len(all_matches)} image tasks")
        
        # Remove all generation markers from the response
        cleaned_response = ai_response
        for pattern in all_patterns:
            try:
                cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.IGNORECASE | re.DOTALL)
            except Exception as clean_error:
                print(f"[DEBUG] Error cleaning pattern {pattern}: {clean_error}")
                continue
        cleaned_response = cleaned_response.strip()
        
        # Prepare image generation tasks
        for image_prompt, count in all_matches:
            try:
                # Ensure both are proper types
                image_prompt = str(image_prompt) if image_prompt else "beautiful artwork"
                count = int(count) if isinstance(count, (int, str)) and str(count).isdigit() else 1
                
                if not image_prompt or len(image_prompt.strip()) < 3:
                    continue
                
                # Limit count for safety
                count = min(count, 4)  # Max 4 images per prompt
                
                # Enhanced prompt cleaning and validation
                # Remove common unwanted phrases
                unwanted_phrases = [
                    "here's", "i'll create", "i'll generate", "i'll make", "i'll show", 
                    "creating", "generating", "making", "showing", "for you", "perfect",
                    "great", "wonderful", "amazing", "beautiful", "stunning", "gorgeous",
                    "would be", "could be", "might be", "looks like", "appears to be"
                ]
                
                for phrase in unwanted_phrases:
                    try:
                        image_prompt = re.sub(rf'\b{phrase}\b', '', image_prompt, flags=re.IGNORECASE)
                    except Exception:
                        continue
                
                # Clean up the prompt
                image_prompt = re.sub(r'\s+', ' ', image_prompt).strip()
                
                # Skip if prompt is too short or contains mostly common words
                if len(image_prompt) < 5:
                    continue
                
                # Enhance prompt quality
                if not any(word in image_prompt.lower() for word in ['detailed', 'beautiful', 'realistic', 'artistic']):
                    image_prompt += ", detailed and beautiful"
                
                image_tasks.append({
                    'prompt': image_prompt,
                    'count': count,
                    'style': 'realistic'
                })
                
                # Enhanced debug logging
                print(f"[DEBUG] Auto-image: Final prompt: '{image_prompt}' (count: {count})")
            
            except Exception as task_error:
                print(f"[DEBUG] Error processing image task: {task_error}")
                continue
        
        return cleaned_response, image_tasks
    else:
        # Enhanced debug when no matches found
        print(f"[DEBUG] No auto-image patterns found for user {user_id}")
        print(f"[DEBUG] User intent: {user_intent['intent']} (confidence: {user_intent['confidence']}, score: {user_intent['score']})")
        print(f"[DEBUG] User message: '{(message.text or '')[:100]}...'")
        print(f"[DEBUG] AI response excerpt: '{ai_response[:200]}...'")
    
    return ai_response, image_tasks

def clean_prompt_for_single_image(original_prompt: str) -> str:
    """
    Clean prompt to ensure it generates a single subject per image
    
    Args:
        original_prompt: Original prompt that might contain multiple subject references
        
    Returns:
        Cleaned prompt for generating a single image with one main subject
    """
    import re
    
    # Ensure we have a string to work with
    if not isinstance(original_prompt, str):
        original_prompt = str(original_prompt) if original_prompt else "beautiful artwork"
    
    prompt = original_prompt.lower().strip()
    
    # Remove number references that suggest multiple subjects
    # "3 cats" -> "cat", "several dogs" -> "dog", "different flowers" -> "flower"
    number_patterns = [
        r'\b\d+\s+(?:different\s+)?(\w+)',  # "3 cats", "4 different dogs"
        r'\b(?:several|multiple|many|few|some|various)\s+(?:different\s+)?(\w+)',  # "several cats"
        r'\b(?:different|various)\s+(\w+)',  # "different cats"
        r'\b(\w+)s\b(?:\s+(?:with|in|of|from|playing|sitting|standing|running))',  # "cats playing" -> "cat playing"
    ]
    
    # Apply patterns to extract singular subject
    for pattern in number_patterns:
        match = re.search(pattern, prompt)
        if match:
            singular_subject = match.group(1)
            # Convert plural to singular if needed
            if singular_subject.endswith('s') and len(singular_subject) > 3:
                # Simple pluralization rules
                if singular_subject.endswith('ies'):
                    singular_subject = singular_subject[:-3] + 'y'
                elif singular_subject.endswith('es'):
                    singular_subject = singular_subject[:-2]
                elif singular_subject.endswith('s'):
                    singular_subject = singular_subject[:-1]
            
            # Replace the original phrase with the singular subject
            prompt = re.sub(pattern, singular_subject, prompt)
            break
    
    # Additional cleaning - remove phrases that suggest multiple items
    multiple_phrases = [
        r'\b(?:different|various|multiple|several|many|few|some)\s+',
        r'\b\d+\s+',
        r'\bgroup\s+of\s+',
        r'\bcollection\s+of\s+',
        r'\bset\s+of\s+',
        r'\bbunch\s+of\s+',
        r'\bsuch\s+'  # Remove "such" as well
    ]
    
    for phrase_pattern in multiple_phrases:
        prompt = re.sub(phrase_pattern, '', prompt)
    
    # Clean up extra spaces and ensure proper format
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    
    # Ensure it starts with "a" or "an" for singular reference
    if not prompt.startswith(('a ', 'an ', 'the ')):
        # Add appropriate article
        if prompt and prompt[0] in 'aeiou':
            prompt = f"an {prompt}"
        else:
            prompt = f"a {prompt}"
    
    return prompt

async def generate_images_in_background(client: Client, message: Message, image_tasks: List[Dict], user_id: int):
    """
    Generate images in the background and send them after text response (Fixed for single subjects)
    """
    if not image_tasks:
        return
    
    # Send initial "generating" message
    generating_msg = await message.reply_text(
        "🎨 **Generating your images...**\n\n"
        f"Creating {sum(task['count'] for task in image_tasks)} image(s) for you. This may take a moment.\n\n"
        "⏳ Please wait..."
    )
    
    all_generated_images = []
    
    try:
        for task_index, task in enumerate(image_tasks):
            original_prompt = task['prompt']
            count = task['count']
            style = task['style']
            
            # Clean the prompt for single image generation
            base_prompt = clean_prompt_for_single_image(original_prompt)
            
            # Update progress with complete prompt
            display_prompt = original_prompt if len(original_prompt) <= 50 else original_prompt[:50] + "..."
            total_images = sum(task['count'] for task in image_tasks)
            
            await generating_msg.edit_text(
                f"🎨 **Generating your images...**\n\n"
                f"Working on: `{display_prompt}`\n"
                f"Task {task_index + 1}/{len(image_tasks)} | Total: {total_images} images\n\n"
                "🖌️ Creating unique visuals..."
            )
            
            # Send typing action
            await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.UPLOAD_PHOTO)
            
            try:
                # For multiple images, generate each one individually with proper variations
                if count > 1:
                    # Generate each image individually with unique characteristics
                    for img_num in range(count):
                        # Create style and perspective variations (not content variations)
                        style_variations = [
                            "detailed and photorealistic",
                            "artistic and beautiful", 
                            "high quality with dramatic lighting",
                            "elegant with vibrant colors"
                        ]
                        
                        perspective_variations = [
                            "close-up view",
                            "wide angle shot", 
                            "artistic perspective",
                            "professional photography style"
                        ]
                        
                        mood_variations = [
                            "in natural lighting",
                            "with dramatic shadows",
                            "in soft morning light", 
                            "with colorful background"
                        ]
                        
                        # Combine base prompt with variations that don't suggest multiple subjects
                        style_mod = style_variations[img_num % len(style_variations)]
                        perspective_mod = perspective_variations[img_num % len(perspective_variations)]
                        mood_mod = mood_variations[img_num % len(mood_variations)]
                        
                        # Create the final prompt ensuring single subject
                        varied_prompt = f"{base_prompt}, {style_mod}, {perspective_mod}, {mood_mod}"
                        
                        print(f"[DEBUG] Generating single image {img_num + 1}/{count}")
                        print(f"[DEBUG] Original prompt: '{original_prompt}'")
                        print(f"[DEBUG] Cleaned base: '{base_prompt}'")
                        print(f"[DEBUG] Final prompt: '{varied_prompt}'")
                        
                        # Update progress for individual image
                        await generating_msg.edit_text(
                            f"🎨 **Generating your images...**\n\n"
                            f"Working on: `{display_prompt}`\n"
                            f"Creating image {img_num + 1}/{count} - each with single subject\n\n"
                            "🖌️ Ensuring unique variations..."
                        )
                        
                        # Generate single image with cleaned prompt
                        urls, error = await generate_images(
                            prompt=varied_prompt,
                            style=style,
                            max_images=1,  # Always 1 to ensure single subject
                            user_id=user_id
                        )
                        
                        if urls and not error:
                            valid_urls = [url for url in urls if validate_image_url(url)]
                            if valid_urls:
                                all_generated_images.extend([(url, f"Image {img_num + 1}: {base_prompt}") for url in valid_urls])
                                await error_log(client, "AUTO_IMAGE_SUCCESS", f"Generated single image {img_num + 1} for: {base_prompt[:50]}...", f"User: {user_id}", user_id)
                            else:
                                await error_log(client, "AUTO_IMAGE_INVALID", f"Generated URLs were invalid for image {img_num + 1}", f"Prompt: {base_prompt[:50]}...", user_id)
                        else:
                            await error_log(client, "AUTO_IMAGE_FAIL", f"Failed to generate image {img_num + 1}: {error or 'Unknown error'}", f"Prompt: {base_prompt[:50]}...", user_id)
                        
                        # Small delay between generations to avoid rate limits
                        await asyncio.sleep(0.5)
                else:
                    # Single image generation - still clean the prompt
                    clean_prompt = clean_prompt_for_single_image(original_prompt)
                    print(f"[DEBUG] Generating single image")
                    print(f"[DEBUG] Original: '{original_prompt}' -> Cleaned: '{clean_prompt}'")
                    
                    urls, error = await generate_images(
                        prompt=clean_prompt,
                        style=style,
                        max_images=1,
                        user_id=user_id
                    )
                    
                    if urls and not error:
                        valid_urls = [url for url in urls if validate_image_url(url)]
                        if valid_urls:
                            all_generated_images.extend([(url, clean_prompt) for url in valid_urls])
                            await error_log(client, "AUTO_IMAGE_SUCCESS", f"Generated image for: {clean_prompt[:50]}...", f"User: {user_id}", user_id)
                        else:
                            await error_log(client, "AUTO_IMAGE_INVALID", "Generated URLs were invalid", f"Prompt: {clean_prompt[:50]}...", user_id)
                    else:
                        await error_log(client, "AUTO_IMAGE_FAIL", f"Failed to generate image: {error or 'Unknown error'}", f"Prompt: {clean_prompt[:50]}...", user_id)
                    
            except Exception as e:
                await error_log(client, "AUTO_IMAGE_ERROR", str(e), f"Prompt: {original_prompt[:50]}...", user_id)
                continue
        
        # Send all generated images
        if all_generated_images:
            # Group images into media groups (max 10 per group)
            image_groups = [all_generated_images[i:i+10] for i in range(0, len(all_generated_images), 10)]
            
            for group_index, image_group in enumerate(image_groups):
                # Prepare media group
                media_group = []
                for i, (image_url, description) in enumerate(image_group):
                    # Add caption with manual generation info for first image only
                    if i == 0 and group_index == 0:
                        caption = (
                            "You can manually gen images as you want by using /img your prompt\n\n"
                            "**Example:**\n"
                            "`/img a cat playing in garden`"
                        )
                    else:
                        caption = ""
                    
                    media_group.append(InputMediaPhoto(media=image_url, caption=caption[:1024] if caption else ""))
                
                # Send media group
                try:
                    await client.send_media_group(
                        chat_id=message.chat.id,
                        media=media_group,
                        reply_to_message_id=message.id
                    )
                except Exception as e:
                    await error_log(client, "AUTO_IMAGE_SEND", str(e), f"Failed to send media group {group_index + 1}", user_id)
            
            # Delete the generating message
            try:
                await generating_msg.delete()
            except Exception:
                pass  # Message might already be deleted
            
        else:
            # No images generated - delete the generating message and show failure
            try:
                await generating_msg.delete()
            except Exception:
                pass
            
            # Send a brief failure message
            await message.reply_text(
                "❌ **Image generation failed**\n"
                f"You can try: `/img {clean_prompt_for_single_image(image_tasks[0]['prompt']) if image_tasks else 'your prompt'}`"
            )
            
    except Exception as e:
        await error_log(client, "AUTO_IMAGE_BACKGROUND", str(e), "Background image generation failed", user_id)
        try:
            await generating_msg.delete()
        except:
            pass
        
        # Send brief error message
        try:
            await message.reply_text(
                "❌ **Image generation error**\n"
                f"You can try: `/img {clean_prompt_for_single_image(image_tasks[0]['prompt']) if image_tasks else 'your prompt'}`"
            )
        except:
            pass

# Default system message with modern, professional tone
DEFAULT_SYSTEM_MESSAGE: List[Dict[str, str]] = [
    {
        "role": "system",
        "content": (
            "You are @AdvChatGptBot (https://t.me/AdvChatGptBot), an advanced multi-modal AI assistant developed by Chandan Singh (@techycsr). "
            "You can: \n"
            "• Answer questions, chat, and help with any topic\n"
            "• Generate images AUTOMATICALLY when users request visuals or when images would enhance your response (single or multiple images)\n"
            "• Read and analyze images (vision, img2text), answer questions about them, solve MCQs in images, and transcribe or summarize documents\n"
            "• Read and summarize documents, extract text from images, and answer questions about their content\n"
            "• Support multiple AI models (Gpt4.1, Qwen3, DeepSeek R1, Dall-e3, Flux, Flux-Pro)\n"
            "• Guide users to use /img for manual image generation, /settings for model selection, and /help for more info\n"
            "• Always be proactive in suggesting features and helping users get the most out of the bot\n"
            "• CRITICAL: AUTOMATIC IMAGE GENERATION - When users ask for images, visual content, or when an image would make your response better, ALWAYS use these exact patterns:\n"
            "  - Single image: '[GENERATE_IMAGE: detailed description]'\n"
            "  - Multiple images: '[GENERATE_IMAGES: number: detailed description]' (e.g., '[GENERATE_IMAGES: 3: cute puppies playing]')\n"
            "  - NEVER forget to use these patterns when generating images automatically\n"
            "  - ALWAYS include the brackets and exact format\n"
            "  - Follow the pattern with engaging text response\n"
            "• WHEN TO AUTO-GENERATE: Use auto-generation for requests like 'show me', 'create', 'generate', 'draw', 'make', 'I want to see', 'can you show', 'display', 'visualize', 'multiple images', 'different images', etc.\n"
            "• If a user sends an image, analyze it, answer any questions, and if it's an MCQ, solve it and explain the answer\n"
            "• If a user sends a document or asks about a file, summarize or extract the main points\n"
            "• Always use a modern, friendly, and helpful tone."
        )
    },
    # --- Enhanced Training examples for automatic image generation ---
    {
        "role": "user",
        "content": "Can you create an image of a futuristic city?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style, ultra-detailed]\n\n"
            "I'll create a stunning futuristic city image for you! This will show a cyberpunk-style metropolis with flying cars, neon lights, and impressive skyscrapers reaching into the sky. 🌃✨"
        )
    },
    {
        "role": "user",
        "content": "Show me a beautiful sunset"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a beautiful sunset over mountains with golden orange sky, dramatic clouds, and peaceful landscape]\n\n"
            "Here's a gorgeous sunset scene for you! You'll see golden orange hues painting the sky over majestic mountains with dramatic clouds creating a peaceful, breathtaking landscape. 🌅🏔️"
        )
    },
    {
        "role": "user",
        "content": "I want to see 3 different cats"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: adorable cats with different breeds and colors, persian cat, siamese cat, maine coon cat, cute and fluffy]\n\n"
            "I'll create 3 different adorable cats for you! You'll see a Persian, Siamese, and Maine Coon - each with their unique characteristics and charm. 🐱🐾"
        )
    },
    {
        "role": "user",
        "content": "Can you show me some flowers?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: beautiful flowers with different colors and types, roses, sunflowers, daisies, vibrant and detailed]\n\n"
            "I'll show you some beautiful flowers! You'll see vibrant roses, cheerful sunflowers, and delicate daisies - each showcasing nature's incredible beauty and colors. 🌹🌻🌼"
        )
    },
    {
        "role": "user",
        "content": "Create 4 different animals for me"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 4: different animals in their natural habitats, lion, elephant, dolphin, eagle, majestic and wild]\n\n"
            "I'll create 4 amazing different animals for you! You'll see a majestic lion, a wise elephant, a playful dolphin, and a soaring eagle - each captured in their natural beauty and strength. 🦁🐘🐬🦅"
        )
    },
    {
        "role": "user",
        "content": "I want to see multiple dogs, maybe 3"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: different dog breeds playing and happy, golden retriever, german shepherd, beagle, cute and energetic]\n\n"
            "Perfect! I'll create 3 different dog breeds for you. You'll get to see a friendly Golden Retriever, a majestic German Shepherd, and an adorable Beagle - each showing their unique personality and charm! 🐕🐶"
        )
    },
    {
        "role": "user",
        "content": "Display different landscapes for me"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: diverse beautiful landscapes, mountain valley, ocean beach, forest path, scenic and breathtaking]\n\n"
            "I'll display 3 diverse and breathtaking landscapes for you - a serene mountain valley, a stunning ocean beach, and a mystical forest path. Each will transport you to a different beautiful world! 🏔️🏖️🌲"
        )
    },
    {
        "role": "user",
        "content": "Generate some cars for me, different types"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: different types of cars, sports car, luxury sedan, electric vehicle, modern and sleek design]\n\n"
            "I'll generate 3 different types of cars for you! You'll see a sleek sports car, an elegant luxury sedan, and a modern electric vehicle - each representing different automotive excellence and innovation. 🚗🏎️🚙"
        )
    },
    {
        "role": "user",
        "content": "Make me an image of a dragon"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a majestic dragon with scales, wings spread wide, breathing fire, fantasy creature, powerful and mythical]\n\n"
            "I'll make an amazing dragon image for you! This will feature a majestic dragon with detailed scales, wings spread wide, breathing fire - a truly powerful and mythical fantasy creature. 🐉🔥"
        )
    },
    {
        "role": "user",
        "content": "I need character designs, can you help?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: different character designs, fantasy warrior, magical wizard, space explorer, detailed and creative]\n\n"
            "I'd love to help with character designs! I'll create 3 unique characters for you - a brave fantasy warrior, a wise magical wizard, and an adventurous space explorer. Each will have their own distinctive style and personality! ⚔️🧙‍♂️🚀"
        )
    },
    {
        "role": "user",
        "content": "Can you visualize different food dishes?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: delicious food dishes from different cuisines, italian pasta, japanese sushi, mexican tacos, appetizing and colorful]\n\n"
            "I'll visualize 3 mouth-watering dishes from different cuisines for you - authentic Italian pasta, fresh Japanese sushi, and flavorful Mexican tacos. Each will look absolutely appetizing and showcase unique cultural flavors! 🍝🍣🌮"
        )
    },
    {
        "role": "user",
        "content": "Draw me a robot"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a futuristic robot with advanced technology, metallic body, glowing eyes, humanoid design, sci-fi style]\n\n"
            "I'll draw a cool futuristic robot for you! This will feature advanced technology with a metallic body, glowing eyes, and sleek humanoid design - perfect sci-fi style. 🤖✨"
        )
    },
    {
        "role": "user",
        "content": "Let me see some space scenes"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: space scenes with different planets and galaxies, alien planet surface, spiral galaxy, nebula with stars, cosmic and spectacular]\n\n"
            "I'll take you on a cosmic journey with 3 spectacular space scenes! You'll explore an alien planet surface, witness a magnificent spiral galaxy, and marvel at a colorful nebula filled with stars. Each scene will be absolutely cosmic and awe-inspiring! 🪐🌌⭐"
        )
    },
    {
        "role": "user",
        "content": "Create artwork of a castle"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a medieval castle on a hill, stone walls, towers, dramatic sky, fantasy architecture, detailed and majestic]\n\n"
            "I'll create beautiful artwork of a castle for you! This will show a medieval castle perched on a hill with stone walls, towers reaching toward a dramatic sky - truly majestic fantasy architecture. 🏰👑"
        )
    },
    {
        "role": "user",
        "content": "Paint me a forest scene"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a mystical forest with tall trees, sunlight filtering through leaves, magical atmosphere, peaceful and enchanting]\n\n"
            "I'll paint a mystical forest scene for you! This will feature tall trees with sunlight filtering through leaves, creating a magical atmosphere that's both peaceful and enchanting. 🌳🌞✨"
        )
    },
    {
        "role": "user",
        "content": "Render some abstract art"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: abstract art with flowing shapes, vibrant colors, geometric patterns, modern artistic style, creative and expressive]\n\n"
            "I'll render some stunning abstract art for you! This will feature flowing shapes with vibrant colors and geometric patterns in a modern artistic style - truly creative and expressive. 🎨🌈"
        )
    },
    {
        "role": "user",
        "content": "How do I use the /img command?"
    },
    {
        "role": "assistant",
        "content": (
            "You have **two amazing ways** to generate images:\n\n"
            "🤖 **Automatic Generation** (New!): Just ask me naturally!\n"
            "• \"Can you show me a sunset over mountains?\"\n"
            "• \"Create a cute robot for me\"\n"
            "• \"I want to see 3 different flowers\"\n"
            "• \"Draw me a dragon\"\n"
            "• \"Generate some cars\"\n\n"
            "⌨️ **Manual /img Command**: For precise control and styles:\n"
            "```/img a cat in space, wearing an astronaut helmet, floating among stars```\n\n"
            "**Manual examples:**\n"
            "• `/img realistic portrait of a wise old wizard`\n"
            "• `/img anime style magical girl with pink hair`\n"
            "• `/img photorealistic mountain landscape at sunset`\n\n"
            "The automatic way is more conversational - just tell me what you want to see! 🎨"
        )
    },
    # --- Training examples for manual /img command ---
    {
        "role": "user",
        "content": "What styles can I use with /img?"
    },
    {
        "role": "assistant",
        "content": (
            "Here are the **amazing styles** you can use with `/img`:\n\n"
            "🎨 **Available Styles:**\n"
            "• `realistic` - Photorealistic images\n"
            "• `anime` - Anime/manga style\n"
            "• `cartoon` - Cartoon/animated style\n"
            "• `digital_art` - Digital artwork style\n"
            "• `oil_painting` - Classic oil painting look\n"
            "• `watercolor` - Soft watercolor effect\n"
            "• `sketch` - Pencil sketch style\n\n"
            "**Examples:**\n"
            "```/img realistic portrait of a mountain climber```\n"
            "```/img anime style magical forest with glowing trees```\n"
            "```/img cartoon cute dinosaur playing with butterflies```\n\n"
            "💡 **Pro Tip**: Be descriptive for better results!"
        )
    },
    {
        "role": "user",
        "content": "Generate an image using /img"
    },
    {
        "role": "assistant",
        "content": (
            "Here's how to use the `/img` command:\n\n"
            "**Copy and paste this example:**\n"
            "```/img a majestic dragon soaring over a medieval castle, fantasy art style, detailed```\n\n"
            "**More examples to try:**\n"
            "```/img realistic photo of a cozy coffee shop on a rainy day```\n"
            "```/img anime style warrior princess with glowing sword```\n"
            "```/img watercolor painting of cherry blossoms in spring```\n\n"
            "Just replace the description with what you want to see! 🎨✨"
        )
    },
    # --- Training examples for MCQ solving in images ---
    {
        "role": "user",
        "content": "[Image of an MCQ: 'What is the capital of France? (A) Berlin (B) Paris (C) Rome (D) Madrid']"
    },
    {
        "role": "assistant",
        "content": (
            "The image contains a multiple choice question. The correct answer is: (B) Paris.\n"
            "If you have more questions or want to generate an image, use the /img command!"
        )
    },
    # --- Training examples for document reading ---
    {
        "role": "user",
        "content": "[Image of a document: 'The water cycle consists of evaporation, condensation, and precipitation...']"
    },
    {
        "role": "assistant",
        "content": (
            "The image is a document about the water cycle. Here's a summary: The water cycle consists of evaporation, condensation, and precipitation.\n"
            "If you want to generate an image about the water cycle, copy and paste this command in chat:\n"
            "```/img a diagram of the water cycle showing evaporation, condensation, and precipitation```"
        )
    },
    # --- Training examples for vision/description ---
    {
        "role": "user",
        "content": "What's in this image?"
    },
    {
        "role": "assistant",
        "content": (
            "Please send the image and I'll analyze it for you. I can describe, answer questions, or solve MCQs in images."
        )
    },
    # --- General help and feature guidance ---
    {
        "role": "user",
        "content": "What can you do?"
    },
    {
        "role": "assistant",
        "content": (
            "I'm @AdvChatGptBot, your multi-modal AI assistant!\n"
            "• Generate images: Use /img with your prompt\n"
            "• Read and answer questions about images\n"
            "• Solve MCQs in images\n"
            "• Summarize documents\n"
            "• Support multiple AI models (change in /settings)\n"
            "• For more, use /help or ask me anything!"
        )
    },
    # --- About the developer ---
    {
        "role": "assistant",
        "content": (
            "👨‍💻 **About the Developer**\n\n"
            "This bot was created by Chandan Singh (@techycsr), a passionate tech enthusiast and student developer. "
            "He specializes in:\n"
            "• Python Development\n"
            "• AI/ML Applications\n"
            "• Telegram Bot Development\n"
            "• Open Source Projects\n\n"
            "🔗 **Connect with the Developer**:\n"
            "• Telegram: @techycsr\n"
            "• Website: techycsr.dev\n"
            "• GitHub: github.com/techycsr\n\n"
            "• LinkedIn: linkedin.com/in/techycsr\n\n"
            "This bot is one of his many projects showcasing his expertise in AI and bot development."
        )
    },
    {
        "role": "system",
        "content": (
            "Remember: This bot was developed by Chandan Singh (@techycsr) as a demonstration of advanced AI "
            "capabilities in Telegram. For support or to learn more about the developer, visit techycsr.dev "
            "or contact @techycsr on Telegram."
        )
    }
]

def post_process_ai_response_for_missing_patterns(ai_response: str, user_intent: dict, user_message: str) -> str:
    """
    Post-process AI response to inject missing generation patterns when they should be there
    
    Args:
        ai_response: Original AI response
        user_intent: User intent analysis
        user_message: Original user message
        
    Returns:
        Enhanced AI response with injected patterns if needed
    """
    # Ensure we have strings to work with
    if not isinstance(ai_response, str):
        ai_response = str(ai_response) if ai_response else ""
    if not isinstance(user_message, str):
        user_message = str(user_message) if user_message else ""
    
    # Only proceed if user clearly wanted images but AI didn't generate patterns
    if user_intent["confidence"] == "none" or user_intent["intent"] == "no_image_request":
        return ai_response
    
    # Check if AI already has generation patterns
    existing_patterns = [
        r'\[GENERATE_IMAGE:', r'\[GENERATE_IMAGES:', r'\[IMAGE:', r'\[IMAGES:',
        r'\[CREATE_IMAGE:', r'\[CREATE_IMAGES:', r'\[DRAW:', r'\[DRAW_IMAGES:'
    ]
    
    import re
    has_existing_patterns = any(re.search(pattern, ai_response, re.IGNORECASE) for pattern in existing_patterns)
    
    if has_existing_patterns:
        return ai_response  # AI already handled it correctly
    
    # Analyze if we should inject patterns
    should_inject = False
    injection_prompt = ""
    injection_count = 1
    
    if user_intent["intent"] == "definite_image_request":
        should_inject = True
        injection_count = user_intent["requested_count"]
    elif user_intent["intent"] == "likely_image_request" and user_intent["has_visual_subjects"]:
        should_inject = True
        injection_count = user_intent["requested_count"]
    
    if should_inject:
        # Try to extract a good prompt from user message or AI response
        if user_intent.get("detected_subjects"):
            # Use detected visual subjects
            subjects = user_intent["detected_subjects"][:3]
            injection_prompt = f"{', '.join(subjects)}, beautiful and detailed"
        else:
            # Try to extract from user message
            user_lower = user_message.lower()
            
            # Remove common request words to get the core concept
            clean_user_msg = user_lower
            request_words = ["show me", "create", "generate", "make", "draw", "i want to see", "can you show", "let me see", "such", "some", "a few"]
            for word in request_words:
                clean_user_msg = clean_user_msg.replace(word, "")
            
            clean_user_msg = clean_user_msg.strip().strip(".,!?")
            
            if len(clean_user_msg) > 5 and len(clean_user_msg) < 100:
                injection_prompt = f"{clean_user_msg}, detailed and beautiful"
            else:
                # Fallback: try to extract from AI response
                response_concepts = extract_visual_concepts_from_response(ai_response, user_intent)
                if response_concepts:
                    injection_prompt = response_concepts[0]
                else:
                    injection_prompt = "beautiful artwork, detailed and creative"
        
        # Inject the pattern at the beginning of the response
        if injection_count > 1:
            pattern = f"[GENERATE_IMAGES: {injection_count}: {injection_prompt}]\n\n"
        else:
            pattern = f"[GENERATE_IMAGE: {injection_prompt}]\n\n"
        
        enhanced_response = pattern + ai_response
        
        print(f"[DEBUG] Post-processing: Injected pattern '{pattern.strip()}' for user intent '{user_intent['intent']}'")
        return enhanced_response
    
    return ai_response

async def track_auto_generation_accuracy(user_id: int, user_intent: dict, ai_response: str, image_tasks: list, success: bool):
    """
    Track auto-generation accuracy for monitoring and improvement
    
    Args:
        user_id: User ID
        user_intent: User intent analysis
        ai_response: AI response
        image_tasks: Generated image tasks
        success: Whether auto-generation was successful
    """
    try:
        # Simple logging for now - could be enhanced with database storage
        status = "SUCCESS" if success else "FAILED"
        intent_info = f"{user_intent['intent']}({user_intent['confidence']})"
        task_count = len(image_tasks) if image_tasks else 0
        
        print(f"[ACCURACY] User:{user_id} | Intent:{intent_info} | Status:{status} | Tasks:{task_count}")
        
        # Log patterns for analysis
        if success and image_tasks:
            for task in image_tasks:
                print(f"[ACCURACY] Generated: '{task['prompt'][:50]}...' x{task['count']}")
        elif not success and user_intent["intent"] != "no_image_request":
            print(f"[ACCURACY] Missed opportunity: Intent '{user_intent['intent']}' but no generation")
            
    except Exception as e:
        print(f"[DEBUG] Error in accuracy tracking: {e}")

async def aires(client: Client, message: Message) -> None:
    """
    Handle user messages and generate AI responses
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    # Ignore messages from bots (including the bot itself)
    if message.from_user and message.from_user.is_bot:
        return
    
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return

    user_id = message.from_user.id
    
    # Check if user can start a new text request
    can_start, queue_message = await can_start_text_request(user_id)
    if not can_start:
        await message.reply_text(queue_message)
        return

    try:
        # Start the text request in queue system
        start_text_request(user_id, f"Processing message: {(message.text or 'media')[:30]}...")
        
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await send_interactive_waiting_message(message)
        
        # Safely extract the message text
        ask = ""
        if hasattr(message, 'text') and message.text:
            ask = str(message.text)
        elif hasattr(message, 'caption') and message.caption:
            ask = str(message.caption)
        else:
            ask = "Hello"  # Fallback for non-text messages
        
        # Pre-analyze user intent for better processing
        user_intent_analysis = analyze_user_intent_for_images(ask)
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            # Ensure history is a list
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else: 
            # Use a copy of the default system message
            history = DEFAULT_SYSTEM_MESSAGE.copy()

        # Context management for auto image generation
        # Check if user is asking for image generation
        user_message_lower = ask.lower()
        is_image_request = user_intent_analysis["intent"] != "no_image_request"
        
        # Enhanced context management for better auto-generation
        if is_image_request:
            # If it's an image request, ensure we have recent training examples in context
            # Count recent messages (exclude system messages)
            recent_messages = [msg for msg in history if msg.get('role') != 'system']
            
            # If conversation is getting long, trim older messages but keep system training
            if len(recent_messages) > 15:
                # Keep system messages and recent training examples
                system_messages = [msg for msg in history if msg.get('role') == 'system']
                recent_training = [msg for msg in DEFAULT_SYSTEM_MESSAGE[:15] if msg.get('role') in ['user', 'assistant']]
                recent_conversation = recent_messages[-10:]  # Keep last 10 messages
                
                # Rebuild history with system + training + recent conversation
                history = system_messages + recent_training + recent_conversation
                
                print(f"[DEBUG] Context management: Trimmed history for user {user_id} due to image request")
            
            # Add enhanced contextual reminder for image generation
            context_reminder = {
                "role": "system",
                "content": (
                    f"CRITICAL REMINDER: The user is requesting visual content (Intent: {user_intent_analysis['intent']}, Confidence: {user_intent_analysis['confidence']}). "
                    f"You MUST use auto-generation patterns:\n"
                    f"- Single image: '[GENERATE_IMAGE: detailed description]'\n"
                    f"- Multiple images: '[GENERATE_IMAGES: {user_intent_analysis['requested_count']}: detailed description]'\n"
                    f"The user wants to see: {', '.join(user_intent_analysis.get('detected_subjects', ['visual content']))}\n"
                    f"ALWAYS include the exact brackets and format. Be creative with descriptions."
                )
            }
            history.append(context_reminder)

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Use non-streaming approach for all chats to avoid flood control
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        
        # --- Get user model ---
        user_model, _ = await get_user_ai_models(user_id)
        is_premium, _, _ = await is_user_premium(user_id)
        is_admin = user_id in ADMINS
        if not is_premium and not is_admin and user_model in RESTRICTED_TEXT_MODELS:
            user_model = DEFAULT_TEXT_MODEL
        model_to_use = user_model
        fallback_used = False
        
        # Enhanced model selection for image requests
        if is_image_request:
            # Use more reliable models for image generation requests
            if user_model in ["deepseek-r1", "qwen3"]:
                print(f"[DEBUG] Using reliable model for image request: {user_model}")
            else:
                print(f"[DEBUG] Image request detected, using model: {user_model}")
        
        try:
            ai_response = get_response(history, model=model_to_use)
        except Exception as e:
            # fallback to default Groq model
            fallback_used = True
            print(f"[DEBUG] Primary model failed, using fallback: {e}")
            ai_response = get_response(history, model="default")
        
        # Ensure ai_response is a string
        if not isinstance(ai_response, str):
            ai_response = str(ai_response) if ai_response else "I apologize, but I'm having trouble generating a response right now."
        
        # Post-process AI response to inject missing patterns if needed
        if is_image_request:
            original_response = ai_response
            ai_response = post_process_ai_response_for_missing_patterns(ai_response, user_intent_analysis, ask)
            if ai_response != original_response:
                print(f"[DEBUG] Post-processing enhanced the response for user {user_id}")
        
        # Process automatic image generation (async approach)
        processed_response, image_tasks = await process_auto_image_generation_async(client, message, ai_response, user_id)
        
        # Track accuracy for monitoring and improvement
        generation_success = len(image_tasks) > 0
        await track_auto_generation_accuracy(user_id, user_intent_analysis, ai_response, image_tasks, generation_success)
        
        # Enhanced feedback for debugging
        if is_image_request and not image_tasks:
            print(f"[WARNING] Image request detected but no auto-generation triggered for user {user_id}")
            print(f"[WARNING] User request: '{ask[:100]}...'")
            print(f"[WARNING] AI response: '{ai_response[:200]}...'")
            print(f"[WARNING] User intent: {user_intent_analysis}")
        
        # Add the AI response to the history (use original response for context)
        history.append({"role": "assistant", "content": ai_response})
        
        # Context cleanup - remove temporary system reminders
        history = [msg for msg in history if not (msg.get('role') == 'system' and 'REMINDER:' in msg.get('content', ''))]
        
        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )

        # --- Fix: Always send the full response, including code blocks ---
        def split_by_limit(text, limit=4096):
            # Split text into chunks by line, never breaking inside a line
            lines = text.splitlines(keepends=True)
            chunks = []
            current = ""
            for line in lines:
                if len(current) + len(line) > limit:
                    chunks.append(current)
                    current = ""
                current += line
            if current:
                chunks.append(current)
            return chunks

        try:
            # Prepare the response text
            if fallback_used:
                full_response = processed_response + "\n\n<b>Note: The selected model is currently unavailable. Using <b>Qwen-3</b> as fallback till it's fixed.</b>"
            else:
                full_response = processed_response
            html_response = markdown_code_to_html(full_response)
            
            # Cancel typing task and delete the temporary message
            if hasattr(temp, '_typing_task'):
                temp._typing_task.cancel()
            await temp.delete()
            
            # Send text response immediately
            try:
                await message.reply_text(html_response, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            except MessageTooLong:
                # If too long, split into chunks by line, never breaking inside a line
                chunks = split_by_limit(html_response)
                for chunk in chunks:
                    await message.reply_text(chunk, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            
            # Start background image generation if there are image tasks
            if image_tasks:
                # Start background task for image generation (non-blocking)
                asyncio.create_task(generate_images_in_background(client, message, image_tasks, user_id))
                        
        except Exception as e:
            # Log the error to log channel
            await error_log(client, "MESSAGE_SEND", str(e), f"Failed to send text response, falling back to plain text", user_id)
            # Fallback: send as plain text (still try markdown conversion)
            try:
                # Cancel typing task and delete temp message
                if hasattr(temp, '_typing_task'):
                    temp._typing_task.cancel()
                await temp.delete()
                # Try with markdown to HTML conversion, fallback to truly plain text if needed
                try:
                    plain_html = markdown_to_html(processed_response)
                    await message.reply_text(plain_html, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
                except:
                    # Truly plain text as last resort
                    await message.reply_text(processed_response)
                
                # Still try to generate images in background if requested
                if image_tasks:
                    asyncio.create_task(generate_images_in_background(client, message, image_tasks, user_id))
                    
            except Exception as fallback_error:
                # Log fallback failure too
                await error_log(client, "MESSAGE_SEND_FALLBACK", str(fallback_error), f"Failed to send even plain text response", user_id)
        
        # Enhanced logging with comprehensive auto-generation info
        auto_gen_info = ""
        if is_image_request:
            if image_tasks:
                auto_gen_info = f"\n[AUTO-GEN: ✅ Success - {sum(task['count'] for task in image_tasks)} image(s), Intent: {user_intent_analysis['intent']}]"
            else:
                auto_gen_info = f"\n[AUTO-GEN: ❌ Failed - Intent: {user_intent_analysis['intent']}, Confidence: {user_intent_analysis['confidence']}]"
        
        await user_log(client, message, f"\nUser: {ask}.\nAI: {processed_response}{auto_gen_info}")

    except Exception as e:
        # Log the error to log channel
        await error_log(client, "AIRES_FUNCTION", str(e), f"User query: {ask[:100]}..." if 'ask' in locals() else "Unknown query", user_id)
        print(f"Error in aires function: {e}")
        await message.reply_text("I'm experiencing technical difficulties. Please try again in a moment or use /new to start a new conversation.")
    finally:
        # Always finish the text request in queue system
        finish_text_request(user_id)

async def new_chat(client: Client, message: Message) -> None:
    """
    Reset a user's chat history
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    try:
        user_id = message.from_user.id
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Delete user history from MongoDB
        history_collection.delete_one({"user_id": user_id})
        
        # Create a new history entry with the default system message list
        history_collection.insert_one({
            "user_id": user_id,
            "history": DEFAULT_SYSTEM_MESSAGE
        })

        # Send confirmation message with modern UI
        await message.reply_text("🔄 <b>Conversation Reset</b>\n\nYour chat history has been cleared. Ready for a fresh conversation!", parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        # Log the error to log channel
        await error_log(client, "NEW_CHAT", str(e), "Error clearing chat history", user_id)
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}") 
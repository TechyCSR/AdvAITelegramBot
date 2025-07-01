import os
import asyncio
import time
import re
import html

from typing import List, Dict, Any, Optional, Generator, Union, Tuple
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from g4f.client import Client as GPTClient
from modules.core.database import get_history_collection
from modules.chatlogs import user_log, error_log
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled
from modules.user.ai_model import get_user_ai_models, DEFAULT_TEXT_MODEL, RESTRICTED_TEXT_MODELS
from modules.user.premium_management import is_user_premium
from config import ADMINS, POLLINATIONS_KEY
from pyrogram.errors import MessageTooLong
from modules.image.image_generation import generate_images
from pyrogram.types import InputMediaPhoto
import uuid

# --- Provider mapping ---
PROVIDER_MAP = {
    "gpt-4o": "PollinationsAI",
    "gpt-4.1": "PollinationsAI",
    "qwen3": "DeepInfraChat",
    "deepseek-r1": "DeepInfraChat"
}

# --- Model mapping for DeepInfraChat ---
DEEPINFRA_MODEL_MAP = {
    "qwen3": "Qwen/Qwen3-235B-A22B",
    "deepseek-r1": "deepseek-r1"
}

# Initialize the GPT client with a more efficient provider
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history: List[Dict[str, str]], model: str = "gpt-4o", provider: str = "PollinationsAI") -> str:
    """
    Get a non-streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        model: The model to use for generating the response
        provider: The provider to use for generating the response
        
    Returns:
        String response from the AI model
    """
    try:
        if not isinstance(history, list):
            history = [history]
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
        gpt_client = GPTClient()
        if provider == "PollinationsAI":
            print(f"Using PollinationsAI model: {model}")
            response = gpt_client.chat.completions.create(
                api_key=POLLINATIONS_KEY,  # Add API key to the request( if you have one )
                model=model,
                messages=history,
                provider="PollinationsAI"
            )
            return response.choices[0].message.content
        elif provider == "DeepInfraChat":
            deep_model = DEEPINFRA_MODEL_MAP.get(model, model)
            print(f"Using DeepInfraChat model: {deep_model}")
            response = gpt_client.chat.completions.create(
                model=deep_model,
                messages=history,
                provider="DeepInfraChat"
            )
            return response.choices[0].message.content
        else:
            # fallback to default
            response = gpt_client.chat.completions.create(
                api_key=POLLINATIONS_KEY,  # Add API key to the request( if you have one )
                model="gpt-4o",
                messages=history,
                provider="PollinationsAI"
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response with model {model} and provider {provider}: {e}")
        raise

def get_streaming_response(history: List[Dict[str, str]]) -> Optional[Generator]:
    """
    Get a streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        Generator yielding response chunks or None if there's an error
    """
    try:
        # Ensure history is a list
        if not isinstance(history, list):
            history = [history]
            
        # If history is empty, use the default system message
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()  # Create a copy to avoid modifying the original
            
        # Ensure each message in history is a dictionary
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
                
        # Stream parameter set to True to get response chunks
        response = gpt_client.chat.completions.create(
            api_key=POLLINATIONS_KEY,  # Add API key to the request( if you have one )
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history,
            stream=True
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

def markdown_code_to_html(text):
    # Replace ```...``` with <pre><code>...</code></pre>
    def replacer(match):
        code = match.group(1)
        return f'<pre><code>{html.escape(code)}</code></pre>'
    # Replace all triple-backtick code blocks
    return re.sub(r'```([\s\S]*?)```', replacer, text)

def validate_image_url(url: str) -> bool:
    """Validate if the URL is a proper image URL"""
    if not url or not isinstance(url, str):
        return False
    return url.startswith(('http://', 'https://')) or url.startswith('/')

async def process_auto_image_generation_async(client: Client, message: Message, ai_response: str, user_id: int) -> Tuple[str, List[Dict]]:
    """
    Process AI response for automatic image generation requests (Async version)
    
    Args:
        client: Pyrogram client instance
        message: Original user message
        ai_response: AI's response text
        user_id: User ID
        
    Returns:
        Tuple of (cleaned_response_text, list_of_image_generation_tasks)
    """
    image_tasks = []
    
    # Enhanced pattern to capture multiple images and count - using DOTALL to capture complete prompts
    patterns = [
        r'\[GENERATE_IMAGE:\s*(.*?)\]',
        r'\[GENERATE_IMAGES:\s*(\d+)\s*:\s*(.*?)\]',  # [GENERATE_IMAGES: 3: cats playing]
        r'\[MULTI_IMAGE:\s*(.*?)\]'
    ]
    
    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if pattern == patterns[1]:  # Multiple images pattern
            for match in matches:
                count, prompt = match
                # Clean and validate the prompt
                clean_prompt = prompt.strip().replace('\n', ' ').replace('\r', ' ')
                clean_prompt = ' '.join(clean_prompt.split())  # Remove extra whitespace
                if clean_prompt:  # Only add if not empty
                    all_matches.append((clean_prompt, int(count) if count.isdigit() and int(count) > 0 else 1))
        else:
            for match in matches:
                # Clean and validate the prompt
                clean_prompt = match.strip().replace('\n', ' ').replace('\r', ' ')
                clean_prompt = ' '.join(clean_prompt.split())  # Remove extra whitespace
                if clean_prompt:  # Only add if not empty
                    all_matches.append((clean_prompt, 1))
    
    if all_matches:
        # Remove all generation markers from the response
        cleaned_response = ai_response
        for pattern in patterns:
            cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.IGNORECASE | re.DOTALL)
        cleaned_response = cleaned_response.strip()
        
        # Prepare image generation tasks
        for image_prompt, count in all_matches:
            if not image_prompt:
                continue
            
            # Limit count for safety
            count = min(count, 4)  # Max 4 images per prompt
            
            image_tasks.append({
                'prompt': image_prompt,
                'count': count,
                'style': 'realistic'
            })
            
            # Debug log the extracted prompt
            print(f"[DEBUG] Auto-image: Extracted prompt: '{image_prompt}' (count: {count})")
        
        return cleaned_response, image_tasks
    
    return ai_response, image_tasks

async def generate_images_in_background(client: Client, message: Message, image_tasks: List[Dict], user_id: int):
    """
    Generate images in the background and send them after text response
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
            prompt = task['prompt']
            count = task['count']
            style = task['style']
            
            # Update progress with complete prompt
            display_prompt = prompt if len(prompt) <= 50 else prompt[:50] + "..."
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
                # For multiple images, generate each one individually with variations
                if count > 1:
                    # Generate each image individually with slight variations
                    for img_num in range(count):
                        # Add variation to the prompt for different results
                        variation_suffixes = [
                            ", detailed and unique",
                            ", different style and composition", 
                            ", alternative perspective and lighting",
                            ", varied colors and mood"
                        ]
                        
                        # Create a varied prompt for each image
                        varied_prompt = f"{prompt}{variation_suffixes[img_num % len(variation_suffixes)]}"
                        
                        print(f"[DEBUG] Generating image {img_num + 1}/{count}: '{varied_prompt}'")
                        
                        # Update progress for individual image
                        await generating_msg.edit_text(
                            f"🎨 **Generating your images...**\n\n"
                            f"Working on: `{display_prompt}`\n"
                            f"Creating image {img_num + 1}/{count} with unique variation\n\n"
                            "🖌️ Each image will be different and unique..."
                        )
                        
                        # Generate single image with variation
                        urls, error = await generate_images(
                            prompt=varied_prompt,
                            style=style,
                            max_images=1,
                            user_id=user_id
                        )
                        
                        if urls and not error:
                            valid_urls = [url for url in urls if validate_image_url(url)]
                            if valid_urls:
                                all_generated_images.extend([(url, varied_prompt) for url in valid_urls])
                                await error_log(client, "AUTO_IMAGE_SUCCESS", f"Generated image {img_num + 1} for: {prompt[:50]}...", f"User: {user_id}", user_id)
                            else:
                                await error_log(client, "AUTO_IMAGE_INVALID", f"Generated URLs were invalid for image {img_num + 1}", f"Prompt: {prompt[:50]}...", user_id)
                        else:
                            await error_log(client, "AUTO_IMAGE_FAIL", f"Failed to generate image {img_num + 1}: {error or 'Unknown error'}", f"Prompt: {prompt[:50]}...", user_id)
                        
                        # Small delay between generations to avoid rate limits
                        await asyncio.sleep(0.5)
                else:
                    # Single image generation
                    print(f"[DEBUG] Sending to image generation: '{prompt}' (style: {style})")
                    
                    urls, error = await generate_images(
                        prompt=prompt,
                        style=style,
                        max_images=1,
                        user_id=user_id
                    )
                    
                    if urls and not error:
                        valid_urls = [url for url in urls if validate_image_url(url)]
                        if valid_urls:
                            all_generated_images.extend([(url, prompt) for url in valid_urls])
                            await error_log(client, "AUTO_IMAGE_SUCCESS", f"Generated image for: {prompt[:50]}...", f"User: {user_id}", user_id)
                        else:
                            await error_log(client, "AUTO_IMAGE_INVALID", "Generated URLs were invalid", f"Prompt: {prompt[:50]}...", user_id)
                    else:
                        await error_log(client, "AUTO_IMAGE_FAIL", f"Failed to generate image: {error or 'Unknown error'}", f"Prompt: {prompt[:50]}...", user_id)
                    
            except Exception as e:
                await error_log(client, "AUTO_IMAGE_ERROR", str(e), f"Prompt: {prompt[:50]}...", user_id)
                continue
        
        # Send all generated images
        if all_generated_images:
            # Group images into media groups (max 10 per group)
            image_groups = [all_generated_images[i:i+10] for i in range(0, len(all_generated_images), 10)]
            
            for group_index, image_group in enumerate(image_groups):
                # Prepare media group
                media_group = []
                for i, (image_url, prompt) in enumerate(image_group):
                    # Add caption with manual generation info for first image only
                    if i == 0 and group_index == 0:
                        caption = (
                            "You can manually gen images as you want by using /img your prompt\n\n"
                            "**Example:**\n"
                            "`/img cats playing in garden`"
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
                f"You can try: `/img {image_tasks[0]['prompt'] if image_tasks else 'your prompt'}`"
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
                f"You can try: `/img {image_tasks[0]['prompt'] if image_tasks else 'your prompt'}`"
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
            "• INTELLIGENT IMAGE GENERATION: When users ask for images, visual content, or when an image would make your response better, use these patterns:\n  - Single image: '[GENERATE_IMAGE: detailed description]'\n  - Multiple images: '[GENERATE_IMAGES: number: detailed description]' (e.g., '[GENERATE_IMAGES: 3: cute puppies]')\n  - Always follow with your engaging text response\n"
            "• If a user sends an image, analyze it, answer any questions, and if it's an MCQ, solve it and explain the answer\n"
            "• If a user sends a document or asks about a file, summarize or extract the main points\n"
            "• Always use a modern, friendly, and helpful tone."
        )
    },
    # --- Training examples for automatic image generation ---
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
        "content": "I want a peaceful nature scene"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGE: a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees, peaceful atmosphere]\n\n"
            "Here's a beautiful peaceful nature scene for you! It captures the tranquility of a forest with a crystal-clear lake, soft morning mist, and warm golden sunlight creating a magical atmosphere. 🌲🌅"
        )
    },
    {
        "role": "user",
        "content": "Show me 3 different cats"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: adorable cats with different breeds and colors, persian cat, siamese cat, maine coon cat, cute and fluffy]\n\n"
            "I'll create 3 different adorable cats for you! You'll see a Persian, Siamese, and Maine Coon - each with their unique characteristics and charm. 🐱🐾"
        )
    },
    # --- More training examples for multiple image generation ---
    {
        "role": "user",
        "content": "Create 4 different flowers for me"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 4: beautiful flowers with different colors and types, roses, sunflowers, tulips, orchids, vibrant and detailed]\n\n"
            "I'll generate 4 stunning different flowers for you! Each will showcase unique colors, shapes, and beauty - from elegant roses to bright sunflowers, delicate tulips, and exotic orchids. 🌸🌻🌷🌺"
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
        "content": "Can you show me different landscapes? Like 3 or 4"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 4: diverse beautiful landscapes, mountain valley, ocean beach, forest path, desert sunset, scenic and breathtaking]\n\n"
            "Absolutely! I'll create 4 diverse and breathtaking landscapes for you - a serene mountain valley, a stunning ocean beach, a mystical forest path, and a dramatic desert sunset. Each will transport you to a different world! 🏔️🏖️🌲🏜️"
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
        "content": "I need multiple character designs, can you help?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 4: different character designs, fantasy warrior, magical wizard, space explorer, steampunk inventor, detailed and creative]\n\n"
            "I'd love to help with character designs! I'll create 4 unique characters for you - a brave fantasy warrior, a wise magical wizard, an adventurous space explorer, and a creative steampunk inventor. Each will have their own distinctive style and personality! ⚔️🧙‍♂️🚀🔧"
        )
    },
    {
        "role": "user",
        "content": "Show me different food dishes, maybe 3 cuisines"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: delicious food dishes from different cuisines, italian pasta, japanese sushi, mexican tacos, appetizing and colorful]\n\n"
            "Delicious! I'll create 3 mouth-watering dishes from different cuisines - authentic Italian pasta, fresh Japanese sushi, and flavorful Mexican tacos. Each will look absolutely appetizing and showcase the unique flavors of their culture! 🍝🍣🌮"
        )
    },
    {
        "role": "user",
        "content": "Can you generate a few houses with different architectural styles?"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 3: houses with different architectural styles, modern minimalist, victorian classic, contemporary glass, beautiful and detailed]\n\n"
            "I'll create 3 houses showcasing different architectural styles! You'll see a sleek modern minimalist design, a charming Victorian classic, and a stunning contemporary glass house - each representing unique design philosophies and beauty. 🏠🏡🏘️"
        )
    },
    {
        "role": "user",
        "content": "I want several fantasy creatures, like 4 different ones"
    },
    {
        "role": "assistant",
        "content": (
            "[GENERATE_IMAGES: 4: magical fantasy creatures, dragon, unicorn, phoenix, griffin, mystical and enchanting]\n\n"
            "What an enchanting request! I'll create 4 magical fantasy creatures for you - a mighty dragon, an elegant unicorn, a majestic phoenix, and a powerful griffin. Each will be mystical and captivating in their own legendary way! 🐉🦄🔥🦅"
        )
    },
    {
        "role": "user",
        "content": "Multiple space scenes please, different planets or galaxies"
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
        "content": "How do I use the /img command?"
    },
    {
        "role": "assistant",
        "content": (
            "You have **two amazing ways** to generate images:\n\n"
            "🤖 **Automatic Generation** (New!): Just ask me naturally!\n"
            "• \"Can you show me a sunset over mountains?\"\n"
            "• \"Create a cute robot for me\"\n"
            "• \"I want to see 3 different flowers\"\n\n"
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
            "• Website: techycsr.me\n"
            "• GitHub: github.com/techycsr\n\n"
            "• LinkedIn: linkedin.com/in/techycsr\n\n"
            "This bot is one of his many projects showcasing his expertise in AI and bot development."
        )
    },
    {
        "role": "system",
        "content": (
            "Remember: This bot was developed by Chandan Singh (@techycsr) as a demonstration of advanced AI "
            "capabilities in Telegram. For support or to learn more about the developer, visit techycsr.me "
            "or contact @techycsr on Telegram."
        )
    }
]

async def aires(client: Client, message: Message) -> None:
    """
    Handle user messages and generate AI responses
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return

    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("⏳")
        user_id = message.from_user.id
        ask = message.text
        
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
        provider = PROVIDER_MAP.get(user_model, "PollinationsAI")
        model_to_use = user_model
        fallback_used = False
        try:
            ai_response = get_response(history, model=model_to_use, provider=provider)
        except Exception as e:
            # fallback to Qwen-3
            fallback_used = True
            ai_response = get_response(history, model="Qwen/Qwen3-235B-A22B", provider="DeepInfraChat")
        
        # Process automatic image generation (async approach)
        processed_response, image_tasks = await process_auto_image_generation_async(client, message, ai_response, user_id)
        
        # Add the AI response to the history (use original response for context)
        history.append({"role": "assistant", "content": ai_response})
        
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
            
            # Delete the temporary message
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
            # Fallback: send as plain text
            try:
                await temp.delete()
                await message.reply_text(processed_response)
                
                # Still try to generate images in background if requested
                if image_tasks:
                    asyncio.create_task(generate_images_in_background(client, message, image_tasks, user_id))
                    
            except Exception as fallback_error:
                # Log fallback failure too
                await error_log(client, "MESSAGE_SEND_FALLBACK", str(fallback_error), f"Failed to send even plain text response", user_id)
        
        # Update logging to mention image generation
        image_info = f"\n[Requested {sum(task['count'] for task in image_tasks)} image(s) - generating in background]" if image_tasks else ""
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ processed_response + image_info)

    except Exception as e:
        # Log the error to log channel
        await error_log(client, "AIRES_FUNCTION", str(e), f"User query: {ask[:100]}..." if 'ask' in locals() else "Unknown query", user_id)
        print(f"Error in aires function: {e}")
        await message.reply_text("I'm experiencing technical difficulties. Please try again in a moment or use /new to start a new conversation.")

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
        await message.reply_text("🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!")

    except Exception as e:
        # Log the error to log channel
        await error_log(client, "NEW_CHAT", str(e), "Error clearing chat history", user_id)
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}") 
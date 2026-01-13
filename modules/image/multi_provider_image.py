"""
Multi-Provider Image Generation System
======================================
This module provides a robust image generation system that tries multiple
providers concurrently or sequentially to maximize success rate.

All providers used here are authentication-free (no API keys, cookies, or sessions needed).
"""

import asyncio
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time
import random

from g4f.client import AsyncClient
from g4f.Provider import (
    BlackForestLabs_Flux1Dev,
    StabilityAI_SD35Large,
    HuggingFaceInference,
    DeepseekAI_JanusPro7b,
    AnyProvider,
)

logger = logging.getLogger(__name__)


class ProviderPriority(Enum):
    """Priority levels for providers"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class ImageProvider:
    """Configuration for an image provider"""
    name: str
    provider_class: Any
    models: List[str]
    priority: ProviderPriority
    timeout: int = 60
    supports_multiple: bool = False  # Whether it can generate multiple images at once
    default_width: int = 1024
    default_height: int = 1024


# ============================================================================
# PROVIDER CONFIGURATIONS
# ============================================================================
# All providers here are AUTH-FREE (needs_auth=False in g4f)
# They don't require any API key, cookie, or session
# NOTE: Pollinations providers excluded as per user request

IMAGE_PROVIDERS: List[ImageProvider] = [
    # Primary providers - most reliable
    ImageProvider(
        name="BlackForestLabs_Flux1Dev",
        provider_class=BlackForestLabs_Flux1Dev,
        models=["flux-dev", "flux"],
        priority=ProviderPriority.HIGH,
        timeout=60,
        supports_multiple=False,
        default_width=1024,
        default_height=1024,
    ),
    ImageProvider(
        name="AnyProvider",
        provider_class=AnyProvider,
        models=["flux", "flux-dev", "sdxl-turbo", "sd-3.5-large", "flux-schnell"],
        priority=ProviderPriority.HIGH,
        timeout=60,
        supports_multiple=False,
        default_width=1024,
        default_height=1024,
    ),
    # Secondary providers - good fallbacks
    ImageProvider(
        name="StabilityAI_SD35Large",
        provider_class=StabilityAI_SD35Large,
        models=["sd-3.5-large"],
        priority=ProviderPriority.MEDIUM,
        timeout=60,
        supports_multiple=False,
        default_width=1024,
        default_height=1024,
    ),
    # Tertiary providers - additional fallbacks
    ImageProvider(
        name="HuggingFaceInference",
        provider_class=HuggingFaceInference,
        models=["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"],
        priority=ProviderPriority.MEDIUM,
        timeout=90,  # HuggingFace can be slower
        supports_multiple=False,
        default_width=1024,
        default_height=1024,
    ),
    ImageProvider(
        name="DeepseekAI_JanusPro7b",
        provider_class=DeepseekAI_JanusPro7b,
        models=["janus-pro-7b-image"],
        priority=ProviderPriority.LOW,
        timeout=90,
        supports_multiple=False,
        default_width=512,  # Janus works better with smaller sizes
        default_height=512,
    ),
]


# User-selectable models (simplified model list for the UI)
USER_IMAGE_MODELS = {
    "flux": "Flux (Fast)",
    "flux-dev": "Flux Dev (Quality)",
    "sd-3.5-large": "Stable Diffusion 3.5",
}

DEFAULT_IMAGE_MODEL = "flux-dev"

# Legacy model mapping - old model names to new equivalents
LEGACY_MODEL_MAP = {
    "dall-e3": "flux-dev",
    "dall-e-3": "flux-dev",
    "flux-pro": "flux-dev",
    "sdxl-1.0": "sd-3.5-large",
    "turbo": "flux",
}

# Model to provider mapping - which providers can handle which models
MODEL_PROVIDER_MAP = {
    "flux": ["BlackForestLabs_Flux1Dev", "AnyProvider"],
    "flux-dev": ["BlackForestLabs_Flux1Dev", "AnyProvider"],
    "sd-3.5-large": ["StabilityAI_SD35Large", "AnyProvider"],
    "sdxl-turbo": ["AnyProvider"],
    "flux-schnell": ["AnyProvider"],
    "black-forest-labs/FLUX.1-dev": ["HuggingFaceInference"],
    "black-forest-labs/FLUX.1-schnell": ["HuggingFaceInference"],
    "janus-pro-7b-image": ["DeepseekAI_JanusPro7b"],
}

# Fallback chains - if one model fails, try these alternatives
MODEL_FALLBACK_CHAIN = {
    "flux": ["flux-dev", "sd-3.5-large", "flux-schnell"],
    "flux-dev": ["flux", "sd-3.5-large", "flux-schnell"],
    "sd-3.5-large": ["flux-dev", "flux", "sdxl-turbo"],
}


def normalize_model_name(model: str) -> str:
    """Convert legacy model names to current equivalents"""
    if model in LEGACY_MODEL_MAP:
        new_model = LEGACY_MODEL_MAP[model]
        logger.info(f"Mapping legacy model '{model}' to '{new_model}'")
        return new_model
    return model


def get_provider_by_name(name: str) -> Optional[ImageProvider]:
    """Get a provider configuration by name"""
    for provider in IMAGE_PROVIDERS:
        if provider.name == name:
            return provider
    return None


def get_providers_for_model(model: str) -> List[ImageProvider]:
    """Get all providers that support a given model"""
    provider_names = MODEL_PROVIDER_MAP.get(model, [])
    providers = []
    for name in provider_names:
        provider = get_provider_by_name(name)
        if provider:
            providers.append(provider)
    return providers


async def generate_with_provider(
    provider: ImageProvider,
    prompt: str,
    model: str,
    width: int = None,
    height: int = None,
    num_images: int = 1,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Generate images using a specific provider.
    
    Args:
        provider: The ImageProvider configuration
        prompt: The text prompt for generation
        model: The model to use
        width: Image width (uses provider default if not specified)
        height: Image height (uses provider default if not specified)
        num_images: Number of images to generate
        
    Returns:
        Tuple of (list of image URLs, error message or None)
    """
    width = width or provider.default_width
    height = height or provider.default_height
    
    logger.info(f"Attempting generation with {provider.name} using model {model}")
    
    try:
        client = AsyncClient(image_provider=provider.provider_class)
        
        # Build generation kwargs
        kwargs = {
            "prompt": prompt,
            "model": model,
            "response_format": "url",
        }
        
        # Add dimensions if the provider supports them
        if provider.name not in ["DeepseekAI_JanusPro7b"]:
            kwargs["width"] = width
            kwargs["height"] = height
        
        # Add number of images if provider supports multiple
        if provider.supports_multiple and num_images > 1:
            kwargs["n"] = num_images
        
        # Generate with timeout
        response = await asyncio.wait_for(
            client.images.generate(**kwargs),
            timeout=provider.timeout
        )
        
        if not response or not response.data:
            logger.warning(f"{provider.name} returned empty response")
            return None, f"{provider.name} returned no image data"
        
        # Extract URLs
        image_urls = []
        for img_data in response.data:
            if hasattr(img_data, 'url') and img_data.url:
                url = img_data.url
                # Validate URL format
                if url.startswith("http://") or url.startswith("https://"):
                    image_urls.append(url)
                else:
                    logger.warning(f"Invalid URL format from {provider.name}: {url[:50]}...")
        
        if image_urls:
            logger.info(f"{provider.name} generated {len(image_urls)} images successfully")
            return image_urls, None
        else:
            return None, f"{provider.name} returned no valid image URLs"
            
    except asyncio.TimeoutError:
        logger.warning(f"{provider.name} timed out after {provider.timeout}s")
        return None, f"{provider.name} timed out"
    except Exception as e:
        logger.error(f"{provider.name} failed: {str(e)}")
        return None, f"{provider.name} error: {str(e)}"


async def generate_with_concurrent_providers(
    providers: List[ImageProvider],
    prompt: str,
    model: str,
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Try multiple providers concurrently and return the first successful result.
    
    Args:
        providers: List of providers to try
        prompt: The text prompt
        model: The model to use
        width: Image width
        height: Image height
        num_images: Number of images
        
    Returns:
        Tuple of (image URLs or None, error message or None)
    """
    if not providers:
        return None, "No providers available for this model"
    
    logger.info(f"Trying {len(providers)} providers concurrently for model {model}")
    
    # Create tasks for all providers
    tasks = []
    for provider in providers:
        # Use the requested model if provider supports it, otherwise use provider's first model
        use_model = model if model in provider.models else provider.models[0]
        task = asyncio.create_task(
            generate_with_provider(provider, prompt, use_model, width, height, num_images)
        )
        tasks.append((provider.name, task))
    
    # Wait for any task to complete successfully
    errors = []
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
                    logger.info(f"Success with {provider_name}, cancelling {len(pending_tasks)} other tasks")
                    return urls, None
                else:
                    errors.append(f"{provider_name}: {error}")
            except Exception as e:
                errors.append(f"{provider_name}: {str(e)}")
    
    # All providers failed
    error_summary = "; ".join(errors) if errors else "All providers failed"
    logger.error(f"All concurrent providers failed: {error_summary}")
    return None, error_summary


async def generate_with_fallback(
    prompt: str,
    model: str = DEFAULT_IMAGE_MODEL,
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    try_concurrent: bool = True,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Main function to generate images with automatic fallback.
    
    This tries the requested model first, then falls back to alternative models
    if needed. Can try multiple providers concurrently for faster results.
    
    Args:
        prompt: The text prompt for generation
        model: The preferred model (defaults to DEFAULT_IMAGE_MODEL)
        width: Image width (default 1024)
        height: Image height (default 1024)
        num_images: Number of images to generate (default 1)
        try_concurrent: Whether to try providers concurrently (default True)
        
    Returns:
        Tuple of (list of image URLs or None, error message or None)
    """
    start_time = time.time()
    
    # Normalize legacy model names to current equivalents
    model = normalize_model_name(model)
    
    # Build the list of models to try (requested model + fallbacks)
    models_to_try = [model]
    fallbacks = MODEL_FALLBACK_CHAIN.get(model, [])
    
    # If no fallbacks defined for this model, use default model's fallbacks
    if not fallbacks and model != DEFAULT_IMAGE_MODEL:
        logger.info(f"No fallback chain for model '{model}', using default model '{DEFAULT_IMAGE_MODEL}'")
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
        
        if try_concurrent and len(providers) > 1:
            # Try multiple providers concurrently
            urls, error = await generate_with_concurrent_providers(
                providers, prompt, try_model, width, height, num_images
            )
        else:
            # Try providers sequentially (in priority order)
            providers.sort(key=lambda p: p.priority.value)
            urls = None
            error = None
            
            for provider in providers:
                urls, error = await generate_with_provider(
                    provider, prompt, try_model, width, height, num_images
                )
                if urls:
                    break
        
        if urls:
            elapsed = time.time() - start_time
            logger.info(f"Image generation succeeded in {elapsed:.2f}s with model {try_model}")
            return urls, None
        
        if error:
            all_errors.append(f"{try_model}: {error}")
    
    # All models and providers failed
    elapsed = time.time() - start_time
    error_msg = f"All providers failed after {elapsed:.2f}s. Errors: {'; '.join(all_errors[:3])}"
    logger.error(error_msg)
    return None, error_msg


async def generate_images_multi_provider(
    prompt: str,
    style: Optional[str] = None,
    model: str = DEFAULT_IMAGE_MODEL,
    num_images: int = 1,
    width: int = 1024,
    height: int = 1024,
    user_id: int = None,
    style_additions: str = "",
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    High-level function for image generation with style support.
    
    This is the main entry point for the bot's image generation feature.
    It handles prompt enhancement, provider selection, and fallback logic.
    
    Args:
        prompt: The user's text prompt
        style: Optional style name (e.g., "realistic", "artistic")
        model: The image model to use
        num_images: Number of images to generate
        width: Image width
        height: Image height
        user_id: User ID for logging/tracking
        style_additions: Additional style text to append to prompt
        
    Returns:
        Tuple of (list of image URLs or None, error message or None)
    """
    # Enhance prompt with style if provided
    if style_additions:
        enhanced_prompt = f"{prompt}, {style_additions}"
    else:
        enhanced_prompt = prompt
    
    logger.info(f"Generating image for user {user_id}: prompt='{prompt[:50]}...', model={model}")
    
    # Generate with multi-provider fallback
    urls, error = await generate_with_fallback(
        prompt=enhanced_prompt,
        model=model,
        width=width,
        height=height,
        num_images=num_images,
        try_concurrent=True,
    )
    
    if error and user_id:
        logger.error(f"Image generation failed for user {user_id}: {error}")
    
    return urls, error


# ============================================================================
# PROVIDER HEALTH TRACKING (Optional - for future enhancement)
# ============================================================================

class ProviderHealthTracker:
    """
    Tracks provider success/failure rates for intelligent routing.
    Providers that fail frequently get lower priority.
    """
    
    def __init__(self):
        self.stats: Dict[str, Dict[str, int]] = {}
        self.last_reset = time.time()
        self.reset_interval = 3600  # Reset stats every hour
    
    def record_success(self, provider_name: str):
        """Record a successful generation"""
        self._ensure_provider(provider_name)
        self.stats[provider_name]["success"] += 1
        self._maybe_reset()
    
    def record_failure(self, provider_name: str):
        """Record a failed generation"""
        self._ensure_provider(provider_name)
        self.stats[provider_name]["failure"] += 1
        self._maybe_reset()
    
    def get_success_rate(self, provider_name: str) -> float:
        """Get the success rate for a provider (0.0 to 1.0)"""
        if provider_name not in self.stats:
            return 0.5  # Unknown provider, assume 50%
        
        s = self.stats[provider_name]
        total = s["success"] + s["failure"]
        if total == 0:
            return 0.5
        return s["success"] / total
    
    def _ensure_provider(self, provider_name: str):
        if provider_name not in self.stats:
            self.stats[provider_name] = {"success": 0, "failure": 0}
    
    def _maybe_reset(self):
        if time.time() - self.last_reset > self.reset_interval:
            self.stats = {}
            self.last_reset = time.time()


# Global health tracker instance
provider_health = ProviderHealthTracker()

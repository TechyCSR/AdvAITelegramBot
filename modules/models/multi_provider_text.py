"""
Multi-Provider Text Generation System
======================================
This module provides a robust text generation system that tries multiple
g4f providers with automatic fallback for maximum success rate.

All providers used here are authentication-free (no API keys, cookies, or sessions needed).
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Generator
from dataclasses import dataclass
from enum import Enum
import time

from g4f.client import Client, AsyncClient
from g4f.Provider import (
    Cloudflare,
    CohereForAI_C4AI_Command,
    LambdaChat,
    Qwen,
    Chatai,
    GradientNetwork,
    AnyProvider,
)

logger = logging.getLogger(__name__)


class ProviderPriority(Enum):
    """Priority levels for providers"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class TextProvider:
    """Configuration for a text provider"""
    name: str
    provider_class: Any
    models: List[str]
    priority: ProviderPriority
    timeout: int = 60
    supports_streaming: bool = True


# ============================================================================
# PROVIDER CONFIGURATIONS
# ============================================================================
# All providers here are AUTH-FREE (needs_auth=False in g4f)
# They don't require any API key, cookie, or session

TEXT_PROVIDERS: List[TextProvider] = [
    # Primary providers - most reliable
    TextProvider(
        name="Qwen",
        provider_class=Qwen,
        models=["qwen3-235b-a22b", "qwen3-max-preview", "qwq-32b", "qwen-plus-2025-01-25"],
        priority=ProviderPriority.HIGH,
        timeout=60,
        supports_streaming=True,
    ),
    TextProvider(
        name="CohereForAI_C4AI_Command",
        provider_class=CohereForAI_C4AI_Command,
        models=["command-a-03-2025", "command-r-plus-08-2024", "command-r-08-2024"],
        priority=ProviderPriority.HIGH,
        timeout=60,
        supports_streaming=True,
    ),
    TextProvider(
        name="LambdaChat",
        provider_class=LambdaChat,
        models=["deepseek-llama3.3-70b", "hermes-3-llama-3.1-405b-fp8", "llama3.3-70b-instruct-fp8", "qwen3-32b-fp8"],
        priority=ProviderPriority.HIGH,
        timeout=60,
        supports_streaming=True,
    ),
    # Secondary providers
    TextProvider(
        name="AnyProvider",
        provider_class=AnyProvider,
        models=["gpt-4o", "gpt-4o-mini", "gpt-4"],
        priority=ProviderPriority.MEDIUM,
        timeout=60,
        supports_streaming=True,
    ),
    TextProvider(
        name="Cloudflare",
        provider_class=Cloudflare,
        models=["deepseek-distill-qwen-32b", "gemma-3-12b", "llama-2-13b"],
        priority=ProviderPriority.MEDIUM,
        timeout=60,
        supports_streaming=True,
    ),
    TextProvider(
        name="GradientNetwork",
        provider_class=GradientNetwork,
        models=["Qwen3 235B", "GPT OSS 120B"],
        priority=ProviderPriority.MEDIUM,
        timeout=90,
        supports_streaming=True,
    ),
    # Tertiary providers
    TextProvider(
        name="Chatai",
        provider_class=Chatai,
        models=["gpt-4o-mini"],
        priority=ProviderPriority.LOW,
        timeout=60,
        supports_streaming=True,
    ),
]


# User-selectable models (simplified model list for the UI)
USER_TEXT_MODELS = {
    "gpt-4o": "GPT-4o (Smart)",
    "qwen3": "Qwen3 235B (Powerful)",
    "llama-70b": "Llama 3.3 70B (Fast)",
    "command-r": "Command R+ (Balanced)",
}

DEFAULT_TEXT_MODEL = "qwen3"

# Model to provider mapping - which providers can handle which models
MODEL_PROVIDER_MAP = {
    # GPT models
    "gpt-4o": ["AnyProvider"],
    "gpt-4o-mini": ["AnyProvider", "Chatai"],
    "gpt-4": ["AnyProvider"],
    # Qwen models
    "qwen3": ["Qwen"],
    "qwen3-235b-a22b": ["Qwen"],
    "qwen3-max-preview": ["Qwen"],
    "qwq-32b": ["Qwen"],
    "qwen3-32b-fp8": ["LambdaChat"],
    # Llama models
    "llama-70b": ["LambdaChat"],
    "deepseek-llama3.3-70b": ["LambdaChat"],
    "llama3.3-70b-instruct-fp8": ["LambdaChat"],
    "hermes-3-llama-3.1-405b-fp8": ["LambdaChat"],
    # Command models
    "command-r": ["CohereForAI_C4AI_Command"],
    "command-a-03-2025": ["CohereForAI_C4AI_Command"],
    "command-r-plus-08-2024": ["CohereForAI_C4AI_Command"],
    # Other models
    "deepseek-distill-qwen-32b": ["Cloudflare"],
    "gemma-3-12b": ["Cloudflare"],
}

# User model to actual model mapping
USER_MODEL_TO_ACTUAL = {
    "gpt-4o": "gpt-4o",
    "qwen3": "qwen3-235b-a22b",
    "llama-70b": "deepseek-llama3.3-70b",
    "command-r": "command-a-03-2025",
}

# Legacy model mapping
LEGACY_TEXT_MODEL_MAP = {
    "gpt-4.1": "qwen3",
    "deepseek-r1": "llama-70b",
}

# Fallback chains - if one model fails, try these alternatives
MODEL_FALLBACK_CHAIN = {
    "gpt-4o": ["qwen3", "command-r", "llama-70b"],
    "qwen3": ["command-r", "llama-70b", "gpt-4o"],
    "llama-70b": ["qwen3", "command-r", "gpt-4o"],
    "command-r": ["qwen3", "llama-70b", "gpt-4o"],
}


def get_provider_by_name(name: str) -> Optional[TextProvider]:
    """Get a provider configuration by name"""
    for provider in TEXT_PROVIDERS:
        if provider.name == name:
            return provider
    return None


def get_providers_for_model(model: str) -> List[TextProvider]:
    """Get all providers that support a given model"""
    provider_names = MODEL_PROVIDER_MAP.get(model, [])
    providers = []
    for name in provider_names:
        provider = get_provider_by_name(name)
        if provider:
            providers.append(provider)
    return providers


def normalize_model_name(model: str) -> str:
    """Convert legacy or user model names to actual model names"""
    # First check legacy mapping
    if model in LEGACY_TEXT_MODEL_MAP:
        model = LEGACY_TEXT_MODEL_MAP[model]
        logger.info(f"Mapped legacy model to: {model}")
    
    # Then check user model mapping
    if model in USER_MODEL_TO_ACTUAL:
        actual = USER_MODEL_TO_ACTUAL[model]
        logger.info(f"Mapped user model '{model}' to actual: {actual}")
        return actual
    
    return model


async def generate_with_provider(
    provider: TextProvider,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple:
    """
    Generate text using a specific provider.
    
    Args:
        provider: The TextProvider configuration
        messages: Conversation history
        model: The model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        Tuple of (response text or None, error message or None)
    """
    logger.info(f"Attempting text generation with {provider.name} using model {model}")
    
    try:
        client = AsyncClient(provider=provider.provider_class)
        
        # Generate with timeout
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=provider.timeout
        )
        
        if not response or not response.choices:
            logger.warning(f"{provider.name} returned empty response")
            return None, f"{provider.name} returned no response"
        
        content = response.choices[0].message.content
        if content:
            logger.info(f"{provider.name} generated response successfully ({len(content)} chars)")
            return content, None
        else:
            return None, f"{provider.name} returned empty content"
            
    except asyncio.TimeoutError:
        logger.warning(f"{provider.name} timed out after {provider.timeout}s")
        return None, f"{provider.name} timed out"
    except Exception as e:
        logger.error(f"{provider.name} failed: {str(e)}")
        return None, f"{provider.name} error: {str(e)}"


def generate_with_provider_sync(
    provider: TextProvider,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple:
    """
    Generate text using a specific provider (synchronous version).
    """
    logger.info(f"Attempting text generation with {provider.name} using model {model}")
    
    try:
        client = Client(provider=provider.provider_class)
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        if not response or not response.choices:
            logger.warning(f"{provider.name} returned empty response")
            return None, f"{provider.name} returned no response"
        
        content = response.choices[0].message.content
        if content:
            logger.info(f"{provider.name} generated response successfully ({len(content)} chars)")
            return content, None
        else:
            return None, f"{provider.name} returned empty content"
            
    except Exception as e:
        logger.error(f"{provider.name} failed: {str(e)}")
        return None, f"{provider.name} error: {str(e)}"


def generate_streaming_with_provider(
    provider: TextProvider,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Optional[Generator]:
    """
    Generate streaming text using a specific provider.
    
    Returns:
        Generator yielding response chunks or None if error
    """
    logger.info(f"Streaming with {provider.name} using model {model}")
    
    try:
        client = Client(provider=provider.provider_class)
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        
        return response
            
    except Exception as e:
        logger.error(f"{provider.name} streaming failed: {str(e)}")
        return None


async def generate_text_multi_provider(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_TEXT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple:
    """
    Main function to generate text with automatic fallback.
    
    Args:
        messages: Conversation history
        model: The preferred model (defaults to DEFAULT_TEXT_MODEL)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        Tuple of (response text or None, error message or None)
    """
    start_time = time.time()
    
    # Normalize model name
    model = normalize_model_name(model)
    
    # Build the list of models to try (requested model + fallbacks)
    models_to_try = [model]
    
    # Get user-facing model name for fallback lookup
    user_model = None
    for um, actual in USER_MODEL_TO_ACTUAL.items():
        if actual == model:
            user_model = um
            break
    
    if user_model:
        fallbacks = MODEL_FALLBACK_CHAIN.get(user_model, [])
        for fb in fallbacks:
            actual_fb = USER_MODEL_TO_ACTUAL.get(fb, fb)
            if actual_fb not in models_to_try:
                models_to_try.append(actual_fb)
    
    all_errors = []
    
    for try_model in models_to_try:
        logger.info(f"Trying model: {try_model}")
        
        # Get providers for this model
        providers = get_providers_for_model(try_model)
        
        if not providers:
            logger.warning(f"No providers available for model {try_model}")
            continue
        
        # Sort by priority and try each
        providers.sort(key=lambda p: p.priority.value)
        
        for provider in providers:
            use_model = try_model if try_model in provider.models else provider.models[0]
            response, error = await generate_with_provider(
                provider, messages, use_model, temperature, max_tokens
            )
            
            if response:
                elapsed = time.time() - start_time
                logger.info(f"Text generation succeeded in {elapsed:.2f}s with {provider.name}")
                return response, None
            
            if error:
                all_errors.append(f"{provider.name}: {error}")
    
    # All providers failed
    elapsed = time.time() - start_time
    error_msg = f"All text providers failed after {elapsed:.2f}s. Errors: {'; '.join(all_errors[:3])}"
    logger.error(error_msg)
    return None, error_msg


def generate_text_sync(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_TEXT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple:
    """
    Synchronous version of text generation with fallback.
    """
    start_time = time.time()
    
    # Normalize model name
    model = normalize_model_name(model)
    
    # Build the list of models to try
    models_to_try = [model]
    
    user_model = None
    for um, actual in USER_MODEL_TO_ACTUAL.items():
        if actual == model:
            user_model = um
            break
    
    if user_model:
        fallbacks = MODEL_FALLBACK_CHAIN.get(user_model, [])
        for fb in fallbacks:
            actual_fb = USER_MODEL_TO_ACTUAL.get(fb, fb)
            if actual_fb not in models_to_try:
                models_to_try.append(actual_fb)
    
    all_errors = []
    
    for try_model in models_to_try:
        logger.info(f"Trying model: {try_model}")
        
        providers = get_providers_for_model(try_model)
        
        if not providers:
            logger.warning(f"No providers available for model {try_model}")
            continue
        
        providers.sort(key=lambda p: p.priority.value)
        
        for provider in providers:
            use_model = try_model if try_model in provider.models else provider.models[0]
            response, error = generate_with_provider_sync(
                provider, messages, use_model, temperature, max_tokens
            )
            
            if response:
                elapsed = time.time() - start_time
                logger.info(f"Text generation succeeded in {elapsed:.2f}s with {provider.name}")
                return response, None
            
            if error:
                all_errors.append(f"{provider.name}: {error}")
    
    elapsed = time.time() - start_time
    error_msg = f"All text providers failed after {elapsed:.2f}s. Errors: {'; '.join(all_errors[:3])}"
    logger.error(error_msg)
    return None, error_msg


def get_streaming_response_multi_provider(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_TEXT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Optional[Generator]:
    """
    Get streaming response with multi-provider fallback.
    
    Returns:
        Generator yielding response chunks or None if all providers fail
    """
    # Normalize model name
    model = normalize_model_name(model)
    
    # Build the list of models to try
    models_to_try = [model]
    
    user_model = None
    for um, actual in USER_MODEL_TO_ACTUAL.items():
        if actual == model:
            user_model = um
            break
    
    if user_model:
        fallbacks = MODEL_FALLBACK_CHAIN.get(user_model, [])
        for fb in fallbacks:
            actual_fb = USER_MODEL_TO_ACTUAL.get(fb, fb)
            if actual_fb not in models_to_try:
                models_to_try.append(actual_fb)
    
    for try_model in models_to_try:
        logger.info(f"Trying streaming with model: {try_model}")
        
        providers = get_providers_for_model(try_model)
        
        if not providers:
            continue
        
        providers.sort(key=lambda p: p.priority.value)
        
        for provider in providers:
            if not provider.supports_streaming:
                continue
                
            use_model = try_model if try_model in provider.models else provider.models[0]
            stream = generate_streaming_with_provider(
                provider, messages, use_model, temperature, max_tokens
            )
            
            if stream:
                logger.info(f"Streaming started with {provider.name}")
                return stream
    
    logger.error("All streaming providers failed")
    return None

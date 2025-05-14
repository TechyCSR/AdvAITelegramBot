import os
import json
import time
import threading
from typing import Dict, Optional, Set, List

# Define constants
RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(RESOURCES_DIR, "cache")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache file paths for different languages
CACHE_FILES = {
    'hi': os.path.join(CACHE_DIR, 'hindi_cache.json'),
    'zh': os.path.join(CACHE_DIR, 'chinese_cache.json'),
    'ar': os.path.join(CACHE_DIR, 'arabic_cache.json'),
    'fr': os.path.join(CACHE_DIR, 'french_cache.json'),
    'ru': os.path.join(CACHE_DIR, 'russian_cache.json')
}

# In-memory cache to avoid repeated file reads
_file_cache: Dict[str, Dict[str, str]] = {}
_last_file_read: Dict[str, float] = {}
_pending_writes: Dict[str, Dict[str, str]] = {}
_dirty_languages: Set[str] = set()
_cache_lock = threading.RLock()  # Reentrant lock for thread safety
_write_interval = 60  # seconds between batch writes (1 minute)
_last_write_time = 0
_cache_stats = {"hits": 0, "misses": 0}
_cache_initialized = False

# Additional in-memory cache for frequently used translations
_hot_cache: Dict[str, Dict[str, str]] = {}
_hot_cache_size = 1000  # Number of most frequent translations to keep per language

def _load_cache_file(lang: str) -> Dict[str, str]:
    """Load the cache file for the specified language"""
    with _cache_lock:
        if lang == 'en':
            return {}  # No translation needed for English
        
        # Create empty file if it doesn't exist
        cache_file = CACHE_FILES.get(lang)
        if not cache_file:
            return {}
        
        # Check if we've already loaded this file recently
        current_time = time.time()
        if lang in _file_cache:
            _last_file_read[lang] = current_time  # Update access time
            return _file_cache[lang]
    
        # Load from file
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    _file_cache[lang] = json.load(f)
                    _last_file_read[lang] = current_time
                    
                    # Initialize hot cache for this language
                    _hot_cache[lang] = {}
                    
                    # Fill hot cache with most common translations
                    if len(_file_cache[lang]) > _hot_cache_size:
                        # Simple approach: just take the first N items
                        # A more advanced approach would track frequency
                        items = list(_file_cache[lang].items())[:_hot_cache_size]
                        _hot_cache[lang] = dict(items)
                    else:
                        _hot_cache[lang] = _file_cache[lang].copy()
                        
                    return _file_cache[lang]
            else:
                # Create empty cache file
                _file_cache[lang] = {}
                _hot_cache[lang] = {}
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                _last_file_read[lang] = current_time
                return {}
        except Exception as e:
            print(f"Error loading translation cache file for {lang}: {e}")
            # Initialize empty caches to prevent repeated attempts to load
            _file_cache[lang] = {}
            _hot_cache[lang] = {}
            return {}

def _save_pending_writes():
    """Save all pending writes to disk in a batch operation"""
    global _last_write_time
    
    with _cache_lock:
        current_time = time.time()
        # Only write if enough time has passed or there are many pending writes
        if (current_time - _last_write_time < _write_interval and 
            sum(len(v) for v in _pending_writes.values()) < 50):
            return
            
        _last_write_time = current_time
        languages_to_save = list(_dirty_languages)
        _dirty_languages.clear()
        
    # Save each dirty language file
    for lang in languages_to_save:
        try:
            cache_file = CACHE_FILES.get(lang)
            if not cache_file:
                continue
                
            with _cache_lock:
                # Merge pending writes with existing cache
                if lang not in _file_cache:
                    _load_cache_file(lang)
                
                # Get cached entries
                cache = _file_cache.get(lang, {})
                
                # Get pending writes for this language
                pending = _pending_writes.get(lang, {})
                if not pending:
                    continue
                    
                # Merge pending writes into cache
                cache.update(pending)
                _file_cache[lang] = cache
                _pending_writes[lang] = {}
            
            # Write to file outside the lock
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
                
            print(f"Batch saved {len(pending)} translations to {lang} cache")
                
        except Exception as e:
            print(f"Error saving batch translations for {lang}: {e}")

def _queue_for_write(lang: str, text: str, translation: str) -> None:
    """Queue a translation to be written to disk in the next batch operation"""
    if lang == 'en' or not CACHE_FILES.get(lang):
        return
        
    with _cache_lock:
        # Initialize pending writes for this language if needed
        if lang not in _pending_writes:
            _pending_writes[lang] = {}
            
        # Add to pending writes
        _pending_writes[lang][text] = translation
        _dirty_languages.add(lang)
        
        # Update in-memory cache immediately
        if lang in _file_cache:
            _file_cache[lang][text] = translation
            
        # Update hot cache for frequently accessed items
        if lang in _hot_cache:
            _hot_cache[lang][text] = translation
            
    # Try to save pending writes if we have accumulated enough
    if sum(len(v) for v in _pending_writes.values()) >= 50:
        _save_pending_writes()

def get_cached_translation(text: str, lang: str) -> Optional[str]:
    """Get a translation from the cache if it exists"""
    global _cache_stats
    
    if lang == 'en':
        return text
        
    # Check if language is supported
    if lang not in CACHE_FILES:
        return None
    
    with _cache_lock:
        # Check hot cache first (fastest)
        if lang in _hot_cache and text in _hot_cache[lang]:
            _cache_stats["hits"] += 1
            return _hot_cache[lang][text]
            
        # Check in-memory cache next (includes pending writes)
        if lang in _file_cache and text in _file_cache[lang]:
            _cache_stats["hits"] += 1
            # Add to hot cache for future fast access
            if lang in _hot_cache and len(_hot_cache[lang]) < _hot_cache_size:
                _hot_cache[lang][text] = _file_cache[lang][text]
            return _file_cache[lang][text]
            
        # Load cache and check again
        cache = _load_cache_file(lang)
        if text in cache:
            _cache_stats["hits"] += 1
            return cache.get(text)
            
        _cache_stats["misses"] += 1
        return None

def add_to_translation_cache(text: str, translation: str, lang: str) -> None:
    """Add a new translation to the cache"""
    if lang == 'en' or not text or not translation:
        return
        
    # Queue the translation for batch writing
    _queue_for_write(lang, text, translation)

def get_translation_stats() -> Dict[str, int]:
    """Get statistics about the translation cache"""
    stats = {}
    with _cache_lock:
        stats = {
            "cache_entries": {},
            "hit_rate": 0,
            "memory_usage": 0
        }
        
        # Get entries per language
        for lang in CACHE_FILES:
            if lang in _file_cache:
                stats["cache_entries"][lang] = len(_file_cache[lang])
            else:
                # Load cache if not loaded
                cache = _load_cache_file(lang)
                stats["cache_entries"][lang] = len(cache)
                
        # Calculate hit rate
        total_lookups = _cache_stats["hits"] + _cache_stats["misses"]
        if total_lookups > 0:
            stats["hit_rate"] = round((_cache_stats["hits"] / total_lookups) * 100, 2)
            
        # Rough estimate of memory usage in MB
        total_entries = sum(len(cache) for cache in _file_cache.values())
        # Assuming average of 100 bytes per entry (key + value)
        stats["memory_usage"] = round((total_entries * 100) / (1024 * 1024), 2)
            
    return stats

def preload_all_caches() -> None:
    """Preload all translation caches into memory for faster access"""
    global _cache_initialized
    
    if _cache_initialized:
        return
        
    start_time = time.time()
    for lang in CACHE_FILES:
        _load_cache_file(lang)
    
    # Print statistics for debugging
    stats = get_translation_stats()
    load_time = time.time() - start_time
    print(f"Preloaded translation caches in {load_time:.2f} seconds: {stats}")
    
    # Start a background thread to periodically save pending writes
    save_thread = threading.Thread(
        target=_periodic_save_thread, 
        daemon=True,
        name="TranslationCacheSaver"
    )
    save_thread.start()
    
    _cache_initialized = True

def batch_cache_translations(texts: List[str], lang: str) -> Dict[str, str]:
    """
    Get translations for multiple texts at once from the cache.
    Returns a dictionary mapping original text to translated text for cache hits.
    """
    if lang == 'en':
        return {text: text for text in texts}
        
    result = {}
    with _cache_lock:
        for text in texts:
            cached = get_cached_translation(text, lang)
            if cached:
                result[text] = cached
                
    return result

def _periodic_save_thread():
    """Background thread that periodically saves pending translations"""
    while True:
        try:
            _save_pending_writes()
        except Exception as e:
            print(f"Error in periodic translation save: {e}")
        
        # Sleep for the write interval
        time.sleep(_write_interval) 
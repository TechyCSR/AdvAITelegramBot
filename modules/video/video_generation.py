import asyncio
import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from google import genai
from google.genai.types import GenerateVideosConfig
from google.cloud import storage
from database import user_db
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable pricing and settings
TOKEN_PRICE_RS = 9  # Rs 9 for 10 tokens
TOKENS_PER_VIDEO = 10
VIDEO_LENGTH_SECONDS = 8
MAX_CONCURRENT_GENERATIONS = 3
MAX_QUEUE_SIZE = 50

class VideoQuality(Enum):
    STANDARD = "standard"
    HD = "hd"
    PREMIUM = "premium"

class VideoStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class VideoRequest:
    request_id: str
    user_id: int
    prompt: str
    quality: VideoQuality
    aspect_ratio: str = "16:9"
    status: VideoStatus = VideoStatus.QUEUED
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    error_message: Optional[str] = None
    local_path: Optional[str] = None
    generation_time: Optional[float] = None
    enhanced_prompt: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

# Enhanced token costs based on quality
QUALITY_TOKEN_COSTS = {
    VideoQuality.STANDARD: 10,
    VideoQuality.HD: 15,
    VideoQuality.PREMIUM: 25
}

# Global video generation queue and tracking
video_queue: List[VideoRequest] = []
active_generations: Dict[str, VideoRequest] = {}
user_video_locks = {}
user_video_locks_lock = Lock()
queue_lock = asyncio.Lock()

def get_user_lock(user_id: int) -> asyncio.Lock:
    """Get or create a lock for a specific user to prevent concurrent generations."""
    with user_video_locks_lock:
        if user_id not in user_video_locks:
            user_video_locks[user_id] = asyncio.Lock()
        return user_video_locks[user_id]

async def get_user_tokens(user_id: int) -> int:
    """Get user's current token balance."""
    try:
        users_collection = user_db.get_user_collection()
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            users_collection.insert_one({"user_id": user_id, "video_tokens": 0})
            return 0
        return user.get("video_tokens", 0)
    except Exception as e:
        logger.error(f"Error getting user tokens for {user_id}: {e}")
        return 0

async def add_user_tokens(user_id: int, tokens: int) -> bool:
    """Add tokens to user's balance."""
    try:
        users_collection = user_db.get_user_collection()
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            users_collection.insert_one({"user_id": user_id, "video_tokens": tokens})
        else:
            users_collection.update_one({"user_id": user_id}, {"$inc": {"video_tokens": tokens}})
        return True
    except Exception as e:
        logger.error(f"Error adding tokens for user {user_id}: {e}")
        return False

async def remove_user_tokens(user_id: int, tokens: int) -> bool:
    """Remove tokens from user's balance."""
    try:
        users_collection = user_db.get_user_collection()
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            users_collection.insert_one({"user_id": user_id, "video_tokens": 0})
            return False
        if user.get("video_tokens", 0) < tokens:
            return False
        users_collection.update_one({"user_id": user_id}, {"$inc": {"video_tokens": -tokens}})
        return True
    except Exception as e:
        logger.error(f"Error removing tokens for user {user_id}: {e}")
        return False

async def enhance_prompt_with_ai(prompt: str) -> str:
    """Enhance user prompt with AI to improve video quality."""
    try:
        enhancement_prompt = f"""
        Enhance this video generation prompt to be more descriptive and cinematic while keeping the core idea:
        
        Original prompt: "{prompt}"
        
        Enhanced prompt should include:
        - Better visual details
        - Lighting and mood descriptions
        - Camera movement suggestions
        - More specific elements
        
        Return only the enhanced prompt, nothing else.
        """
        
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=enhancement_prompt
        )
        
        enhanced = response.text.strip()
        if len(enhanced) > 500:  # Keep it reasonable
            enhanced = enhanced[:497] + "..."
            
        return enhanced if enhanced else prompt
    except Exception as e:
        logger.warning(f"Failed to enhance prompt: {e}")
        return prompt

async def add_to_queue(request: VideoRequest) -> str:
    """Add a video request to the generation queue."""
    async with queue_lock:
        if len(video_queue) >= MAX_QUEUE_SIZE:
            raise Exception("Generation queue is full. Please try again later.")
        
        video_queue.append(request)
        logger.info(f"Added request {request.request_id} to queue for user {request.user_id}")
        return request.request_id

async def get_queue_position(request_id: str) -> int:
    """Get the position of a request in the queue."""
    async with queue_lock:
        for i, req in enumerate(video_queue):
            if req.request_id == request_id:
                return i + 1
        return -1

async def get_user_active_requests(user_id: int) -> List[VideoRequest]:
    """Get all active requests for a user."""
    requests = []
    async with queue_lock:
        # Check queue
        for req in video_queue:
            if req.user_id == user_id:
                requests.append(req)
        # Check active generations
        for req in active_generations.values():
            if req.user_id == user_id:
                requests.append(req)
    return requests

async def cancel_request(request_id: str, user_id: int) -> bool:
    """Cancel a video generation request."""
    async with queue_lock:
        # Check queue first
        for i, req in enumerate(video_queue):
            if req.request_id == request_id and req.user_id == user_id:
                req.status = VideoStatus.CANCELLED
                video_queue.pop(i)
                # Refund tokens
                token_cost = QUALITY_TOKEN_COSTS[req.quality]
                await add_user_tokens(user_id, token_cost)
                logger.info(f"Cancelled queued request {request_id}")
                return True
        
        # Check active generations
        if request_id in active_generations:
            req = active_generations[request_id]
            if req.user_id == user_id:
                req.status = VideoStatus.CANCELLED
                # Note: Active generations can't be easily cancelled, 
                # but we mark them as cancelled for UI purposes
                logger.info(f"Marked active request {request_id} as cancelled")
                return True
    
    return False

async def process_video_queue():
    """Background task to process the video generation queue."""
    while True:
        try:
            # Check if we can start a new generation
            if len(active_generations) >= MAX_CONCURRENT_GENERATIONS:
                await asyncio.sleep(5)
                continue
            
            # Get next request from queue
            request = None
            async with queue_lock:
                if video_queue:
                    request = video_queue.pop(0)
            
            if not request:
                await asyncio.sleep(2)
                continue
            
            # Start generation
            active_generations[request.request_id] = request
            asyncio.create_task(generate_video_internal(request))
            
        except Exception as e:
            logger.error(f"Error in video queue processor: {e}")
            await asyncio.sleep(5)

async def generate_video_internal(request: VideoRequest):
    """Internal video generation function."""
    try:
        request.status = VideoStatus.PROCESSING
        request.started_at = datetime.now()
        
        # Enhance prompt if requested
        if request.quality in [VideoQuality.HD, VideoQuality.PREMIUM]:
            request.enhanced_prompt = await enhance_prompt_with_ai(request.prompt)
            final_prompt = request.enhanced_prompt
        else:
            final_prompt = request.prompt
        
        client = genai.Client()
        start_time = time.time()
        
        # Configure generation based on quality
        config_params = {
            "aspect_ratio": request.aspect_ratio,
            "output_gcs_uri": "gs://techycsr/test_vdo_output"
        }
        
        if request.quality == VideoQuality.PREMIUM:
            # Premium quality settings (when available)
            pass
        
        operation = client.models.generate_videos(
            model="veo-3.0-generate-preview",
            prompt=final_prompt,
            config=GenerateVideosConfig(**config_params),
        )
        
        # Monitor progress
        while not operation.done:
            await asyncio.sleep(15)
            operation = client.operations.get(operation)
            # Update progress (simplified - real progress would need operation details)
            request.progress = min(request.progress + 10, 90)
        
        request.generation_time = time.time() - start_time
        
        if operation.response:
            video_uri = operation.result.generated_videos[0].video.uri
            
            # Download video
            import re
            match = re.match(r'gs://([^/]+)/(.+)', video_uri)
            if match:
                bucket_name, blob_name = match.groups()
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                
                local_path = f'generated_images/generated_video_{request.user_id}_{request.request_id}.mp4'
                blob.download_to_filename(local_path)
                
                request.local_path = local_path
                request.status = VideoStatus.COMPLETED
                request.completed_at = datetime.now()
                request.progress = 100
                
                logger.info(f"Video generation completed for request {request.request_id}")
            else:
                raise Exception("Failed to parse GCS URI")
        else:
            raise Exception("Video generation failed - no response")
            
    except Exception as e:
        request.status = VideoStatus.FAILED
        request.error_message = str(e)
        request.completed_at = datetime.now()
        
        # Refund tokens on failure
        token_cost = QUALITY_TOKEN_COSTS[request.quality]
        await add_user_tokens(request.user_id, token_cost)
        
        logger.error(f"Video generation failed for request {request.request_id}: {e}")
    
    finally:
        # Remove from active generations
        if request.request_id in active_generations:
            del active_generations[request.request_id]

async def create_video_request(
    user_id: int, 
    prompt: str, 
    quality: VideoQuality = VideoQuality.STANDARD,
    aspect_ratio: str = "16:9"
) -> Tuple[Optional[str], Optional[str]]:
    """Create a new video generation request."""
    try:
        # Check if user has enough tokens
        token_cost = QUALITY_TOKEN_COSTS[quality]
        user_tokens = await get_user_tokens(user_id)
        
        if user_tokens < token_cost:
            return None, f"Insufficient tokens. Need {token_cost}, have {user_tokens}"
        
        # Check user's active requests limit
        active_requests = await get_user_active_requests(user_id)
        if len(active_requests) >= 3:  # Max 3 concurrent requests per user
            return None, "Maximum concurrent requests reached. Please wait for completion."
        
        # Deduct tokens
        if not await remove_user_tokens(user_id, token_cost):
            return None, "Failed to deduct tokens. Please try again."
        
        # Create request
        request = VideoRequest(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            prompt=prompt,
            quality=quality,
            aspect_ratio=aspect_ratio
        )
        
        # Add to queue
        request_id = await add_to_queue(request)
        
        return request_id, None
        
    except Exception as e:
        logger.error(f"Error creating video request: {e}")
        return None, str(e)

async def get_request_status(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a video generation request."""
    # Check active generations first
    if request_id in active_generations:
        request = active_generations[request_id]
        return {
            "request_id": request.request_id,
            "status": request.status.value,
            "progress": request.progress,
            "queue_position": 0,  # Currently processing
            "estimated_time": max(0, 120 - (time.time() - request.started_at.timestamp())) if request.started_at else 120,
            "quality": request.quality.value,
            "enhanced_prompt": request.enhanced_prompt
        }
    
    # Check queue
    async with queue_lock:
        for i, request in enumerate(video_queue):
            if request.request_id == request_id:
                return {
                    "request_id": request.request_id,
                    "status": request.status.value,
                    "progress": 0,
                    "queue_position": i + 1,
                    "estimated_time": (i + 1) * 120 + len(active_generations) * 60,
                    "quality": request.quality.value,
                    "enhanced_prompt": None
                }
    
    return None

# Legacy function for backwards compatibility
async def generate_video_for_user(user_id: int, prompt: str, output_gcs_uri: str) -> Tuple[Optional[str], Any]:
    """Legacy function maintained for backwards compatibility."""
    request_id, error = await create_video_request(user_id, prompt)
    
    if error:
        return None, error
    
    # Wait for completion (for synchronous behavior)
    timeout = 300  # 5 minutes timeout
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = await get_request_status(request_id)
        if not status:
            return None, "Request not found"
        
        if status["status"] == VideoStatus.COMPLETED.value:
            # Find the completed request
            for req in [*active_generations.values(), *video_queue]:
                if req.request_id == request_id and req.local_path:
                    return req.local_path, req.generation_time
        
        elif status["status"] == VideoStatus.FAILED.value:
            # Find the failed request
            for req in [*active_generations.values(), *video_queue]:
                if req.request_id == request_id:
                    return None, req.error_message or "Generation failed"
        
        await asyncio.sleep(5)
    
    return None, "Request timed out"

# Queue processor will be started by the main application
# This prevents issues with event loop not being ready during import
queue_processor_task = None

def start_queue_processor():
    """Start the video generation queue processor."""
    global queue_processor_task
    if queue_processor_task is None or queue_processor_task.done():
        queue_processor_task = asyncio.create_task(process_video_queue())
        logger.info("Video generation queue processor started")
    
def stop_queue_processor():
    """Stop the video generation queue processor."""
    global queue_processor_task
    if queue_processor_task and not queue_processor_task.done():
        queue_processor_task.cancel()
        logger.info("Video generation queue processor stopped") 
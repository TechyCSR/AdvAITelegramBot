import asyncio
import time
import logging
from typing import Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class UserRequestState:
    """Track a user's current request states"""
    user_id: int
    image_processing: bool = False
    text_processing: bool = False
    image_start_time: float = field(default=0.0)
    text_start_time: float = field(default=0.0)
    image_task_info: str = field(default="")
    text_task_info: str = field(default="")
    
    def is_image_expired(self, timeout: float = 600.0) -> bool:
        """Check if image request has expired (default 10 minutes)"""
        if not self.image_processing:
            return False
        return time.time() - self.image_start_time > timeout
    
    def is_text_expired(self, timeout: float = 300.0) -> bool:
        """Check if text request has expired (default 5 minutes)"""
        if not self.text_processing:
            return False
        return time.time() - self.text_start_time > timeout
    
    def start_image_request(self, task_info: str = "") -> None:
        """Start an image request"""
        self.image_processing = True
        self.image_start_time = time.time()
        self.image_task_info = task_info
        logger.info(f"Started image request for user {self.user_id}: {task_info}")
    
    def start_text_request(self, task_info: str = "") -> None:
        """Start a text request"""
        self.text_processing = True
        self.text_start_time = time.time()
        self.text_task_info = task_info
        logger.info(f"Started text request for user {self.user_id}: {task_info}")
    
    def finish_image_request(self) -> None:
        """Finish an image request"""
        self.image_processing = False
        self.image_start_time = 0.0
        self.image_task_info = ""
        logger.info(f"Finished image request for user {self.user_id}")
    
    def finish_text_request(self) -> None:
        """Finish a text request"""
        self.text_processing = False
        self.text_start_time = 0.0
        self.text_task_info = ""
        logger.info(f"Finished text request for user {self.user_id}")

# Global request state tracker
user_request_states: Dict[int, UserRequestState] = {}

def get_user_state(user_id: int) -> UserRequestState:
    """Get or create a user's request state"""
    if user_id not in user_request_states:
        user_request_states[user_id] = UserRequestState(user_id)
    return user_request_states[user_id]

def cleanup_expired_requests() -> None:
    """Clean up expired requests"""
    current_time = time.time()
    for user_id, state in list(user_request_states.items()):
        if state.is_image_expired():
            logger.warning(f"Force cleaning expired image request for user {user_id}")
            state.finish_image_request()
        
        if state.is_text_expired():
            logger.warning(f"Force cleaning expired text request for user {user_id}")
            state.finish_text_request()
        
        # Remove empty states
        if not state.image_processing and not state.text_processing:
            if current_time - max(state.image_start_time, state.text_start_time) > 300:  # 5 minutes
                del user_request_states[user_id]

async def can_start_image_request(user_id: int) -> Tuple[bool, str]:
    """Check if user can start an image request"""
    cleanup_expired_requests()
    state = get_user_state(user_id)
    
    if state.image_processing:
        if not state.is_image_expired():
            return False, "⏳ Your previous image request is being processed. Please wait for that to be complete."
        else:
            # Auto-cleanup expired request
            state.finish_image_request()
    
    return True, ""

async def can_start_text_request(user_id: int) -> Tuple[bool, str]:
    """Check if user can start a text request"""
    cleanup_expired_requests()
    state = get_user_state(user_id)
    
    if state.text_processing:
        if not state.is_text_expired():
            return False, "⏳ Your previous request is being processed. Please wait for that to be complete."
        else:
            # Auto-cleanup expired request
            state.finish_text_request()
    
    return True, ""

def start_image_request(user_id: int, task_info: str = "") -> None:
    """Start an image request for a user"""
    state = get_user_state(user_id)
    state.start_image_request(task_info)

def start_text_request(user_id: int, task_info: str = "") -> None:
    """Start a text request for a user"""
    state = get_user_state(user_id)
    state.start_text_request(task_info)

def finish_image_request(user_id: int) -> None:
    """Finish an image request for a user"""
    if user_id in user_request_states:
        user_request_states[user_id].finish_image_request()

def finish_text_request(user_id: int) -> None:
    """Finish a text request for a user"""
    if user_id in user_request_states:
        user_request_states[user_id].finish_text_request()

def get_user_request_status(user_id: int) -> Dict[str, any]:
    """Get current request status for a user"""
    if user_id not in user_request_states:
        return {"image_processing": False, "text_processing": False}
    
    state = user_request_states[user_id]
    return {
        "image_processing": state.image_processing,
        "text_processing": state.text_processing,
        "image_task": state.image_task_info,
        "text_task": state.text_task_info,
        "image_elapsed": int(time.time() - state.image_start_time) if state.image_processing else 0,
        "text_elapsed": int(time.time() - state.text_start_time) if state.text_processing else 0
    }

# Background cleanup task
async def start_cleanup_scheduler():
    """Start the background cleanup scheduler"""
    while True:
        try:
            cleanup_expired_requests()
            await asyncio.sleep(60)  # Clean up every minute
        except Exception as e:
            logger.error(f"Error in cleanup scheduler: {e}")
            await asyncio.sleep(60) 
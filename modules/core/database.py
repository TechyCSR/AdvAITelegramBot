from typing import Optional, Dict, Any
import os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import logging
from config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Singleton database service with connection pooling for MongoDB.
    
    This class provides centralized database access with connection pooling
    to reduce overhead and improve performance.
    """
    _instance: Optional['DatabaseService'] = None
    
    def __new__(cls) -> 'DatabaseService':
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the database connection pool"""
        if not getattr(self, '_initialized', False):
            self._db_client: Optional[MongoClient] = None
            self._db: Optional[Database] = None
            self._collections: Dict[str, Collection] = {}
            self._connect()
            self._initialized = True
    
    def _connect(self) -> None:
        """Establish connection to MongoDB with connection pooling"""
        try:
            # Connection pool configuration
            # maxPoolSize: Maximum number of connections in the pool
            # minPoolSize: Minimum number of connections in the pool
            # maxIdleTimeMS: How long a connection can remain idle before being closed
            # waitQueueTimeoutMS: How long a thread will wait for a connection
            connection_options = {
                'maxPoolSize': 20,  # Adjust based on expected concurrent operations
                'minPoolSize': 5,   # Keep minimum connections ready
                'maxIdleTimeMS': 30000,  # Close idle connections after 30 seconds
                'waitQueueTimeoutMS': 5000,  # Wait up to 5 seconds for a connection
            }
            
            # Connect to MongoDB with connection pooling
            self._db_client = MongoClient(DATABASE_URL, **connection_options)
            
            # Access the database
            self._db = self._db_client['aibotdb']
            logger.info("Database connection established with connection pooling")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get a collection with caching to avoid repeated lookups
        
        Args:
            collection_name: Name of the MongoDB collection
            
        Returns:
            MongoDB collection object
        """
        if collection_name not in self._collections:
            self._collections[collection_name] = self._db[collection_name]
        return self._collections[collection_name]
    
    def close(self) -> None:
        """Close database connection"""
        if self._db_client:
            self._db_client.close()
            logger.info("Database connection closed")
            
    def __del__(self) -> None:
        """Ensure connection is closed on object deletion"""
        try:
            self.close()
        except:
            # Suppress errors during interpreter shutdown
            pass

# Create a global instance for import
db_service = DatabaseService()

# Helper functions for common collections
def get_history_collection() -> Collection:
    """Get the history collection"""
    return db_service.get_collection('history')

def get_user_collection() -> Collection:
    """Get the user collection"""
    return db_service.get_collection('users')

def get_user_lang_collection() -> Collection:
    """Get the user language collection"""
    return db_service.get_collection('user_lang')

def get_image_feedback_collection() -> Collection:
    """Get the image feedback collection"""
    return db_service.get_collection('image_feedback')

def get_prompt_storage_collection() -> Collection:
    """Get the prompt storage collection"""
    return db_service.get_collection('prompt_storage')

def get_user_images_collection() -> Collection:
    """Get the user images collection"""
    return db_service.get_collection('user_images')

def get_feature_settings_collection() -> Collection:
    """Get the feature settings collection"""
    return db_service.get_collection('feature_settings') 
"""
Database Service for AdvAI Image Generator Webapp
Provides MongoDB connection and collection management for the webapp.
"""

import logging
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

class WebappDatabaseService:
    """
    Database service for the webapp with connection pooling for MongoDB.
    Uses the same database as the main bot to maintain data consistency.
    """
    _instance: Optional['WebappDatabaseService'] = None
    
    def __new__(cls) -> 'WebappDatabaseService':
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(WebappDatabaseService, cls).__new__(cls)
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
            connection_options = {
                'maxPoolSize': 10,  # Smaller pool for webapp
                'minPoolSize': 2,   # Minimum connections
                'maxIdleTimeMS': 30000,  # Close idle connections after 30 seconds
                'waitQueueTimeoutMS': 5000,  # Wait up to 5 seconds for a connection
            }
            
            # Connect to MongoDB with connection pooling
            self._db_client = MongoClient(DATABASE_URL, **connection_options)
            
            # Access the same database as the bot ('aibotdb')
            self._db = self._db_client['aibotdb']
            logger.info("Webapp database connection established")
        except Exception as e:
            logger.error(f"Webapp database connection error: {str(e)}")
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
            logger.info("Webapp database connection closed")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            self._db_client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

# Create a global instance for import
webapp_db_service = WebappDatabaseService()

# Helper functions for common collections used in premium system
def get_premium_users_collection() -> Collection:
    """Get the premium users collection (same as bot)"""
    return webapp_db_service.get_collection('premium_users')

def get_user_collection() -> Collection:
    """Get the users collection (same as bot)"""
    return webapp_db_service.get_collection('users')

def get_user_lang_collection() -> Collection:
    """Get the user language collection (same as bot)"""
    return webapp_db_service.get_collection('user_lang')

def get_user_ai_model_settings_collection() -> Collection:
    """Get the user AI model settings collection (same as bot)"""
    return webapp_db_service.get_collection('user_ai_model_settings')

def get_webapp_sessions_collection() -> Collection:
    """Get the webapp sessions collection (webapp-specific)"""
    return webapp_db_service.get_collection('webapp_sessions')

def get_webapp_image_history_collection() -> Collection:
    """Get the webapp image history collection (webapp-specific)"""
    return webapp_db_service.get_collection('webapp_image_history') 
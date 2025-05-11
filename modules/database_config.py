from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
import os
from functools import wraps
import time

logger = logging.getLogger(__name__)

class DatabaseConfig:
    _instance = None
    _client = None
    _db = None
    
    # MongoDB connection settings
    MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DB_NAME = "aibotdb"
    MAX_RETRIES = 5  # Increased retries
    RETRY_DELAY = 2
    CONNECTION_TIMEOUT = 10000  # Increased timeout to 10 seconds
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if DatabaseConfig._client is None:
            self._connect()
    
    def _connect(self):
        try:
            DatabaseConfig._client = MongoClient(
                self.MONGO_URI,
                serverSelectionTimeoutMS=self.CONNECTION_TIMEOUT,
                connectTimeoutMS=self.CONNECTION_TIMEOUT,
                socketTimeoutMS=self.CONNECTION_TIMEOUT,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=2500,
                retryWrites=True,
                retryReads=True
            )
            DatabaseConfig._db = DatabaseConfig._client[self.DB_NAME]
            
            # Test connection with retry
            for attempt in range(self.MAX_RETRIES):
                try:
                    DatabaseConfig._client.admin.command('ping')
                    logger.info("Successfully connected to MongoDB")
                    break
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    if attempt == self.MAX_RETRIES - 1:
                        logger.error(f"Failed to connect to MongoDB after {self.MAX_RETRIES} attempts: {e}")
                        raise
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
            
            # Create indexes
            self._create_indexes()
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise
    
    def _create_indexes(self):
        try:
            # User language collection
            self.db.user_lang.create_index("user_id", unique=True)
            
            # User settings collection
            self.db.user_settings.create_index("user_id", unique=True)
            
            # User voice settings collection
            self.db.user_voice.create_index("user_id", unique=True)
            
            # User AI mode collection
            self.db.user_ai_mode.create_index("user_id", unique=True)
            
            logger.info("Successfully created database indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    @property
    def db(self):
        if DatabaseConfig._db is None:
            self._connect()
        return DatabaseConfig._db
    
    def retry_on_failure(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for attempt in range(DatabaseConfig.MAX_RETRIES):
                try:
                    return await func(self, *args, **kwargs)
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    if attempt == DatabaseConfig.MAX_RETRIES - 1:
                        logger.error(f"Database operation failed after {DatabaseConfig.MAX_RETRIES} attempts: {e}")
                        raise
                    logger.warning(f"Database operation failed, retrying in {DatabaseConfig.RETRY_DELAY} seconds...")
                    time.sleep(DatabaseConfig.RETRY_DELAY)
                    self._connect()
        return wrapper

db_config = DatabaseConfig.get_instance() 
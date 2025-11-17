from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    database = None

db = Database()

async def get_database():
    """Get database instance"""
    return db.database

async def connect_to_mongo():
    """Create database connection"""
    try:
        logger.info("Connecting to MongoDB...")
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=10,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        
        # Test the connection
        await db.client.admin.command('ping')
        
        db.database = db.client[settings.DATABASE_NAME]
        logger.info(f"Successfully connected to MongoDB database: {settings.DATABASE_NAME}")
        
        # Create indexes for better performance
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    try:
        if db.client:
            logger.info("Closing MongoDB connection...")
            db.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")

async def create_indexes():
    """Create database indexes for better search performance"""
    try:
        # Assignment collection indexes
        assignments_collection = db.database.assignments
        
        # Index for search functionality (title, subject, description)
        await assignments_collection.create_index([
            ("title", "text"),
            ("subject", "text"), 
            ("description", "text")
        ], name="search_index")
        
        # Index for user assignments
        await assignments_collection.create_index("user_id")
        
        # Index for status queries
        await assignments_collection.create_index("status")
        
        # Index for date-based queries
        await assignments_collection.create_index("created_at")
        await assignments_collection.create_index("due_date")
        
        # Compound index for user + status queries
        await assignments_collection.create_index([("user_id", 1), ("status", 1)])
        
        # Solutions collection indexes
        solutions_collection = db.database.solutions
        
        # Index for assignment-solution relationship
        await solutions_collection.create_index("assignment_id")
        
        # Users collection indexes
        users_collection = db.database.users
        
        # Index for Google OAuth
        await users_collection.create_index("google_id", unique=True)
        await users_collection.create_index("email", unique=True)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        # Don't raise here as indexes might already exist
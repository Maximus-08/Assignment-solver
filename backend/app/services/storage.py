"""
File storage service supporting both local and cloud storage
"""
import os
import uuid
from typing import Optional, BinaryIO
from pathlib import Path
import aiofiles
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """Abstract storage service interface"""
    
    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """Upload file and return storage URL"""
        raise NotImplementedError
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        raise NotImplementedError
    
    async def get_file_url(self, file_path: str) -> str:
        """Get public URL for file"""
        raise NotImplementedError

class LocalStorageService(StorageService):
    """Local filesystem storage service"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """Upload file to local storage"""
        try:
            # Generate unique filename
            file_extension = Path(file.filename).suffix if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create folder path
            folder_path = self.upload_dir / folder if folder else self.upload_dir
            folder_path.mkdir(exist_ok=True)
            
            file_path = folder_path / unique_filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Return relative path for storage
            relative_path = str(file_path.relative_to(self.upload_dir))
            logger.info(f"File uploaded to local storage: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"Error uploading file to local storage: {e}")
            raise HTTPException(status_code=500, detail="File upload failed")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from local storage"""
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted from local storage: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file from local storage: {e}")
            return False
    
    async def get_file_url(self, file_path: str) -> str:
        """Get URL for local file"""
        return f"/api/v1/files/{file_path}"

class CloudStorageService(StorageService):
    """Google Cloud Storage service for production"""
    
    def __init__(self):
        try:
            from google.cloud import storage
            self.client = storage.Client(project=settings.CLOUD_STORAGE_PROJECT_ID)
            self.bucket = self.client.bucket(settings.CLOUD_STORAGE_BUCKET)
        except ImportError:
            logger.error("Google Cloud Storage client not available. Install google-cloud-storage.")
            raise
        except Exception as e:
            logger.error(f"Error initializing Cloud Storage: {e}")
            raise
    
    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """Upload file to Google Cloud Storage"""
        try:
            # Generate unique filename
            file_extension = Path(file.filename).suffix if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create blob path
            blob_path = f"{folder}/{unique_filename}" if folder else unique_filename
            blob = self.bucket.blob(blob_path)
            
            # Upload file
            content = await file.read()
            blob.upload_from_string(content, content_type=file.content_type)
            
            logger.info(f"File uploaded to cloud storage: {blob_path}")
            return blob_path
            
        except Exception as e:
            logger.error(f"Error uploading file to cloud storage: {e}")
            raise HTTPException(status_code=500, detail="File upload failed")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Google Cloud Storage"""
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.delete()
                logger.info(f"File deleted from cloud storage: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file from cloud storage: {e}")
            return False
    
    async def get_file_url(self, file_path: str) -> str:
        """Get public URL for cloud storage file"""
        blob = self.bucket.blob(file_path)
        return blob.public_url

# Storage service factory
def get_storage_service() -> StorageService:
    """Get appropriate storage service based on configuration"""
    if settings.use_cloud_storage:
        return CloudStorageService()
    else:
        return LocalStorageService()

# Global storage service instance
storage_service = get_storage_service()
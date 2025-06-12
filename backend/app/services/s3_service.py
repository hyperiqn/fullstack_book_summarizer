# app/services/s3_service.py 
import aiobotocore.session
import logging
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import Optional
from fastapi import UploadFile
import os
import asyncio
logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region_name = settings.AWS_REGION_NAME

    async def upload_file(self, file: UploadFile, object_name: str) -> Optional[str]:
        async with self.session.create_client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY 
        ) as client:
            try:
                file_content = await file.read()
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_content,
                    ContentType=file.content_type
                )
                s3_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{object_name}"
                logger.info(f"Successfully uploaded {object_name} to S3. URL: {s3_url}")
                return s3_url
            except ClientError as e:
                logger.error(f"Failed to upload file {object_name} to S3: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred during S3 upload of {object_name}: {e}")
                return None

    async def download_file(self, object_name: str) -> Optional[bytes]:
        async with self.session.create_client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY 
        ) as client:
            try:
                response = await client.get_object(Bucket=self.bucket_name, Key=object_name)
                file_content = await response['Body'].read()
                logger.info(f"Successfully downloaded {object_name} from S3.")
                return file_content
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"File {object_name} not found in S3.")
                else:
                    logger.error(f"Failed to download file {object_name} from S3: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred during S3 download of {object_name}: {e}")
                return None

    async def delete_file(self, object_name: str) -> bool:
        async with self.session.create_client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY 
        ) as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=object_name)
                logger.info(f"Successfully deleted {object_name} from S3.")
                return True
            except ClientError as e:
                logger.error(f"Failed to delete file {object_name} from S3: {e}")
                return False
            except Exception as e:
                logger.error(f"An unexpected error occurred during S3 deletion of {object_name}: {e}")
                return False

    async def object_exists(self, object_name: str) -> bool:
        try:
            await asyncio.to_thread(self.s3_client.head_object, Bucket=self.bucket_name, Key=object_name)
            logger.debug(f"S3 object '{object_name}' found.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.debug(f"S3 object '{object_name}' not found (404 error).")
                return False
            else:
                logger.error(f"Error checking S3 object '{object_name}': {e}")
                raise 
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking S3 object '{object_name}': {e}")
            return False
        
s3_service = S3Service()
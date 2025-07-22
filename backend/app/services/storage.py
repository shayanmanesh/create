import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import aiofiles
import asyncio
from app.config import settings
import uuid
from datetime import datetime
import mimetypes

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)


async def upload_to_s3(
    file_content: bytes | str,
    key: str,
    content_type: Optional[str] = None
) -> str:
    """Upload file to S3 and return URL"""
    
    # If content is string, encode to bytes
    if isinstance(file_content, str):
        file_content = file_content.encode('utf-8')
    
    # Guess content type if not provided
    if not content_type:
        content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
    
    try:
        # Run S3 upload in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
                CacheControl='public, max-age=31536000',  # 1 year cache
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
        )
        
        # Return CloudFront URL if available, otherwise S3 URL
        return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
        
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        raise


async def upload_file_to_s3(
    file_path: str,
    key: str,
    content_type: Optional[str] = None
) -> str:
    """Upload file from disk to S3"""
    
    async with aiofiles.open(file_path, 'rb') as file:
        content = await file.read()
        return await upload_to_s3(content, key, content_type)


async def generate_presigned_url(
    key: str,
    expires_in: int = 3600
) -> str:
    """Generate presigned URL for temporary access"""
    
    try:
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.s3_bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        raise


async def delete_from_s3(key: str) -> bool:
    """Delete file from S3"""
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=key
            )
        )
        return True
    except ClientError as e:
        print(f"Error deleting from S3: {e}")
        return False


def generate_unique_key(prefix: str, extension: str) -> str:
    """Generate unique S3 key with timestamp"""
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}/{timestamp}_{unique_id}.{extension}"


async def create_bucket_if_not_exists():
    """Create S3 bucket if it doesn't exist"""
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3_client.head_bucket(Bucket=settings.s3_bucket_name)
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                await loop.run_in_executor(
                    None,
                    lambda: s3_client.create_bucket(
                        Bucket=settings.s3_bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': settings.aws_region
                        } if settings.aws_region != 'us-east-1' else {}
                    )
                )
                
                # Enable public access for CDN
                await loop.run_in_executor(
                    None,
                    lambda: s3_client.put_bucket_cors(
                        Bucket=settings.s3_bucket_name,
                        CORSConfiguration={
                            'CORSRules': [{
                                'AllowedHeaders': ['*'],
                                'AllowedMethods': ['GET', 'HEAD'],
                                'AllowedOrigins': ['*'],
                                'MaxAgeSeconds': 3000
                            }]
                        }
                    )
                )
                
                print(f"Created S3 bucket: {settings.s3_bucket_name}")
            except ClientError as create_error:
                print(f"Error creating bucket: {create_error}")
                raise


# Convenience functions for different content types
async def upload_image(image_data: bytes, format: str = "jpg") -> str:
    """Upload image to S3"""
    key = generate_unique_key("images", format)
    content_type = f"image/{format}"
    return await upload_to_s3(image_data, key, content_type)


async def upload_audio(audio_data: bytes, format: str = "mp3") -> str:
    """Upload audio to S3"""
    key = generate_unique_key("audio", format)
    content_type = f"audio/{format}"
    return await upload_to_s3(audio_data, key, content_type)


async def upload_video(video_data: bytes, format: str = "mp4") -> str:
    """Upload video to S3"""
    key = generate_unique_key("videos", format)
    content_type = f"video/{format}"
    return await upload_to_s3(video_data, key, content_type)


async def upload_json(data: dict, prefix: str = "data") -> str:
    """Upload JSON data to S3"""
    import json
    key = generate_unique_key(prefix, "json")
    content = json.dumps(data).encode('utf-8')
    return await upload_to_s3(content, key, "application/json")
import boto3
from django.conf import settings
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import uuid

class S3Uploader:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', None)
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def upload_file(self, file, folder='uploads'):
        """Upload file to S3 and return metadata including a presigned URL"""
        try:
            # Generate unique filename
            file_extension = file.name.split('.')[-1] if getattr(file, 'name', None) else 'bin'
            unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
            content_type = getattr(file, 'content_type', None) or 'application/octet-stream'
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                unique_filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'
                }
            )
            
            # Prefer a presigned URL for private objects
            presigned_url = self.generate_presigned_url(unique_filename)
            
            return {
                'success': True,
                'file_key': unique_filename,
                'url': presigned_url or f"https://{getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', self.bucket_name)}/{unique_filename}",
                'content_type': content_type
            }
        except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, file_key):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return {'success': True}
        except ClientError as e:
            return {'success': False, 'error': str(e)}
    
    def generate_presigned_url(self, file_key, expiration=3600):
        """Generate a presigned URL for private file access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except (ClientError, NoCredentialsError, PartialCredentialsError):
            return None
        
    def download_file_blob(self, file_key):
        """Download file from S3 and return its binary content"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            return response['Body'].read()
        except ClientError as e:
            return None
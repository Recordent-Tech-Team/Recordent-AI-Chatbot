import aioboto3

from app.core.config import settings
from app.core.logger import get_logger
from app.utils.aws_errors import to_aws_auth_app_exception

logger = get_logger("upload_service.py")


class S3UploadService:
    def __init__(self, aws_session: aioboto3.Session):
        self._session = aws_session

    async def upload_file(
        self,
        file_bytes: bytes,
        s3_key: str,
        content_type: str,
    ) -> str:
        bucket = settings.S3_BUCKET_NAME
        try:
            async with self._session.client(
                "s3",
                region_name=settings.AWS_REGION,
            ) as client:
                await client.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
        except Exception as error:
            logger.error(f"S3 upload failed: {error}")
            mapped_exception = to_aws_auth_app_exception(
                error,
                service_name="S3",
                operation="PutObject",
            )
            if mapped_exception:
                raise mapped_exception from error
            raise
        logger.info(f"Uploaded file to s3://{bucket}/{s3_key}")
        return s3_key

    def build_document_key(
        self,
        version_uuid: str,
        file_name: str,
    ) -> str:
        prefix = settings.S3_CHATBOT_DOCUMENT_PREFIX.rstrip("/")
        return f"{prefix}/{version_uuid}/{file_name}"

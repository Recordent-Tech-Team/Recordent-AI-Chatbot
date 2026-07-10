import aioboto3

from app.core.config import settings
from app.core.logger import get_logger
from app.utils.aws_errors import to_aws_auth_app_exception

logger = get_logger("archive_service.py")


class S3ArchiveService:
    def __init__(self, aws_session: aioboto3.Session):
        self._session = aws_session

    async def archive_objects(
        self,
        source_keys: list[str],
        version_uuid: str,
    ) -> list[str]:
        bucket = settings.S3_BUCKET_NAME
        archive_prefix = settings.S3_CHATBOT_ARCHIVE_PREFIX.rstrip("/")
        archived_keys: list[str] = []

        try:
            async with self._session.client(
                "s3",
                region_name=settings.AWS_REGION,
            ) as client:
                for source_key in source_keys:
                    file_name = source_key.split("/")[-1]
                    dest_key = f"{archive_prefix}/{version_uuid}/{file_name}"
                    await client.copy_object(
                        Bucket=bucket,
                        CopySource={"Bucket": bucket, "Key": source_key},
                        Key=dest_key,
                    )
                    archived_keys.append(dest_key)
                    logger.info(
                        f"Archived s3://{bucket}/{source_key} "
                        f"to s3://{bucket}/{dest_key}"
                    )
        except Exception as error:
            logger.error(f"S3 archive failed: {error}")
            mapped_exception = to_aws_auth_app_exception(
                error,
                service_name="S3",
                operation="CopyObject",
            )
            if mapped_exception:
                raise mapped_exception from error
            raise

        return archived_keys

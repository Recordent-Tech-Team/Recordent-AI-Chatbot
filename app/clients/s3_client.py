from app.clients.aws_session import get_aioboto3_session
from app.core.config import settings


def get_s3_client_context():
    session = get_aioboto3_session()
    return session.client("s3", region_name=settings.AWS_REGION)

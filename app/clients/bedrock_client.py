import aioboto3

from app.clients.aws_session import get_aioboto3_session


def get_aws_session() -> aioboto3.Session:
    return get_aioboto3_session()

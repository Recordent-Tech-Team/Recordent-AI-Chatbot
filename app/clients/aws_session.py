from functools import lru_cache

import aioboto3
import boto3

from app.core.config import settings


@lru_cache
def get_boto3_session() -> boto3.Session:
    if settings.AWS_PROFILE:
        return boto3.Session(
            profile_name=settings.AWS_PROFILE,
            region_name=settings.AWS_REGION,
        )
    # In ECS/production, rely on task role credentials.
    return boto3.Session(region_name=settings.AWS_REGION)


@lru_cache
def get_aioboto3_session() -> aioboto3.Session:
    if settings.AWS_PROFILE:
        return aioboto3.Session(
            profile_name=settings.AWS_PROFILE,
            region_name=settings.AWS_REGION,
        )
    # In ECS/production, rely on task role credentials.
    return aioboto3.Session(region_name=settings.AWS_REGION)


def get_aws_client_context(service_name: str):
    session = get_aioboto3_session()
    return session.client(service_name, region_name=settings.AWS_REGION)


def get_s3_client_context():
    return get_aws_client_context("s3")


def get_bedrock_runtime_client_context():
    return get_aws_client_context("bedrock-runtime")


def get_bedrock_agent_runtime_client_context():
    return get_aws_client_context("bedrock-agent-runtime")

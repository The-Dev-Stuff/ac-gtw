"""
s3_service.py
S3 operations for storing and retrieving OpenAPI specs.
"""
import os
import json
import time
import uuid
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def _ensure_s3_bucket(bucket_name: str = None) -> str:
    """
    Ensure an S3 bucket exists and return its name.

    Args:
        bucket_name: Optional explicit bucket name. If not provided, generates a default per-account name.

    Returns:
        The bucket name (either provided or generated)
    """
    session = boto3.Session(region_name=AWS_REGION)
    s3 = session.client("s3")
    sts = session.client("sts")

    if not bucket_name:
        account_id = sts.get_caller_identity()["Account"]
        bucket_name = f"agentcore-gateway-targets-openapi-specs-{account_id}-{AWS_REGION}"

    print(f"Ensuring S3 bucket exists: {bucket_name}")
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
        print("✓ Created S3 bucket.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print("✓ S3 bucket already exists.")
        else:
            raise

    return bucket_name


def upload_openapi_spec(spec_json: dict, tool_name: str, gateway_id: str, bucket_name: str = None) -> str:
    """
    Upload an OpenAPI spec provided as a Python dict (in-memory) to S3 and return an s3:// URI.

    Args:
        spec_json: OpenAPI spec as a Python dict
        tool_name: Logical name of the tool
        gateway_id: ID of the gateway this tool is being registered with
        bucket_name: Optional S3 bucket name; if omitted a default per-account bucket is used

    Returns:
        s3://bucket/key string
    """
    session = boto3.Session(region_name=AWS_REGION)
    s3 = session.client("s3")

    bucket_name = _ensure_s3_bucket(bucket_name)

    # Build hierarchical object key: gateways/{gateway_id}/tools/{tool_name}/{timestamp}-{uuid}.json
    # This allows:
    # - Easy listing of all tools for a gateway: s3://bucket/gateways/{gateway_id}/tools/
    # - Easy listing of all versions of a tool: s3://bucket/gateways/{gateway_id}/tools/{tool_name}/
    # - Simple cleanup policies per gateway or tool
    object_key = f"gateways/{gateway_id}/tools/{tool_name}/{int(time.time())}-{uuid.uuid4().hex}.json"
    body = json.dumps(spec_json).encode("utf-8")

    print(f"Uploading OpenAPI spec to S3: {object_key}")
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=body, ContentType="application/json")
    print("✓ OpenAPI spec uploaded.")

    s3_uri = f"s3://{bucket_name}/{object_key}"
    print(f"S3 URI: {s3_uri}")
    return s3_uri


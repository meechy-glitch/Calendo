import uuid
import os
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.database import get_db
from src.backend import schemas, crud, models
from src.backend.auth import get_current_user
from src.backend.config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
    R2_PUBLIC_BASE_URL,
)

router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
PRESIGN_EXPIRY = 300  # 5 minutes


def _ext_for(content_type: str) -> str:
    return {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


@router.post("/presign", response_model=schemas.PresignResponse)
def presign_upload(
    body: schemas.PresignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported file type. Use JPEG, PNG, or WebP.")
    if body.size_bytes > MAX_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="File exceeds 8 MB limit.")
    if body.size_bytes <= 0:
        raise HTTPException(status_code=422, detail="Invalid file size.")

    ext = _ext_for(body.content_type)
    key = f"users/{current_user.id}/media/{uuid.uuid4()}.{ext}"
    public_url = f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"

    asset = crud.create_media_asset(
        db,
        user_id=current_user.id,
        storage_key=key,
        public_url=public_url,
        original_filename=body.filename,
        mime_type=body.content_type,
        file_size_bytes=body.size_bytes,
    )

    try:
        client = _r2_client()
        upload_url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": R2_BUCKET,
                "Key": key,
                "ContentType": body.content_type,
            },
            ExpiresIn=PRESIGN_EXPIRY,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not generate upload URL: {exc}")

    return schemas.PresignResponse(
        upload_url=upload_url,
        media_asset_id=asset.id,
        storage_key=key,
        public_url=public_url,
        expires_in=PRESIGN_EXPIRY,
    )


@router.post("/confirm", response_model=schemas.MediaAssetResponse)
def confirm_upload(
    body: schemas.ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    asset = crud.get_media_asset(db, body.media_asset_id, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found.")

    try:
        client = _r2_client()
        client.head_object(Bucket=R2_BUCKET, Key=asset.storage_key)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            raise HTTPException(status_code=409, detail="Object not found in storage. Upload may have failed.")
        raise HTTPException(status_code=502, detail=f"Storage check failed: {exc}")

    updated = crud.set_media_asset_ready(db, body.media_asset_id, current_user.id)
    return updated

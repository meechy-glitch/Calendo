import json
import os
import subprocess
import tempfile
import uuid
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

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_TYPES = {"video/mp4", "video/quicktime"}
ALLOWED_TYPES = IMAGE_TYPES | VIDEO_TYPES

IMAGE_MAX_BYTES = 8 * 1024 * 1024   # 8 MB
VIDEO_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

PRESIGN_EXPIRY = 300  # 5 minutes

_EXT_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}

# Per-platform video spec table
# (max_bytes, allowed_mimes, min_duration_s, max_duration_s, target_aspect_w_h)
_PLATFORM_VIDEO_SPECS = {
    "x": {
        "max_bytes": 50 * 1024 * 1024,
        "mimes": {"video/mp4"},
        "min_duration": None,
        "max_duration": None,
        "aspect": None,
    },
    "linkedin": {
        "max_bytes": 200 * 1024 * 1024,
        "mimes": {"video/mp4"},
        "min_duration": 3,
        "max_duration": 600,
        "aspect": None,
    },
    "instagram": {
        "max_bytes": 100 * 1024 * 1024,
        "mimes": {"video/mp4"},
        "min_duration": 3,
        "max_duration": 90,
        "aspect": (9, 16),
    },
    "tiktok": {
        "max_bytes": None,
        "mimes": {"video/mp4", "video/quicktime"},
        "min_duration": None,
        "max_duration": None,
        "aspect": (9, 16),
    },
    "facebook": {
        # Facebook accepts large MP4 uploads (up to ~4 GB / 240 min for Pages);
        # use a generous cap so warnings only fire on clearly oversized files.
        "max_bytes": 1024 * 1024 * 1024,  # 1 GB
        "mimes": {"video/mp4", "video/quicktime"},
        "min_duration": None,
        "max_duration": None,
        "aspect": None,
    },
}

_PLATFORM_NAMES = {
    "x": "X",
    "linkedin": "LinkedIn",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "facebook": "Facebook",
}


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _video_spec_warnings(asset: models.MediaAsset) -> dict:
    if not asset.mime_type or asset.mime_type not in VIDEO_TYPES:
        return {}

    size_bytes = asset.file_size_bytes or 0
    duration = asset.duration_seconds
    w, h = asset.width or 0, asset.height or 0
    mime = asset.mime_type

    warnings: dict[str, list[str]] = {}
    for platform, spec in _PLATFORM_VIDEO_SPECS.items():
        label = _PLATFORM_NAMES[platform]
        w_list: list[str] = []

        if spec["max_bytes"] and size_bytes > spec["max_bytes"]:
            limit_mb = spec["max_bytes"] // (1024 * 1024)
            actual_mb = size_bytes / (1024 * 1024)
            w_list.append(f"Exceeds {label}'s {limit_mb} MB limit ({actual_mb:.1f} MB)")

        if mime not in spec["mimes"]:
            allowed = "/".join(m.split("/")[1].upper() for m in spec["mimes"])
            w_list.append(f"{label} requires {allowed} format")

        if duration is not None:
            if spec["min_duration"] and duration < spec["min_duration"]:
                w_list.append(f"{label} minimum video length is {spec['min_duration']}s")
            if spec["max_duration"] and duration > spec["max_duration"]:
                w_list.append(f"{label} maximum video length is {spec['max_duration']}s")

        if spec["aspect"] and w > 0 and h > 0:
            aw, ah = spec["aspect"]
            expected = aw / ah
            actual = w / h
            if abs(actual - expected) > 0.05:
                w_list.append(f"{label} recommends {aw}:{ah} vertical video (got {w}×{h})")

        warnings[platform] = w_list

    return warnings


def _process_video(asset: models.MediaAsset, client, db: Session) -> None:
    """Probe duration/dimensions and extract thumbnail via ffmpeg. Updates asset in-place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.bin")
        thumb_path = os.path.join(tmpdir, "thumb.jpg")

        try:
            obj = client.get_object(Bucket=R2_BUCKET, Key=asset.storage_key)
            with open(video_path, "wb") as f:
                f.write(obj["Body"].read())
        except Exception:
            return

        # Probe metadata
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", "-show_format", video_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            probe = json.loads(result.stdout)
            duration = float(probe.get("format", {}).get("duration", 0) or 0)
            if duration > 0:
                asset.duration_seconds = duration
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    asset.width = stream.get("width") or asset.width
                    asset.height = stream.get("height") or asset.height
                    break
        except Exception:
            pass

        # Extract thumbnail at ~1s (or start if shorter)
        try:
            offset = min(1.0, (asset.duration_seconds or 0) * 0.1)
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(offset), "-i", video_path,
                    "-vframes", "1", "-q:v", "2", thumb_path,
                ],
                capture_output=True,
                timeout=60,
            )
            if os.path.exists(thumb_path):
                thumb_key = f"users/{asset.user_id}/media/thumb_{uuid.uuid4()}.jpg"
                with open(thumb_path, "rb") as f:
                    client.put_object(
                        Bucket=R2_BUCKET,
                        Key=thumb_key,
                        Body=f.read(),
                        ContentType="image/jpeg",
                    )
                asset.thumbnail_key = thumb_key
        except Exception:
            pass


@router.post("/presign", response_model=schemas.PresignResponse)
def presign_upload(
    body: schemas.PresignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported file type. Use JPEG, PNG, WebP, MP4, or MOV.",
        )

    is_video = body.content_type in VIDEO_TYPES
    max_bytes = VIDEO_MAX_BYTES if is_video else IMAGE_MAX_BYTES
    if body.size_bytes > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"File exceeds {limit_mb} MB limit.")
    if body.size_bytes <= 0:
        raise HTTPException(status_code=422, detail="Invalid file size.")

    ext = _EXT_MAP[body.content_type]
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

    client = _r2_client()
    try:
        client.head_object(Bucket=R2_BUCKET, Key=asset.storage_key)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            raise HTTPException(
                status_code=409,
                detail="Object not found in storage. Upload may have failed.",
            )
        raise HTTPException(status_code=502, detail=f"Storage check failed: {exc}")

    is_video = asset.mime_type in VIDEO_TYPES
    if is_video:
        asset.status = "processing"
        db.commit()
        _process_video(asset, client, db)

    asset.status = "ready"
    db.commit()
    db.refresh(asset)

    response = schemas.MediaAssetResponse.model_validate(asset)
    if is_video:
        response.spec_warnings = _video_spec_warnings(asset)
    return response


@router.get("/{asset_id}", response_model=schemas.MediaAssetResponse)
def get_media_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    asset = crud.get_media_asset(db, asset_id, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found.")
    response = schemas.MediaAssetResponse.model_validate(asset)
    if asset.mime_type in VIDEO_TYPES:
        response.spec_warnings = _video_spec_warnings(asset)
    return response

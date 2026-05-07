import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.backend.database import get_db
from src.backend import schemas, crud, models
from src.backend.auth import get_current_user

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=list[schemas.PostResponse])
def list_posts(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_posts(db, current_user.id, month)


@router.post("", status_code=201, response_model=schemas.PostResponse)
def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_post(db, post, current_user.id)


# IMPORTANT: /export/csv must be registered before /{post_id} to avoid routing conflict
@router.get("/export/csv")
def export_csv(
    month: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    posts = crud.get_posts(db, current_user.id, month)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Caption", "Platform", "Scheduled Date", "Status"])
    for p in posts:
        writer.writerow(
            [
                p.title,
                p.caption or "",
                p.platform.value,
                str(p.scheduled_date),
                p.status.value,
            ]
        )
    output.seek(0)
    filename = f"calendo-posts-{month}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{post_id}", response_model=schemas.PostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = crud.get_post_by_id(db, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int,
    post_update: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.update_post(db, post_id, post_update, current_user.id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Post not found")
    if result == "forbidden":
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this post"
        )
    return result


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.delete_post(db, post_id, current_user.id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Post not found")
    if result == "forbidden":
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this post"
        )

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.backend.database import get_db
from src.backend import schemas, crud
from src.backend.auth import verify_password, create_access_token

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])



def _get_limit():
    if os.getenv("ENVIRONMENT") == "test":
        return "1000/minute"
    return "10/minute"

@router.post("/register", status_code=201, response_model=schemas.UserResponse)
@limiter.limit(_get_limit)
def register(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    if len(user.password) < 8:
        raise HTTPException(
            status_code=422, detail="Password must be at least 8 characters"
        )
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@router.post("/login", response_model=schemas.Token)
@limiter.limit(_get_limit)
def login(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_in = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
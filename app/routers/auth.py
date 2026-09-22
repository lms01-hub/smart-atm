from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.db.models import User


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


class LoginRequest(BaseModel):
    login_id: str
    password: str


@router.post("/login")
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.login_id == body.login_id
        )
    )

    if user is None:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "아이디 또는 비밀번호가 올바르지 않습니다.",
            },
        }

    if not verify_password(
        body.password,
        user.password_hash,
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "아이디 또는 비밀번호가 올바르지 않습니다.",
            },
        }

    access_token = create_access_token(user.id)

    return {
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "login_id": user.login_id,
                "name": user.name,
                "profile_image": user.profile_image,
            },
            "access_token": access_token,
            "token_type": "bearer",
        },
    }

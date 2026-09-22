from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.db.models import User


router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": {
            "user": {
                "id": current_user.id,
                "login_id": current_user.login_id,
                "name": current_user.name,
                "profile_image": current_user.profile_image,
            }
        },
    }

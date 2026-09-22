from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Friendship, User


router = APIRouter(
    prefix="/api/v1/friends",
    tags=["friends"],
)


@router.get("")
def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.scalars(
        select(Friendship).where(
            or_(
                Friendship.user_id == current_user.id,
                Friendship.friend_id == current_user.id,
            )
        )
    ).all()

    friends = []

    for friendship in friendships:
        if friendship.user_id == current_user.id:
            friend_id = friendship.friend_id
        else:
            friend_id = friendship.user_id

        friend = db.scalar(
            select(User).where(User.id == friend_id)
        )

        if friend is not None:
            friends.append({
                "id": friend.id,
                "login_id": friend.login_id,
                "name": friend.name,
                "profile_image": friend.profile_image,
                "introduce": friend.introduce,
            })

    return {
        "success": True,
        "data": {
            "friends": friends
        },
    }

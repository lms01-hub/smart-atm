from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import (
    ChatRoomMember,
    Message,
    User,
)


router = APIRouter(
    prefix="/api/v1/chats",
    tags=["chats"],
)


class MessageCreate(BaseModel):
    content: str


def check_membership(
    chat_id: int,
    user_id: int,
    db: Session,
):
    return db.scalar(
        select(ChatRoomMember).where(
            ChatRoomMember.chat_room_id == chat_id,
            ChatRoomMember.user_id == user_id,
        )
    )


def get_chat_friend(
    chat_id: int,
    current_user_id: int,
    db: Session,
):
    friend_member = db.scalar(
        select(ChatRoomMember).where(
            ChatRoomMember.chat_room_id == chat_id,
            ChatRoomMember.user_id != current_user_id,
        )
    )

    if friend_member is None:
        return None

    return db.scalar(
        select(User).where(
            User.id == friend_member.user_id
        )
    )


@router.get("")
def get_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.scalars(
        select(ChatRoomMember).where(
            ChatRoomMember.user_id == current_user.id
        )
    ).all()

    chats = []

    for membership in memberships:
        chat_id = membership.chat_room_id

        friend = get_chat_friend(
            chat_id,
            current_user.id,
            db,
        )

        last_message = db.scalar(
            select(Message)
            .where(
                Message.chat_room_id == chat_id
            )
            .order_by(Message.sent_at.desc(), Message.id.desc())
            .limit(1)
        )

        chats.append(
            {
                "id": chat_id,
                "friend": (
                    {
                        "id": friend.id,
                        "name": friend.name,
                        "profile_image": friend.profile_image,
                    }
                    if friend
                    else None
                ),
                "last_message": (
                    last_message.content
                    if last_message
                    else None
                ),
                "last_message_at": (
                    last_message.sent_at.isoformat()
                    if last_message
                    else None
                ),
                "unread_count": 0,
            }
        )

    chats.sort(
        key=lambda chat: (
            chat["last_message_at"] or ""
        ),
        reverse=True,
    )

    return {
        "success": True,
        "data": {
            "chats": chats
        },
    }


@router.get("/{chat_id}/messages")
def get_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = check_membership(
        chat_id,
        current_user.id,
        db,
    )

    if membership is None:
        raise HTTPException(
            status_code=404,
            detail="채팅방을 찾을 수 없습니다.",
        )

    friend = get_chat_friend(
        chat_id,
        current_user.id,
        db,
    )

    messages = db.scalars(
        select(Message)
        .where(
            Message.chat_room_id == chat_id
        )
        .order_by(Message.sent_at.asc(), Message.id.asc())
    ).all()

    return {
        "success": True,
        "data": {
            "chat": {
                "id": chat_id,
                "friend": (
                    {
                        "id": friend.id,
                        "name": friend.name,
                        "profile_image": friend.profile_image,
                    }
                    if friend
                    else None
                ),
            },
            "messages": [
                {
                    "id": message.id,
                    "chat_id": message.chat_room_id,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "sent_at": message.sent_at.isoformat(),
                }
                for message in messages
            ],
        },
    }


@router.post(
    "/{chat_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    chat_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = check_membership(
        chat_id,
        current_user.id,
        db,
    )

    if membership is None:
        raise HTTPException(
            status_code=404,
            detail="채팅방을 찾을 수 없습니다.",
        )

    content = body.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="메시지 내용을 입력해주세요.",
        )

    message = Message(
        chat_room_id=chat_id,
        sender_id=current_user.id,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "success": True,
        "data": {
            "message": {
                "id": message.id,
                "chat_id": message.chat_room_id,
                "sender_id": message.sender_id,
                "content": message.content,
                "sent_at": message.sent_at.isoformat(),
            }
        },
    }


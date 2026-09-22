from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import (
    AnalysisResult,
    ChatRoomMember,
    Message,
    User,
)
from app.services.ai_service import analyze_phishing_messages


router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["analysis"],
)


@router.post("/chats/{chat_id}")
def analyze_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = db.scalar(
        select(ChatRoomMember)
        .where(
            ChatRoomMember.chat_room_id == chat_id,
            ChatRoomMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=404,
            detail="채팅방을 찾을 수 없습니다.",
        )

    message_rows = db.scalars(
        select(Message)
        .where(
            Message.chat_room_id == chat_id
        )
        .order_by(Message.sent_at.asc())
    ).all()

    if not message_rows:
        raise HTTPException(
            status_code=400,
            detail="분석할 메시지가 없습니다.",
        )

    message_contents = [
        message.content
        for message in message_rows
    ]

    result = analyze_phishing_messages(
        message_contents
    )

    analysis = AnalysisResult(
        chat_room_id=chat_id,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        reasons=result["reasons"],
        summary=result["summary"],
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    session_id = f"VP-{analysis.id:06d}"

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "analysis_id": analysis.id,
            "chat_id": chat_id,
            "risk_level": analysis.risk_level,
            "risk_score": analysis.risk_score,
            "reasons": analysis.reasons,
            "summary": analysis.summary,
            "analyzed_at": analysis.analyzed_at.isoformat(),
        },
    }


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.scalar(
        select(AnalysisResult)
        .where(
            AnalysisResult.id == analysis_id
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다.",
        )

    membership = db.scalar(
        select(ChatRoomMember)
        .where(
            ChatRoomMember.chat_room_id == analysis.chat_room_id,
            ChatRoomMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="해당 분석 결과에 접근할 수 없습니다.",
        )

    return {
        "success": True,
        "data": {
            "analysis_id": analysis.id,
            "chat_id": analysis.chat_room_id,
            "risk_level": analysis.risk_level,
            "risk_score": analysis.risk_score,
            "reasons": analysis.reasons,
            "summary": analysis.summary,
            "analyzed_at": analysis.analyzed_at.isoformat(),
        },
    }


@router.get("/{analysis_id}/atm")
def get_atm_data(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.scalar(
        select(AnalysisResult)
        .where(
            AnalysisResult.id == analysis_id
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다.",
        )

    membership = db.scalar(
        select(ChatRoomMember)
        .where(
            ChatRoomMember.chat_room_id == analysis.chat_room_id,
            ChatRoomMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="해당 분석 결과에 접근할 수 없습니다.",
        )

    session_id = f"VP-{analysis.id:06d}"

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "analysis_id": analysis.id,
            "risk_level": analysis.risk_level,
            "risk_score": analysis.risk_score,
            "summary": analysis.summary,
            "detected_at": analysis.analyzed_at.isoformat(),
        },
    }

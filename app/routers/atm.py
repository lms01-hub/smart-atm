from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AnalysisResult


router = APIRouter(
    prefix="/api/v1/atm",
    tags=["atm"],
)


@router.get("/verify/{session_id}")
def verify_atm_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    if not session_id.startswith("VP-"):
        raise HTTPException(
            status_code=400,
            detail="잘못된 ATM 세션입니다.",
        )

    try:
        analysis_id = int(session_id[3:])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="잘못된 ATM 세션입니다.",
        )

    analysis = db.scalar(
        select(AnalysisResult).where(
            AnalysisResult.id == analysis_id
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="ATM 세션을 찾을 수 없습니다.",
        )

    if analysis.risk_level == "DANGER":
        atm_action = "BLOCK"

    elif analysis.risk_level == "CAUTION":
        atm_action = "VERIFY"

    else:
        atm_action = "ALLOW"

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "risk_level": analysis.risk_level,
            "risk_score": analysis.risk_score,
            "atm_action": atm_action,
            "summary": analysis.summary,
        },
    }

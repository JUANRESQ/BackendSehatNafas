from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Analysis  # pastikan model ini ada
from app.deps import get_current_user  # kalau kamu pakai auth (opsional)

router = APIRouter(prefix="/analysis", tags=["analysis"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/history")
def history(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),  # hapus ini kalau belum pakai auth
):
    rows = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)   # sesuaikan field
        .order_by(Analysis.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "label": r.label,
            "confidence": float(r.confidence),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/save")
def save_analysis(
    label: str = Form(...),
    confidence: float = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),  # hapus ini kalau belum pakai auth
):
    row = Analysis(
        user_id=user.id,   # sesuaikan field
        label=label,
        confidence=confidence,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}

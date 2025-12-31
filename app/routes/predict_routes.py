# Backend/app/routes/predict_routes.py
import os
import io
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

import numpy as np
import tensorflow as tf
import librosa

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app import models

router = APIRouter(prefix="/analysis", tags=["analysis"])

MODEL: Optional[tf.keras.Model] = None

def _project_root() -> Path:
    # file ini: Backend/app/routes/predict_routes.py
    # root backend: Backend/
    return Path(__file__).resolve().parents[2]  # .../Backend

def load_model_once() -> tf.keras.Model:
    global MODEL
    if MODEL is not None:
        return MODEL

    # 1) kalau kamu set ENV: MODEL_PATH, itu dipakai dulu
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        model_path = Path(env_path).expanduser().resolve()
    else:
        # 2) default: Backend/app/model/model_batuk.h5
        model_path = (_project_root() / "app" / "model" / "model_batuk.h5").resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model tidak ditemukan di: {model_path}")

    MODEL = tf.keras.models.load_model(str(model_path), compile=False)
    return MODEL

def resize_2d_linear(a: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    in_h, in_w = a.shape
    x_old = np.linspace(0, 1, in_w)
    x_new = np.linspace(0, 1, out_w)

    tmp = np.zeros((in_h, out_w), dtype=np.float32)
    for i in range(in_h):
        tmp[i, :] = np.interp(x_new, x_old, a[i, :]).astype(np.float32)

    y_old = np.linspace(0, 1, in_h)
    y_new = np.linspace(0, 1, out_h)

    out = np.zeros((out_h, out_w), dtype=np.float32)
    for j in range(out_w):
        out[:, j] = np.interp(y_new, y_old, tmp[:, j]).astype(np.float32)

    return out

def wav_bytes_to_model_input(wav_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    # load wav
    y, sr = librosa.load(io.BytesIO(wav_bytes), sr=target_sr, mono=True)

    # minimal 1 detik
    min_len = target_sr
    if len(y) < min_len:
        y = np.pad(y, (0, min_len - len(y)), mode="constant")

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=target_sr,
        n_fft=1024,
        hop_length=256,
        n_mels=128,
        power=2.0,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max).astype(np.float32)

    # normalize 0..1
    log_mel = log_mel - float(log_mel.min())
    log_mel = log_mel / (float(log_mel.max()) + 1e-8)

    # resize (128,128)
    log_mel_128 = resize_2d_linear(log_mel, 128, 128)

    # (1,128,128,1)
    x = log_mel_128[np.newaxis, :, :, np.newaxis].astype(np.float32)
    return x

def infer_label_conf(model: tf.keras.Model, x: np.ndarray) -> Tuple[str, float]:
    pred = model.predict(x, verbose=0)
    pred = np.array(pred)

    # multiclass softmax (1,N)
    if pred.ndim == 2 and pred.shape[1] >= 2:
        idx = int(np.argmax(pred[0]))
        conf = float(pred[0, idx])

        # SESUAIKAN label sesuai training kamu
        labels = ["Basah", "Kering", "Non"]
        label = labels[idx] if idx < len(labels) else f"class_{idx}"
        return label, conf

    # binary sigmoid (1,1)
    if pred.ndim == 2 and pred.shape[1] == 1:
        p = float(pred[0, 0])
        label = "Batuk" if p >= 0.5 else "Non"
        conf = p if p >= 0.5 else (1.0 - p)
        return label, conf

    return "Unknown", 0.0

@router.post("/predict")
async def predict_and_optional_save(
    file: UploadFile = File(...),
    save_history: bool = Form(True),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        model = load_model_once()

        wav_bytes = await file.read()
        if not wav_bytes:
            raise HTTPException(status_code=400, detail="File kosong")

        x = wav_bytes_to_model_input(wav_bytes, target_sr=16000)
        label, confidence = infer_label_conf(model, x)
        confidence = round(float(confidence), 6)

        if save_history:
            row = models.Analysis(
                user_id=user.id,
                label=label,
                confidence=confidence,
            )
            db.add(row)
            db.commit()

        return {
            "label": label,
            "confidence": confidence,
            "saved": bool(save_history),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Predict error: {repr(e)}")

@router.get("/history")
def history(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == user.id)
        .order_by(models.Analysis.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "label": r.label,
            "confidence": float(r.confidence),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

@router.post("/save")
def save_manual(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    label = str(payload.get("label", "-"))
    confidence = float(payload.get("confidence", 0.0))
    save_history = bool(payload.get("save_history", True))

    if not save_history:
        return {"label": label, "confidence": confidence, "saved": False}

    row = models.Analysis(
        user_id=user.id,
        label=label,
        confidence=round(confidence, 6),
    )
    db.add(row)
    db.commit()

    return {"label": row.label, "confidence": float(row.confidence), "saved": True}

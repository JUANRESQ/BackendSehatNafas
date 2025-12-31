from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app import schemas, models
from app.deps import get_db
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=schemas.RegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):

    # bcrypt limit 72 bytes
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password maksimal 72 karakter")

    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email sudah dipakai")

    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username sudah dipakai")

    user = models.User(
        nama=payload.nama,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Registrasi berhasil",
        "data": user
    }


@router.post(
    "/login",
    response_model=schemas.LoginResponse,
    status_code=status.HTTP_200_OK
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # cari user by username
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    # ✅ kalau username tidak ditemukan
    if not user:
        # response FastAPI default: {"detail":"..."}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Akun tidak ditemukan"
        )

    # ✅ kalau password salah
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password salah"
        )

    # ✅ sukses
    token = create_access_token({"sub": str(user.id)})

    return {
        "success": True,
        "message": "Login berhasil",
        "data": {
            "access_token": token,
            "token_type": "bearer"
        }
    }

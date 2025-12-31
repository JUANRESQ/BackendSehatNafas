from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
  raise RuntimeError(f"ENV DB belum lengkap. "
                     f"DB_HOST={DB_HOST} DB_PORT={DB_PORT} DB_NAME={DB_NAME} DB_USER={DB_USER} DB_PASS={'SET' if DB_PASS else None}")

# URL-encode password (penting kalau ada karakter spesial)
DB_PASS_ENC = quote_plus(DB_PASS)

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS_ENC}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Kalau Railway kamu REQUIRE SSL, aktifkan block ini:
CONNECT_ARGS = {}
# CONNECT_ARGS = {"ssl": {"ssl_mode": "REQUIRED"}}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=CONNECT_ARGS,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ✅ ini yang kamu butuh biar predict_routes bisa import get_db
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

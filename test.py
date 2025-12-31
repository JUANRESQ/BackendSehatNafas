from sqlalchemy import text
from app.db import engine

with engine.connect() as conn:
    print(conn.execute(text("SELECT 1")).all())
    print("✅ DB CONNECTED")

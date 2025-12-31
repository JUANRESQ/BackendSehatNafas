import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.db import Base, engine
from app import models  # supaya SQLAlchemy load model

from app.routes.auth_routes import router as auth_router
from app.routes.analysis_routes import router as analysis_router
from app.routes.predict_routes import router as predict_router

app = FastAPI(title="SehatNafas API")

# =========================
# GLOBAL ERROR HANDLER
# Semua error jadi: {success:false, message:"...", data:null}
# =========================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "Terjadi kesalahan"
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": msg, "data": None},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Defaultnya 422 punya detail ARRAY, kita ubah jadi string enak dibaca
    errors = exc.errors()
    parts = []
    for e in errors:
        loc = [str(x) for x in e.get("loc", []) if x not in ("body", "query", "path")]
        field = loc[-1] if loc else "input"
        msg = e.get("msg", "Input tidak valid")
        parts.append(f"{field}: {msg}")

    message = " | ".join(parts) if parts else "Input tidak valid"

    return JSONResponse(
        status_code=422,
        content={"success": False, "message": message, "data": None},
    )

# (opsional) supaya error tak terduga juga rapi (tanpa array)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Server error, coba lagi nanti", "data": None},
    )

# create table (aman untuk project kecil)
Base.metadata.create_all(bind=engine)

# register routers
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(predict_router)

@app.get("/")
def root():
    return {"success": True, "message": "OK", "data": {"status": "ok"}}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)

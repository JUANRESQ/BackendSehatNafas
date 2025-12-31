import os
from fastapi import FastAPI

from app.db import Base, engine
from app import models  # supaya SQLAlchemy load model

from app.routes.auth_routes import router as auth_router
from app.routes.analysis_routes import router as analysis_router
from app.routes.predict_routes import router as predict_router

app = FastAPI(title="SehatNafas API")

# create table (aman untuk project kecil)
Base.metadata.create_all(bind=engine)

# register routers
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(predict_router)

@app.get("/")
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port
    )

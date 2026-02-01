from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fastapi import Request

from app.db import engine
from app.models import Base
from app.routes import router

app = FastAPI(title="DnD TG WebApp")

#@app.on_event("startup")
#async def on_startup():
#    async with engine.begin() as conn:
#        await conn.run_sync(Base.metadata.create_all)
from datetime import datetime

@app.get("/api/version")
def version():
    return {"deployed_at": datetime.utcnow().isoformat() + "Z"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.head("/")
def root_head():
    return {}

@app.get("/")
def root():
    return RedirectResponse(url="/webapp/")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(router, prefix="/api")

# Раздаём webapp (папка рядом с backend/)
app.mount("/webapp", StaticFiles(directory="../webapp", html=True), name="webapp")

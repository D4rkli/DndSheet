from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.responses import Response

from app.db import init_db
from app.routes import router
from app.auth_routes import router as auth_router
from app.campaign_routes import router as campaign_router

app = FastAPI(title="DnD TG WebApp")
from fastapi.middleware.cors import CORSMiddleware



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://d4rkli.ru",
        "https://www.d4rkli.ru",
        "https://web.telegram.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from datetime import datetime

@app.on_event("startup")
async def on_startup():
    await init_db()

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
app.include_router(auth_router, prefix="/api/auth")
app.include_router(campaign_router, prefix="/api/campaigns")

# Раздаём webapp (папка рядом с backend/)
app.mount("/webapp", StaticFiles(directory="../webapp", html=True), name="webapp")

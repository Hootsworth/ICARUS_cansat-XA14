"""
Main FastAPI Application Entry Point for RVSAT-1 Telemetry Challenge.
"""
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from config import MASTER_SECRET, BASE_DIR
from models import init_db
from app.routes_pages import pages_router
from app.routes_api import api_router
from app.routes_round1 import router as round1_router
from app.routes_round2 import router as round2_router
from app.routes_round3 import router as round3_router
from app.routes_competition import router as competition_router

app = FastAPI(
    title="RVSAT-1 Satellite Telemetry Challenge",
    description="Live Ground Segment & Telemetry Analysis Flight Operations System",
    version="1.0.0"
)

# Add Session Middleware for cookie authentication
app.add_middleware(SessionMiddleware, secret_key=MASTER_SECRET, session_cookie="rvsat_session")

# Mount Static Files (CSS, JS, SVG assets)
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include Routers
app.include_router(pages_router)
app.include_router(api_router)
app.include_router(round1_router)
app.include_router(round2_router)
app.include_router(round3_router)
app.include_router(competition_router)

@app.on_event("startup")
async def on_startup():
    print("[*] Initializing Satellite Telemetry Database & Flight Operations Engine...")
    init_db()
    print("[✓] RVSAT-1 Mission Control Flight Server Ready.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

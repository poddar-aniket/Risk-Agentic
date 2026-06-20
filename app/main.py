"""
FastAPI app entrypoint. Wires together routes, CORS, and DB table creation.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as queue_router
from app.db.session import Base, engine
from app.models import supplier, inventory, decision, approval_queue, event  # noqa: F401 — registers tables

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RiskRadar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queue_router)
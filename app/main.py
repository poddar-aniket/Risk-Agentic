"""
FastAPI app entrypoint. Wires together routes, CORS, and DB table creation.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as queue_router
from app.db.session import Base, engine
from app.models import supplier, inventory, decision, approval_queue, event  # noqa: F401 — registers tables
from app.orchestration.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: runs once per real worker process, NOT in uvicorn --reload's
    # separate file-watcher process -- unlike a bare module-level call,
    # which was firing twice (once per process) before this fix.
    start_scheduler()
    yield
    # Shutdown: nothing to clean up yet. If start_scheduler() is ever
    # changed to return the BackgroundScheduler instance for real use
    # (it already does, just unused here), scheduler.shutdown() would
    # go here.


app = FastAPI(title="RiskRadar API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(queue_router)
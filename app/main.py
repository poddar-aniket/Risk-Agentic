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
    import os
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        start_scheduler()
    else:
        import logging
        logging.getLogger(__name__).info(
            "Scheduler disabled — use POST /pipeline/run to trigger manually."
        )
    yield


app = FastAPI(title="RiskRadar API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(queue_router)
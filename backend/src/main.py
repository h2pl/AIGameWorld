"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load config, init world state (future)
    yield
    # Shutdown: persist world state (future)


app = FastAPI(
    title="SimGameWorld API",
    description="DM-driven DND world simulation",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "simgameworld-backend"}

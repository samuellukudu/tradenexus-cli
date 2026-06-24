"""
FastAPI application factory for the TradeNexus API.

Port of the Express server (server/index.ts) to FastAPI.
Wraps the existing tradenexus.core and tradenexus.agent modules.

Usage:
    uvicorn tradenexus.api.app:app --host 0.0.0.0 --port 3000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tradenexus.api.routers.health import router as health_router
from tradenexus.api.routers.ai import router as ai_router
from tradenexus.api.routers.agent import router as agent_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    yield
    # shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="TradeNexus AI Sales Agent API",
        description="Autonomous AI sales agent for international B2B trade — FastAPI port",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — mirrors the Express setup (no restrictive CORS in the original)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # 25 MB JSON body limit (mirrors express.json({ limit: "25mb" }))
    # FastAPI/Starlette doesn't have a built-in size limit, so we add
    # a small middleware to guard.
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def enforce_body_limit(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 25 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large (max 25 MB)"},
            )
        return await call_next(request)

    # ------------------------------------------------------------------
    # global error handler (mirrors Express fallback error handler)
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def global_error_handler(_request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )

    # mount routers
    app.include_router(health_router)
    app.include_router(ai_router)
    app.include_router(agent_router)

    return app


app = create_app()

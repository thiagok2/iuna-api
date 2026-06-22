from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.endpoints import router as api_router
from app.api.middleware import RequestIdMiddleware
from app.api.routers.health import router as health_router
from app.clients.es_client import es_client
from app.config import settings
from app.core.exceptions import IunaBaseError


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await es_client.connect()
    yield
    # Shutdown
    await es_client.close()


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: X-Request-Id
# ---------------------------------------------------------------------------

app.add_middleware(RequestIdMiddleware)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(IunaBaseError)
async def iuna_base_error_handler(request: Request, exc: IunaBaseError):
    """Handle all IunaBaseError subclasses with a consistent JSON response."""
    request_id = getattr(request.state, "request_id", None)
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "request_id": request_id,
        },
    )
    if request_id:
        response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unexpected exceptions — always returns 500."""
    request_id = getattr(request.state, "request_id", None)
    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "request_id": request_id,
        },
    )
    if request_id:
        response.headers["X-Request-Id"] = request_id
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "docs_url": "/docs",
    }


# Include existing API endpoints under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include health router under /api/v1
app.include_router(health_router, prefix=settings.API_V1_STR)

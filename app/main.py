from fastapi import FastAPI
from app.config import settings
from app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "docs_url": "/docs"
    }

# Include API endpoints under /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

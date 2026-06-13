from fastapi import APIRouter

router = APIRouter()

@router.get("/health-check")
def health_check():
    return {"status": "ok", "message": "IUNA API is running smoothly"}

@router.get("/info")
def get_info():
    return {
        "name": "IUNA API",
        "description": "API do projeto IUNA - IFAL",
        "version": "0.1.0"
    }

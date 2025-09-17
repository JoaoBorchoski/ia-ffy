from fastapi import APIRouter, Depends
from src.models.models import HealthResponse
from src.db.database import db_manager
from src.dependencies import check_database_connection
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=dict)
async def root():
    return {
        "message": "Carga AI Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    database_connected = db_manager.pool is not None

    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        message="API funcionando" if database_connected else "Banco desconectado",
        database_connected=database_connected,
        timestamp=datetime.now()
    )

from fastapi import APIRouter, HTTPException, Depends
from src.db.database import db_manager
from src.dependencies import check_database_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cargas/{owner_id}", response_model=dict)
async def list_cargas(owner_id: str, _: None = Depends(check_database_connection)):
    try:
        cargas = await db_manager.get_all_cargas_by_owner(owner_id)

        return {
            "owner_id": owner_id,
            "total_cargas": len(cargas),
            "cargas": cargas
        }

    except Exception as e:
        logger.error(f"Erro ao listar cargas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar cargas: {str(e)}"
        )

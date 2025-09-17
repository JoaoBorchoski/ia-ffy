from fastapi import APIRouter, HTTPException, Depends
from src.ai_agent.ai_agent import ai_agent
from src.dependencies import check_database_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/memory/{owner_id}", response_model=dict)
async def get_user_memory(owner_id: str, user_id: str = None, _: None = Depends(check_database_connection)):
    try:
        memory_info = ai_agent.get_user_memory_info(owner_id, user_id)
        return {
            "owner_id": owner_id,
            "user_id": user_id,
            "memory_info": memory_info
        }
    except Exception as e:
        logger.error(f"Erro ao obter memória do usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter memória: {str(e)}"
        )


@router.delete("/memory/{owner_id}", response_model=dict)
async def clear_user_memory(owner_id: str, user_id: str = None, _: None = Depends(check_database_connection)):
    try:
        success = ai_agent.clear_user_memory(owner_id, user_id)
        return {
            "owner_id": owner_id,
            "user_id": user_id,
            "cleared": success,
            "message": "Memória limpa com sucesso" if success else "Usuário não tinha memória"
        }
    except Exception as e:
        logger.error(f"Erro ao limpar memória do usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao limpar memória: {str(e)}"
        )


@router.get("/memory", response_model=dict)
async def get_all_memories(_: None = Depends(check_database_connection)):
    try:
        memories_info = ai_agent.get_all_memories_info()
        return memories_info
    except Exception as e:
        logger.error(f"Erro ao obter informações das memórias: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter memórias: {str(e)}"
        )


@router.get("/redis/info", response_model=dict)
async def get_redis_info(_: None = Depends(check_database_connection)):
    try:
        redis_info = ai_agent.get_redis_info()
        return redis_info
    except Exception as e:
        logger.error(f"Erro ao obter informações do Redis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter informações do Redis: {str(e)}"
        )

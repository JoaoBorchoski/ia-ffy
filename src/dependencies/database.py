from fastapi import HTTPException, Depends
from src.db.database import db_manager


async def check_database_connection():
    if not db_manager.pool:
        raise HTTPException(
            status_code=503,
            detail="Banco de dados não conectado"
        )

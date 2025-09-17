from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.db.database import db_manager
from src.api.routers import main_router, cargas_router, memory_router, health_router
from src.middleware import global_exception_handler
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicação...")
    try:
        await db_manager.connect()
        logger.info("Aplicação iniciada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao iniciar aplicação: {e}")
        raise

    yield

    logger.info("Encerrando aplicação...")
    try:
        await db_manager.disconnect()
        logger.info("Aplicação encerrada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao encerrar aplicação: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Carga AI Agent API",
        description="API com agente de IA para consulta de dados de cargas",
        version="1.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(Exception, global_exception_handler)

    app.include_router(health_router)
    app.include_router(main_router)
    app.include_router(cargas_router)
    app.include_router(memory_router)

    return app


app = create_app()

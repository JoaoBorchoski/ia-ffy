import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from src.models.models import AskRequest, AskResponse, HealthResponse, CargaInfo
from src.db.database import db_manager
from src.ai_agent.ai_agent import ai_agent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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


async def check_database_connection():
    if not db_manager.pool:
        raise HTTPException(
            status_code=503,
            detail="Banco de dados não conectado"
        )


@app.get("/", response_model=dict)
async def root():
    return {
        "message": "Carga AI Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    database_connected = db_manager.pool is not None

    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        message="API funcionando" if database_connected else "Banco desconectado",
        database_connected=database_connected,
        timestamp=datetime.now()
    )


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, _: None = Depends(check_database_connection)):
    try:
        logger.info(
            f"Pergunta recebida: '{request.question}' para owner_id: {request.owner_id}")

        if not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Pergunta não pode estar vazia"
            )

        if not request.owner_id.strip():
            raise HTTPException(
                status_code=400,
                detail="owner_id é obrigatório"
            )

        result = await ai_agent.process_question(
            request.question.strip(),
            request.owner_id.strip()
        )

        if not result["success"]:
            logger.error(f"Erro no processamento: {result['response']}")
            raise HTTPException(
                status_code=500,
                detail=result["response"]
            )

        cargas = []
        if result.get("raw_data"):
            for item in result["raw_data"]:
                carga = CargaInfo(**item)
                cargas.append(carga)

        response = AskResponse(
            success=True,
            question=request.question,
            owner_id=request.owner_id,
            response=result["response"],
            data_count=result["data_count"],
            analysis=result.get("analysis"),
            cargas=cargas
        )

        logger.info(
            f"Resposta gerada com {result['data_count']} cargas encontradas")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado no endpoint /ask: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {str(e)}"
        )


@app.get("/cargas/{owner_id}", response_model=dict)
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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Exceção não tratada: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "message": str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Iniciando servidor em {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

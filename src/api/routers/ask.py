from fastapi import APIRouter, HTTPException, Depends
from src.models.models import AskRequest, AskResponse, CargaInfo
from src.ai_agent.ai_agent import ai_agent
from src.dependencies import check_database_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
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

        if not request.user_id.strip():
            raise HTTPException(
                status_code=400,
                detail="user_id é obrigatório"
            )

        result = await ai_agent.process_question(
            request.question.strip(),
            request.owner_id.strip(),
            request.user_id.strip()
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

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class AskRequest(BaseModel):
    question: str = Field(..., description="Pergunta sobre as cargas")
    owner_id: str = Field(..., description="ID do proprietário das cargas")
    user_id: Optional[str] = Field(
        None, description="ID do usuário (não utilizado no momento)")


class CargaInfo(BaseModel):
    oferta_id: Optional[str] = None
    codigo: Optional[str] = None
    nome_empresa_remetente: Optional[str] = None
    endereco_remetente: Optional[str] = None
    cidade_remetente: Optional[str] = None
    estado_remetente: Optional[str] = None
    nome_empresa_destinatario: Optional[str] = None
    endereco_destinatario: Optional[str] = None
    cidade_destinatario: Optional[str] = None
    estado_destinatario: Optional[str] = None
    status: Optional[str] = None
    pedido_embarcador: Optional[str] = None
    data_criacao_carga: Optional[datetime] = None
    numero_documento: Optional[str] = None
    chave_documento: Optional[str] = None
    serie: Optional[str] = None
    tipo_documento: Optional[str] = None
    data_emissao: Optional[date] = None
    nome_owner: Optional[str] = None
    documento_owner: Optional[str] = None
    email_owner: Optional[str] = None


class AskResponse(BaseModel):
    success: bool
    question: str
    owner_id: str
    response: str
    data_count: int
    analysis: Optional[Dict[str, Any]] = None
    cargas: Optional[List[CargaInfo]] = None


class HealthResponse(BaseModel):
    status: str
    message: str
    database_connected: bool
    timestamp: datetime

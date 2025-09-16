import os
import asyncpg
from typing import Optional, List, Dict, Any
import logging
from dotenv import load_dotenv
import re

load_dotenv()

logger = logging.getLogger(__name__)


def convert_jdbc_to_postgresql_url(jdbc_url: str) -> str:
    if jdbc_url.startswith('jdbc:postgresql://'):
        return jdbc_url.replace('jdbc:postgresql://', 'postgresql://')
    return jdbc_url


class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        try:
            DATABASE_URL = os.getenv(
                "DATABASE_URL",
                "postgresql://username:password@localhost:5432/database_name"
            )

            DATABASE_URL = convert_jdbc_to_postgresql_url(DATABASE_URL)
            logger.info(f"Conectando ao banco com URL: {DATABASE_URL}")

            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Conexão com banco PostgreSQL estabelecida")

        except Exception as e:
            logger.error(f"Erro ao conectar com o banco: {e}")
            raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Conexão com banco fechada")

    async def search_carga_by_identifier(self, identifier: str, owner_id: str) -> List[Dict[str, Any]]:
        if not self.pool:
            raise Exception("Banco não conectado")

        query = """
        SELECT DISTINCT
            oc.id::text as oferta_id,
            oc.codigo,
            oc.nome_empresa_remetente,
            oc.endereco_remetente,
            oc.cidade_remetente,
            oc.estado_remetente,
            oc.nome_empresa_destinatario,
            oc.endereco_destinatario,
            oc.cidade_destinatario,
            oc.estado_destinatario,
            oc.status,
            oc.pedido_embarcador,
            oc.data_criacao as data_criacao_carga,
            cd.numero as numero_documento,
            cd.chave as chave_documento,
            cd.serie,
            cd.tipo_documento,
            cd.data_emissao,
            o.nome as nome_owner,
            o.documento as documento_owner,
            o.email as email_owner
        FROM oferta_carga oc
        LEFT JOIN carga_documento cd ON oc.id = cd.oferta_carga_id
        LEFT JOIN owners o ON oc.owner_id = o.id
        WHERE oc.owner_id = $1
        AND (
            UPPER(oc.codigo) LIKE UPPER($2) OR
            UPPER(oc.pedido_embarcador) LIKE UPPER($2) OR
            UPPER(cd.numero) LIKE UPPER($2) OR
            UPPER(cd.chave) LIKE UPPER($2)
        )
        ORDER BY oc.data_criacao DESC
        """

        search_pattern = f"%{identifier}%"

        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, owner_id, search_pattern)

        return [dict(row) for row in rows]

    async def get_all_cargas_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        if not self.pool:
            raise Exception("Banco não conectado")

        query = """
        SELECT DISTINCT
            oc.id::text as oferta_id,
            oc.codigo,
            oc.nome_empresa_remetente,
            oc.endereco_remetente,
            oc.cidade_remetente,
            oc.estado_remetente,
            oc.nome_empresa_destinatario,
            oc.endereco_destinatario,
            oc.cidade_destinatario,
            oc.estado_destinatario,
            oc.status,
            oc.pedido_embarcador,
            oc.data_criacao as data_criacao_carga,
            cd.numero as numero_documento,
            cd.chave as chave_documento,
            cd.serie,
            cd.tipo_documento,
            cd.data_emissao
        FROM oferta_carga oc
        LEFT JOIN carga_documento cd ON oc.id = cd.oferta_carga_id
        WHERE oc.owner_id = $1
        ORDER BY oc.data_criacao DESC
        """

        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, owner_id)

        return [dict(row) for row in rows]

    async def search_cargas_by_status(self, status: str, owner_id: str) -> List[Dict[str, Any]]:
        if not self.pool:
            raise Exception("Banco não conectado")

        query = """
        SELECT DISTINCT
            oc.id::text as oferta_id,
            oc.codigo,
            oc.nome_empresa_remetente,
            oc.endereco_remetente,
            oc.cidade_remetente,
            oc.estado_remetente,
            oc.nome_empresa_destinatario,
            oc.endereco_destinatario,
            oc.cidade_destinatario,
            oc.estado_destinatario,
            oc.status,
            oc.pedido_embarcador,
            oc.data_criacao as data_criacao_carga,
            cd.numero as numero_documento,
            cd.chave as chave_documento,
            cd.serie,
            cd.tipo_documento,
            cd.data_emissao
        FROM oferta_carga oc
        LEFT JOIN carga_documento cd ON oc.id = cd.oferta_carga_id
        WHERE oc.owner_id = $1
        AND UPPER(oc.status) = UPPER($2)
        ORDER BY oc.data_criacao DESC
        """

        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, owner_id, status)

        return [dict(row) for row in rows]


db_manager = DatabaseManager()

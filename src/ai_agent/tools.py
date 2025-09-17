import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from src.db.database import db_manager

logger = logging.getLogger(__name__)


@tool
async def search_carga_by_identifier(identifier: str, owner_id: str) -> str:
    """Busca uma carga específica pelo identificador (código ou número do documento).

    Args:
        identifier: Código da carga ou número do documento
        owner_id: ID do proprietário da carga

    Returns:
        String com informações da carga encontrada ou mensagem de erro
    """
    try:
        logger.info(
            f"Buscando carga por identificador: {identifier} para owner: {owner_id}")
        data = await db_manager.search_carga_by_identifier(identifier, owner_id)

        if not data:
            return f"Nenhuma carga encontrada com o identificador '{identifier}'"

        cargas_unicas = {}
        documentos_por_carga = {}

        for item in data:
            codigo = item.get('codigo', 'N/A')
            if codigo not in cargas_unicas:
                cargas_unicas[codigo] = item
                documentos_por_carga[codigo] = []

            doc_info = {
                'numero': item.get('numero_documento', 'N/A'),
                'tipo': item.get('tipo_documento', 'N/A'),
                'chave': item.get('chave_documento', 'N/A'),
                'data_emissao': item.get('data_emissao', 'N/A')
            }
            documentos_por_carga[codigo].append(doc_info)

        if len(cargas_unicas) == 1:
            codigo = list(cargas_unicas.keys())[0]
            item = cargas_unicas[codigo]
            documentos = documentos_por_carga[codigo]

            response = f"""
Carga encontrada:
• Código: {item.get('codigo', 'N/A')}
• Status: {item.get('status', 'N/A')}
• Pedido Embarcador: {item.get('pedido_embarcador', 'N/A')}
• Remetente: {item.get('nome_empresa_remetente', 'N/A')} - {item.get('cidade_remetente', 'N/A')}/{item.get('estado_remetente', 'N/A')}
• Destinatário: {item.get('nome_empresa_destinatario', 'N/A')} - {item.get('cidade_destinatario', 'N/A')}/{item.get('estado_destinatario', 'N/A')}
            """.strip()

            if len(documentos) == 1:
                doc = documentos[0]
                response += f"""
• Documento: {doc['numero']} (Tipo: {doc['tipo']})
• Chave: {doc['chave']}
• Data Emissão: {doc['data_emissao']}"""
            else:
                response += f"\n• Documentos ({len(documentos)}):"
                for i, doc in enumerate(documentos, 1):
                    response += f"""
  {i}. {doc['numero']} (Tipo: {doc['tipo']}) - Chave: {doc['chave']}"""

            return response
        else:
            response = f"Encontradas {len(cargas_unicas)} cargas com o identificador '{identifier}':\n\n"
            for i, (codigo, item) in enumerate(cargas_unicas.items(), 1):
                response += f"{i}. Código: {codigo} | Status: {item.get('status', 'N/A')} | Remetente: {item.get('nome_empresa_remetente', 'N/A')}\n"

            return response

    except Exception as e:
        logger.error(f"Erro ao buscar carga por identificador: {e}")
        return f"Erro ao buscar carga: {str(e)}"


@tool
async def search_cargas_by_status(status: str, owner_id: str) -> str:
    """Busca cargas por status específico.

    Args:
        status: Status da carga para filtrar
        owner_id: ID do proprietário das cargas

    Returns:
        String com lista de cargas encontradas ou mensagem de erro
    """

    try:
        logger.info(
            f"Buscando cargas por status: {status} para owner: {owner_id}")
        data = await db_manager.search_cargas_by_status(status, owner_id)

        if not data:
            return f"Nenhuma carga encontrada com status '{status}'"

        response = f"Encontradas {len(data)} cargas com status '{status}':\n\n"
        for i, item in enumerate(data[:10], 1):
            response += f"{i}. Código: {item.get('codigo', 'N/A')} | Pedido: {item.get('pedido_embarcador', 'N/A')} | Remetente: {item.get('nome_empresa_remetente', 'N/A')}\n"

        if len(data) > 10:
            response += f"\n... e mais {len(data) - 10} cargas."

        return response

    except Exception as e:
        logger.error(f"Erro ao buscar cargas por status: {e}")
        return f"Erro ao buscar cargas por status: {str(e)}"


@tool
async def list_all_cargas(owner_id: str, limit: int = 20) -> str:
    """Lista todas as cargas de um proprietário com limite opcional.

    Args:
        owner_id: ID do proprietário das cargas
        limit: Número máximo de cargas para retornar (padrão: 20)

    Returns:
        String com lista de cargas ou mensagem de erro
    """

    try:
        logger.info(f"Listando todas as cargas para owner: {owner_id}")
        data = await db_manager.get_all_cargas_by_owner(owner_id)

        if not data:
            return "Nenhuma carga encontrada"

        limited_data = data[:limit]

        response = f"Encontradas {len(data)} cargas (mostrando {len(limited_data)}):\n\n"
        for i, item in enumerate(limited_data, 1):
            response += f"{i}. Código: {item.get('codigo', 'N/A')} | Status: {item.get('status', 'N/A')} | Pedido: {item.get('pedido_embarcador', 'N/A')} | Remetente: {item.get('nome_empresa_remetente', 'N/A')}\n"

        if len(data) > limit:
            response += f"\n... e mais {len(data) - limit} cargas. Use um limite maior se necessário."

        return response

    except Exception as e:
        logger.error(f"Erro ao listar cargas: {e}")
        return f"Erro ao listar cargas: {str(e)}"


@tool
async def get_carga_details(codigo: str, owner_id: str) -> str:
    """Obtém detalhes completos de uma carga específica.

    Args:
        codigo: Código da carga
        owner_id: ID do proprietário da carga

    Returns:
        String com detalhes completos da carga ou mensagem de erro
    """

    try:
        logger.info(
            f"Obtendo detalhes da carga: {codigo} para owner: {owner_id}")
        data = await db_manager.search_carga_by_identifier(codigo, owner_id)

        if not data:
            return f"Carga com código '{codigo}' não encontrada"

        cargas_unicas = {}
        documentos_por_carga = {}

        for item in data:
            codigo_carga = item.get('codigo', 'N/A')
            if codigo_carga not in cargas_unicas:
                cargas_unicas[codigo_carga] = item
                documentos_por_carga[codigo_carga] = []

            doc_info = {
                'numero': item.get('numero_documento', 'N/A'),
                'tipo': item.get('tipo_documento', 'N/A'),
                'chave': item.get('chave_documento', 'N/A'),
                'data_emissao': item.get('data_emissao', 'N/A')
            }
            documentos_por_carga[codigo_carga].append(doc_info)

        codigo = list(cargas_unicas.keys())[0]
        item = cargas_unicas[codigo]
        documentos = documentos_por_carga[codigo]

        response = f"""
DETALHES COMPLETOS DA CARGA:

Código: {item.get('codigo', 'N/A')}
Status: {item.get('status', 'N/A')}
Pedido Embarcador: {item.get('pedido_embarcador', 'N/A')}

REMETENTE:
• Empresa: {item.get('nome_empresa_remetente', 'N/A')}
• Cidade: {item.get('cidade_remetente', 'N/A')}
• Estado: {item.get('estado_remetente', 'N/A')}

DESTINATÁRIO:
• Empresa: {item.get('nome_empresa_destinatario', 'N/A')}
• Cidade: {item.get('cidade_destinatario', 'N/A')}
• Estado: {item.get('estado_destinatario', 'N/A')}
        """.strip()

        if len(documentos) == 1:
            doc = documentos[0]
            response += f"""

DOCUMENTO:
• Número: {doc['numero']}
• Tipo: {doc['tipo']}
• Chave: {doc['chave']}
• Data Emissão: {doc['data_emissao']}"""
        else:
            response += f"""

DOCUMENTOS ({len(documentos)}):"""
            for i, doc in enumerate(documentos, 1):
                response += f"""
{i}. Número: {doc['numero']}
   Tipo: {doc['tipo']}
   Chave: {doc['chave']}
   Data Emissão: {doc['data_emissao']}"""

        return response

    except Exception as e:
        logger.error(f"Erro ao obter detalhes da carga: {e}")
        return f"Erro ao obter detalhes da carga: {str(e)}"


TOOLS = [
    search_carga_by_identifier,
    search_cargas_by_status,
    list_all_cargas,
    get_carga_details
]

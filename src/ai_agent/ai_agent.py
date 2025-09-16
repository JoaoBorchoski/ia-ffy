import os
from dotenv import load_dotenv
import json
import logging
from typing import Dict, List, Any
from openai import AsyncOpenAI
from src.db.database import db_manager

load_dotenv()

logger = logging.getLogger(__name__)


class CargaAIAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    async def analyze_question(self, question: str) -> Dict[str, Any]:
        system_prompt = """
        Você é um assistente especializado em análise de cargas e logística.
        Sua função é analisar perguntas sobre cargas e determinar que tipo de busca deve ser feita no banco de dados.

        Tipos de busca disponíveis:
        1. "search_by_identifier" - quando o usuário menciona um código, número, chave ou pedido específico
        2. "search_by_status" - quando o usuário pergunta sobre status das cargas
        3. "list_all" - quando o usuário quer ver todas as cargas
        4. "general_info" - para perguntas gerais sobre uma carga específica

        IMPORTANTE: Para extrair identificadores, procure por:
        - Códigos de carga (ex: D-ABCD, C-123)
        - Números de documento (ex: 00123456, 123456789)
        - Chaves de documento (ex: chaves de NFe, CT-e)
        - Pedidos do embarcador (ex: PED-123, ORD-456)
        
        Extraia APENAS o identificador específico, não a pergunta inteira.

        Responda SEMPRE em formato JSON com:
        {
            "search_type": "tipo_de_busca",
            "identifier": "identificador_extraído_se_houver",
            "status": "status_se_mencionado",
            "intent": "intenção_da_pergunta"
        }

        Exemplos:
        - "qual o status da carga D-ABCD" -> {"search_type": "search_by_identifier", "identifier": "D-ABCD", "status": null, "intent": "verificar_status"}
        - "qual o status da carga 00123456" -> {"search_type": "search_by_identifier", "identifier": "00123456", "status": null, "intent": "verificar_status"}
        - "mostre cargas disponíveis" -> {"search_type": "search_by_status", "identifier": null, "status": "disponivel", "intent": "listar_por_status"}
        - "liste todas as cargas" -> {"search_type": "list_all", "identifier": null, "status": null, "intent": "listar_todas"}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.1,
                max_tokens=200
            )

            analysis = json.loads(response.choices[0].message.content)
            return analysis

        except Exception as e:
            logger.error(f"Erro ao analisar pergunta: {e}")
            return {
                "search_type": "search_by_identifier",
                "identifier": question,
                "status": None,
                "intent": "busca_geral"
            }

    async def format_response(self, question: str, data: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
        if not data:
            return "Não foram encontradas cargas que correspondam à sua consulta."

        data_summary = []
        for item in data:
            summary = {
                "codigo": item.get("codigo"),
                "status": item.get("status"),
                "pedido_embarcador": item.get("pedido_embarcador"),
                "remetente": f"{item.get('nome_empresa_remetente')} - {item.get('cidade_remetente')}/{item.get('estado_remetente')}",
                "destinatario": f"{item.get('nome_empresa_destinatario')} - {item.get('cidade_destinatario')}/{item.get('estado_destinatario')}",
                "documento": {
                    "numero": item.get("numero_documento"),
                    "chave": item.get("chave_documento"),
                    "tipo": item.get("tipo_documento"),
                    "data_emissao": str(item.get("data_emissao")) if item.get("data_emissao") else None
                }
            }
            data_summary.append(summary)

        system_prompt = f"""
        Você é um assistente especializado em logística e cargas.
        Formate uma resposta clara e organizada baseada nos dados encontrados.
        
        Pergunta original: "{question}"
        Intenção detectada: {analysis.get('intent', 'busca_geral')}
        
        Diretrizes:
        - Seja claro e objetivo
        - Organize as informações de forma lógica
        - Inclua todos os dados relevantes
        - Use formatação para melhor legibilidade
        - Se houver múltiplas cargas, organize por relevância
        - Destaque informações importantes como status
        
        Dados encontrados: {json.dumps(data_summary, ensure_ascii=False, indent=2)}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Formate uma resposta baseada nos dados fornecidos."}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Erro ao formatar resposta: {e}")
            return self._format_simple_response(data)

    def _format_simple_response(self, data: List[Dict[str, Any]]) -> str:
        if len(data) == 1:
            item = data[0]
            return f"""
Carga encontrada:
• Código: {item.get('codigo', 'N/A')}
• Status: {item.get('status', 'N/A')}
• Pedido Embarcador: {item.get('pedido_embarcador', 'N/A')}
• Remetente: {item.get('nome_empresa_remetente', 'N/A')} - {item.get('cidade_remetente', 'N/A')}/{item.get('estado_remetente', 'N/A')}
• Destinatário: {item.get('nome_empresa_destinatario', 'N/A')} - {item.get('cidade_destinatario', 'N/A')}/{item.get('estado_destinatario', 'N/A')}
• Documento: {item.get('numero_documento', 'N/A')} (Tipo: {item.get('tipo_documento', 'N/A')})
• Chave: {item.get('chave_documento', 'N/A')}
            """.strip()
        else:
            response = f"Encontradas {len(data)} cargas:\n\n"
            for i, item in enumerate(data[:5], 1):
                response += f"{i}. Código: {item.get('codigo', 'N/A')} | Status: {item.get('status', 'N/A')} | Remetente: {item.get('nome_empresa_remetente', 'N/A')}\n"

            if len(data) > 5:
                response += f"\n... e mais {len(data) - 5} cargas."

            return response

    async def process_question(self, question: str, owner_id: str) -> Dict[str, Any]:
        try:
            analysis = await self.analyze_question(question)
            logger.info(f"Análise da pergunta: {analysis}")

            data = []
            search_type = analysis.get("search_type", "search_by_identifier")

            if search_type == "search_by_identifier" and analysis.get("identifier"):
                data = await db_manager.search_carga_by_identifier(
                    analysis["identifier"], owner_id
                )
            elif search_type == "search_by_status" and analysis.get("status"):
                data = await db_manager.search_cargas_by_status(
                    analysis["status"], owner_id
                )
            elif search_type == "list_all":
                data = await db_manager.get_all_cargas_by_owner(owner_id)
            else:
                # Fallback: tentar extrair identificadores da pergunta
                import re

                # Procurar por padrões de identificadores comuns
                patterns = [
                    r'\b[A-Z]-\d+\b',  # D-123, C-456
                    r'\b\d{6,}\b',     # 00123456, 123456789
                    r'\b[A-Z]{2,}\d+\b',  # PED123, ORD456
                    r'\b\d+[A-Z]+\b',  # 123ABC
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, question.upper())
                    for match in matches:
                        temp_data = await db_manager.search_carga_by_identifier(match, owner_id)
                        if temp_data:
                            data.extend(temp_data)
                            break
                    if data:
                        break

                # Se ainda não encontrou nada, tentar palavras individuais
                if not data:
                    words = question.split()
                    for word in words:
                        if len(word) > 2 and word.isalnum():
                            temp_data = await db_manager.search_carga_by_identifier(word, owner_id)
                            if temp_data:
                                data.extend(temp_data)
                                break

            formatted_response = await self.format_response(question, data, analysis)

            return {
                "success": True,
                "response": formatted_response,
                "data_count": len(data),
                "analysis": analysis,
                "raw_data": data
            }

        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {e}")
            return {
                "success": False,
                "response": f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}",
                "data_count": 0,
                "analysis": None,
                "raw_data": []
            }


ai_agent = CargaAIAgent()

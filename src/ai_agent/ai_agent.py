import os
from dotenv import load_dotenv
import json
import logging
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain.memory import ConversationBufferWindowMemory
from src.ai_agent.tools import TOOLS
from src.ai_agent.memory_manager import RedisMemoryManager

load_dotenv()

logger = logging.getLogger(__name__)


class CargaAIAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.memory_manager = RedisMemoryManager(memory_window=10)

        self.user_memories: Dict[str, ConversationBufferWindowMemory] = {}

        self.memory_window = 10

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
Você é um assistente especializado em análise de cargas e logística.
Sua função é ajudar usuários a encontrar informações sobre cargas usando as ferramentas disponíveis.

FERRAMENTAS DISPONÍVEIS:
- search_carga_by_identifier: Busca carga por código, número de documento, chave ou pedido
- search_cargas_by_status: Busca cargas por status específico
- list_all_cargas: Lista todas as cargas do proprietário
- get_carga_details: Obtém detalhes completos de uma carga específica

INSTRUÇÕES:
1. Analise a pergunta do usuário cuidadosamente
2. Identifique qual ferramenta usar baseado na pergunta
3. Extraia os parâmetros necessários (identificador, status, owner_id)
4. Use a ferramenta apropriada
5. Se necessário, use múltiplas ferramentas para obter informações completas
6. Forneça uma resposta clara e organizada

EXEMPLOS DE USO:
- "Qual o status da carga D-ABCD?" → use search_carga_by_identifier
- "Mostre cargas disponíveis" → use search_cargas_by_status com status="disponivel"
- "Liste todas as cargas" → use list_all_cargas
- "Detalhes da carga D-ABCD" → use get_carga_details

Seja sempre útil e forneça informações completas e organizadas.
            """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=TOOLS,
            prompt=self.prompt
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def _get_user_memory(self, owner_id: str, user_id: str) -> ConversationBufferWindowMemory:
        memory_key = f"{owner_id}:{user_id}"

        if self.memory_manager.is_connected():
            return self.memory_manager.get_user_memory(memory_key)

        if memory_key not in self.user_memories:
            self.user_memories[memory_key] = ConversationBufferWindowMemory(
                k=self.memory_window,
                return_messages=True,
                memory_key="chat_history"
            )
            logger.info(
                f"Criada nova memória de contexto em RAM para owner_id: {owner_id}, user_id: {user_id}")

        return self.user_memories[memory_key]

    def _create_agent_with_memory(self, owner_id: str, user_id: str, user_memory: ConversationBufferWindowMemory) -> AgentExecutor:
        logger.info(
            f"Memória criada para owner_id: {owner_id}, user_id: {user_id}, mensagens: {len(user_memory.chat_memory.messages)}")

        agent_with_memory = create_openai_tools_agent(
            llm=self.llm,
            tools=TOOLS,
            prompt=self.prompt
        )

        agent_executor = AgentExecutor(
            agent=agent_with_memory,
            tools=TOOLS,
            memory=user_memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

        return agent_executor

    async def process_question(self, question: str, owner_id: str, user_id: str) -> Dict[str, Any]:
        try:
            logger.info(
                f"Processando pergunta: '{question}' para owner_id: {owner_id}, user_id: {user_id}")

            user_memory = self._get_user_memory(owner_id, user_id)

            user_memory.chat_memory.add_user_message(question)

            contextual_question = f"Pergunta: {question}\n\nContexto: O owner_id é '{owner_id}'. Use este owner_id em todas as buscas no banco de dados."

            agent_with_memory = self._create_agent_with_memory(
                owner_id, user_id, user_memory)

            result = await agent_with_memory.ainvoke({
                "input": contextual_question
            })

            agent_response = result.get(
                "output", "Não foi possível processar a pergunta.")

            user_memory.chat_memory.add_ai_message(agent_response)

            if self.memory_manager.is_connected():
                memory_key = f"{owner_id}:{user_id}"
                success = self.memory_manager.save_user_memory(
                    memory_key, user_memory)
                if success:
                    logger.info(
                        f"Memória salva no Redis para owner_id: {owner_id}, user_id: {user_id} ({len(user_memory.chat_memory.messages)} mensagens)")
                else:
                    logger.warning(
                        f"Falha ao salvar memória no Redis para owner_id: {owner_id}, user_id: {user_id}")
            else:
                logger.warning(
                    "Redis não conectado, memória não será persistida")

            raw_data = []
            data_count = 0

            if "código:" in agent_response.lower() or "carga encontrada" in agent_response.lower():
                data_count = 1

            return {
                "success": True,
                "response": agent_response,
                "data_count": data_count,
                "analysis": {
                    "agent_used": True,
                    "tools_available": [tool.name for tool in TOOLS],
                    "reasoning": "Agente LangChain processou a pergunta usando ferramentas disponíveis"
                },
                "raw_data": raw_data
            }

        except Exception as e:
            logger.error(f"Erro ao processar pergunta com agente: {e}")
            return {
                "success": False,
                "response": f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}",
                "data_count": 0,
                "analysis": {
                    "agent_used": True,
                    "error": str(e)
                },
                "raw_data": []
            }

    def clear_user_memory(self, owner_id: str, user_id: str = None) -> bool:
        try:
            if user_id:
                memory_key = f"{owner_id}:{user_id}"

                if self.memory_manager.is_connected():
                    success = self.memory_manager.clear_user_memory(memory_key)
                    if success:
                        logger.info(
                            f"Memória limpa no Redis para owner_id: {owner_id}, user_id: {user_id}")
                        return True

                if memory_key in self.user_memories:
                    del self.user_memories[memory_key]
                    logger.info(
                        f"Memória limpa em RAM para owner_id: {owner_id}, user_id: {user_id}")
                    return True
            else:
                cleared_count = 0

                if self.memory_manager.is_connected():
                    pattern = f"agent_memory:{owner_id}:*"
                    keys = self.memory_manager.redis_client.keys(pattern)
                    for key in keys:
                        if self.memory_manager.redis_client.delete(key):
                            cleared_count += 1
                    logger.info(
                        f"Memórias limpas no Redis para owner_id: {owner_id} ({cleared_count} usuários)")

                memory_keys_to_remove = [
                    key for key in self.user_memories.keys() if key.startswith(f"{owner_id}:")]
                for key in memory_keys_to_remove:
                    del self.user_memories[key]
                    cleared_count += 1
                logger.info(
                    f"Memórias limpas em RAM para owner_id: {owner_id} ({len(memory_keys_to_remove)} usuários)")

                return cleared_count > 0

            return False
        except Exception as e:
            logger.error(f"Erro ao limpar memória: {e}")
            return False

    def get_user_memory_info(self, owner_id: str, user_id: str = None) -> Dict[str, Any]:
        if user_id:
            memory_key = f"{owner_id}:{user_id}"

            if self.memory_manager.is_connected():
                return self.memory_manager.get_user_memory_info(memory_key)

            if memory_key not in self.user_memories:
                return {
                    "has_memory": False,
                    "message_count": 0,
                    "memory_window": self.memory_window,
                    "storage": "ram",
                    "owner_id": owner_id,
                    "user_id": user_id
                }

            memory = self.user_memories[memory_key]
            return {
                "has_memory": True,
                "message_count": len(memory.chat_memory.messages),
                "memory_window": self.memory_window,
                "storage": "ram",
                "owner_id": owner_id,
                "user_id": user_id,
                "recent_messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    }
                    for msg in memory.chat_memory.messages[-5:]
                ]
            }
        else:
            users_info = []

            if self.memory_manager.is_connected():
                pattern = f"agent_memory:{owner_id}:*"
                keys = self.memory_manager.redis_client.keys(pattern)
                for key in keys:
                    user_id_from_key = key.replace(
                        f"agent_memory:{owner_id}:", "")
                    user_info = self.memory_manager.get_user_memory_info(key)
                    user_info["owner_id"] = owner_id
                    user_info["user_id"] = user_id_from_key
                    users_info.append(user_info)
            else:
                for memory_key in self.user_memories.keys():
                    if memory_key.startswith(f"{owner_id}:"):
                        user_id_from_key = memory_key.replace(
                            f"{owner_id}:", "")
                        memory = self.user_memories[memory_key]
                        user_info = {
                            "has_memory": True,
                            "message_count": len(memory.chat_memory.messages),
                            "memory_window": self.memory_window,
                            "storage": "ram",
                            "owner_id": owner_id,
                            "user_id": user_id_from_key
                        }
                        users_info.append(user_info)

            return {
                "owner_id": owner_id,
                "total_users": len(users_info),
                "users": users_info
            }

    def get_all_memories_info(self) -> Dict[str, Any]:
        if self.memory_manager.is_connected():
            return self.memory_manager.get_all_memories_info()

        return {
            "total_users": len(self.user_memories),
            "users": list(self.user_memories.keys()),
            "memory_window": self.memory_window,
            "storage": "ram"
        }

    def get_redis_info(self) -> Dict[str, Any]:
        return self.memory_manager.get_redis_info()


ai_agent = CargaAIAgent()

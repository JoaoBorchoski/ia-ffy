import json
import redis
import logging
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)


class RedisMemoryManager:

    def __init__(self, redis_url: str = None, memory_window: int = 10):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379")
        self.memory_window = memory_window
        self.redis_client = None
        self._connect()

    def _connect(self):
        try:
            self.redis_client = redis.from_url(
                self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Conectado ao Redis com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}")
            self.redis_client = None

    def _get_memory_key(self, memory_key: str) -> str:
        return f"agent_memory:{memory_key}"

    def _serialize_messages(self, messages: List[BaseMessage]) -> str:
        serialized = []
        for msg in messages:
            serialized.append({
                "type": msg.__class__.__name__,
                "content": msg.content
            })
        return json.dumps(serialized)

    def _deserialize_messages(self, data: str) -> List[BaseMessage]:
        if not data:
            return []

        try:
            messages_data = json.loads(data)
            messages = []
            for msg_data in messages_data:
                if msg_data["type"] == "HumanMessage":
                    messages.append(HumanMessage(content=msg_data["content"]))
                elif msg_data["type"] == "AIMessage":
                    messages.append(AIMessage(content=msg_data["content"]))
            return messages
        except Exception as e:
            logger.error(f"Erro ao deserializar mensagens: {e}")
            return []

    def get_user_memory(self, memory_key: str) -> ConversationBufferWindowMemory:
        if not self.redis_client:
            logger.warning("Redis não conectado, usando memória em RAM")
            return ConversationBufferWindowMemory(
                k=self.memory_window,
                return_messages=True,
                memory_key="chat_history"
            )

        try:
            redis_key = self._get_memory_key(memory_key)

            messages_data = self.redis_client.get(redis_key)

            if messages_data:
                messages = self._deserialize_messages(messages_data)
                logger.info(
                    f"Memória carregada do Redis para {memory_key} ({len(messages)} mensagens)")
            else:
                messages = []
                logger.info(f"Nova memória criada para {memory_key}")

            memory = ConversationBufferWindowMemory(
                k=self.memory_window,
                return_messages=True,
                memory_key="chat_history"
            )

            for msg in messages:
                memory.chat_memory.add_message(msg)

            return memory

        except Exception as e:
            logger.error(f"Erro ao obter memória do Redis: {e}")
            return ConversationBufferWindowMemory(
                k=self.memory_window,
                return_messages=True,
                memory_key="chat_history"
            )

    def save_user_memory(self, memory_key: str, memory: ConversationBufferWindowMemory) -> bool:
        if not self.redis_client:
            logger.warning("Redis não conectado, memória não será persistida")
            return False

        try:
            redis_key = self._get_memory_key(memory_key)

            messages_data = self._serialize_messages(
                memory.chat_memory.messages)

            self.redis_client.setex(
                redis_key, 7 * 24 * 60 * 60, messages_data)

            logger.info(
                f"Memória salva no Redis para {memory_key} ({len(memory.chat_memory.messages)} mensagens)")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar memória no Redis: {e}")
            return False

    def clear_user_memory(self, memory_key: str) -> bool:
        if not self.redis_client:
            logger.warning("Redis não conectado")
            return False

        try:
            redis_key = self._get_memory_key(memory_key)
            result = self.redis_client.delete(redis_key)

            if result:
                logger.info(
                    f"Memória limpa no Redis para {memory_key}")
                return True
            else:
                logger.info(
                    f"Nenhuma memória encontrada para {memory_key}")
                return False

        except Exception as e:
            logger.error(f"Erro ao limpar memória no Redis: {e}")
            return False

    def get_user_memory_info(self, memory_key: str) -> Dict[str, Any]:
        if not self.redis_client:
            return {
                "has_memory": False,
                "message_count": 0,
                "memory_window": self.memory_window,
                "storage": "ram_fallback"
            }

        try:
            redis_key = self._get_memory_key(memory_key)
            messages_data = self.redis_client.get(redis_key)

            if not messages_data:
                return {
                    "has_memory": False,
                    "message_count": 0,
                    "memory_window": self.memory_window,
                    "storage": "redis"
                }

            messages = self._deserialize_messages(messages_data)

            return {
                "has_memory": True,
                "message_count": len(messages),
                "memory_window": self.memory_window,
                "storage": "redis",
                "recent_messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    }
                    for msg in messages[-5:]
                ]
            }

        except Exception as e:
            logger.error(f"Erro ao obter informações da memória: {e}")
            return {
                "has_memory": False,
                "message_count": 0,
                "memory_window": self.memory_window,
                "storage": "error",
                "error": str(e)
            }

    def get_all_memories_info(self) -> Dict[str, Any]:
        if not self.redis_client:
            return {
                "total_users": 0,
                "users": [],
                "memory_window": self.memory_window,
                "storage": "ram_fallback"
            }

        try:
            pattern = "agent_memory:*"
            keys = self.redis_client.keys(pattern)

            users = []
            for key in keys:
                owner_id = key.replace("agent_memory:", "")
                users.append(owner_id)

            return {
                "total_users": len(users),
                "users": users,
                "memory_window": self.memory_window,
                "storage": "redis"
            }

        except Exception as e:
            logger.error(f"Erro ao obter informações das memórias: {e}")
            return {
                "total_users": 0,
                "users": [],
                "memory_window": self.memory_window,
                "storage": "error",
                "error": str(e)
            }

    def is_connected(self) -> bool:
        return self.redis_client is not None

    def get_redis_info(self) -> Dict[str, Any]:
        if not self.redis_client:
            return {"connected": False, "error": "Redis não conectado"}

        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "version": info.get("redis_version"),
                "uptime": info.get("uptime_in_seconds"),
                "memory_used": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

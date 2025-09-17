import os
import logging
from dotenv import load_dotenv

load_dotenv()


class Settings:
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))

    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Redis settings
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=getattr(logging, Settings.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)


settings = Settings()

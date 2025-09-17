import uvicorn
from src.config import settings
from src.api import app

settings.setup_logging()

if __name__ == "__main__":
    logger = settings.setup_logging()
    logger.info(f"Iniciando servidor em {settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )

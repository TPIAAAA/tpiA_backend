import os

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://plan2sim:dev_change_me@127.0.0.1:3307/plan2sim?charset=utf8mb4")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ALWAYS_EAGER = os.getenv("CELERY_ALWAYS_EAGER", "0") == "1"
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

# LLM（學生 A/C/E 共用）。金鑰只放 .env，不可 commit。
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL") or "gemini-3.5-flash"
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "120"))
LLM_LOG_DIR = os.getenv("LLM_LOG_DIR") or None

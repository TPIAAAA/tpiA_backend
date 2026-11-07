import os

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://plan2sim:dev_change_me@127.0.0.1:3307/plan2sim?charset=utf8mb4")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ALWAYS_EAGER = os.getenv("CELERY_ALWAYS_EAGER", "0") == "1"
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

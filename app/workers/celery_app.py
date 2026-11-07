from celery import Celery
from app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_ALWAYS_EAGER

celery_app = Celery("plan2sim", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND,
                    include=["app.workers.tasks"])
celery_app.conf.update(task_always_eager=CELERY_ALWAYS_EAGER, task_eager_propagates=True)

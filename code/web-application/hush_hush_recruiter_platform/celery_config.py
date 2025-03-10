import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hush_hush_recruiter_platform.settings')

app = Celery('hush_hush_recruiter_platform')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.update(
    result_expires=3600,  # Results expire after 1 hour
    worker_max_tasks_per_child=500,  # Restart worker after 500 tasks
    task_time_limit=600,  # 10 minute timeout
    task_soft_time_limit=300,  # 5 minute soft timeout
    worker_concurrency=4,  # Number of worker processes
    task_default_queue='default',
    task_queues={
        'default': {},
        'evaluations': {
            'exchange': 'evaluations',
            'routing_key': 'evaluations',
        },
    },
    task_routes={
        'core.tasks.evaluate_assessment': {'queue': 'evaluations'},
    },
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
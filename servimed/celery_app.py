import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

app = Celery('servimed', 
             broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
             include=['tasks']
             )

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo'
)
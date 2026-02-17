from celery_app import app
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from billiard import Process

def execute_spider(user, password, razao, cliente_id, external_id=None, situacao=None):
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    # Chama o spider de produtos passando as credenciais
    process.crawl('product_spider', user=user, password=password, razao=razao, cliente_id=cliente_id, external_id=external_id, situacao=situacao)
    process.start()

@app.task(name="tasks.run_product_scraping")
def run_product_scraping(user, password, razao, cliente_id, external_id=None, situacao=None):
    # Process isolado para evitar erros de Reactor do Scrapy
    p = Process(target=execute_spider, args=(user, password, razao, cliente_id, external_id, situacao))
    p.start()
    p.join()
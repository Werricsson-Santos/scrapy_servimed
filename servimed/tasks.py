from celery_app import app
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from billiard import Process, Queue 
from scrapy.signalmanager import dispatcher
from scrapy import signals
import os

# Função que roda no processo isolado (FILHO)
def execute_spider(razao, cliente_id, external_id, situacao, queue):
    settings = get_project_settings()
    
    # Lista para capturar o resultado
    resultados = []

    def item_scraped(item, response, spider):
        # 1. Captura o retorno bruto da API
        raw_msg = item.get('integracao_response')
        clean_msg = ""

        # 2. Lógica de Limpeza Visual
        if isinstance(raw_msg, list):
            # Se for lista, é sucesso com os IDs. Mostramos apenas a contagem.
            clean_msg = f"✅ Lista de {len(raw_msg)} IDs gerados com sucesso."
        else:
            # Se for texto (erro) ou dict, convertemos para string e cortamos se for muito grande
            msg_str = str(raw_msg)
            clean_msg = msg_str[:100] + "..." if len(msg_str) > 100 else msg_str

        # 3. Formatação do Resultado Visual (pode ser customizado conforme necessidade)
        resultado_visual = {
            "🏢 Cliente": f"{item.get('empresa_nome')} (ID: {item.get('empresa_codigo')})",
            "📦 Produtos": item.get('quantidade_integrada'),
            "📡 Status API": item.get('integracao_status'),
            "📝 Detalhe": clean_msg
        }
        
        resultados.append(resultado_visual)

    # Conecta o sinal antes de iniciar o processo
    dispatcher.connect(item_scraped, signal=signals.item_scraped)

    process = CrawlerProcess(settings)
    process.crawl('product_spider', razao=razao, cliente_id=cliente_id, external_id=external_id, situacao=situacao)
    process.start()
    
    # Ao final do Scrapy, coloca o resultado na Fila para o pai ler
    if resultados:
        # Envia o item formatado
        queue.put(resultados[0]) 
    else:
        # Caso o spider não tenha gerado nada (ex: carrinho vazio na origem)
        queue.put({
            "🏢 Cliente": f"{razao} ({cliente_id})",
            "⚠️ Status": "Vazio", 
            "📝 Detalhe": "Nenhum produto encontrado no carrinho."
        })

# Função da Task do Celery (PAI)
@app.task(name="tasks.run_product_scraping", bind=True)
def run_product_scraping(self, razao, cliente_id, external_id=None, situacao=None):
    # Cria a fila de comunicação do billiard
    q = Queue()
    
    # Passa a fila (q) para o processo filho
    p = Process(target=execute_spider, args=(razao, cliente_id, external_id, situacao, q))
    p.start()
    p.join()
    
    # Lê o que o filho mandou de volta
    if not q.empty():
        resultado = q.get()
        return resultado # <--- O Flower exibirá este JSON limpo na coluna Result
    
    return {"Status": "Erro Crítico", "Msg": "Processo terminou sem comunicação"}
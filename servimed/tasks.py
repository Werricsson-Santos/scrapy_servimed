from celery_app import app
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from billiard import Process, Queue 
from scrapy.signalmanager import dispatcher
from scrapy import signals
import os

def formatar_moeda(valor):
    """Converte um float/int para string formatada em Real (R$)"""
    if not valor:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função que roda no processo isolado (FILHO)
def execute_spider(razao, cnpj, cliente_id, external_id, situacao, queue):
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
            "🏢 Cliente": f"{item.get('cliente_nome')} (ID: {item.get('cliente_id')})",
            "📦 Produtos": item.get('quantidade_integrada'),
            "📡 Status API": item.get('integracao_status'),
            "📝 Detalhe": clean_msg
        }
        
        resultados.append(resultado_visual)

    # Conecta o sinal antes de iniciar o processo
    dispatcher.connect(item_scraped, signal=signals.item_scraped)

    process = CrawlerProcess(settings)
    process.crawl('product_spider', razao=razao, cnpj=cnpj, cliente_id=cliente_id, external_id=external_id, situacao=situacao)
    process.start()
    
    # Ao final do Scrapy, coloca o resultado na Fila para o pai ler
    if resultados:
        # Envia o item formatado
        queue.put(resultados[0]) 
    else:
        # Caso o spider não tenha gerado nada (ex: carrinho vazio na origem)
        queue.put({
            "🏢 Cliente": f"{razao} ({cnpj})",
            "⚠️ Status": "Vazio", 
            "📝 Detalhe": "Nenhum produto encontrado no carrinho."
        })

# Função da Task do Celery (PAI)
@app.task(name="tasks.run_product_scraping", bind=True)
def run_product_scraping(self, razao, cnpj, cliente_id, external_id=None, situacao=None):
    # Cria a fila de comunicação do billiard
    q = Queue()
    
    # Passa a fila (q) para o processo filho
    p = Process(target=execute_spider, args=(razao, cnpj, cliente_id, external_id, situacao, q))
    p.start()
    p.join()
    
    # Lê o que o filho mandou de volta
    if not q.empty():
        resultado = q.get()
        return resultado # <--- O Flower exibirá este JSON limpo na coluna Result
    
    return {"Status": "Erro Crítico", "Msg": "Processo terminou sem comunicação"}

def execute_order_spider(payload, queue):
    settings = get_project_settings()
    
    resultados = []

    def item_scraped(item, response, spider):
        # Filtra apenas o item final de resultado do pedido
        if item.get('type') == 'order_result':
            resultados.append(item)

    
    dispatcher.connect(item_scraped, signal=signals.item_scraped)

    process = CrawlerProcess(settings)
    # Inicia o spider passando o payload recebido do pipeline
    process.crawl('order_spider', pedido_data=payload)
    process.start()
    
    if resultados:
        queue.put(resultados[0])
    else:
        queue.put({"status_final": "erro_interno", "msg": "Spider não gerou output"})

# ---------------------------------------------------------
#        Nível 3 - Simulação Pedido de Compra 
# ---------------------------------------------------------
@app.task(name="tasks.run_purchase_simulation", bind=True)
def run_purchase_simulation(self, payload):
    """
    Executa a simulação de compra (Nível 3).
    Recebe: Dict com credenciais Servimed, ID do pedido e lista de produtos.
    """
    
    # Cria a fila de comunicação
    q = Queue()
    
    # Inicia o processo isolado
    p = Process(target=execute_order_spider, args=(payload, q))
    p.start()
    p.join()
    
    # Processa o retorno para exibir no Flower
    if not q.empty():
        res = q.get()
        
        return {
            "🏢 Cliente": f"{res.get('cliente_nome')} (ID: {res.get('cnpj')})",
            "🛒 Pedido Desafio": res.get('challenge_order_id'),
            "🏢 Pedido Servimed": res.get('servimed_order_id'),
            "💰 Valor do pedido": formatar_moeda(res.get('valor_total_erp')),
            "📝 Situacao Real": res.get('situacao_erp'),
            "🏁 Status Callback": res.get('status_final'),
            "📡 Callback API": "✅ Enviado" if res.get('callback_enviado') else "❌ Falha"
        }
    
    return {"Status": "Erro Crítico", "Msg": "Spider de pedido falhou silenciosamente"}
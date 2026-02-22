import ast
import os
import scrapy
import json
import base64
import hmac
import hashlib
import uuid
from curl_cffi.requests import AsyncSession
from datetime import datetime

def gerar_x_cart(payload, timestamp):
    """
    Gera a assinatura X-Cart exigida pela API da Servimed.
    Mesma lógica utilizada no ProductSpider.
    """
    secret = os.getenv("SERVIMED_SECRET")
    # O payload deve ser compactado (sem espaços após os separadores)
    payload_str = json.dumps(payload, separators=(',', ':'))
    mensagem = f"{payload_str}{timestamp}"
    
    signature = hmac.new(
        secret.encode('utf-8'),
        mensagem.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

class OrderSpider(scrapy.Spider):
    name = 'order_spider'

    def __init__(self, pedido_data=None, *args, **kwargs):
        super(OrderSpider, self).__init__(*args, **kwargs)

        self.base_api_url = "https://peapi.servimed.com.br/api"
        
        # 1. Desserializa o payload recebido do Celery/Pipeline
        if isinstance(pedido_data, dict):
            self.payload = pedido_data
        elif isinstance(pedido_data, str):
            self.payload = json.loads(pedido_data)
            
            
        # self._aplicar_mock() # Ativa dados de teste para desenvolvimento local (remover em produção)
        
            
        # 2. Credenciais e Contexto (Mesmo padrão do ProductSpider)
        self.user = os.getenv("SERVIMED_USER")
        self.password = os.getenv("SERVIMED_PASS")
        self.cliente_id = self.payload.get('cliente_id')
        self.cnpj = self.payload.get('cnpj')
        self.cliente_nome = self.payload.get('cliente_nome')
        self.cliente_external_id = self.payload.get('cliente_external_id')
        self.logger.info(f"OrderSpider iniciado com cliente_id: {self.cliente_id}")
        
        self.pedido_aleatorio = self.payload.get('pedido_aleatorio') # Dados do pedido vindo do desafio (Cote Fácil)  
                
        self.itens_finais_servimed = self.payload.get('produtos') # Já tratado no pipeline
        
        self.id_pedido_aleatorio = self.payload.get('id_pedido') # ID do pedido vindo do desafio (Cote Fácil)

        self.logger.info(f"Iniciando OrderSpider para Pedido #{self.id_pedido_aleatorio} | Cliente: {self.cliente_id}")

    def _aplicar_mock(self):
        """Dados de teste para não depender de argumentos do terminal"""
        self.logger.warning("⚠️ MOCK ATIVADO: Ignorando argumentos de entrada.")
        self.payload = {
            "id_pedido": 141,
            "cliente_id": "267511",
            "cnpj": "05272420000221",
            "produtos": [
                {"id":430401,"selectedPromotionID":-1,"taxValue":45.35071834200001,"quantityRequested":1,"baseValue":115.65,"totalStIvaValue":45.35071834200001,"totalValue":45.35071834200001,"discount":68.59,"discountValue":33.230718342,"stIVA":12.120000000000001},{"id":430400,"selectedPromotionID":-1,"taxValue":81.75518512080001,"quantityRequested":1,"baseValue":198.58,"totalStIvaValue":81.75518512080001,"totalValue":81.75518512080001,"discount":65.13,"discountValue":63.34518512080001,"stIVA":18.41}
            ],
            "cliente_nome": "Teste Cliente",
            "cliente_id": "267511",
            "cliente_external_id": "267511_ext"
        }

    def start_requests(self):
        # Gatilho inicial com Scrapy padrão para iniciar o ciclo
        url_login = f'{self.base_api_url}/usuario/login'
        payload = {"senha": self.password, "usuario": self.user}
        
        yield scrapy.Request(
            url=url_login,
            method='POST',
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            callback=self.processar_pedido,
            dont_filter=True
        )

    async def processar_pedido(self, response):
        """
        Lógica principal assíncrona usando curl_cffi.
        
        """
        
        # --- 1. Extração de Identidade e Tokens ---
        set_cookies = response.headers.getlist('Set-Cookie')
        
        # Tenta extrair o token do cookie bruto
        try:
            full_jwt = next((c.decode('utf-8').split('accesstoken=')[1].split(';')[0] 
                             for c in set_cookies if b'accesstoken=' in c), None)
        except Exception:
            full_jwt = None

        if not full_jwt:
            self.logger.error("❌ Falha crítica: Não foi possível extrair JWT dos cookies de login.")
            return

        # Decodifica o JWT para pegar o UUID do token
        try:
            payload_part = full_jwt.split('.')[1]
            decoded = json.loads(base64.b64decode(payload_part + "====").decode('utf-8'))
            token_uuid = decoded.get('token')
            
            # Pega o ID do usuário do corpo da resposta
            login_resp = response.json()
            user_id = str(login_resp.get('usuario', {}).get('codigoUsuario'))
        except Exception as e:
            self.logger.error(f"❌ Falha ao decodificar dados do usuário: {e}")
            return

        # Monta o cookie para o curl_cffi
        cookie_completo = f"sessiontoken={full_jwt}; accesstoken={full_jwt}"

        # --- 2. Início da Sessão Async (Impersonate Chrome) ---
        async with AsyncSession(impersonate="chrome120") as s:
            base_headers = {
                'accept': 'application/json, text/plain, */*',
                'accesstoken': token_uuid,
                'loggeduser': user_id,
                'content-type': 'application/json',
                'origin': 'https://pedidoeletronico.servimed.com.br',
                'referer': 'https://pedidoeletronico.servimed.com.br/',
                'Cookie': cookie_completo,
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Authorization': f'Bearer {full_jwt}'
            }

            # --- A: Obter Prazo Médio (Term) ---
            self.logger.info("🔄 Consultando Prazo Médio (Term)...")
            res_term = await s.get(
                f"{self.base_api_url}/cliente/avarage-term/{self.cliente_id}", 
                headers=base_headers, verify=False
            )
            
            if res_term.status_code != 200:
                self.logger.error(f"❌ Erro ao obter Term: {res_term.status_code}")
                return
            
            term_resp = res_term.json() # Ex: 28
            
            term_dias = term_resp.get('term', term_resp) if isinstance(term_resp, dict) else term_resp
            
            # --- B: Obter Condições de Pagamento (Pieces) ---
            self.logger.info(f"🔄 Consultando Condições (Pieces) para {term_dias} dias...")
            res_pieces = await s.get(
                f"{self.base_api_url}/cliente/pieces/{term_dias}", 
                headers=base_headers, verify=False
            )
            
            if res_pieces.status_code != 200:
                self.logger.error(f"❌ Erro ao obter Pieces: {res_pieces.status_code}")
                return
                
            pieces_lista = res_pieces.json() # Ex: [21, 28, 35]

            # --- C: Obter Timestamp (Peperone) ---
            self.logger.info("🔄 Obtendo Timestamp para assinatura...")
            res_time = await s.get(
                f"{self.base_api_url}/Produto/get-timestamp", 
                headers=base_headers, verify=False
            )
            
            if res_time.status_code != 200:
                self.logger.error("❌ Erro ao obter Timestamp")
                return

            # Extrai timestamp limpo (remove aspas se vier string json)
            peperone = str(res_time.json().get('timestamp', res_time.text.strip().replace('"', '')))


            payload_final = {
                "customerId": int(self.cliente_id),
                "userCode": int(user_id),
                "daysOfPlots": int(term_dias),
                "pieces": pieces_lista,
                "quantityPlots": 1,
                "sellId": 1,
                "itens": self.itens_finais_servimed
            }

            # --- E: Gerar Hash de Segurança (X-Cart) ---
            x_cart_sig = gerar_x_cart(payload_final, peperone)
            
            # Prepara headers finais de transmissão
            headers_order = base_headers.copy()
            headers_order.update({
                'x-cart': x_cart_sig,
                'x-peperone': peperone
            })

            # --- F: Transmitir Pedido (O Disparo) ---
            self.logger.info(f"🚀 Transmitindo pedido com {len(self.itens_finais_servimed)} itens...")
            self.logger.debug(f"Payload de Transmissão: {json.dumps(payload_final)}")
            
            res_order = await s.post(
                f"{self.base_api_url}/Pedido/TrasmitirPedido",
                json=payload_final,
                headers=headers_order,
                verify=False
            )

            # --- G: Processar Resultado ---
            if res_order.status_code in [200, 201]:
                resp_json = res_order.json()
                
                if resp_json.get('executado') == 'Ok':
                    self.logger.info("🎉 Transmissão aceita! Aguardando indexação para capturar ID...")
                    
                    # Aguarda um pequeno delay para o sistema da Servimed processar
                    import asyncio
                    await asyncio.sleep(2)

                    # Tenta capturar o ID real do pedido na listagem
                    pedido_real_erp = await self.obter_id_pedido_real(s, base_headers, user_id, self.cnpj, self.cliente_id)

                    if pedido_real_erp:
                        servimed_id = pedido_real_erp.get('id') or pedido_real_erp.get('codigoExterno')
                        situacao_erp = pedido_real_erp.get('situacao')
                        valor_total_erp = pedido_real_erp.get('valorLiquido')
                    else:
                        servimed_id = f"PROTO-{uuid.uuid4().hex[:8].upper()}"
                        situacao_erp = "NÃO LOCALIZADO"
                        valor_total_erp = 0.0

                    self.logger.info(f"Pedido registrado com ID: {servimed_id} | Situação: {situacao_erp} | Valor: {valor_total_erp}")
                    
                    yield {
                        'type': 'order_result',
                        'cliente_nome': self.cliente_nome,
                        'cliente_id': self.cliente_id,
                        'cnpj': self.cnpj,
                        'pedido_unimed': self.itens_finais_servimed,
                        'pedido_aleatorio': self.pedido_aleatorio,
                        'cliente_external_id': self.cliente_external_id,
                        'challenge_order_id': self.id_pedido_aleatorio,
                        'servimed_order_id': servimed_id,
                        'status_final': 'pedido_realizado' if pedido_real_erp else 'realizado_com_protocolo_temporario',
                        'situacao_erp': situacao_erp,         
                        'valor_total_erp': valor_total_erp,   
                        'status_final': 'pedido_realizado',
                        'callback_enviado': False, # Este campo será atualizado no pipeline após o PATCH de callback na API cote fácil
                        'data_processamento': datetime.now().isoformat()
                    }
                else:
                    self.logger.error(f"⚠️ Pedido recusado pelo backend: {resp_json}")
            else:
                self.logger.error(f"💀 Erro HTTP na Transmissão ({res_order.status_code}): {res_order.text}")

    async def obter_id_pedido_real(self, session, base_headers, user_id, cnpj, cliente_id):
        """
        Consulta a API de listagem para capturar o ID do pedido recém criado.
        
        """
        self.logger.info("🔍 Buscando ID do pedido na listagem oficial...")
        
        # 1. Obter novo Timestamp para a assinatura desta consulta
        res_time = await session.get(f"{self.base_api_url}/Produto/get-timestamp", headers=base_headers, verify=False)
        peperone = str(res_time.json().get('timestamp', res_time.text.strip().replace('"', '')))
        self.logger.debug(f"Realizando pesquisa para o cnpj {cnpj}")

        # 2. Montar Payload de Filtro (conforme o cURL enviado)
        payload_busca = {
            "dataInicio": "",
            "dataFim": "",
            "filtro": f"{cnpj}",
            "pagina": 1,
            "registrosPorPagina": 10,
            "codigoExterno": int(self.cliente_id), # Ajuste conforme necessidade (518565 no curl)
            "codigoUsuario": int(user_id),
            "kindSeller": 0,
            "users": [int(user_id), int(cliente_id)]
        }

        # 3. Gerar Assinatura X-Cart
        x_cart_sig = gerar_x_cart(payload_busca, peperone)
        
        headers_busca = base_headers.copy()
        headers_busca.update({
            'x-cart': x_cart_sig,
            'x-peperone': peperone
        })

        # 4. Executar a consulta
        res_pedido = await session.post(
            f"{self.base_api_url}/Pedido",
            json=payload_busca,
            headers=headers_busca,
            verify=False
        )

        if res_pedido.status_code == 200:
            self.logger.info(f"✅ Consulta de pedidos bem-sucedida. retorno obtido: {json.dumps(res_pedido.json())[:200]}...")  # Log parcial para debug
            pedidos = res_pedido.json()['lista'] # Espera-se uma lista de objetos
            self.logger.info(f"Pedidos encontrados na listagem: {json.dumps(pedidos, indent=2)}")
            if not pedidos or not isinstance(pedidos, list):
                self.logger.warning("⚠️ Nenhum pedido encontrado na listagem.")
                return None

            # 5. Filtrar o mais recente com data de hoje
            hoje = datetime.now().strftime("%d/%m/%Y")
            
            for p in pedidos:
                data_p = p.get('dataCadastro', '')
                if hoje in data_p:
                    id_real = p.get('id') or p.get('codigoExterno')
                    self.logger.info(f"✅ ID Real localizado: {id_real}")
                    return p
            
            self.logger.warning("⚠️ Pedido enviado não apareceu na lista com a data de hoje.")
        else:
            self.logger.error(f"❌ Erro ao buscar lista de pedidos: {res_pedido.status_code}")
        
        return None
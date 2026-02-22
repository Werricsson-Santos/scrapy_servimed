import requests
import os # <--- Necessário para ler o .env
from tasks import run_purchase_simulation

class CoteFacilPipeline:
    def __init__(self):
        self.base_url = os.getenv("COTE_FACIL_BASE_URL", "https://desafio.cotefacil.net")

    def process_item(self, item, spider):
        # 1. Filtro Global: Se não for nenhuma das nossas spiders, ignora.
        if spider.name not in ['product_spider', 'order_spider']:
            return item

        # 2. Fluxo da ORDER_SPIDER (Pós-compra na Servimed)
        if spider.name == 'order_spider':
            if item.get('type') == 'order_result':
                return self.processar_callback_pedido(item, spider)
            return item # Se vier outro tipo de item da order_spider, apenas passa adiante

        # 3. Fluxo da PRODUCT_SPIDER (Integração inicial)
        if spider.name == 'product_spider':
            return self.processar_fluxo_produtos(item, spider)

        return item

    def processar_fluxo_produtos(self, item, spider):
        """Toda a sua lógica original de Cadastro -> Login -> Envio -> Task"""
        username_api = f"{item['cliente_nome']}_{item['cliente_id']}"
        password_api = f"{item['cliente_id']}_{item['cliente_external_id']}"
        
        spider.logger.info(f"🚀 INTEGRANDO PRODUTOS: {item['cliente_nome']}")

        token = self.get_auth_token(username_api, password_api, spider)
        if token:
            # Enviar Produtos
            status_code, response_body, qtd = self.send_products(token, item['produtos'], spider)
            item['integrado_com_sucesso'] = status_code in [200, 201]

            # Gatilho do Pedido
            if item['integrado_com_sucesso']:
                pedido_json = self.gerar_pedido_aleatorio(token, spider)
                
                itens_finais_servimed = []

                for item_aleatorio in pedido_json['itens']:  # O que veio do Cote Fácil
                    # Busca o "DNA" completo do produto na lista de originais
                    # Usando o 'codigo' como chave de ligação
                    original = next(
                        (p for p in item['produtos_originais'] if str(p['codigoBarras']) == str(item_aleatorio['gtin'])), 
                        None
                    )

                    if original:
                        qtd = int(item_aleatorio['quantidade'])
                        
                        # Cálculo dos valores totais baseados na quantidade solicitada
                        # Note que a Servimed espera valores proporcionais à quantidade
                        itens_finais_servimed.append({
                            "id": original['id'],
                            "selectedPromotionID": -1,
                            "quantityRequested": qtd,
                            "baseValue": original['valorBase'],
                            "discount": original['desconto'],
                            "discountValue": round(original['valorComDesconto'] * qtd, 2),
                            "stIVA": round(original['stIVA'] * qtd, 2),
                            "taxValue": round(original['valorImposto'] * qtd, 2),
                            "totalValue": round((original['valorComDesconto'] + original['stIVA']) * qtd, 2),
                            "totalStIvaValue": round(original['valorImposto'] * qtd, 2)
                        })
                    else:
                        self.logger.warning(f"⚠️ Produto {item_aleatorio['codigo']} não encontrado nos originais!")
                if pedido_json and 'itens' in pedido_json:
                    task_payload = {
                        "cliente_id": item['cliente_id'],
                        "cliente_external_id": item['cliente_external_id'],
                        "cliente_nome": item['cliente_nome'],
                        "cnpj": item['cnpj'],
                        "id_pedido": pedido_json['id'],
                        "pedido_aleatorio": pedido_json['itens'], # Envia o que veio do desafio para ser escrito no json final, sem misturar com a estrutura da Servimed  
                        "produtos": itens_finais_servimed, # Envia a lista já processada para a task focar só no desafio do pedido
                    }
                    run_purchase_simulation.delay(payload=task_payload)
                    spider.logger.info(f"🔥 TASK DISPARADA: {pedido_json['id']}")
        
        return item # Retorna o item processado para o Scrapy

    def processar_callback_pedido(self, item, spider):
        """Lógica do PATCH que discutimos anteriormente"""
        username_api = f"{item['cliente_nome']}_{item['cliente_id']}"
        password_api = f"{item['cliente_id']}_{item['cliente_external_id']}"
        token = self.get_auth_token(username_api, password_api, spider)
        if token:
            url = f"{self.base_url}/pedido/{item['challenge_order_id']}"
            payload_patch = {
                "codigo_confirmacao": str(item['servimed_order_id']),
                "status": "pedido_realizado"
            }
            res = requests.patch(url, json=payload_patch, headers={"Authorization": f"Bearer {token}"})
            if res.status_code == 200:
                spider.logger.info(f"✅ CALLBACK OK: {item['challenge_order_id']}")
                item['callback_enviado'] = True
        return item

    def gerar_pedido_aleatorio(self, token, spider):
        url = f"{self.base_url}/pedido"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            res = requests.post(url, headers=headers, timeout=15)
            if res.status_code == 201:
                return res.json() # Retorna o JSON {id: 141, itens: [...]}
            spider.logger.error(f"Erro API Pedido: {res.text}")
        except Exception as e:
            spider.logger.error(f"Exceção API Pedido: {e}")
        return None

    # --- MÉTODOS AUXILIARES (Devem estar no mesmo nível de indentação do process_item) ---

    def get_auth_token(self, username, password, spider):
        signup_url = f"{self.base_url}/oauth/signup"
        login_url = f"{self.base_url}/oauth/token"
        
        # 1. Tenta Cadastro
        payload_signup = {"username": username, "password": password}
        try:
            res_signup = requests.post(signup_url, json=payload_signup, timeout=10)
            if res_signup.status_code == 200:
                spider.logger.info(f"Usuário {username} cadastrado.")
                return res_signup.json().get('access_token')
        except Exception as e:
            spider.logger.error(f"Erro de conexão no Signup: {e}")
            return None
        
        # 2. Se já existe, faz Login
        payload_login = {
            "username": username,
            "password": password,
            "grant_type": "password"
        }
        try:
            res_login = requests.post(login_url, data=payload_login, timeout=10)
            if res_login.status_code == 200:
                return res_login.json().get('access_token')
            else:
                spider.logger.error(f"Erro login {username}: {res_login.text}")
        except Exception as e:
            spider.logger.error(f"Erro de conexão no Login: {e}")
        
        return None

    def send_products(self, token, produtos, spider):
        url = f"{self.base_url}/produto"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Validação de GTIN numérico
        produtos_validados = [
            {
                "gtin": str(p['gtin']),
                "codigo": str(p['codigo']),
                "descricao": str(p['descricao']),
                "preco_fabrica": float(p['preco_fabrica'] or 0),
                "estoque": int(p['estoque'] or 0)
            }
            for p in produtos 
            if p.get('gtin') and str(p['gtin']).isdigit()
        ]

        if not produtos_validados:
            return 0, "Nenhum produto com GTIN válido", 0

        try:
            res = requests.post(url, json=produtos_validados, headers=headers, timeout=30)
            try:
                msg = res.json()
            except:
                msg = res.text
            return res.status_code, msg, len(produtos_validados)
        except Exception as e:
            return 500, str(e), len(produtos_validados)
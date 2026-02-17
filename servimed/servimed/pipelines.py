# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import requests

class CoteFacilPipeline:
    def __init__(self):
        self.base_url = "https://desafio.cotefacil.net"

    def process_item(self, item, spider):
        # Filtra para rodar apenas no spider de produtos
        if spider.name != 'product_spider':
            return item

        # Definição das credenciais baseada na regra solicitada
        username = f"{item['empresa_nome']}_{item['empresa_codigo']}"
        password = f"{item['empresa_codigo']}_{item['empresa_codigo_externo']}"
        
        spider.logger.info(f"Iniciando integração Cote Fácil para: {username}")

        # 1. Tentar Signup
        token = self.get_auth_token(username, password, spider)
        
        if token:
            # 2. Enviar Produtos
            self.send_products(token, item['produtos'], spider)
        
        return item

    def get_auth_token(self, username, password, spider):
        signup_url = f"{self.base_url}/oauth/signup"
        login_url = f"{self.base_url}/oauth/token"
        
        # Tenta o cadastro
        payload_signup = {"username": username, "password": password}
        res_signup = requests.post(signup_url, json=payload_signup)
        
        if res_signup.status_code == 200:
            spider.logger.info(f"Usuário {username} cadastrado com sucesso.")
            return res_signup.json().get('access_token')
        
        # Se já existe (Erro 400 conforme seu prompt), tenta o Login
        if res_signup.status_code == 400 or "já registrado" in res_signup.text:
            spider.logger.info(f"Usuário {username} já existente. Realizando login...")
            
            # ATENÇÃO: Rota de token é x-www-form-urlencoded (data= em vez de json=)
            payload_login = {
                "username": username,
                "password": password,
                "grant_type": "password"
            }
            res_login = requests.post(login_url, data=payload_login)
            
            if res_login.status_code == 200:
                return res_login.json().get('access_token')
            else:
                spider.logger.error(f"Falha no login para {username}: {res_login.text}")
        else:
            spider.logger.error(f"Erro inesperado no signup de {username}: {res_signup.text}")
        
        return None

    def send_products(self, token, produtos, spider):
        url = f"{self.base_url}/produto"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Tratamento: A API exige GTIN com dígitos e tamanho mínimo. 
        # Vamos garantir que os campos nulos não quebrem o contrato da API.
        produtos_validados = []
        for p in produtos:
            if p.get('gtin') and str(p['gtin']).isdigit():
                produtos_validados.append({
                    "gtin": str(p['gtin']),
                    "codigo": str(p['codigo']),
                    "descricao": str(p['descricao']),
                    "preco_fabrica": float(p['preco_fabrica'] or 0),
                    "estoque": int(p['estoque'] or 0)
                })

        if not produtos_validados:
            spider.logger.warning("Nenhum produto válido (com GTIN numérico) para enviar.")
            return

        # Envio em lote (Batch) conforme a documentação
        res = requests.post(url, json=produtos_validados, headers=headers)
        
        if res.status_code in [200, 201]:
            spider.logger.info(f"Sucesso! {len(produtos_validados)} produtos integrados no Cote Fácil.")
        else:
            spider.logger.error(f"Erro ao cadastrar produtos: {res.text}")
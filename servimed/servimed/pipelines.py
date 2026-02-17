# servimed/pipelines.py
import requests

class CoteFacilPipeline:
    def __init__(self):
        self.base_url = "https://desafio.cotefacil.net"

    def process_item(self, item, spider):
        # Filtra para rodar apenas no spider de produtos
        if spider.name != 'product_spider':
            return item

        username = f"{item['empresa_nome']}_{item['empresa_codigo']}"
        password = f"{item['empresa_codigo']}_{item['empresa_codigo_externo']}"
        
        # Log Visual de Início
        spider.logger.info(f"\n{'='*70}\n🚀 INICIANDO INTEGRAÇÃO COTE FÁCIL: {item['empresa_nome']}\n{'='*70}")

        # Chama o método auxiliar (que estava faltando/erro)
        token = self.get_auth_token(username, password, spider)
        
        if token:
            status_code, response_body, qtd = self.send_products(token, item['produtos'], spider)
            
            # Enriquecendo o item com o resultado para o Flower ler depois
            item['integracao_status'] = status_code
            item['integracao_response'] = response_body
            item['quantidade_integrada'] = qtd
            item['integrado_com_sucesso'] = status_code in [200, 201]
            
            # Log Visual de Sucesso/Erro
            check = "✅" if item['integrado_com_sucesso'] else "❌"
            spider.logger.info(
                f"\n"
                f"{'#'*60}\n"
                f"{check} INTEGRAÇÃO COTE FÁCIL FINALIZADA\n"
                f"{'-'*60}\n"
                f"🏢 EMPRESA: {item['empresa_nome']}\n"
                f"📦 ITENS ENVIADOS: {qtd}\n"
                f"📡 STATUS API: {status_code}\n"
                f"💬 RESPOSTA: {response_body}\n"
                f"{'#'*60}\n"
            )
        else:
            # Caso falhe no login, marcamos no item também
            item['integrado_com_sucesso'] = False
            item['integracao_status'] = 401
            item['integracao_response'] = "Falha ao obter token (Login)"
            spider.logger.error(f"❌ Falha crítica de autenticação para {username}")
        
        return item

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
import os
import scrapy
import json
import base64
import hmac
import hashlib
from dotenv import load_dotenv
from curl_cffi.requests import AsyncSession

load_dotenv()

    
def gerar_x_cart(payload, timestamp):
    # Chave utilizada para gerar o HMAC
    secret = os.getenv("SERVIMED_SECRET")

    
    payload_str = json.dumps(payload, separators=(',', ':'))
    mensagem = f"{payload_str}{timestamp}"
    
    # Calcula o HMAC-SHA256
    signature = hmac.new(
        secret.encode('utf-8'),
        mensagem.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

class ServimedSpider(scrapy.Spider):
    name = 'servimed'

    # Para facilitar, utiliza como padrão os dados do env, mas permite override via argumentos
    def __init__(self, user=None, password=None, *args, **kwargs):
        super(ServimedSpider, self).__init__(*args, **kwargs)
        self.user = user or os.getenv("SERVIMED_USER") or "not_defined_use_env_or_arguments"
        self.password = password or os.getenv("SERVIMED_PASS") or "not_defined_use_env_or_arguments"

    def start_requests(self):
        url_login = 'https://peapi.servimed.com.br/api/usuario/login'
        payload = {"senha": self.password, "usuario": self.user}
        
        self.logger.info(f"Iniciando login via Scrapy para o usuário {self.user}...")
        yield scrapy.Request(
            url=url_login,
            method='POST',
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            callback=self.after_login
        )

    async def after_login(self, response):
        # 1. Extração de Identidade e Tokens
        set_cookies = response.headers.getlist('Set-Cookie')
        full_jwt = next((c.decode('utf-8').split('accesstoken=')[1].split(';')[0] 
                         for c in set_cookies if b'accesstoken=' in c), None)
        
        payload_part = full_jwt.split('.')[1]
        decoded = json.loads(base64.b64decode(payload_part + "====").decode('utf-8'))
        token_uuid = decoded.get('token')
        user_id = str(response.json().get('usuario', {}).get('codigoUsuario', '22850'))
        codigo_externo_original = response.json().get('usuario', {}).get('codigoExterno', 518565)

        cookie_completo = f"sessiontoken={full_jwt}; accesstoken={full_jwt}"

        async with AsyncSession(impersonate="chrome120") as s:
            base_headers = {
                'accept': 'application/json, text/plain, */*',
                'accesstoken': token_uuid,
                'loggeduser': user_id,
                'content-type': 'application/json',
                'contenttype': 'application/json',
                'origin': 'https://pedidoeletronico.servimed.com.br',
                'referer': 'https://pedidoeletronico.servimed.com.br/',
                'Cookie': cookie_completo,
                'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
            }

            # PASSO 1: findByFilter para obter a lista de empresas
            payload_filter = {
                "filtro": "", "pagina": 1, "registrosPorPagina": 20,
                "codigoExterno": int(codigo_externo_original), "codigoUsuario": int(user_id),
                "users": [518565, 267511], "list": True
            }
            
            res_filter = await s.post("https://peapi.servimed.com.br/api/cliente/findByFilter", 
                                     json=payload_filter, headers=base_headers, verify=False)
            
            if res_filter.status_code != 200:
                self.logger.error(f"Erro ao obter lista de empresas: {res_filter.status_code}")
                return

            empresas = res_filter.json().get('lista', [])
            self.logger.info(f"Encontradas {len(empresas)} empresas. Iniciando extração individual...")

            # PASSO 2: Loop pelas empresas (filtrando apenas ATIVAS)
            for empresa in empresas:
                # No momento não existem empresas ativas, mas caso haja, o filtro pode ser reativado
                # if empresa.get('situacao') != 'ATIVO':
                #     continue
                
                cliente_id = empresa.get('codigo')
                codigo_externo = empresa.get('codigoExterno')
                razao_social = empresa.get('razaoSocial')
                
                produtos_acumulados = []
                
                self.logger.info(f"Processando: {razao_social} ({cliente_id})")

                payload_cart = {
                    "filtro": "", "pagina": 1, "registrosPorPagina": 50,
                    "ordenarDecrescente": False, "colunaOrdenacao": "nenhuma",
                    "clienteId": int(cliente_id), "tipoVendaId": 1,
                    "fabricanteIdFiltro": 0, "pIIdFiltro": 0, "cestaPPFiltro": False,
                    "codigoExterno": 0, "codigoUsuario": int(user_id),
                    "promocaoSelecionada": "", "indicadorTipoUsuario": "CLI",
                    "kindUser": 0, "xlsx": [], "principioAtivo": "",
                    "master": False, "kindSeller": 0, "grupoEconomico": "",
                    "users": [int(codigo_externo), int(cliente_id)], "list": True
                }


                # A: Obter Timestamp (Peperone) para esta empresa
                res_time = await s.get("https://peapi.servimed.com.br/api/Produto/get-timestamp", 
                                      headers=base_headers, verify=False)
                try:
                    peperone_json = res_time.json()
                    peperone = str(peperone_json.get('timestamp', peperone_json))
                except:
                    peperone = res_time.text.strip().replace('"', '')

                self.logger.info(f"Timestamp (Peperone) obtido: {peperone} para {razao_social}")

                x_cart_dinamico = gerar_x_cart(payload_cart, peperone)
                self.logger.info(f"x-cart gerado: {x_cart_dinamico} para {razao_social}")

                # B: Preparar headers e payload para o Carrinho Oculto
                headers_cart = base_headers.copy()
                headers_cart.update({
                    'x-cart': x_cart_dinamico,
                    'x-peperone': peperone,
                    'Authorization': f'Bearer {full_jwt}'
                })


                # C: Requisição inicial para obter o total de registros e calcular a paginação necessária
                res_total = await s.post("https://peapi.servimed.com.br/api/carrinho/oculto?siteVersion=4.0.29",
                                        json=payload_cart, headers=headers_cart, verify=False)

                itens_por_pagina = 50
                if res_total.status_code == 200:
                    total_registros = int(res_total.json().get('totalRegistros', 0))
                    total_paginas = (total_registros // itens_por_pagina) + (1 if total_registros % itens_por_pagina > 0 else 0)
                    total_paginas = 1

                    self.logger.info(f"Total de registros para {razao_social}: {total_registros}. Total de páginas: {total_paginas}")

                    for pag in range(1, total_paginas + 1):
                        # Atualiza o payload para a página atual
                        payload_cart.update({
                            "pagina": pag,
                            "registrosPorPagina": itens_por_pagina,
                            "users": [int(codigo_externo), int(cliente_id)]
                        })

                        if pag > 1:
                            self.logger.info(f"Processando página {pag} de {total_paginas} para {razao_social}...\nQuantidade produtos acumulados: {len(produtos_acumulados)}")

                        # Gera o x-cart para o payload específico desta página
                        res_time = await s.get("https://peapi.servimed.com.br/api/Produto/get-timestamp", headers=base_headers, verify=False)
                        peperone = str(res_time.json().get('timestamp'))
                        
                        headers_cart.update({
                            'x-cart': gerar_x_cart(payload_cart, peperone),
                            'x-peperone': peperone
                        })

                        res_cart = await s.post("https://peapi.servimed.com.br/api/carrinho/oculto?siteVersion=4.0.29",
                                                json=payload_cart, headers=headers_cart, verify=False)

                        if res_cart.status_code == 200:
                            dados_lista = res_cart.json().get('lista', [])
                            for item in dados_lista:
                                # Filtra apenas os atributos desejados e faz o push na lista da empresa
                                produtos_acumulados.append({
                                    "gtin": item.get("gtin"),
                                    "codigo": item.get("codigo"),
                                    "descricao": item.get("descricao"),
                                    "preco_fabrica": item.get("precoFabrica"),
                                    "estoque": item.get("estoque")
                                })
                        else:
                            self.logger.error(f"Erro na pág {pag} de {razao_social}: {res_cart.status_code}")

                    # APÓS coletar todas as páginas da empresa, faz o yield do objeto estruturado
                    if produtos_acumulados:
                        self.logger.info(f"Total de produtos coletados para {razao_social}: {len(produtos_acumulados)}")
                        yield {
                            "empresa_nome": razao_social,
                            "empresa_codigo": cliente_id,
                            "produtos": produtos_acumulados
                        }
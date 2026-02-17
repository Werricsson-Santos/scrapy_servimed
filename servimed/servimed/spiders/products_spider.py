import os
import scrapy
import json
import base64
import hmac
import hashlib
from curl_cffi.requests import AsyncSession

def gerar_x_cart(payload, timestamp):
    secret = os.getenv("SERVIMED_SECRET")
    payload_str = json.dumps(payload, separators=(',', ':'))
    mensagem = f"{payload_str}{timestamp}"
    signature = hmac.new(
        secret.encode('utf-8'),
        mensagem.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

class ProductSpider(scrapy.Spider):
    name = 'product_spider'

    def __init__(self, user=None, password=None, razao=None, cliente_id=None, external_id=None, *args, **kwargs):
        super(ProductSpider, self).__init__(*args, **kwargs)
        self.user = user or os.getenv("SERVIMED_USER")
        self.password = password or os.getenv("SERVIMED_PASS")
        self.razao = razao
        self.cliente_id = cliente_id
        self.external_id = external_id

        self.logger.info(f"argumentos recebidos - user: {self.user}, razao: {self.razao}, cliente_id: {self.cliente_id}, external_id: {self.external_id}")

    def start_requests(self):
        url_login = 'https://peapi.servimed.com.br/api/usuario/login'
        payload = {"senha": self.password, "usuario": self.user}
        
        self.logger.info(f"Iniciando raspagem de PRODUTOS para: {self.razao} ({self.cliente_id})")
        
        yield scrapy.Request(
            url=url_login,
            method='POST',
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            callback=self.after_login,
            dont_filter=True
        )

    async def after_login(self, response):
        # 1. Extração de Identidade e Tokens
        set_cookies = response.headers.getlist('Set-Cookie')
        full_jwt = next((c.decode('utf-8').split('accesstoken=')[1].split(';')[0] 
                         for c in set_cookies if b'accesstoken=' in c), None)
        
        if not full_jwt:
            self.logger.error(f"Falha ao obter JWT para {self.razao}")
            return

        payload_part = full_jwt.split('.')[1]
        decoded = json.loads(base64.b64decode(payload_part + "====").decode('utf-8'))
        token_uuid = decoded.get('token')
        user_id = str(response.json().get('usuario', {}).get('codigoUsuario'))
        
        cookie_completo = f"sessiontoken={full_jwt}; accesstoken={full_jwt}"

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

            produtos_acumulados = []
            itens_por_pagina = 50
            
            # Payload base para o Carrinho Oculto
            payload_cart = {
                "filtro": "", "pagina": 1, "registrosPorPagina": itens_por_pagina,
                "ordenarDecrescente": False, "colunaOrdenacao": "nenhuma",
                "clienteId": int(self.cliente_id), "tipoVendaId": 1,
                "fabricanteIdFiltro": 0, "pIIdFiltro": 0, "cestaPPFiltro": False,
                "codigoExterno": 0, "codigoUsuario": int(user_id),
                "promocaoSelecionada": "", "indicadorTipoUsuario": "CLI",
                "kindUser": 0, "xlsx": [], "principioAtivo": "",
                "master": False, "kindSeller": 0, "grupoEconomico": "",
                "users": [int(self.external_id), int(self.cliente_id)], 
                "list": True
            }

            # A: Requisição inicial para obter o total de registros (Página 1)
            res_time = await s.get("https://peapi.servimed.com.br/api/Produto/get-timestamp", headers=base_headers, verify=False)
            peperone = str(res_time.json().get('timestamp', res_time.text.strip().replace('"', '')))

            headers_cart = base_headers.copy()
            headers_cart.update({
                'x-cart': gerar_x_cart(payload_cart, peperone),
                'x-peperone': peperone
            })

            res_initial = await s.post("https://peapi.servimed.com.br/api/carrinho/oculto?siteVersion=4.0.29",
                                       json=payload_cart, headers=headers_cart, verify=False)

            if res_initial.status_code == 200:
                data = res_initial.json()
                self.logger.info(f"dados obtidos {json.dumps(data)[:500]}...")  # Log parcial dos dados para debug
                total_registros = int(data.get('totalRegistros'))
                total_paginas = (total_registros // 25) + (1 if total_registros % 25 > 0 else 0)
                
                self.logger.info(f"Total para {self.razao} | {self.cliente_id}: {total_registros} itens em {total_paginas} páginas.")

                # Processa a primeira página já obtida
                for item in data.get('lista', []):
                    produtos_acumulados.append({
                        "gtin": item.get("gtin"),
                        "codigo": item.get("codigo"),
                        "descricao": item.get("descricao"),
                        "preco_fabrica": item.get("precoFabrica"),
                        "estoque": item.get("estoque")
                    })

                # B: Loop para as demais páginas (se houver)
                for pag in range(2, total_paginas + 1):
                    self.logger.info(f"Coletando página {pag}/{total_paginas} de {self.razao} | {self.cliente_id}...")
                    
                    payload_cart["pagina"] = pag
                    
                    # Renovação do Timestamp (Peperone) por página para evitar expiração do x-cart
                    res_time = await s.get("https://peapi.servimed.com.br/api/Produto/get-timestamp", headers=base_headers, verify=False)
                    peperone = str(res_time.json().get('timestamp', res_time.text.strip().replace('"', '')))
                    
                    headers_cart.update({
                        'x-cart': gerar_x_cart(payload_cart, peperone),
                        'x-peperone': peperone
                    })

                    res_pag = await s.post("https://peapi.servimed.com.br/api/carrinho/oculto?siteVersion=4.0.29",
                                           json=payload_cart, headers=headers_cart, verify=False)

                    if res_pag.status_code == 200:
                        for item in res_pag.json().get('lista', []):
                            produtos_acumulados.append({
                                "gtin": item.get("gtin"),
                                "codigo": item.get("codigo"),
                                "descricao": item.get("descricao"),
                                "preco_fabrica": item.get("precoFabrica"),
                                "estoque": item.get("estoque")
                            })
                    else:
                        self.logger.error(f"Erro na pág {pag} de {self.razao} | {self.cliente_id}: {res_pag.status_code}")

                # --- YIELD FINAL APÓS TODAS AS PÁGINAS ---
                if produtos_acumulados:
                    self.logger.info(f"Finalizado: {len(produtos_acumulados)} produtos para {self.razao} | {self.cliente_id}")
                    yield {
                        "empresa_nome": self.razao,
                        "empresa_codigo": self.cliente_id,
                        "empresa_codigo_externo": self.external_id,
                        "produtos": produtos_acumulados
                    }
            else:
                self.logger.error(f"Erro no login/carrinho de {self.razao} | {self.cliente_id}: {res_initial.status_code}")
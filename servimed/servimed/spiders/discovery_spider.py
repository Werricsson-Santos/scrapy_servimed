import os
import scrapy
import json
import base64
from curl_cffi.requests import AsyncSession
from tasks import run_product_scraping

class DiscoverySpider(scrapy.Spider):
    name = 'discovery'
    
    def start_requests(self):
        # O login inicial pode ser feito via Scrapy padrão para obter os cookies/JWT
        url_login = 'https://peapi.servimed.com.br/api/usuario/login'
        payload = {
            "senha": self.settings.get('SERVIMED_PASS'), 
            "usuario": self.settings.get('SERVIMED_USER')
        }

        self.logger.info("Realizando login via Scrapy para descobrir empresas...")
        
        yield scrapy.Request(
            url=url_login,
            method='POST',
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            callback=self.after_login
        )

    async def after_login(self, response):
        # 1. Extração do Token JWT dos Cookies
        set_cookies = response.headers.getlist('Set-Cookie')
        full_jwt = next((c.decode('utf-8').split('accesstoken=')[1].split(';')[0] 
                         for c in set_cookies if b'accesstoken=' in c), None)
        
        if not full_jwt:
            self.logger.error("Não foi possível capturar o JWT no login.")
            return

        # 2. Decodificação do Payload do JWT para obter o token_uuid
        payload_part = full_jwt.split('.')[1]
        decoded = json.loads(base64.b64decode(payload_part + "====").decode('utf-8'))
        token_uuid = decoded.get('token')
        
        # 3. Dados para o filtro
        user_id = str(response.json().get('usuario', {}).get('codigoUsuario', '22850'))
        codigo_ext_login = response.json().get('usuario', {}).get('codigoExterno', 518565)
        
        cookie_completo = f"sessiontoken={full_jwt}; accesstoken={full_jwt}"

        # 4. Início da Sessão com curl_cffi para evitar 403 no findByFilter
        async with AsyncSession(impersonate="chrome120") as s:
            headers = {
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

            payload_filter = {
                "filtro": "", "pagina": 1, "registrosPorPagina": 100,
                "codigoExterno": int(codigo_ext_login), "codigoUsuario": int(user_id),
                "users": [518565, 267511], "list": True
            }
            
            self.logger.info("Buscando lista de empresas via curl_cffi...")
            
            res = await s.post(
                "https://peapi.servimed.com.br/api/cliente/findByFilter",
                json=payload_filter,
                headers=headers,
                verify=False
            )

            if res.status_code == 200:
                empresas = res.json().get('lista', [])
                self.logger.info(f"Encontradas {len(empresas)} empresas.")

                for empresa in empresas:
                    dados_empresa = {
                        "razao": empresa.get('razaoSocial'),
                        "cliente_id": empresa.get('codigo'),
                        "external_id": empresa.get('codigoExterno'),
                        "situacao": empresa.get('situacao')
                    }
                    
                    # Envia para a fila do Celery/Redis
                    run_product_scraping.delay(
                        user=self.settings.get('SERVIMED_USER'), 
                        password=self.settings.get('SERVIMED_PASS'),
                        **dados_empresa
                    )
                    self.logger.info(f"Fila -> Empresa: {dados_empresa['razao']}")

                    yield dados_empresa
            else:
                self.logger.error(f"Erro ao buscar empresas: {res.status_code} - {res.text}")
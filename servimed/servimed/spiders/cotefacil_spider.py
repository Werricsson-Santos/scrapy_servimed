import scrapy
import json
import base64

class CotefacilSpider(scrapy.Spider):
    name = 'cotefacil_spider'
    
    # Base URL corrigida para o subdomínio de API (peapi) verificado anteriormente
    base_url = 'https://desafio.cotefacil.net'

    def start_requests(self):
        url_auth = f"{self.base_url}/oauth/token"
        
        # O Swagger especifica x-www-form-urlencoded
        payload = {
            "grant_type": "password",
            "username": "juliano@farmaprevonline.com.br",
            "password": "a007299A",
            "scope": "",
            "client_id": "null",
            "client_secret": "null"
        }

        self.logger.info(f"Solicitando access_token em: {url_auth}")
        
        yield scrapy.FormRequest(
            url=url_auth,
            formdata=payload,
            callback=self.after_login
        )

    def after_login(self, response):
        # Log da resposta bruta para depuração do erro 'Expecting value'
        self.logger.info(f"Resposta bruta recebida: {response.text[:200]}")

        if response.status != 200 or not response.text:
            self.logger.error(f"Falha na autenticação ou resposta vazia. Status: {response.status}")
            return

        try:
            # A resposta deve seguir o esquema AuthInfo
            auth_data = response.json()
            token = auth_data.get('access_token')
            token_type = auth_data.get('token_type', 'Bearer')
            
            # Endpoint GET /produto conforme OpenAPI
            url_produtos = f"{self.base_url}/produto"
            
            headers = {
                'Authorization': f'{token_type} {token}',
                'Accept': 'application/json'
            }

            yield scrapy.Request(
                url=url_produtos,
                method='GET',
                headers=headers,
                callback=self.parse_produtos
            )
        except json.JSONDecodeError:
            self.logger.error("A resposta não é um JSON válido. Verifique a 'Resposta bruta' acima.")

    def parse_produtos(self, response):
        # Processa a lista de objetos conforme o esquema Produto
        if response.status == 200:
            produtos = response.json()
            for produto in produtos:
                yield {
                    'gtin': produto.get('gtin'),
                    'codigo': produto.get('codigo'),
                    'descricao': produto.get('descricao'),
                    'preco_fabrica': produto.get('preco_fabrica'),
                    'estoque': produto.get('estoque')
                }
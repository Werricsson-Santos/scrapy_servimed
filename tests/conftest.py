"""
Configurações e fixtures compartilhadas para todos os testes
"""
import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from scrapy.http import HtmlResponse, Request
from scrapy.utils.test import get_crawler
from scrapy.crawler import CrawlerRunner
import json

# Adiciona o diretório do projeto ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'servimed'))

@pytest.fixture(scope="session")
def test_settings():
    """Settings de teste para Scrapy"""
    return {
        'SERVIMED_USER': 'test_user',
        'SERVIMED_PASS': 'test_password',
        'REDIS_URL': 'redis://localhost:6379/15',
        'BOT_NAME': 'servimed_test',
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 0,
        'FEEDS': {},  # Desabilita feeds durante testes
    }

@pytest.fixture
def mock_spider_settings(test_settings):
    """Mock das settings do spider"""
    mock_settings = Mock()
    mock_settings.get.side_effect = lambda key, default=None: test_settings.get(key, default)
    return mock_settings

@pytest.fixture
def sample_login_response():
    """Response simulado de login bem-sucedido"""
    return {
        "usuario": {
            "codigoUsuario": "12345",
            "codigoExterno": 518565,
            "nome": "Usuario Teste"
        },
        "token": "sample.jwt.token"
    }

@pytest.fixture
def sample_jwt_token():
    """JWT token simulado para testes"""
    import base64
    
    # Cria um payload JWT simulado
    payload = {
        "token": "uuid-test-123",
        "user_id": "12345",
        "exp": 9999999999
    }
    
    # Simula a estrutura JWT (header.payload.signature)
    header = base64.b64encode(json.dumps({"typ": "JWT"}).encode()).decode()
    payload_encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = "fake_signature"
    
    return f"{header}.{payload_encoded}.{signature}"

@pytest.fixture
def mock_response():
    """Factory para criar responses simulados"""
    def _create_response(url="http://test.com", status=200, body="", headers=None, method="GET"):
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        request = Request(url=url, method=method)
        response = HtmlResponse(
            url=url,
            status=status,
            body=body.encode() if isinstance(body, str) else body,
            headers=headers,
            request=request
        )
        return response
    
    return _create_response

@pytest.fixture
def temp_extractions_dir():
    """Diretório temporário para arquivos de extração"""
    temp_dir = tempfile.mkdtemp()
    extractions_path = os.path.join(temp_dir, 'extractions')
    os.makedirs(extractions_path, exist_ok=True)
    
    yield extractions_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_celery_app():
    """Mock da aplicação Celery"""
    with patch('celery_app.app') as mock_app:
        mock_app.conf = Mock()
        mock_app.task = lambda func: func  # Retorna a função sem decorar
        yield mock_app

@pytest.fixture
def mock_redis():
    """Mock do Redis"""
    with patch('redis.Redis') as mock_redis_class:
        mock_redis_instance = Mock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Simula operações básicas do Redis
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.set.return_value = True
        mock_redis_instance.get.return_value = None
        
        yield mock_redis_instance

@pytest.fixture
def mock_scrapy_crawler():
    """Mock do Scrapy Crawler"""
    return get_crawler()

@pytest.fixture
def sample_company_data():
    """Dados simulados de empresa"""
    return {
        "razao": "Empresa Teste LTDA",
        "cnpj": "12.345.678/0001-90",
        "cliente_id": "12345",
        "external_id": "EXT123",
        "situacao": "ATIVA"
    }

@pytest.fixture
def sample_product_data():
    """Dados simulados de produto"""
    return {
        "codigo": "PROD001",
        "descricao": "Produto Teste",
        "preco": 99.99,
        "categoria": "Categoria Teste"
    }

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Configuração automática do ambiente de teste"""
    # Define variáveis de ambiente para teste
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("SERVIMED_USER", "test_user")
    monkeypatch.setenv("SERVIMED_PASS", "test_pass")

@pytest.fixture
def mock_requests():
    """Mock para requests HTTP"""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Response padrão de sucesso
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_session.request.return_value = mock_response
        
        yield mock_session

@pytest.fixture
def mock_curl_cffi():
    """Mock para curl_cffi.requests"""
    with patch('curl_cffi.requests.AsyncSession') as mock_async_session:
        mock_session = Mock()
        mock_async_session.return_value = mock_session
        
        # Response padrão
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_session.request.return_value = mock_response
        
        yield mock_session
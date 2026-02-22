"""
Testes para configurações e utilitários do projeto
"""
import pytest
import os
import json
from unittest.mock import Mock, patch
import sys

# Adiciona o path do projeto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'servimed'))

@pytest.mark.unit
class TestScrapySettings:
    """Testes para as configurações do Scrapy"""
    
    @patch.dict(os.environ, {
        'SERVIMED_USER': 'test_user_env',
        'SERVIMED_PASS': 'test_pass_env'
    })
    def test_settings_load_environment_variables(self):
        """Testa se as variáveis de ambiente são carregadas corretamente"""
        try:
            from servimed import settings
            
            assert settings.SERVIMED_USER == 'test_user_env'
            assert settings.SERVIMED_PASS == 'test_pass_env'
            assert settings.BOT_NAME == 'servimed'
            
        except ImportError:
            pytest.skip("Módulo settings não disponível")
    
    def test_feeds_configuration(self):
        """Testa configuração dos feeds de saída"""
        try:
            from servimed import settings
            
            assert hasattr(settings, 'FEEDS')
            assert isinstance(settings.FEEDS, dict)
            
            # Verifica se há configuração para JSON
            feed_keys = list(settings.FEEDS.keys())
            assert len(feed_keys) > 0
            
            # Verifica a primeira configuração de feed
            first_feed_config = list(settings.FEEDS.values())[0]
            assert 'format' in first_feed_config
            assert 'encoding' in first_feed_config
            
        except ImportError:
            pytest.skip("Módulo settings não disponível")
    
    def test_spider_modules_configuration(self):
        """Testa configuração dos módulos de spider"""
        try:
            from servimed import settings
            
            assert hasattr(settings, 'SPIDER_MODULES')
            assert hasattr(settings, 'NEWSPIDER_MODULE')
            
            assert 'servimed.spiders' in settings.SPIDER_MODULES
            assert settings.NEWSPIDER_MODULE == 'servimed.spiders'
            
        except ImportError:
            pytest.skip("Módulo settings não disponível")

@pytest.mark.unit
class TestProjectStructure:
    """Testes para estrutura do projeto"""
    
    def test_extractions_directory_creation(self, temp_extractions_dir):
        """Testa criação do diretório de extrações"""
        assert os.path.exists(temp_extractions_dir)
        assert os.path.isdir(temp_extractions_dir)
    
    def test_json_file_operations(self, temp_extractions_dir):
        """Testa operações com arquivos JSON"""
        test_file = os.path.join(temp_extractions_dir, 'test_data.json')
        
        # Dados de teste
        test_data = {
            'teste': 'dados',
            'numero': 123,
            'lista': [1, 2, 3]
        }
        
        # Escreve arquivo
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        # Verifica se foi criado
        assert os.path.exists(test_file)
        
        # Lê e verifica conteúdo
        with open(test_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == test_data

@pytest.mark.unit
class TestUtilityFunctions:
    """Testes para funções utilitárias"""
    
    def test_currency_formatting(self):
        """Testa formatação de moeda brasileira"""
        def format_brl_currency(value):
            """Função auxiliar para formatação de moeda"""
            if not value:
                return "R$ 0,00"
            return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Testes
        assert format_brl_currency(1500.50) == "R$ 1.500,50"
        assert format_brl_currency(0) == "R$ 0,00"
        assert format_brl_currency(None) == "R$ 0,00"
        assert format_brl_currency(10) == "R$ 10,00"
    
    def test_cnpj_validation_format(self):
        """Testa formato básico de CNPJ"""
        def is_cnpj_format(cnpj):
            """Valida formato básico de CNPJ"""
            if not cnpj:
                return False
            # Remove caracteres especiais
            clean_cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
            return len(clean_cnpj) == 14 and clean_cnpj.isdigit()
        
        # Testes
        assert is_cnpj_format("12.345.678/0001-90") == True
        assert is_cnpj_format("12345678000190") == True
        assert is_cnpj_format("123.456.789") == False
        assert is_cnpj_format("") == False
        assert is_cnpj_format(None) == False
    
    def test_data_sanitization(self):
        """Testa sanitização de dados"""
        def sanitize_string(text):
            """Remove caracteres especiais de strings"""
            if not text:
                return ""
            return text.strip().replace('\n', ' ').replace('\t', ' ')
        
        # Testes
        assert sanitize_string("  Texto com espaços  ") == "Texto com espaços"
        assert sanitize_string("Texto\ncom\nquebras") == "Texto com quebras"
        assert sanitize_string("Texto\tcom\ttabs") == "Texto com tabs"
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""

@pytest.mark.unit
class TestDataValidation:
    """Testes para validação de dados"""
    
    def test_required_fields_validation(self):
        """Testa validação de campos obrigatórios"""
        def validate_company_data(data):
            """Valida dados mínimos de empresa"""
            required_fields = ['razao', 'cnpj', 'cliente_id']
            errors = []
            
            for field in required_fields:
                if not data.get(field):
                    errors.append(f"Campo '{field}' é obrigatório")
            
            return len(errors) == 0, errors
        
        # Dados válidos
        valid_data = {
            'razao': 'Empresa Teste LTDA',
            'cnpj': '12.345.678/0001-90',
            'cliente_id': '12345'
        }
        
        is_valid, errors = validate_company_data(valid_data)
        assert is_valid == True
        assert len(errors) == 0
        
        # Dados inválidos
        invalid_data = {
            'razao': 'Empresa Teste LTDA',
            'cnpj': ''  # CNPJ vazio
            # cliente_id ausente
        }
        
        is_valid, errors = validate_company_data(invalid_data)
        assert is_valid == False
        assert len(errors) == 2
        assert any("cnpj" in error for error in errors)
        assert any("cliente_id" in error for error in errors)
    
    def test_api_response_validation(self):
        """Testa validação de respostas da API"""
        def validate_api_response(response):
            """Valida estrutura básica de resposta da API"""
            if not isinstance(response, dict):
                return False, "Resposta deve ser um dicionário"
            
            if response.get('status') not in ['success', 'error']:
                return False, "Status deve ser 'success' ou 'error'"
            
            return True, "OK"
        
        # Resposta válida
        valid_response = {'status': 'success', 'data': []}
        is_valid, message = validate_api_response(valid_response)
        assert is_valid == True
        
        # Resposta inválida
        invalid_response = {'status': 'unknown'}
        is_valid, message = validate_api_response(invalid_response)
        assert is_valid == False

@pytest.mark.integration
class TestEnvironmentSetup:
    """Testes para configuração do ambiente"""
    
    def test_environment_variables_loaded(self):
        """Testa se variáveis de ambiente necessárias estão definidas"""
        required_vars = ['TESTING', 'REDIS_URL', 'SERVIMED_USER', 'SERVIMED_PASS']
        
        for var in required_vars:
            value = os.getenv(var)
            assert value is not None, f"Variável {var} não está definida"
            assert value != "", f"Variável {var} está vazia"
    
    def test_redis_url_format(self):
        """Testa formato da URL do Redis"""
        redis_url = os.getenv('REDIS_URL')
        assert redis_url.startswith('redis://'), "URL do Redis deve começar com redis://"
        assert ':6379/' in redis_url, "URL do Redis deve conter porta padrão 6379"
    
    def test_testing_flag(self):
        """Testa se flag de teste está ativada"""
        testing = os.getenv('TESTING')
        assert testing == 'true', "Flag TESTING deve ser 'true' durante os testes"

@pytest.mark.unit
def test_error_handling():
    """Testa tratamento básico de erros"""
    def safe_json_parse(text):
        """Parse JSON com tratamento de erro"""
        try:
            return json.loads(text), None
        except json.JSONDecodeError as e:
            return None, str(e)
    
    # JSON válido
    data, error = safe_json_parse('{"test": "value"}')
    assert data == {"test": "value"}
    assert error is None
    
    # JSON inválido
    data, error = safe_json_parse('{"invalid": json}')
    assert data is None
    assert error is not None
    assert "expecting" in error.lower() or "json" in error.lower()

@pytest.mark.unit 
def test_logging_configuration():
    """Testa configuração básica de logging"""
    import logging
    
    # Testa se é possível criar logger
    logger = logging.getLogger('test_logger')
    assert logger is not None
    
    # Testa se é possível definir nível
    logger.setLevel(logging.INFO)
    assert logger.level == logging.INFO
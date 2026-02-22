@echo off
REM Script para executar testes automatizados no Windows
REM Uso: test.bat [opcoes]

echo.
echo 🧪 Scrapy Servimed - Testes Automatizados
echo ==========================================

REM Verifica se está no diretório correto
if not exist "servimed" (
    echo ❌ Execute este script a partir da raiz do projeto
    echo    ^(onde esta o diretorio servimed/^)
    exit /b 1
)

REM Verifica se Python está disponível
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado. Instale Python 3.11+
    exit /b 1
)

REM Verifica se pytest está instalado
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  pytest nao encontrado. Instalando dependencias...
    python -m pip install -r requirements.txt
)

echo.
echo 🔄 Executando testes...
echo.

REM Executa os testes baseado nos parâmetros
if "%1"=="--fast" (
    echo "Executando apenas testes unitarios..."
    python -m pytest -m unit -v
) else if "%1"=="--coverage" (
    echo "Executando testes com cobertura..."
    python -m pytest --cov=servimed --cov-report=html --cov-report=term-missing -v
) else if "%1"=="--integration" (
    echo "Executando testes de integracao..."
    python -m pytest -m integration -v
) else (
    echo "Executando todos os testes..."
    python -m pytest -v
)

REM Verifica resultado
if errorlevel 1 (
    echo.
    echo ❌ Alguns testes falharam
    exit /b 1
) else (
    echo.
    echo ✅ Todos os testes passaram!
    if "%1"=="--coverage" (
        echo.
        echo 📊 Relatorio de cobertura disponivel em: htmlcov\index.html
    )
)

echo.
echo 💡 Dica: Use as opcoes --fast, --coverage ou --integration
echo    Exemplo: test.bat --coverage
echo.
<h1 align="center">🕷️ Servimed Scraper (Nível 1 - Básico)</h1>

<p align='center'>
    <a href="https://docs.scrapy.org/">
        <img src="https://img.shields.io/badge/Executar%20Scrapy-60A839?style=for-the-badge&logo=scrapy&logoColor=white" />
    </a>
</p>

<p align='center'> 
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
    <img src="https://img.shields.io/badge/Scrapy-2.11.2-60A839?style=for-the-badge&logo=scrapy&logoColor=white"/>
    <img src="https://img.shields.io/badge/JSON-Local-FFB84D?style=for-the-badge&logo=json&logoColor=white"/>
</p>

<p>Este projeto é um sistema de web scraping <strong>simples e direto</strong> para extrair dados do portal Servimed utilizando <strong>Scrapy</strong>. Os dados são salvos localmente em arquivos JSON e a execução é feita diretamente no terminal, sem necessidade de containerização ou processamento distribuído.</p>

<h2>📋 Índice</h2>

<ul>
    <li><a href="#-funcionalidades">🚀 Funcionalidades</a></li>
    <li><a href="#-pré-requisitos">🔧 Pré-requisitos</a></li>
    <li><a href="#️-instalação">⚙️ Instalação</a></li>
    <li><a href="#-uso">📱 Uso</a></li>
    <li><a href="#-resultados">📊 Resultados</a></li>
    <li><a href="#-estrutura-do-projeto">📁 Estrutura do Projeto</a></li>
    <li><a href="#-troubleshooting">🐛 Troubleshooting</a></li>
</ul>

<h2>🚀 Funcionalidades</h2>

<ul>
    <li>✅ <strong>Scraping direto</strong> com Scrapy puro</li>
    <li>✅ <strong>Execução simples</strong> via terminal</li>
    <li>✅ <strong>Armazenamento local</strong> em JSON/JSONLines</li>
    <li>✅ <strong>Autenticação automática</strong> na API Servimed</li>
    <li>✅ <strong>Spider Servimed</strong> para extrair dados principais</li>
    <li>✅ <strong>Configuração flexível</strong> via variáveis de ambiente</li>
</ul>

<h2>🔧 Pré-requisitos</h2>

<p>Antes de começar, certifique-se de ter instalado:</p>

<h3>Windows/Linux/macOS</h3>
<ul>
    <li>🐍 <strong>Python 3.11+</strong> (<a href="https://www.python.org/downloads/">Download</a>)</li>
    <li>📦 <strong>pip</strong> (incluído no Python)</li>
    <li>📦 <strong>Git</strong> (<a href="https://git-scm.com/downloads">Download</a>)</li>
</ul>

<h2>⚙️ Instalação</h2>

<h3>1. Clone o repositório</h3>
<pre><code>git clone https://github.com/Werricsson-Santos/scrapy_servimed.git
cd scrapy_servimed
</code></pre>

<p><strong>ℹ️ Info:</strong> Por padrão, o clone vem na branch <code>master</code> que já contém a versão simples do projeto.</p>

<h3>2. Criar ambiente virtual (recomendado)</h3>
<pre><code># Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS  
python3 -m venv .venv
source .venv/bin/activate
</code></pre>

<h3>3. Instalar dependências</h3>
<pre><code>pip install -r requirements.txt
</code></pre>

<h3>4. Configurar variáveis de ambiente</h3>
<p>Crie um arquivo <code>.env</code> na raiz do projeto:</p>
<pre><code># Credenciais Servimed
SERVIMED_USER=seu_usuario_aqui
SERVIMED_PASS=sua_senha_aqui
</code></pre>

<p><strong>⚠️ Importante:</strong> Substitua <code>seu_usuario_aqui</code> e <code>sua_senha_aqui</code> pelas suas credenciais reais do Servimed.</p>

<p><strong>💡 Alternativa:</strong> Se preferir não criar o arquivo <code>.env</code>, você pode passar as credenciais diretamente como argumentos na execução (veja seção <a href="#-uso">Uso</a>).</p>

<h2>📱 Uso</h2>

<h3>Como executar o sistema:</h3>

<p>Este projeto utiliza <strong>Scrapy tradicional</strong> com execução direta no terminal.</p>

<h4>1. Navegar para o diretório do Scrapy</h4>
<pre><code>cd servimed
</code></pre>

<h4>2. Executar o Spider Servimed</h4>
<p><strong>💡 Dica para teste rápido:</strong> Para executar um teste limitado a apenas 1 página de resultados, descomente a linha 157 no arquivo <code>servimed/servimed/spiders/servimed_spider.py</code>:</p>
<pre><code># Linha 157: Alterar de comentário para ativo
# total_paginas = 1  # Para testes, limitar a 1 página
total_paginas = 1  # Para testes, limitar a 1 página
</code></pre>
<p>Para extrair dados do portal principal:</p>
<pre><code>scrapy crawl servimed
</code></pre>

<h4>3. Executar com configurações customizadas</h4>
<pre><code># Com output específico
scrapy crawl servimed -o resultados_custom.json

# Com settings customizados
scrapy crawl servimed -s USER_AGENT='MeuBot 1.0'
</code></pre>

<h4>4. Executar com credenciais via argumentos (sem arquivo .env)</h4>
<p>Caso prefira não criar o arquivo <code>.env</code>, você pode passar as credenciais diretamente:</p>
<pre><code># Spider Servimed com credenciais
scrapy crawl servimed -a usuario=SEU_USUARIO -a senha=SUA_SENHA

# Combinando argumentos e output customizado
scrapy crawl servimed -a usuario=SEU_USUARIO -a senha=SUA_SENHA -o meus_dados.json
</code></pre>

<p><strong>⚠️ Importante:</strong> Substitua <code>SEU_USUARIO</code> e <code>SUA_SENHA</code> pelas suas credenciais reais do Servimed.</p>

<h2>📊 Resultados</h2>

<h3>Onde encontrar os dados extraídos:</h3>

<ul>
    <li><strong>📁 extractions/:</strong> Pasta principal com resultados
        <ul>
            <li><strong>servimed_spider.json:</strong> Dados do portal Servimed</li>
        </ul>
    </li>
    <li><strong>🔍 Formato:</strong> JSONLines (.json) com um objeto por linha</li>
    <li><strong>📝 Encoding:</strong> UTF-8 com indentação para fácil leitura</li>
</ul>

<h3>Exemplo de arquivo gerado:</h3>
<pre><code>{
    "empresa": "Empresa Exemplo Ltda",
    "cnpj": "12.345.678/0001-90",
    "produtos": [...],
    "timestamp": "2026-02-17T15:30:00"
}
</code></pre>

<h2>📁 Estrutura do Projeto</h2>

<ul>
    <li><strong>requirements.txt:</strong> Dependências Python necessárias</li>
    <li><strong>.env:</strong> Variáveis de ambiente (criar manualmente)</li>
    <li><strong>.venv/:</strong> Ambiente virtual Python (criar com venv)</li>
    <li><strong>extractions/:</strong> Pasta onde são salvos os dados extraídos</li>
    <li><strong>servimed/:</strong> Código fonte principal do Scrapy
        <ul>
            <li><strong>scrapy.cfg:</strong> Configuração do projeto Scrapy</li>
            <li><strong>servimed/:</strong> Módulo Python do projeto
                <ul>
                    <li><strong>settings.py:</strong> Configurações do Scrapy</li>
                    <li><strong>items.py:</strong> Definição de itens extraídos</li>
                    <li><strong>pipelines.py:</strong> Processamento dos dados</li>
                    <li><strong>middlewares.py:</strong> Middlewares customizados</li>
                    <li><strong>spiders/:</strong> Spiders de extração
                        <ul>
                            <li><strong>servimed_spider.py:</strong> Spider principal</li>
                        </ul>
                    </li>
                </ul>
            </li>
        </ul>
    </li>
</ul>

<h2>🐛 Troubleshooting</h2>

<h3>Problemas Comuns</h3>

<h4>1. 🐍 Python não encontrado</h4>
<ul>
    <li>Certifique-se de que o Python 3.11+ está instalado</li>
    <li>Verifique se o Python está no PATH do sistema</li>
    <li>Teste: <code>python --version</code></li>
</ul>

<h4>2. 📦 Erro ao instalar dependências</h4>
<pre><code># Atualizar pip primeiro
python -m pip install --upgrade pip

# Instalar dependências novamente
pip install -r requirements.txt
</code></pre>

<h4>3. 🔐 Erro de autenticação</h4>
<ul>
    <li>Verifique se as credenciais no <code>.env</code> estão corretas</li>
    <li>Confirme se o usuário tem acesso ao portal Servimed</li>
    <li>Teste o login manualmente no site</li>
</ul>

<h4>4. 📁 Pasta extractions não criada</h4>
<p>Crie manualmente a pasta:</p>
<pre><code>mkdir extractions
</code></pre>

<h4>5. 🕷️ Spider não executa</h4>
<ul>
    <li>Certifique-se de estar na pasta <code>servimed/</code></li>
    <li>Verifique se o ambiente virtual está ativo</li>
    <li>Confirme se as dependências estão instaladas</li>
</ul>

<h3>Comandos Úteis</h3>
<pre><code># Verificar spiders disponíveis
scrapy list

# Ver configurações ativas
scrapy settings

# Executar com debug verbose
scrapy crawl servimed -L DEBUG

# Verificar se o Scrapy está funcionando
scrapy version -v
</code></pre>

<hr>

<h2>Requisitos Técnicos</h2>

<h3>Linguagens e Frameworks:</h3>
<ul>
    <li><strong>Core:</strong> Python 3.11+, Scrapy 2.11.2</li>
    <li><strong>HTTP Client:</strong> curl-cffi para requisições modernas</li>
    <li><strong>Parsing:</strong> lxml, parsel (inclusos no Scrapy)</li>
    <li><strong>Persistência:</strong> JSON/JSONLines nativo</li>
    <li><strong>Configuração:</strong> python-dotenv para variáveis de ambiente</li>
</ul>

<hr>

<div align="center">
<h2>Werricsson Santos</h2>
    <img align="center" alt="Werricsson Santos" style="border-radius: 25px;" height="190" width="190" src="https://avatars.githubusercontent.com/u/112734393?v=4">
</div>
</br> </br>
<div align="center">
    <a href = "mailto:werricsson.santos@gmail.com"><img src="https://img.shields.io/badge/-Gmail-%23333?style=for-the-badge&logo=gmail&logoColor=white" target="_blank"></a>
    <a href="https://www.linkedin.com/in/werricsson-santos/" target="_blank"><img src="https://img.shields.io/badge/-LinkedIn-%230077B5?style=for-the-badge&logo=linkedin&logoColor=white" target="_blank"></a> 
</div>
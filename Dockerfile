FROM python:3.11-slim

# Instala dependências do sistema para o Scrapy/Redis
RUN apt-get update && apt-get install -y gcc libssl-dev

WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do projeto
COPY . .

# Define o PYTHONPATH para o Python achar as pastas corretamente
ENV PYTHONPATH=/app
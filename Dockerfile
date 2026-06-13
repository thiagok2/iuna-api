# Use a imagem base oficial do Python slim
FROM python:3.10-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Instala dependências do sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de requisitos para o container
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código-fonte para o container
COPY . .

# Expõe a porta que a aplicação escuta
EXPOSE 8000

# Comando para iniciar o servidor Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

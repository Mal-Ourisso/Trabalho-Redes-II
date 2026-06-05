# Utilizando a imagem oficial do Ubuntu solicitada no projeto
FROM ubuntu:22.04

# Evita que o apt-get trave pedindo confirmações interativas
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza os repositórios e instala as dependências essenciais
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    iproute2 \
    tcpdump \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto local para dentro da pasta /app no container
COPY . /app

# Comando padrão para manter o container ativo em segundo plano
CMD ["tail", "-f", "/dev/null"]
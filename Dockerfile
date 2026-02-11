# Usa uma versão leve do Python
FROM python:3.11-slim

# Define a pasta de trabalho no servidor
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o seu código para o servidor
COPY . .

# Configurações do Flet para rodar na Web
ENV FLET_SERVER_PORT=8080
ENV FLET_SERVER_IP=0.0.0.0

# Libera a porta 8080
EXPOSE 8080

# Comando para iniciar o app (modo Web)
CMD ["flet", "run", "app.py", "--web", "--port", "8080"]
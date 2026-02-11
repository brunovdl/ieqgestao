# Usa uma versão leve do Python
FROM python:3.11-slim

# Define a pasta de trabalho no servidor
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o seu código para o servidor
COPY . .

# Libera a porta 8080
EXPOSE 8080

# Comando para iniciar o app (modo Web)
CMD ["python", "app.py"]
<<<<<<< HEAD
# IEQ - Sistema de Gestão

Sistema modular para gerenciamento de igreja, desenvolvido com Flet (Python).

## 📁 Estrutura do Projeto

```
ieq_gestao/
├── main.py                 # Arquivo principal da aplicação
├── database/               # Módulo de banco de dados
│   ├── __init__.py
│   └── db_manager.py      # Gerenciador do banco SQLite
├── views/                  # Módulo de interfaces
│   ├── __init__.py
│   ├── login_view.py      # Tela de login
│   ├── dashboard_view.py  # Dashboard principal
│   └── visitors_view.py   # Cadastro de visitantes
├── utils/                  # Módulo de utilitários
│   ├── __init__.py
│   └── config.py          # Configurações e constantes
├── assets/                 # Recursos (imagens, etc)
│   └── logoieq.png        # Logo da igreja
└── README.md              # Documentação
```

## 🚀 Como Executar

1. Certifique-se de ter o Python 3.8+ instalado
2. Instale as dependências:
   ```bash
   pip install flet
   ```
3. Execute o aplicativo:
   ```bash
   python main.py
   ```

## 🔑 Credenciais Padrão

- **Usuário:** admin
- **Senha:** admin123

## 📦 Funcionalidades

### ✅ Implementadas
- Login de usuários
- Cadastro de visitantes com:
  - Nome
  - Telefone/WhatsApp
  - E-mail
  - Endereço
  - Observações
  - Data/hora da visita (automática)

### 🚧 Em Desenvolvimento
- Gestão de células
- Relatórios
- Gestão de membros
- Gestão financeira

## 🗄️ Banco de Dados

O sistema utiliza SQLite3 com as seguintes tabelas:

### Tabela `users`
- id (INTEGER, PK)
- username (TEXT, UNIQUE)
- password (TEXT)

### Tabela `visitors`
- id (INTEGER, PK)
- name (TEXT)
- phone (TEXT)
- email (TEXT)
- address (TEXT)
- date_visit (TEXT)
- observations (TEXT)

## 🛠️ Tecnologias

- **Flet**: Framework para criar interfaces
- **SQLite3**: Banco de dados local
- **Python 3**: Linguagem de programação

## 📝 Notas

- O banco de dados é criado automaticamente na primeira execução
- Os assets (como logo) devem estar na pasta `assets/`
- Credenciais padrão são apenas para desenvolvimento

## 🔄 Atualizações Futuras

- [ ] Sistema de permissões
- [ ] Backup automático
- [ ] Exportação de relatórios
- [ ] Dashboard com estatísticas
- [ ] Sistema de notificações
=======
# ieqgestao
>>>>>>> ebfdd347c34df266c2c8235c6ff7ceffec5cf87f

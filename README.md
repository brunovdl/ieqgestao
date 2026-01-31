# 🏛️ IEQ Gestão - Sistema Integrado de Gestão Eclesiástica

Sistema completo para gestão de igrejas, desenvolvido em Python com Flet e Supabase.

## ✨ Funcionalidades

### 📋 Gestão de Visitantes
- Cadastro completo de visitantes
- Integração com API ViaCEP para preenchimento automático de endereços
- Lista com busca e filtros
- Edição de dados
- Botão direto para WhatsApp

### 👥 Gestão de Voluntários
- Cadastro de colaboradores e equipe
- Organização por departamentos
- Controle de cargos e funções
- Histórico de atividades

### 🏠 Casa de Cornélio (Células)
- Gestão completa de células/pequenos grupos
- Informações de líderes e anfitriões
- Endereço e horários de reunião
- Status ativo/inativo

### 👤 Gestão de Usuários
- Sistema de permissões granular
- Níveis de acesso diferenciados
- Login com Google (simulado)
- Autenticação segura

## 🚀 Tecnologias

- **Frontend**: [Flet](https://flet.dev) (Python)
- **Backend/Database**: [Supabase](https://supabase.com) (PostgreSQL)
- **APIs Externas**: ViaCEP
- **Infraestrutura**: Cloud (Supabase)

## 📦 Instalação

### Pré-requisitos
- Python 3.8 ou superior
- Conta no Supabase (gratuita)

### Passo 1: Clone o projeto
```bash
git clone <url-do-repositorio>
cd ieq-gestao
```

### Passo 2: Instale as dependências
```bash
pip install -r requirements.txt
```

### Passo 3: Configure o Supabase

Siga o guia completo em: **[GUIA_MIGRACAO_SUPABASE.md](GUIA_MIGRACAO_SUPABASE.md)**

Resumo:
1. Crie um projeto no Supabase
2. Execute o SQL em `supabase_schema.sql`
3. Configure o arquivo `.env`:
```env
SUPABASE_URL=sua-url-aqui
SUPABASE_KEY=sua-chave-aqui
```

### Passo 4: Execute o sistema
```bash
python ieq_gestao_supabase.py
```

## 🔄 Migração de Dados

Se você já tem dados no SQLite local:
```bash
python migrate_data.py
```

## 📁 Estrutura do Projeto

```
ieq-gestao/
├── ieq_gestao_supabase.py      # Aplicação principal (com Supabase)
├── supabase_schema.sql          # Schema do banco de dados
├── migrate_data.py              # Script de migração SQLite → Supabase
├── requirements.txt             # Dependências Python
├── .env.example                 # Exemplo de configuração
├── .env                         # Suas credenciais (NÃO COMMITAR!)
├── GUIA_MIGRACAO_SUPABASE.md   # Guia detalhado de migração
└── README.md                    # Este arquivo
```

## 🔐 Segurança

### Credenciais
- ✅ **NUNCA** commite o arquivo `.env`
- ✅ Use variáveis de ambiente
- ✅ Mantenha chaves privadas seguras

### Banco de Dados
- Configure Row Level Security (RLS) no Supabase
- Altere a senha padrão do admin
- Use HTTPS para todas as conexões

## 👨‍💻 Uso

### Login Padrão
- **Usuário**: admin
- **Senha**: admin123

⚠️ **IMPORTANTE**: Altere essa senha assim que possível!

### Tipos de Usuário

**Administrador**
- Acesso total ao sistema
- Gerenciamento de usuários
- Todas as permissões

**Voluntário**
- Acesso restrito conforme permissões
- Pode cadastrar visitantes, células, etc.

**Membro**
- Acesso somente leitura
- Visualização de células e voluntários

## 📊 Painel Supabase

Acesse o painel do Supabase para:
- 📋 Ver dados em tempo real
- 📈 Monitorar performance
- 🔍 Executar queries SQL
- 📝 Gerenciar usuários
- 🔒 Configurar políticas de segurança

## 🆘 Suporte

### Problemas Comuns

**Erro de conexão com Supabase**
- Verifique suas credenciais no `.env`
- Confirme que o projeto Supabase está ativo
- Teste sua conexão com internet

**Dados não aparecem**
- Verifique no Table Editor do Supabase
- Confira políticas RLS
- Veja logs de erro no console

**Migração falhou**
- Certifique-se de que executou o `supabase_schema.sql`
- Verifique se o banco SQLite existe
- Confira erros específicos no console

### Documentação
- [Documentação Flet](https://flet.dev/docs)
- [Documentação Supabase](https://supabase.com/docs)
- [ViaCEP API](https://viacep.com.br/)

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto é de código aberto e está disponível para uso livre.

## 🙏 Agradecimentos

Desenvolvido com ❤️ para a **Igreja do Evangelho Quadrangular**

---

**Versão**: 2.0 (Supabase)  
**Última atualização**: Janeiro 2026
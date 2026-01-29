# Guia de Migração

## Como migrar do arquivo único para a estrutura modular

### Passo 1: Copiar o projeto
```bash
# Copie toda a pasta ieq_gestao para seu diretório de trabalho
cp -r ieq_gestao /caminho/do/seu/projeto/
```

### Passo 2: Mover o logo
```bash
# Se você tem o arquivo logoieq.png, mova-o para a pasta assets
mv logoieq.png ieq_gestao/assets/
```

### Passo 3: Executar
```bash
cd ieq_gestao
python main.py
```

## Vantagens da Nova Estrutura

### 1. **Separação de Responsabilidades**
- `database/`: Toda lógica de banco de dados isolada
- `views/`: Cada tela em seu próprio arquivo
- `utils/`: Configurações centralizadas

### 2. **Facilidade de Manutenção**
- Fácil encontrar e modificar código específico
- Cada módulo pode ser testado independentemente
- Reduz chance de conflitos em equipe

### 3. **Escalabilidade**
- Adicionar novas funcionalidades é mais simples
- Estrutura preparada para crescimento
- Padrão profissional de desenvolvimento

### 4. **Reutilização**
- Componentes podem ser reutilizados
- Imports organizados e claros
- Código mais limpo e legível

## Diferenças Principais

### Arquivo Único (Antigo)
```python
# Tudo em um arquivo de ~200 linhas
# - Banco de dados
# - Views
# - Lógica
# - Configurações
```

### Estrutura Modular (Nova)
```python
# Dividido em módulos especializados
from database import Database
from views import login_view, dashboard_view
from utils import APP_TITLE, WINDOW_WIDTH
```

## Próximos Passos Sugeridos

1. **Adicionar testes unitários** em uma pasta `tests/`
2. **Criar mais views** para novas funcionalidades
3. **Adicionar validações** no módulo `utils/validators.py`
4. **Implementar logging** para debug
5. **Criar sistema de backup** automático do banco

## Compatibilidade

✅ Mantém todas as funcionalidades do código original
✅ Mesmo banco de dados (compatível)
✅ Mesmas credenciais padrão
✅ Interface idêntica

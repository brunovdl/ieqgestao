# IEQ Jd Portugal - Aplicação Web

Este projeto é a migração completa da antiga aplicação Flet/Python para uma **Stack Web Moderna**, garantindo mais velocidade, um design responsivo aperfeiçoado e um ecossistema mais escalável.

## Stack de Tecnologia
- **Frontend**: React.js 18 + Vite
- **Linguagem**: TypeScript
- **Estilização**: Vanilla CSS (Mobile-first, Glassmorphism, CSS Variables)
- **Gerenciamento de Estado**: Zustand
- **Roteamento**: React Router
- **Backend / Bancos de Dados**: Supabase (PostgreSQL, Storage, Auth)

## Estrutura Atual
- `src/components/`: Componentes globais da interface (Header, Sidebar, LoginModal).
- `src/pages/`: Telas principais da aplicação (rotas).
- `src/state/`: Stores do Zustand (ex: controle global de sessão).
- `src/lib/`: Configuração de clientes de API (ex: `supabase.ts`).

## Pré-requisitos
- **Node.js**: Versão 18+ ou compatível (recomendado LTS)
- **NPM** ou **Yarn**

## Como rodar o projeto localmente

1. **Instale as dependências** no diretório atual contendo o `package.json`:
   ```bash
   npm install
   ```

2. **Configure as Variáveis de Ambiente**:
   O arquivo `.env` já foi configurado com as chaves de acesso essenciais do Supabase e Groq.

3. **Inicie o Servidor de Desenvolvimento**:
   ```bash
   npm run dev
   ```
   Acesse a aplicação no navegador em: `http://localhost:5173/` (ou na porta que o Vite fornecer).

## Como compilar para produção

Quando desejar realizar o deploy da aplicação (por exemplo, Netlify, Vercel, Hostinger), execute o seguinte comando:
```bash
npm run build
```
Isso criará uma pasta `dist/` com todos os arquivos minificados prontos para deploy de conteúdo estático.

## Funcionalidades Migradas
- [x] **Início (Home)**: Saudação de acordo com o fuso, verificação de Auth, reprodutor ao-vivo do YouTube de culto.
- [x] **Células (Casas de Cornélio)**: Busca dinâmica em layout agradável das rotinas da igreja.
- [x] **Galeria**: Grid Masonry para álbuns e visualização limpa de fotos arquivadas no Supabase Storage.
- [x] **Visitantes**: Painel protegido com visualização modular e aprovação (Marcar como contatado).
- [x] **Carona Solidária**: Mural vivo com cards para ofertar/pedir carona.
- [x] **Usuários**: Acesso logado via Modal e permissão granular para Administradores.
- [x] **Analytics**: Visualização rápida da rotina de page views, extraída dos registros do Supabase.

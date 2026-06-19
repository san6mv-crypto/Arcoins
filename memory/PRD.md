# Arcoins - PRD (Product Requirements Document)

## Problema original
Plataforma Educacional Financeira "Arcoins" — banco escolar digital que ensina educação financeira para alunos do ensino fundamental II e médio usando moeda fictícia "Arc" (₡). Inclui mesada diária, desafios educacionais, loja escolar virtual e poupança simulada. 3 perfis: Aluno, Professor, Admin escolar.

## User Personas
- **Aluno (11-17 anos)**: recebe mesada, completa desafios, compra na loja, poupa.
- **Professor**: gerencia turmas, cria desafios, aprova submissões.
- **Admin escolar**: gerencia usuários/loja/turmas, configura mesada, distribui mesada diária, vê relatórios.

## Requisitos core
- Moeda fictícia "Arc" com símbolo ₡
- 3 papéis com permissões distintas (RBAC)
- Mesada diária idempotente
- Loja com estoque e saldo validado
- Poupança simulada
- Desafios: criar → submeter → aprovar → creditar
- Aparência lúdica (target 11-17 anos)
- **Admin cria contas para professores e alunos (com senha)**
- Autenticação estável com JWT + bcrypt

## Stack
- Backend: FastAPI + MongoDB (Motor) + JWT (PyJWT) + bcrypt
- Frontend: React 19 + React Router 7 + Tailwind + Framer Motion + react-confetti
- Fonts: Fredoka (títulos) + Nunito (corpo)
- Paleta: #00B4D8, #FFBE0B, #FF006E, #06D6A0

## Implementado

### Janeiro 2026 — MVP navegável
- 3 dashboards (Aluno/Professor/Admin) com 13 telas
- Mascote "Arco" (SVG)
- Auth JWT + bcrypt + RBAC
- Seed idempotente: 1 admin + 2 professores + 8 alunos + 2 turmas + 5 desafios + 6 itens loja
- Documentação `ARCHITECTURE.md` + `test_credentials.md`

### Junho 2026 — Gestão de usuários + setup local
- ✅ Backend: `POST /api/admin/users` (com validação de e-mail duplicado, senha mín 4 chars, turma existente)
- ✅ Backend: `DELETE /api/admin/users/{id}` (com proteção contra auto-remoção)
- ✅ Backend: `GET/POST /api/admin/classes` (com proteção contra duplicidade)
- ✅ Frontend: tela `/admin/usuarios` com formulário de criação (seletor visual de role, campos contextualizados para aluno) + filtros (Todos/Admin/Professores/Alunos) + remover usuário
- ✅ Frontend: tela `/admin/turmas` com formulário de criação + lista de turmas (com professor e contagem de alunos)
- ✅ Saldo inicial cria transação "Saldo inicial de boas-vindas" no extrato do aluno
- ✅ `README.md` com instruções completas para rodar localmente (Python venv + yarn + Mongo Docker)
- ✅ Testes 100% (14/14 backend pytest + 100% frontend E2E)
  - Admin cria aluno → aluno loga → vê saldo inicial corretamente
  - Validações: e-mail duplicado, senha curta, turma inválida, auto-remoção
  - JWT estável em múltiplas requisições

## Backlog

### P1
- Tela "Meu Perfil" para usuário trocar própria senha/email
- Cron job de mesada diária automática
- Rendimento real da poupança (job diário)

### P2
- Relatórios exportáveis (CSV/PDF)
- Edição de usuário existente pelo admin (não só remover)
- Reset de senha pelo admin
- Bulk import de alunos via CSV
- Rate limiting no login (anti-brute force)
- Refactor server.py em routers (auth/admin/teacher/student)

### P3
- App mobile (React Native)
- Multi-tenant (múltiplas escolas)
- Registro INPI (marca + software)
- 2FA para admin
- Gamificação avançada (badges, ranking)

## Próximas tasks sugeridas
1. Tela "Meu Perfil" (usuário troca própria senha/email)
2. Bulk import CSV de alunos
3. Cron job da mesada
4. Deploy em staging para escola piloto

## Histórico
- **Jan/2026**: MVP navegável funcional (3 dashboards + backend + seed + docs)
- **Jun/2026**: Gestão de usuários pelo admin + setup local documentado + 100% nos testes

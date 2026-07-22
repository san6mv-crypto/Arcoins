# Arcoins - PRD (Product Requirements Document)

## Problema original
Plataforma Educacional Financeira "Arcoins" — banco escolar digital que ensina educação financeira para alunos do ensino fundamental II e médio usando moeda fictícia "Arc" (₡). 3 perfis: Aluno, Professor, Admin escolar.

## User Personas
- **Aluno (11-17 anos)**: recebe mesada, completa desafios, compra na loja, poupa, transfere Arc, resgata vouchers
- **Professor**: gerencia turmas, cria desafios, aprova submissões, marca presença, cria vouchers
- **Admin escolar**: gestão global, cadastra em massa via CSV, configura mesada condicional, cria vouchers, marca presença

## Requisitos core
- Moeda fictícia "Arc" com símbolo ₡
- 3 papéis com RBAC
- Mesada diária idempotente (opcionalmente condicional à presença)
- Loja com estoque e saldo validado
- Poupança simulada
- Desafios: criar → submeter → aprovar → creditar
- Aparência lúdica
- Admin cria contas manualmente E via CSV com login `@primeiroNome` + senha=RA
- Autenticação estável (JWT + bcrypt)
- Transferências P2P entre alunos via RA
- Vouchers uso único (professor/admin)
- Presença condicionando mesada

## Stack
- Backend: FastAPI + MongoDB (Motor) + JWT (PyJWT) + bcrypt
- Frontend: React 19 + React Router 7 + Tailwind + Framer Motion + react-confetti
- Fonts: Fredoka (títulos) + Nunito (corpo)

## Implementado

### Jan/2026 — MVP navegável
- 3 dashboards (Aluno/Professor/Admin), 13 telas iniciais
- Mascote "Arco" (SVG)
- Auth JWT + bcrypt + RBAC
- Seed idempotente

### Jun/2026 — Gestão de usuários + setup local
- Criação manual de usuários pelo admin, criação de turmas
- README para rodar localmente

### Jun/2026 — Beta-1: CSV bulk import + Vouchers
- Import CSV alunos: login `@firstname`, senha=RA, `password_locked=true`
- Duplicidade: `@nome.<RA>`
- Vouchers uso único (professor/admin criam, aluno resgata)
- Widget de resgate no dashboard do aluno (com confetti)
- Fix: campo de login mudou de type=email para type=text (para aceitar `@login`)

### Jul/2026 — Beta-2: Transferências P2P + Presença + Mesada condicional
- ✅ `POST /api/student/transfer` (RA + valor + mensagem) — cria transfer_out/in
- ✅ Validações: RA inexistente, saldo insuficiente, auto-envio, valor inválido, máx 10k
- ✅ Página `/aluno/transferir` com histórico das últimas transferências
- ✅ `POST /api/attendance/mark` + `GET /api/attendance/class/{class_id}` — professor marca só sua turma, admin todas
- ✅ Página `/professor/presenca` e `/admin/presenca` com Presente/Ausente por aluno
- ✅ Config `attendance_required` + toggle na tela de configurações
- ✅ `POST /api/admin/run-allowance` respeita presença quando ativo
- ✅ Testes 20/20 backend + 100% frontend

## Backlog

### P1
- Tela "Meu Perfil" (usuário não-locked troca senha/e-mail)
- Botão "Imprimir credenciais dos alunos" (PDF/CSV pós-import) ← próximo
- Edição de vouchers (data de validade, multi-uso) ← próximo
- Cron job de mesada automática diária

### P2
- Split de `server.py` em routers (auth/admin/teacher/student/vouchers/attendance/transfers)
- Mongo transactions para transferência atômica
- Índices otimizados: (user_id, type, meta.date) para run-allowance
- Reset senha via admin
- Bulk import CSV: template imprimível de credenciais

### P3
- App mobile (React Native)
- Multi-tenant (múltiplas escolas)
- 2FA para admin
- Registro INPI (marca + software)
- Gamificação avançada (badges, ranking)

## Histórico
- **Jan/2026**: MVP navegável
- **Jun/2026**: gestão de usuários + setup local
- **Jun/2026**: Beta-1 (CSV import + vouchers)
- **Jul/2026**: Beta-2 (transferências + presença condicional)

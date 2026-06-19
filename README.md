# Arcoins — Plataforma Educacional Financeira

Banco Escolar Digital que ensina educação financeira através da moeda fictícia **Arc (₡)**.

3 perfis: **Aluno · Professor · Administrador**.

---

## 🚀 Como rodar LOCALMENTE

### Pré-requisitos
- **Python 3.10+** (testado em 3.11)
- **Node.js 18+** e **Yarn**
- **MongoDB** local na porta `27017` — instale via [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community) ou rode com Docker:
  ```bash
  docker run -d --name arcoins-mongo -p 27017:27017 mongo:7
  ```

### 1️⃣ Backend (FastAPI + MongoDB)

```bash
cd backend

# (Opcional) Criar virtualenv
python3 -m venv .venv
source .venv/bin/activate           # Linux/Mac
# .venv\Scripts\activate            # Windows

# Instalar dependências
pip install -r requirements.txt
pip install pyjwt bcrypt             # caso não estejam no requirements

# Conferir/ajustar o .env (defaults adequados já estão lá)
cat .env
# Deve conter:
#   MONGO_URL="mongodb://localhost:27017"
#   DB_NAME="arcoins_db"
#   JWT_SECRET="<qualquer string longa aleatória>"
#   ADMIN_EMAIL="admin@arcoins.edu"
#   ADMIN_PASSWORD="admin123"

# Iniciar o servidor (porta 8001)
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

📌 Na primeira execução o backend **cria automaticamente** (seed idempotente):
- 1 administrador
- 2 professores
- 8 alunos de exemplo
- 2 turmas
- 5 desafios e 6 itens na loja

### 2️⃣ Frontend (React)

Abra **outro terminal**:

```bash
cd frontend

# Apontar para o backend local
echo 'REACT_APP_BACKEND_URL=http://localhost:8001' > .env

# Instalar deps e iniciar (porta 3000)
yarn install
yarn start
```

Acesse: **http://localhost:3000** 🎉

---

## 🔑 Credenciais iniciais (seed)

| Perfil | E-mail | Senha |
|---|---|---|
| Admin | `admin@arcoins.edu` | `admin123` |
| Professor (7º A) | `professor@arcoins.edu` | `prof123` |
| Professora (8º B) | `marta@arcoins.edu` | `prof123` |
| Aluno | `aluno@arcoins.edu` | `aluno123` |
| Demais alunos | `maria@`, `joao@`, `sofia@`, `pedro@`, `julia@`, `rafa@`, `bia@` arcoins.edu | `aluno123` |

Na tela de login há **3 botões de acesso rápido** para entrar como cada perfil sem digitar nada.

---

## 👥 Fluxo principal: Admin cria contas para professores/alunos

1. Login como **admin** (`admin@arcoins.edu` / `admin123`)
2. Menu superior → **Usuários**
3. No card "➕ Criar novo usuário":
   - Escolha o **perfil** (Aluno · Professor · Admin)
   - **Nome**, **E-mail** (será o login), **Senha** (mínimo 4 caracteres)
   - Para alunos: opcionalmente selecione **Turma** e **Saldo inicial em ₡**
   - Clique em **Criar usuário** ✅
4. O sistema:
   - Salva no MongoDB com **senha hasheada (bcrypt)**
   - Valida e-mail duplicado
   - Para alunos com saldo inicial > 0: cria transação "Saldo inicial de boas-vindas" no extrato
   - O **novo usuário já pode logar imediatamente** com o e-mail/senha definidos
5. Para criar **novas turmas** antes de cadastrar alunos: menu superior → **Turmas → ➕ Nova turma**

> 💡 Você pode também filtrar usuários por perfil (Todos · Admin · Professores · Alunos) e remover usuários (exceto a si mesmo).

---

## 🧪 Testar a API manualmente

```bash
# Login admin
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@arcoins.edu","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Criar aluno com saldo inicial de ₡50
curl -X POST http://localhost:8001/api/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Aluno Teste","email":"teste@arcoins.edu","password":"teste123","role":"student","initial_balance":50}'

# Login do aluno recém-criado
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@arcoins.edu","password":"teste123"}'

# Listar usuários
curl http://localhost:8001/api/admin/users -H "Authorization: Bearer $TOKEN"

# Criar turma
curl -X POST http://localhost:8001/api/admin/classes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"9º Ano C"}'
```

---

## 🏗️ Arquitetura

- **Backend**: FastAPI + Motor (MongoDB async) + JWT (PyJWT) + bcrypt
- **Frontend**: React 19 + React Router 7 + Tailwind + Framer Motion
- **Banco**: MongoDB (`arcoins_db`) — 8 collections (`users`, `classes`, `transactions`, `challenges`, `submissions`, `store_items`, `purchases`, `config`)
- **Auth**: JWT Bearer Token (7 dias) + cookie httpOnly opcional

Documentação completa: [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 🔄 Resetar o banco

Com o backend parado:
```bash
mongosh arcoins_db --eval 'db.dropDatabase()'
```
Reinicie o backend → seed roda automaticamente.

---

## ❓ Problemas comuns

| Erro | Causa | Solução |
|---|---|---|
| `ServerSelectionTimeoutError` | MongoDB não está rodando | Inicie `mongod` ou o container Docker |
| Tela em branco no front | `REACT_APP_BACKEND_URL` errado | Confirme `http://localhost:8001` em `frontend/.env` |
| `401 Unauthorized` ao logar | Senha errada / seed não rodou | Use credenciais da tabela acima; confira logs |
| `E-mail já cadastrado` | E-mail em uso | Use outro e-mail ou remova o usuário antes |
| `403 Acesso negado` | Token de role errado | Logue com a conta do perfil correto |

---

## 📄 Licença & PI

Protótipo educacional. O nome **Arcoins** e a moeda **Arc** devem ser registrados no INPI (Brasil) para proteção de marca conforme descrito no documento de concepção.

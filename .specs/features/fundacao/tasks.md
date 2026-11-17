# Fundação Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/fundacao/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from project guidelines and spec. Guidelines found: requisitos do usuário, seção 19 (testes unitários e de integração obrigatórios); AD-001 (teste de arquitetura); AD-004 (integração contra PostgreSQL real). Nenhum teste existente: strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules, verifier) | unit | All branches; 1:1 to spec ACs; every listed edge case | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Core config / security utils | unit | All branches | `backend/tests/unit/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Repositories / migrations / seed | integration | Key query paths + error paths (unique, optimistic lock) | `backend/tests/integration/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Use cases + API routes | integration | All routes in scope: happy + every listed edge case + error paths (401/403/404/409/422/429) | `backend/tests/integration/api/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend pages/components | unit | Each UI AC: render + interaction + error display | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Docker / nginx / compose | e2e smoke | INFRA-01..05 verified against the running stack | `scripts/smoke.sh` | `./scripts/smoke.sh` |
| Dependency manifests | none | build gate only | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or config-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm test -- --run && npm run build` |

---

## Execution Plan

### Phase 1: Backend scaffold

```
T1 → T2 → T3
```

### Phase 2: Domain

```
T4 → T5 → T6 → T7 → T8
```

### Phase 3: Persistence

```
T9 → T10 → T11
```

### Phase 4: Auth and platform API

```
T12 → T13 → T14 → T15
```

### Phase 5: Business API

```
T16 → T17 → T18 → T19 → T20 → T21 → T22
```

### Phase 6: Frontend

```
T23 → T24 → T25 → T26
```

### Phase 7: Deploy

```
T27 → T28
```

---

## Task Breakdown

### T1: Dependências do backend e ambiente local

**What**: Criar `backend/requirements.txt` (versões fixas) e `backend/pyproject.toml` (pytest, ruff), criar `.venv` e instalar as bibliotecas.
**Where**: `backend/requirements.txt`
**Depends on**: None
**Reuses**: versões verificadas no design
**Requirement**: INFRA-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `backend/.venv/bin/pip install -r requirements.txt` termina sem erro
- [x] `backend/.venv/bin/pytest --collect-only -q` executa (0 testes)
- [x] `backend/.venv/bin/ruff check .` passa

**Tests**: none
**Gate**: build

**Commit**: `build(backend): add pinned requirements and tooling config`

---

### T2: Configuração por ambiente

**What**: `Settings` (pydantic-settings, `extra="ignore"`) com variáveis obrigatórias, `MARITALK_*` opcionais com padrão de fallback `sabia-4-br-sp`, `COOKIE_SECURE`; erro de inicialização nomeia a variável faltante sem exibir valores.
**Where**: `backend/app/core/config.py`
**Depends on**: T1
**Reuses**: -
**Requirement**: INFRA-06, INFRA-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste: variável obrigatória ausente → erro cita o nome dela e não contém valores de outras variáveis
- [x] Teste: `repr(settings)` e `settings.model_dump()` público não expõem `MARITALK_API_KEY`
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(core): add environment settings with fail-fast validation`

---

### T3: Teste de arquitetura das camadas

**What**: Teste que falha se `app/domain` ou `app/application` importarem `fastapi`, `sqlalchemy`, `httpx` ou `app.infrastructure`/`app.presentation`; esqueleto de pacotes das 4 camadas.
**Where**: `backend/tests/architecture/test_layers.py`
**Depends on**: T2
**Reuses**: -
**Requirement**: AD-001 (INFRA-01)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste passa no esqueleto e falha se um import proibido for adicionado (verificado manualmente uma vez)
- [x] Gate quick passa (`pytest tests/unit tests/architecture`)

**Tests**: unit
**Gate**: quick

**Commit**: `test(arch): enforce clean architecture layer boundaries`

---

### T4: Valor de domínio Interstice

**What**: `Interstice(start, end)` com `months()` (meses civis completos com ajuste de fim de mês), `days()`, `crosses(date)`.
**Where**: `backend/app/domain/rules/interstice.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: -
**Requirement**: PROC-02, edge cases 29/02 e 31/12/2024

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 23/11/2024→23/11/2026 = 24 meses; →22/11/2026 = 23; 29/02/2024→28/02/2026 = 24; dias corretos
- [x] `crosses(2025-01-01)` verdadeiro/falso nos limites
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add interstice value object with civil-month count`

---

### T5: Entidades de carreira versionada

**What**: `CareerClass`, `CareerVersion` (`covers`, `get_class`, `next_class`, `min_months`) e `select_version(versions, end_date)`.
**Where**: `backend/app/domain/entities/career.py`
**Depends on**: T4
**Reuses**: -
**Requirement**: CARR-01, CARR-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Seleção por data final nos limites 31/12/2024 e 01/01/2025; `None` sem versão vigente
- [x] `min_months` para progressão e promoção conforme a definição
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add versioned career structure entities`

---

### T6: Catálogo normativo das duas versões do Magistério Superior

**What**: Definições Res. 4.644/2015 e Lei 15.141/2025 (classes, denominações, níveis, interstícios, `norm_reference`) como dados puros.
**Where**: `backend/app/domain/rules/career_catalog.py`
**Depends on**: T5
**Reuses**: tabela "Dados semeados" do design
**Requirement**: CARR-02, CARR-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes afirmam cada classe/nível/denominação/interstício da tabela do design e a vigência
- [x] Toda versão tem `norm_reference` não vazia
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add magisterio superior career catalog with sources`

---

### T7: Verificador do processo

**What**: `verify_process(snapshot, versions) -> list[Alert]` com todos os códigos da spec.
**Where**: `backend/app/domain/rules/process_verification.py`
**Depends on**: T6
**Reuses**: `Interstice`, `select_version`, catálogo
**Requirement**: PROC-03, PROC-05..PROC-11, CARR-04..CARR-07, edge case DADOS_INCOMPLETOS

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Um teste por AC (PROC-05..09, CARR-04..07) com severidade e código exatos
- [x] PROC-10: zero alertas ERRO; PROC-11: conjunto exato de 5 códigos
- [x] Snapshot não é modificado (PROC-03)
- [x] Gate quick passa; 15+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add deterministic process verification rules`

---

### T8: Entidades de processo, docente, usuário e portas

**What**: Entidades, enums (`ProcessStatus` com transições, `Role`, `Titration`, `WorkRegime`), erros de domínio e Protocols de repositório/UoW/hasher.
**Where**: `backend/app/domain/entities/process.py`
**Depends on**: T7
**Reuses**: -
**Requirement**: PROC-12, DOC-04, AUTH-08, AUTH-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de todas as transições de status permitidas/negadas
- [x] Teste de arquitetura continua passando
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add process, professor and user entities with ports`

---

### T9: Modelos ORM e migração inicial

**What**: Modelos SQLAlchemy das tabelas do design e migração Alembic inicial (inclui REVOKE UPDATE/DELETE em `audit_logs`); fixture de PostgreSQL efêmero.
**Where**: `backend/app/infrastructure/database/models.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: data models do design
**Requirement**: INFRA-02, AUD-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `alembic upgrade head` e `downgrade base` funcionam no Postgres de teste
- [x] Teste: UPDATE/DELETE em `audit_logs` pelo papel da aplicação falha
- [x] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add initial schema and migration`

---

### T10: Repositórios SQLAlchemy e UnitOfWork

**What**: Implementações das portas com mapeamento entidade↔ORM e lock otimista.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T9
**Reuses**: portas de T8
**Requirement**: DOC-03, edge case gravação simultânea

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] SIAPE duplicado → `Conflict`; versão desatualizada → `StaleVersion`
- [x] Round-trip de cada entidade
- [x] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add sqlalchemy repositories and unit of work`

---

### T11: Seed idempotente

**What**: Semeia estrutura e versões de carreira, unidades (Campus Tocantins/Cametá, FASI, IFCH) e ADMIN inicial.
**Where**: `backend/app/infrastructure/database/seed.py`
**Depends on**: T10
**Reuses**: catálogo de T6
**Requirement**: CARR-02, UNIT-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Rodar duas vezes não duplica registros
- [ ] Versões persistidas idênticas ao catálogo
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add idempotent reference data seed`

---

### T12: Hasher Argon2id e tokens

**What**: `Argon2PasswordHasher` e utilitários de token de sessão (geração, sha256) e CSRF.
**Where**: `backend/app/infrastructure/security/argon2_hasher.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: porta `PasswordHasher`
**Requirement**: AUTH-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Hash começa com `$argon2id$`; verify correto/incorreto
- [ ] Gate quick passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(security): add argon2id hasher and session tokens`

---

### T13: Casos de uso de autenticação

**What**: `Login` (mensagem única, rate limit 5/15 min), `Logout`, `GetCurrentSession` (inatividade 30 min, absoluto 8 h) com relógio injetado.
**Where**: `backend/app/application/use_cases/auth.py`
**Depends on**: T12
**Reuses**: repositórios de T10
**Requirement**: AUTH-02, AUTH-04, AUTH-05, AUTH-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes: 5 falhas → 6ª bloqueada; liberada após 15 min; expiração 30 min/8 h nos limites
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(auth): add login, logout and session use cases`

---

### T14: Rotas de autenticação, CSRF e app FastAPI

**What**: `main.py`, dependências, mapeamento de erros, middleware CSRF, rotas `/api/auth/login|logout|me`.
**Where**: `backend/app/presentation/api/auth.py`
**Depends on**: T13
**Reuses**: casos de uso de T13
**Requirement**: AUTH-01, AUTH-02, AUTH-03, AUTH-06, AUTH-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cookie HttpOnly/SameSite=Strict (Secure conforme config); 401 sem sessão; 403 sem CSRF; 429 no bloqueio
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add auth routes with csrf protection`

---

### T15: Health check

**What**: `GET /api/health` com verificação do banco (200 ok / 503 degraded).
**Where**: `backend/app/presentation/api/health.py`
**Depends on**: T14
**Reuses**: engine
**Requirement**: INFRA-01, INFRA-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 200 com corpo exato; 503 com corpo exato quando o banco está inacessível
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add health endpoint with database probe`

---

### T16: Serviço de auditoria e rota de usuários

**What**: `AuditService` (só campos alterados) e `POST/GET /api/users` (ADMIN).
**Where**: `backend/app/presentation/api/users.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `AuditService` em `application/services/audit_service.py`
**Requirement**: AUTH-10, AUD-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 422 nomeando campo (e-mail duplicado, senha < 10); não-ADMIN → 403; evento de auditoria gravado
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add user management with audit trail`

---

### T17: Rotas de unidades acadêmicas

**What**: CRUD/arquivamento de unidades (ADMIN) e listagem.
**Where**: `backend/app/presentation/api/units.py`
**Depends on**: T16
**Reuses**: AuditService
**Requirement**: UNIT-01, UNIT-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Não-ADMIN não altera; unidade arquivada em docente/processo → 422
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add academic unit management`

---

### T18: Rotas de docentes

**What**: Criar/editar/listar/arquivar docente com auditoria.
**Where**: `backend/app/presentation/api/professors.py`
**Depends on**: T17
**Reuses**: AccessPolicy, AuditService
**Requirement**: DOC-01..DOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] SIAPE inválido 422; duplicado 409; enums restritos; edição audita
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add professor registration`

---

### T19: Criar, obter e listar processos

**What**: `POST/GET /api/processes`, `GET /api/processes/{id}` com interstício e alertas; política de acesso.
**Where**: `backend/app/presentation/api/processes.py`
**Depends on**: T18
**Reuses**: `verify_process`, AccessPolicy
**Requirement**: PROC-01..PROC-04, PROC-10, PROC-11, PROC-14, AUTH-08, AUTH-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Casos PROC-10/PROC-11 pela API com conjuntos exatos de códigos
- [ ] DOCENTE/SECRETARIA de fora → 404; listagem filtrada com contagem por severidade
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add process creation, retrieval and listing`

---

### T20: Atualizar processo, mudar status e histórico

**What**: `PUT /api/processes/{id}` (justificativa, versão), `POST .../status`, `GET .../history`.
**Where**: `backend/app/application/use_cases/processes.py`
**Depends on**: T19
**Reuses**: AuditService, transições de T8
**Requirement**: PROC-12, PROC-13, AUD-01, AUD-03, edge cases 409 e docente arquivado

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] CONCLUIDO/ARQUIVADO → 409; EM_ANDAMENTO sem justificativa → 422; versão antiga → 409
- [ ] Histórico cronológico com valores anterior/novo
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add process updates, status changes and history`

---

### T21: Rotas de versões de carreira

**What**: Listar versões; ADMIN cria nova versão com `norm_reference` obrigatória; versões em uso são imutáveis.
**Where**: `backend/app/presentation/api/career.py`
**Depends on**: T20
**Reuses**: schema de definição
**Requirement**: CARR-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem referência normativa → 422; não-ADMIN → 403; definição inválida → 422
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add career version administration`

---

### T22: Logging sem dados pessoais

**What**: Configuração de logging de acesso com rota-template, status, duração e `user_id`.
**Where**: `backend/app/core/logging.py`
**Depends on**: T21
**Reuses**: -
**Requirement**: AUD-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste captura logs de um fluxo completo (cria docente e processo) e afirma ausência de nome e SIAPE
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `feat(core): add pii-free access logging`

---

### T23: Scaffold do frontend, cliente da API e login

**What**: Projeto Vite/React/TS, `api/client.ts` (credentials + CSRF), `RequireAuth`, página de login.
**Where**: `frontend/src/pages/Login.tsx`
**Depends on**: None (fase anterior concluída)
**Reuses**: contratos da API
**Requirement**: UI-01, UI-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste: rota protegida sem sessão redireciona para `/login`; erro 401 exibe mensagem
- [ ] `npm run lint`, `npm test -- --run` e `npm run build` passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add app scaffold, api client and login`

---

### T24: Painel

**What**: Dashboard com totais por status e lista de processos com contagem de alertas.
**Where**: `frontend/src/pages/Dashboard.tsx`
**Depends on**: T23
**Reuses**: api client
**Requirement**: UI-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste renderiza totais e contagens a partir de resposta simulada
- [ ] Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add dashboard`

---

### T25: Formulário de docente

**What**: Cadastro/edição de docente com erros por campo.
**Where**: `frontend/src/pages/ProfessorForm.tsx`
**Depends on**: T24
**Reuses**: `FieldError`
**Requirement**: UI-05, DOC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste: 422 exibe mensagem junto ao campo `siape`
- [ ] Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add professor form`

---

### T26: Etapa 1 do processo

**What**: Formulário da Etapa 1, navegação das 9 etapas, lista de alertas por severidade com referência normativa, layout responsivo.
**Where**: `frontend/src/pages/ProcessStep1.tsx`
**Depends on**: T25
**Reuses**: `StepNav`, `AlertList`
**Requirement**: UI-03, UI-04, UI-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste: após salvar, exibe duração e alertas agrupados; etapas 2–9 desabilitadas com "em breve"
- [ ] CSS sem largura fixa > 360 px (verificado em teste de estilo ou revisão no navegador)
- [ ] Build gate passa

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): add process step 1 with verification alerts`

---

### T27: Imagem do backend

**What**: Dockerfile do backend e entrypoint (migrações → seed → uvicorn).
**Where**: `backend/Dockerfile`
**Depends on**: None (fase anterior concluída)
**Reuses**: -
**Requirement**: INFRA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `scripts/smoke_backend.sh`: constrói a imagem, roda contra Postgres efêmero e `GET /api/health` = 200 após migrações aplicadas
- [ ] Build gate passa

**Tests**: e2e
**Gate**: build

**Commit**: `build(backend): add docker image and entrypoint`

---

### T28: Compose, nginx, frontend e smoke test

**What**: `docker-compose.yml`, `nginx/nginx.conf`, `frontend/Dockerfile`, `.env.example`, `scripts/smoke.sh`.
**Where**: `docker-compose.yml`
**Depends on**: T27
**Reuses**: imagem de T27
**Requirement**: INFRA-01, INFRA-04, INFRA-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `./scripts/smoke.sh`: sobe a stack, health 200 em ≤120 s via nginx, login do ADMIN, `down` sem `-v` e novo `up` preservam dados
- [ ] `.env.example` sem valores secretos
- [ ] Build gate passa

**Tests**: e2e
**Gate**: build

**Commit**: `build: add docker compose stack with nginx and smoke test`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7

Phase 1:  T1 → T2 → T3
Phase 2:  T4 → T5 → T6 → T7 → T8
Phase 3:  T9 → T10 → T11
Phase 4:  T12 → T13 → T14 → T15
Phase 5:  T16 → T17 → T18 → T19 → T20 → T21 → T22
Phase 6:  T23 → T24 → T25 → T26
Phase 7:  T27 → T28
```

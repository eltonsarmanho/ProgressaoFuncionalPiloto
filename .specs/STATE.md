# STATE

## Decisions

### AD-001
- **Decision**: Clean Architecture em quatro camadas: `domain` e `application` em Python puro, sem importar FastAPI, SQLAlchemy, httpx ou `app.infrastructure`; a regra é verificada por teste de arquitetura.
- **Reason**: Exigência do usuário; regras de negócio testáveis e provedor de IA substituível.
- **Trade-off**: Mais código de mapeamento (entidades ↔ modelos ORM ↔ schemas).
- **Scope**: todo o backend, todas as features
- **Date**: 2026-11-16
- **Status**: active

### AD-002
- **Decision**: Regras institucionais (estruturas de carreira, tabelas de pontuação, normas) são dados versionados com vigência e `norm_reference` obrigatória. Verificadores são funções puras que retornam alertas (ERRO/ALERTA/REQUER_ANALISE_NORMATIVA) e nunca bloqueiam nem corrigem dados informados.
- **Reason**: Proibição de inventar regras e de corrigir divergências; normas mudam (Lei 15.141/2025) e variam por unidade (FASI ≠ IFCH).
- **Trade-off**: Regras complexas exigem um schema de definição em vez de código direto.
- **Scope**: `fundacao` (carreira), `pontuacao`, `normativo`, `banca-parecer`
- **Date**: 2026-11-16
- **Status**: active

### AD-003
- **Decision**: Autenticação por sessão no servidor (tabela `sessions` no Postgres; cookie HttpOnly guarda o token, banco guarda só o hash) com token CSRF em header; sem JWT.
- **Reason**: Revogação imediata (logout, expiração por inatividade), sem segredo de assinatura para gerenciar.
- **Trade-off**: Uma consulta ao banco por requisição autenticada.
- **Scope**: backend e frontend
- **Date**: 2026-11-16
- **Status**: active

### AD-004
- **Decision**: Testes de integração rodam contra PostgreSQL real (container efêmero ou `TEST_DATABASE_URL`), nunca SQLite.
- **Reason**: JSONB, citext, enums e locks otimistas se comportam de forma diferente no SQLite.
- **Trade-off**: A suíte de integração exige Docker.
- **Scope**: todas as features
- **Date**: 2026-11-16
- **Status**: active

### AD-005
- **Decision**: A MariTalk é acessada pelo endpoint compatível com OpenAI em `MARITALK_API_BASE`, com o modelo `MARITALK_MODEL`; se a chamada falhar por erro de modelo, há uma nova tentativa com `sabia-4-br-sp`. A chave fica só no backend.
- **Reason**: Instrução do usuário (2026-11-16).
- **Trade-off**: Dependência da compatibilidade OpenAI da Maritaca.
- **Scope**: `inteligencia-documental`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-16
- **Status**: active

## Handoff

- **Feature**: `.specs/features/fundacao` (Complex). Depois vêm: `normativo` → `inteligencia-documental` → `pontuacao` → `documentos-gerados` → `banca-parecer` → `implantacao`
- **Phase / Task**: Execute. Lote 1 (T1–T8) concluído (110 testes); lote 2 (T9–T15) em execução; os lotes rodam em sequência: 1 = T1–T8, 2 = T9–T15, 3 = T16–T22, 4 = T23–T28. Depois, o Verificador independente
- **Completed**: Specify, Design e Tasks aprovados; commit `3387587` (artefatos de planejamento)
- **In-progress** (file:line): lote 1, backend/ (scaffold e domínio)
- **Next step**: com o resumo do lote 1, conferir os commits e o gate e disparar o lote 2
- **Blockers**: a chave MariTalk do `.env` retorna 401 (invalid_api_key); o usuário precisa gerar uma nova antes de `inteligencia-documental`. Falta o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD
- **Deploy**: o usuário ofereceu a VM descrita em AcessoVM.txt para `implantacao`. Ainda não acessada; exige aval no momento do deploy
- **Uncommitted files**: none (além do trabalho do lote em andamento)
- **Branch**: feat/fundacao

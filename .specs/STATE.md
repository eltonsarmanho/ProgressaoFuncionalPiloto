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
- **Phase / Task**: Execute concluído (T1–T34); Verificador iteração 3 = FAIL. Limite de 3 iterações atingido: escalado ao usuário
- **Completed**: T1–T34 (286 testes backend, 14 frontend, smoke e smoke_backend PASS); 60/60 ACs com evidência
- **In-progress** (file:line): none
- **Next step**: o usuário decide entre (a) 4ª rodada só de testes (K1/K2: sobreposição de um dia só em `career.py:77,80`; K3: último dia permitido em `career.py:125`) + Verificador, ou (b) aceitar o risco e encerrar a feature
- **Blockers**: decisão do usuário; chave MariTalk retorna 401; faltam o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD; padrões PROC-02 (dias) e PROC-04 (referência) aguardam confirmação
- **Deploy**: VM do AcessoVM.txt reservada para `implantacao`; não acessada; exige aval no momento
- **Uncommitted files**: none
- **Branch**: feat/fundacao (não enviada ao remoto)

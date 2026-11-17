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
- **Phase / Task**: Execute concluído (T1–T36). Verificador iteração 4 (rodada extra aprovada pelo usuário) = FAIL: 27 de 28 mutantes mortos, 60/60 ACs com evidência
- **Completed**: T1–T36; 289 testes backend, 14 frontend, smoke e smoke_backend PASS; branch enviada ao GitHub; deploy na VM
- **In-progress** (file:line): none
- **Next step**: o usuário decide entre (a) mais uma rodada com 1 teste (X6: a regra "em uso" de `career.py:89` não é pinada; criar o processo do Requerimento 2024-2026 e afirmar `in_use` False para Res. 4.644 e True para a Lei) + Verificador, ou (b) aceitar o risco e encerrar a feature
- **Blockers**: chave MariTalk retorna 401 (invalid_api_key) em sabia-4 e sabia-4-br-sp, com Bearer e Key; padrões PROC-02 (dias) e PROC-04 (referência) aguardam confirmação; falta o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; stack em /opt/progressao com compose + override local que publica o nginx só em 127.0.0.1:8400; site `progressao` no nginx do servidor; certificado Let's Encrypt com renovação automática). Credenciais do ADMIN em /opt/progressao/.admin-credentials (modo 600). Sem backup configurado (feature `implantacao`). Imagens construídas localmente do commit 360eefb e enviadas por `docker save | docker load`
- **Uncommitted files**: none
- **Branch**: feat/fundacao (enviada ao origin; sem PR; main intocada)

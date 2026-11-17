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

- **Feature**: `fundacao` CONCLUÍDA e verificada (`.specs/features/fundacao/validation.md`, iteração 5 = PASS; `validate_state.py` exit 0). Próximas, em ordem: `normativo` → `inteligencia-documental` → `pontuacao` → `documentos-gerados` → `banca-parecer` → `implantacao`
- **Phase / Task**: nenhuma em andamento. Próxima: Specify de `normativo` ou de `inteligencia-documental` (a definir com o usuário)
- **Completed**: T1–T37; 290 testes backend, 14 frontend; 60/60 requisitos verificados; sensor 40/41 mutantes mortos (o sobrevivente Y1 é equivalente); deploy feito
- **In-progress** (file:line): none
- **Next step**: o usuário escolhe a próxima feature; antes de `inteligencia-documental` é preciso uma chave MariTalk válida
- **Blockers**: chave MariTalk retorna 401 (invalid_api_key) em sabia-4 e sabia-4-br-sp, com Bearer e Key; padrões PROC-02 (dias) e PROC-04 (referência) aguardam confirmação; falta o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD
- **Dívidas**: UI-06 (360 px) só tem verificação estática de CSS, falta teste em navegador real (cabe em `implantacao`); sem backup configurado; rotas de negócio devolvem 500 (não 503) com o banco fora do ar; sem tela de troca de senha
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; stack em /opt/progressao com compose + override local que publica o nginx só em 127.0.0.1:8400; site `progressao` no nginx do servidor; certificado Let's Encrypt com renovação automática). Credenciais do ADMIN em /opt/progressao/.admin-credentials (modo 600). Código de produção no ar = commit 360eefb (idêntico ao HEAD em backend/app e frontend/src)
- **Uncommitted files**: none
- **Branch**: feat/fundacao (enviada ao origin; sem PR; main intocada)

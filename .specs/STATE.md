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

- **Feature**: `.specs/features/pontuacao` (Complex). `fundacao` está concluída e verificada. Depois de `pontuacao`: `normativo` → `inteligencia-documental` → `documentos-gerados` → `banca-parecer` → `implantacao`
- **Phase / Task**: Specify de `pontuacao`: `spec.md` escrita, 80 requisitos, `validate_spec.py` limpo. Aguarda o usuário esclarecer 4 pontos e aprovar. Em seguida vem o Design
- **Completed**: `fundacao` (T1–T37, 290 testes backend, 14 frontend, deploy no ar); spec de `pontuacao`
- **In-progress** (file:line): none
- **Next step**: o usuário responde às divergências do Grupo I (CH docente 68 h × 20 h; ofertas de 2022 anteriores ao interstício; soma 92 não reproduzível) e aprova a spec; depois, Design de `pontuacao` (ler `references/design.md`, registrar ADs)
- **Blockers**: as 3 divergências do Grupo I acima (linhas "Caso real e Grupo I", "CH docente do Cálculo Computacional II" e "Grupo I e o início do interstício" da spec); padrões PROC-02 e PROC-04 de `fundacao` aguardam confirmação; faltam o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD
- **Dívidas**: UI-06 (360 px) só tem verificação estática; sem backup configurado; rotas de negócio devolvem 500 (não 503) com o banco fora do ar; sem tela de troca de senha
- **MariTalk**: funciona (testado em 2026-11-17 com `test/test_maritalk.py`): `sabia-4`, `sabia-4-br-sp` e `sabiazinho-4` respondem em `https://chat.maritaca.ai/api` (Bearer); `response_format` com `json_schema` estrito funciona e devolve `null` para dado ausente. A VM ainda tem `MARITALK_API_KEY` vazia; configurar no deploy de `inteligencia-documental`
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; stack em /opt/progressao com compose + override local que publica o nginx só em 127.0.0.1:8400; site `progressao` no nginx do servidor; certificado Let's Encrypt com renovação automática). Credenciais do ADMIN em /opt/progressao/.admin-credentials (modo 600). Código de produção no ar = commit 360eefb (idêntico ao HEAD em backend/app e frontend/src)
- **Uncommitted files**: none (pasta `test/` sem versionar)
- **Branch**: feat/pontuacao (local; `feat/fundacao` enviada ao origin, com 1 commit local de STATE ainda não enviado)

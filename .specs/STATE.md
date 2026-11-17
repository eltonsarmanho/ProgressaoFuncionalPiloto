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

### AD-006
- **Decision**: O resultado da pontuação de um processo é calculado sob demanda a partir da versão da tabela e das atividades, e não é persistido. A tabela `scoring_results` do prompt não é criada em `pontuacao`.
- **Reason**: Resultado gravado fica desatualizado a cada edição de atividade; o cálculo determinístico é barato e reproduzível.
- **Trade-off**: Não há histórico de totais até `documentos-gerados`, que grava o próprio instantâneo no documento gerado.
- **Scope**: `pontuacao`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-17
- **Status**: active

### AD-007
- **Decision**: Tabelas de pontuação usam tabelas relacionais (versão → grupos → critérios), diferente das estruturas de carreira, que guardam a definição em JSONB.
- **Reason**: Critérios são editados um a um, importados por CSV, comparados entre versões e consultados por (grupo, item); linhas permitem constraints, migrações e consultas.
- **Trade-off**: Mais código de mapeamento e mais joins que um JSON por versão.
- **Scope**: `pontuacao`, `normativo`
- **Date**: 2026-11-17
- **Status**: active

## Handoff

- **Feature**: `pontuacao` CONCLUÍDA e verificada (`.specs/features/pontuacao/validation.md`, iteração 2 = PASS; `validate_state.py` exit 0). `fundacao` também concluída. Próximas, em ordem: `normativo` → `inteligencia-documental` → `documentos-gerados` → `banca-parecer` → `implantacao`
- **Phase / Task**: nenhuma em andamento. Próxima: Specify de `inteligencia-documental` ou de `normativo` (a definir com o usuário)
- **Completed**: `fundacao` (T1–T37) e `pontuacao` (T1–T41; 731 testes backend, 67 frontend; 80/80 requisitos verificados; sensor 47 de 49 mutantes mortos, os 2 sobreviventes são equivalentes; caso real FASI 2022–2024 dá 92, 120, 15, 95, 0, 30, 6, 56 e total 414)
- **In-progress** (file:line): none
- **Next step**: o usuário decide a próxima feature e se envia/implanta `pontuacao`
- **Blockers**: nenhum técnico. Pendentes de confirmação: padrões PROC-02 e PROC-04 de `fundacao`; as 3 suposições novas de `pontuacao` (desempate da sugestão de tabela, tabela duplicada sem unidades, teste de 360 px só estático); a regra "item I.3 isento". Faltam o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD (a página do Manual do Servidor e a correlação de classes já foram lidas)
- **Dívidas**: UI-06 e TELA-08 (360 px) só têm verificação estática de CSS, falta teste em navegador real (cabe em `implantacao`); sem backup configurado; rotas de negócio devolvem 500 (não 503) com o banco fora do ar; sem tela de troca de senha; `api/client.ts` só envia JSON (o upload de CSV usa `fetch` direto); a tabela da FASI segue `PENDENTE_VALIDACAO` e o Grupo I do caso real tem 16 pontos (de 92) que os documentos não explicam; mínimos de pontuação das classes novas (Res. 4.644, art. 12) sem regra
- **MariTalk**: funciona (`test/test_maritalk.py`): `sabia-4`, `sabia-4-br-sp` e `sabiazinho-4` em `https://chat.maritaca.ai/api` (Bearer); `response_format` com `json_schema` estrito devolve `null` para dado ausente. A VM ainda tem `MARITALK_API_KEY` vazia; configurar no deploy de `inteligencia-documental`
- **Fontes novas**: PROGEP, Manual do Servidor (atualizado em 12/11/2026), tabela de correlação do Magistério Superior e modelo oficial de requerimento (ver `docs/referencias/normas/FONTES.md`, itens 10 e 11)
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; stack em /opt/progressao com compose + override local que publica o nginx só em 127.0.0.1:8400; site `progressao` no nginx do servidor; certificado Let's Encrypt com renovação automática). Credenciais do ADMIN em /opt/progressao/.admin-credentials (modo 600). O que está no ar é só `fundacao` (commit 360eefb); `pontuacao` NÃO foi implantada
- **Uncommitted files**: none (pasta `test/` e `requeriment.txt` sem versionar)
- **Branch**: feat/pontuacao, empilhada sobre feat/fundacao; só `feat/fundacao` está no origin (sem PR; main intocada); `feat/pontuacao` e alguns commits de documentação de `fundacao` estão só locais

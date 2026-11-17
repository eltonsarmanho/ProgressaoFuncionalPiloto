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

### AD-008
- **Decision**: O processamento de documentos roda numa thread única dentro do processo do backend, com tarefas e estados no PostgreSQL (`FOR UPDATE SKIP LOCKED`), e não em Celery e Redis.
- **Reason**: A VM tem 1 CPU e pouca memória livre; o prompt admite começar assim (seção 18) e os casos de uso não mudam quando a fila externa chegar.
- **Trade-off**: Sem escala horizontal nem reentrega automática além da recuperação na partida; a thread morre com o app.
- **Scope**: `inteligencia-documental`, `documentos-gerados`
- **Date**: 2026-11-17
- **Status**: active

### AD-009
- **Decision**: A saída da IA é tratada como não confiável: resposta em JSON com schema estrito, mais a verificação determinística de que cada valor extraído aparece no texto da página citada (senão vira `null` com aviso). O item de pontuação vem de uma tabela de regras versionada, nunca da IA. A IA recebe só texto.
- **Reason**: O prompt proíbe inventar datas, cargas horárias, participantes e títulos; a validação determinística garante a regra mesmo se o modelo errar.
- **Trade-off**: A verificação pode recusar valor certo por formatação e exige normalizar datas e números; campos vazios pedem digitação.
- **Scope**: `inteligencia-documental`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-17
- **Status**: active

## Handoff

- **Feature**: `.specs/features/inteligencia-documental` (Complex). `fundacao` e `pontuacao` concluídas e verificadas. Depois: `documentos-gerados` → `banca-parecer` → `normativo` → `implantacao`
- **Phase / Task**: Specify (72 requisitos) e Design aprovados; `tasks.md` escrita (54 tarefas em 10 fases, 72/72 requisitos cobertos, `validate_tasks.py` limpo), aguardando aprovação e a escolha de sub-agentes (7 lotes: 8, 7, 10, 9, 7, 9 e 4 tarefas). Em seguida vem o Execute
- **Completed**: `fundacao` (T1–T37) e `pontuacao` (T1–T41, 731 testes backend, 67 frontend, 80/80 verificados)
- **In-progress** (file:line): none
- **Next step**: (1) Verificador da `tabela-oficial` (T1–T23 executadas; 22 de 23 requisitos Implemented, ACE-02 Pending por não ter teste dedicado); (2) lotes 6 e 7 de `inteligencia-documental` (telas, Tesseract na imagem, nginx 120 MB, script de corpus); (3) Verificador de `inteligencia-documental`; (4) validação real nos 45 documentos; (5) deploy só com o aval explícito do usuário
- **Status da `tabela-oficial` (2026-11-17)**: T1–T23 executadas e commitadas na branch atual (backend e frontend verdes); aguarda o Verificador. A VM ainda roda `pontuacao` com as tabelas antigas. Decisão de T4/T5: o modo de horas de PIT só vale quando a tabela tem o Grupo I fora do total com um critério de carga semanal; processos em versões antigas (Grupo I em pontos) mantêm o cálculo anterior, e o frontend mostra "Total geral" e o Grupo I em pontos para essas versões. A API de pontuação expõe `pit_hours`, `group1_hours_by_period` e `group1_total_hours`; o critério ganha `min_hours` (CSV, edição e leitura)
- **Tabela oficial (2026-11-17)**: o usuário anexou `Modelos/tabela-progressao-docente.xlsx` e determinou que é a ÚNICA fonte de verdade da pontuação (as tabelas do IFCH e da FASI deixam de valer). Itens: Grupo I = 2 (horas de PIT por semestre, FORA do total), II 16, III 9, IV 6, V 5, VI 14, VII 11, VIII 37 (renumerado); somas II–VIII: 158, 44, 40, 75, 332, 258, 407. Decisões: II.10 = 10, VI.14 = 6, VIII.4 = 15, VIII.8 = 15, VIII.12 = 2 (a planilha traz texto e fórmula diferentes nesses itens). PIT: 68 h na graduação = 8 HORAS. Palestra passa a VIII.24. O cenário derivado do caso 2022–2024 dá 211 pontos (não mais 414). A VM ainda roda `pontuacao` com as tabelas antigas até a `tabela-oficial` ser implantada
- **Decisões do usuário em 2026-11-17**: o modelo da IA é o do `MARITALK_MODEL` no `.env` (hoje `sabia-4-thinking`, que raciocina e devolve `content` vazio com `max_tokens` baixo; use 8000 ou mais; vazio = `sabia-4-br-sp`; erro de modelo = nova tentativa com `sabia-4-br-sp`), revisando a decisão anterior de usar `sabia-4-br-sp` como padrão; mascarar CPF, RG, e-mail e telefone antes de enviar à MariTalk. A AD-005 continua válida
- **Blockers**: nenhum técnico. Pendentes de confirmação: padrões PROC-02 e PROC-04 (`fundacao`), 3 suposições e a isenção do I.3 (`pontuacao`); faltam o "Modelo Relatorio Atividades 2.docx" e as URLs da PROGEP/CPPD
- **Dívidas**: teste de 360 px só estático; sem backup; sem troca de senha; rotas de negócio devolvem 500 com banco fora do ar; `api/client.ts` só envia JSON; Grupo I do caso real com 16 pontos sem explicação; mínimos das classes novas sem regra; nginx do compose e do servidor limitam o corpo a 20 MB (precisa subir a 120 MB nesta feature); antivírus ausente na VM
- **MariTalk**: funciona (`test/test_maritalk.py`): `sabia-4`, `sabia-4-br-sp`, `sabiazinho-4` em `https://chat.maritaca.ai/api` (Bearer); `response_format` com `json_schema` estrito devolve `null` para dado ausente. A VM ainda tem `MARITALK_API_KEY` vazia; configurar no deploy desta feature
- **Documentos reais** (`Documentos/`, não versionados): 44 PDFs e 1 PNG; 3 só de imagem (Prêmio Sebrae, Certificado RPC, PNG de banca) e portarias com camada de texto cheia de lixo; tipos: declarações de banca e de coorientação, atas de defesa e do SIPAC, certificados de cursos e palestras, portarias, artigos (5 a 12 páginas) e registro do INPI
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; ver `docs/deploy/vm.md`). No ar desde 2026-11-17: `fundacao` + `pontuacao` (commit 369f710), com o banco `progressao` no PostgreSQL do `dashboard_db` (meu PostgreSQL foi removido; dump em /opt/progressao/backups), nginx do projeto só em 127.0.0.1:8400 e limites de memória e de log. Credenciais do ADMIN em /opt/progressao/.admin-credentials. Documentos (Etapas 2 e 3) NÃO estão no ar
- **Uncommitted files**: none (pasta `test/` e `requeriment.txt` sem versionar)
- **Branch**: feat/inteligencia-documental, empilhada sobre feat/pontuacao sobre feat/fundacao; só `feat/fundacao` está no origin (sem PR; main intocada). A branch empilhada tem mais de 100 commits sem push; nenhum push foi autorizado

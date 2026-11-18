# Documentos Gerados Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/documentos-gerados/design.md`
**Spec**: `.specs/features/documentos-gerados/spec.md`
**Status**: Implementing

Regras de execução desta feature: cada tarefa escreve primeiro os testes que derivam dos critérios de aceitação da spec e só então o código (os itens `Done when` começam pelo teste); nenhum teste, fixture ou commit leva dado pessoal real; `Documentos/` não é aberto por nenhuma tarefa, exceto a tarefa de contagem do corpus, e só com autorização do usuário; push, deploy, acesso à VM e chamada real à MariTalk exigem autorização explícita para cada ação (a tarefa de implantação só escreve uma nota).

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: requisitos do usuário, seção 19; AD-001 (teste de arquitetura); AD-004 (integração em PostgreSQL real); AD-009 e AD-014 (saída da IA não é confiável); suites e comandos de `fundacao`, `pontuacao` e `inteligencia-documental`. Existing tests sampled: `backend/tests/unit/{domain,application,infrastructure}`, `backend/tests/integration/{api,documents}`, `frontend/src/**/*.test.tsx`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules) | unit | All branches; 1:1 to spec ACs; every listed edge case and each boundary value (400 e 401 páginas, 12 megapixels, 20 000 caracteres) | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Document writers (DOCX, PDF, assembler) | unit | Key paths + error paths com documentos sintéticos: texto e páginas do PDF, XML do DOCX, igualdade por pixel e por bytes das páginas originais | `backend/tests/unit/infrastructure/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Adapters (storage, AI client) | unit | Key paths + error paths com diretório temporário e transporte HTTP simulado | `backend/tests/unit/infrastructure/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Settings and configuration files | unit | Padrões, sobrescrita por variável, arquivo inválido e conteúdo do arquivo contra a spec | `backend/tests/unit/test_config_*.py`, `backend/tests/unit/infrastructure/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| API schemas | unit | Serialização sem dado pessoal e campos extras recusados | `backend/tests/unit/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Repositories / migrations / worker | integration | Key query paths, concorrência (`SKIP LOCKED`, índices parciais únicos), gatilhos de imutabilidade e error paths | `backend/tests/integration/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Use cases + API routes | integration | All routes in scope: happy + every listed edge case + error paths (401/403/404/409/410/422); IA simulada, nunca real | `backend/tests/integration/{api,documents,doc_usecases}/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend components/pages | unit | Each UIG, DEL e ORD AC: render + interação + exibição de erro, com a API simulada | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Ports / types / dependencies / docs | none | build gate only | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or config-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order. A tarefa que depende de fase anterior lista a dependência em `Depends on`; o diagrama de cada fase mostra só a cadeia da própria fase.

### Phase 1: Dependências e refatorações com rede de proteção

```
T1 → T2 → T3 → T4 → T5
```

### Phase 2: Domínio: entidades

```
T6 → T7 → T8 → T9
```

### Phase 3: Regras puras: formatação e Tabela de Pontuação

```
T10 → T11 → T12 → T13 → T14
```

### Phase 4: Regras puras: arranjo e plano do Comprovante

```
T15 → T16 → T17 → T18 → T19 → T20
```

### Phase 5: Regras puras: rascunho e redação do Relatório

```
T21 → T22 → T23 → T24 → T25 → T26 → T27
```

### Phase 6: Regras puras: conclusão do processo

```
T28 → T29
```

### Phase 7: Banco: migração, modelos e portas

```
T30 → T31 → T32 → T33
```

### Phase 8: Repositórios

```
T34 → T35 → T36 → T37 → T38 → T39
```

### Phase 9: Armazenamento e configuração

```
T40 → T41 → T42 → T43 → T44
```

### Phase 10: Escritores da Tabela e do Relatório

```
T45 → T46 → T47 → T48 → T49
```

### Phase 11: Montagem do PDF do Comprovante

```
T50 → T51 → T52 → T53 → T54 → T55
```

### Phase 12: Executor e adaptador de redação

```
T56 → T57
```

### Phase 13: Aplicação: geração dos documentos

```
T58 → T59 → T60 → T61 → T62 → T63 → T64 → T65 → T66
```

### Phase 14: Aplicação: rascunho, arranjo e redação

```
T67 → T68 → T69 → T70 → T71 → T72 → T73
```

### Phase 15: Aplicação: conclusão e arquivos excluídos

```
T74 → T75 → T76 → T77 → T78 → T79 → T80
```

### Phase 16: API

```
T81 → T82 → T83 → T84 → T85 → T86 → T87 → T88
```

### Phase 17: Aceitação do backend

```
T89 → T90 → T91 → T92 → T93
```

### Phase 18: Interface: base

```
T94 → T95 → T96 → T97 → T98
```

### Phase 19: Interface: Relatório e Comprovante

```
T99 → T100 → T101 → T102
```

### Phase 20: Interface: documentos, conclusão e página

```
T103 → T104 → T105 → T106 → T107 → T108
```

### Phase 21: Encerramento: implantação, corpus e verificação

```
T109 → T110 → T111
```

### Batches (proposta de execução)

Fases inteiras acumuladas até ~7 tarefas por lote; o lote só fecha na fronteira de uma fase. Os lotes rodam em sequência.

| Lote | Fases | Tarefas | Quantidade |
| --- | --- | --- | --- |
| 1 | 1, 2 | T1 a T9 | 9 |
| 2 | 3, 4 | T10 a T20 | 11 |
| 3 | 5 | T21 a T27 | 7 |
| 4 | 6, 7, 8 | T28 a T39 | 12 |
| 5 | 9, 10 | T40 a T49 | 10 |
| 6 | 11, 12 | T50 a T57 | 8 |
| 7 | 13 | T58 a T66 | 9 |
| 8 | 14 | T67 a T73 | 7 |
| 9 | 15 | T74 a T80 | 7 |
| 10 | 16 | T81 a T88 | 8 |
| 11 | 17, 18 | T89 a T98 | 10 |
| 12 | 19, 20 | T99 a T108 | 10 |
| 13 | 21 | T109 a T111 | 3 |

Total: 111 tarefas em 21 fases e 13 lotes. O Verificador roda depois do último lote (T111).

---

## Task Breakdown

### Phase 1: Dependências e refatorações com rede de proteção

#### T1: Fixar as dependências de documentos

**What**: Acrescentar `python-docx==1.2.0`, `lxml==6.1.3` e `reportlab==5.1.0` (mais o `charset-normalizer` que o `pip` resolver, fixado) e instalar no ambiente de desenvolvimento.
**Where**: `backend/requirements.txt`
**Depends on**: None
**Reuses**: pinos existentes (`pymupdf==1.28.2`, `pillow==13.0.0`)
**Requirement**: TAB-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `pip install -r requirements.txt` roda sem compilador e `import docx, lxml, reportlab` funciona no `.venv`
- [x] A suíte inteira passa com reportlab 5.1.0; se algum teste falhar por causa dele, o pino cai para `reportlab==4.5.1` e o design registra a queda em Risks
- [x] Gate full passa; contagem de testes igual à anterior (nenhum teste removido)

**Tests**: none
**Gate**: full

**Commit**: `build(deps): pin the document generation libraries`

---

#### T2: Extrair `compute_process_score` com testes de caracterização

**What**: Escrever antes o teste de caracterização da resposta de `/scoring` e extrair o corpo de `CalculateProcessScore` para `compute_process_score(uow, process) -> ProcessScore`, chamável sem ator.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T1
**Reuses**: `CalculateProcessScore` (`scoring.py:646`) e os testes de pontuação existentes como rede de proteção
**Requirement**: TAB-01, TAB-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Primeiro o teste de caracterização: com o cenário do `test_scoring_golden.py` a resposta de `/scoring` (total 211, subtotais 52, 7, 62, 0, 30, 4, 56, contadores) é fixada e passa antes da extração
- [x] Depois da extração o mesmo teste passa sem alteração e o caso de uso só chama `compute_process_score` depois de checar o acesso
- [x] Teste novo: `compute_process_score(uow, process)` devolve o mesmo resultado que a rota, sem receber ator
- [x] Gate full passa; 3+ testes novos e nenhum teste de pontuação alterado

**Tests**: integration
**Gate**: full

**Commit**: `refactor(scoring): extract compute_process_score for reuse by generation`

---

#### T3: Erros de geração e de arquivo excluído

**What**: Criar `Gone(code, message)` e `GenerationRefused(code, message)` ao lado de `NotFound` e `Conflict`, com `code` e `message` acessíveis.
**Where**: `backend/app/domain/errors.py`
**Depends on**: T2
**Reuses**: `ValidationFailed` (campo e mensagem)
**Requirement**: TAB-07, DEL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os dois erros carregam `code` e `message` e descendem de `DomainError`
- [x] O teste de arquitetura segue verde (nada de framework no domínio)
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add generation and gone errors`

---

#### T4: Mapear os erros novos para HTTP

**What**: Mapear `GenerationRefused` para 422 e `Gone` para 410 com o corpo `{detail: [{field, code, message}]}`, e fazer `Conflict` com código devolver o `code` no corpo 409.
**Where**: `backend/app/presentation/errors.py`
**Depends on**: T3
**Reuses**: `install_error_handlers` e a forma de erro de `documents.py`
**Requirement**: TAB-07, DEL-12, DEL-14, VER-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Rota de teste que levanta `GenerationRefused` responde 422 com `field`, `code` e `message`
- [x] Rota de teste que levanta `Gone` responde 410 e `Conflict` com código responde 409 com o código no corpo
- [x] Os erros existentes (404, 409 sem código, 422 de validação) respondem como antes
- [x] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): map generation and gone errors to http`

---

#### T5: Extrair `MariTalkClient` do extrator

**What**: Extrair o transporte (cabeçalho, mapeamento de status, modelo reserva `sabia-4-br-sp`, prazo total por chamada) de `MariTalkExtractor` para `MariTalkClient`, sem mudar o comportamento do extrator.
**Where**: `backend/app/infrastructure/ai/maritalk.py`
**Depends on**: T4
**Reuses**: `MariTalkExtractor._post` (`maritalk.py:72-127`) e os testes do extrator com transporte falso
**Requirement**: REL-03, REL-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os testes existentes do extrator (`test_maritalk_prompt.py` e vizinhos) passam sem alteração depois da extração
- [x] Teste novo: `MariTalkClient.chat(...)` repete uma vez com o modelo reserva quando o erro é de modelo e respeita o prazo total informado
- [x] Gate quick passa; 3+ testes novos

**Tests**: unit
**Gate**: quick

**Commit**: `refactor(ai): extract the MariTalk transport into a shared client`

---

### Phase 2: Domínio: entidades

#### T6: Entidades de documento gerado

**What**: `DocumentKind`, `DocumentFormat`, `GenerationState`, `can_transition`, `GeneratedDocument`, `GeneratedFile`, `GenerationCode`, `GenerationAlertCode` e `WordingJob`.
**Where**: `backend/app/domain/entities/generated.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: padrão de `entities/document.py` (`StrEnum`, `can_transition`)
**Requirement**: VER-01, VER-04, VER-05, REL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `can_transition`: `GERANDO` para `PRONTO` ou `FALHOU`; qualquer outra transição é recusada, inclusive a partir de `PRONTO` e `FALHOU`
- [x] Os códigos do design existem com o nome exato (`SEM_ATIVIDADES_VALIDADAS`, `TABELA_NAO_ESCOLHIDA`, `ATIVIDADE_SEM_DESCRICAO`, `COMPROVANTE_GRANDE_DEMAIS`, `IMAGEM_GRANDE_DEMAIS`, `ORIGINAL_INDISPONIVEL`, `ORIGINAIS_EXCLUIDOS`, `INTERROMPIDA`, `ESPACO_INSUFICIENTE`, `ERRO_INTERNO`, `GERACAO_EM_ANDAMENTO`, `REDACAO_EM_ANDAMENTO`, `ARTEFATOS_PENDENTES`, `CONFIRMACAO_OBRIGATORIA`, `OPERACAO_EM_ANDAMENTO`, `CONCLUSAO_EXIGE_EXCLUSAO`, `ARQUIVO_EXCLUIDO`, `PAGINA_FORA_DO_DOCUMENTO`, `VERSAO_DESATUALIZADA`, `PROCESSO_SOMENTE_LEITURA`) e os alertas (`ATIVIDADE_SEM_COMPROVANTE`, `REDACAO_REJEITADA`, `REDACAO_INDISPONIVEL`, `ARRANJO_DESATUALIZADO`, `NUMERACAO_DIVERGENTE`, `ATIVIDADES_FORA_DO_DOCUMENTO`, `PAGINA_REPETIDA_JUSTIFICADA`, `PAGINA_RASTERIZADA`, `RASCUNHO_DESATUALIZADO`, `EXCLUSAO_PARCIAL`)
- [x] Nada importa framework (teste de arquitetura verde); gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add generated document entities`

---

#### T7: Entidades do rascunho do Relatório

**What**: `ReportTemplate`, `TemplateSection`, `ReportDraft`, `DraftSection`, `DraftEntry` e `EntrySource` (`MODELO`, `IA`, `USUARIO`).
**Where**: `backend/app/domain/entities/report.py`
**Depends on**: T6
**Reuses**: padrão de `entities/activity.py`
**Requirement**: REL-01, REL-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `DraftEntry` guarda `activity_id`, `text`, `source` e avisos; `source` só admite os três valores
- [x] `ReportTemplate` representa seção com `match`, `group_by`, `entry` e `order_items`; o rascunho é imutável por cópia (`replace`)
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add report draft entities`

---

#### T8: Entidades do arranjo do Comprovante

**What**: `ComprovanteLayout`, `LayoutActivity`, `LayoutPage` (com `repeat_justification`), `ComprovantePlan`, `PlanPage` (`CAPA`, `SUMARIO`, `SEPARADOR`, `ORIGINAL`) e `Staleness`.
**Where**: `backend/app/domain/entities/comprovante.py`
**Depends on**: T7
**Reuses**: padrão de `entities/activity.py`
**Requirement**: ARR-01, CMP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `LayoutPage(document_id, page, repeat_justification)` aceita justificativa vazia como `None` e recusa página menor que 1
- [x] `ComprovantePlan` guarda a lista ordenada de páginas com número e o `plan_hash`
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add comprovante layout entities`

---

#### T9: Entidades da conclusão

**What**: `ConclusionPreview`, `ConclusionResult` e `ConclusionCheck`.
**Where**: `backend/app/domain/entities/conclusion.py`
**Depends on**: T8
**Reuses**: padrão de `entities/generated.py`
**Requirement**: DEL-03, DEL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `ConclusionPreview` guarda `files`, `bytes` e `artifacts` por tipo; `ConclusionResult` guarda `status`, `files_removed`, `files_pending`, `bytes_freed` e alertas
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add conclusion entities`

---

### Phase 3: Regras puras: formatação e Tabela de Pontuação

#### T10: Formatação em português

**What**: `pt_format`: datas `dd/mm/aaaa`, decimais com vírgula, `1º Período de 2023`, carga horária e intervalo de interstício.
**Where**: `backend/app/domain/rules/pt_format.py`
**Depends on**: T6 (fase 2)
**Reuses**: `Interstice`
**Requirement**: TAB-02, REL-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `Decimal('52.00')` vira `52,00`; `date(2024,11,23)` vira `23/11/2024`; `2023.1` vira `1º Período de 2023`
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add portuguese formatting rules`

---

#### T11: Nome de arquivo do download

**What**: `download_name(kind, fmt, interstice, version)`, por exemplo `Tabela_de_Pontuacao_2020-2024_v2.pdf`, sem nome do docente.
**Where**: `backend/app/domain/rules/download_names.py`
**Depends on**: T10
**Reuses**: `pt_format`
**Requirement**: VER-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os seis nomes (três tipos, dois formatos onde existem) saem sem acento nem espaço e sem o nome do docente
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add download file names`

---

#### T12: Modelo da Tabela: linhas e faixas de grupo

**What**: `build_table_document` parte 1: 7 colunas (item `I.1`, atividade, quantidade, pontos unitários, total, comprovante, status), grupo como faixa com nome e subtotal (também para grupos vazios, com zero), na ordem dos grupos e itens, com o número do comprovante ou `sem comprovante`.
**Where**: `backend/app/domain/rules/table_document.py`
**Depends on**: T11
**Reuses**: `ScoringResult`, `ScoringRow` (`scoring_engine.py`)
**Requirement**: TAB-02, TAB-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cabeçalho com docente, classe e nível atuais e pretendidos, unidade, interstício e nome e referência normativa da versão da tabela
- [x] Cenário de 211 pontos: sete faixas de grupo com os subtotais 52, 7, 62, 0, 30, 4 e 56; grupo sem atividade aparece com zero
- [x] Cada linha traz o número do comprovante vindo do plano ou `sem comprovante`; a ordem segue grupos e itens
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): build the scoring table rows and group bands`

---

#### T13: Modelo da Tabela: totais, horas e alertas

**What**: `build_table_document` parte 2: pontuação geral, contagens (atividades, comprovantes, pendentes, não pontuadas, divergências), seção separada das horas de PIT e os alertas da pontuação com o texto da tela.
**Where**: `backend/app/domain/rules/table_document.py`
**Depends on**: T12
**Reuses**: `Counters`, `Alert`, `AlertList` da tela de pontuação
**Requirement**: TAB-04, TAB-05, TAB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Total 211 e contagens idênticas às do resultado do motor
- [x] Horas de PIT 24, 24, 24 e 20 (total 92) em seção separada, sem somar aos pontos; sem essa tabela de horas a seção não existe
- [x] Limites aplicados, carga horária insuficiente e data final ausente aparecem com o texto do motor
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add table totals, pit hours and alerts`

---

#### T14: Instantâneo da versão

**What**: `build_snapshot(...)` com a versão da tabela, intervalo, total, subtotais, horas de PIT, atividades (grupo, item, quantidade, pontos, status), excluídas por motivo, alertas, modelo e acréscimos por tipo.
**Where**: `backend/app/domain/rules/generation_snapshot.py`
**Depends on**: T13
**Reuses**: `ScoringResult`; formato do design
**Requirement**: VER-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O instantâneo da Tabela do cenário de 211 contém identificador e nome da versão da tabela, total, subtotais e lista de atividades
- [x] A chave `layout` (Tabela e Comprovante) e `report` (Relatório) só aparecem no tipo correspondente
- [x] O dicionário é serializável em JSON e estável (mesma entrada, mesma saída)
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add the generation snapshot`

---

### Phase 4: Regras puras: arranjo e plano do Comprovante

#### T15: Arranjo derivado dos vínculos

**What**: `derive_layout(activities, evidences, documents)`: ordem dos grupos e itens da tabela e, dentro do item, por data da atividade.
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T8 (fase 2)
**Reuses**: `ActivityEvidence`, ordenação de `scoring_engine.py`
**Requirement**: ARR-01, ARR-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem arranjo salvo, as atividades saem por grupo, item e data; as páginas seguem a ordem dos vínculos
- [x] Duas atividades com o mesmo título no mesmo item aparecem as duas, cada uma com as suas páginas
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): derive the comprovante layout from the links`

---

#### T16: Plano do Comprovante: páginas e numeração

**What**: `plan_comprovante` parte 1: lista ordenada `CAPA`, `SUMARIO`, `SEPARADOR` por grupo e `ORIGINAL`, numeração contínua a partir da capa, capacidade fixa de linhas do sumário e primeira página de cada grupo, item e atividade.
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T15
**Reuses**: `derive_layout`
**Requirement**: CMP-01, CMP-02, CMP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Processo de 3 grupos e 5 atividades: capa na página 1, sumário com `ceil(linhas / capacidade)` páginas, um separador por grupo com atividade, originais na ordem do arranjo
- [x] O sumário traz para cada grupo, item e atividade o número da primeira página; cada entrada de atividade traz documento de origem, página e intervalo no Comprovante
- [x] Grupo sem atividade não gera separador (edge case)
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): plan the comprovante pages and numbering`

---

#### T17: Plano do Comprovante: página repetida e atividade sem página

**What**: `plan_comprovante` parte 2: a mesma página em mais de uma atividade é anexada uma vez e as demais recebem remissão; repetição com justificativa anexa de novo e registra `PAGINA_REPETIDA_JUSTIFICADA`; atividade sem página entra com `Sem comprovante anexado` e `ATIVIDADE_SEM_COMPROVANTE`.
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T16
**Reuses**: `plan_comprovante` parte 1
**Requirement**: CMP-05, CMP-06, CMP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Duas atividades apontando a mesma página: a primeira anexa, a segunda traz `ver comprovante nº N, p. X`
- [x] Com `repeat_justification` a página entra de novo, o alerta sai e a justificativa vai para o plano
- [x] Atividade sem página aparece com a linha `Sem comprovante anexado` e gera `ATIVIDADE_SEM_COMPROVANTE`; a numeração dos demais não muda
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): handle shared and missing pages in the plan`

---

#### T18: Plano do Comprovante: limites, origens indisponíveis e hash

**What**: `plan_comprovante` parte 3: `COMPROVANTE_GRANDE_DEMAIS` acima de 400 páginas anexadas, `ORIGINAL_INDISPONIVEL` (documento ausente ou página inexistente), `IMAGEM_GRANDE_DEMAIS` (PNG acima de 12 megapixels), `ORIGINAIS_EXCLUIDOS` e `plan_hash` (SHA-256 do plano em JSON canônico).
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T17
**Reuses**: `GenerationCode`
**Requirement**: CMP-09, CMP-10, CMP-13, DEL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 400 páginas passam e 401 recusam com `COMPROVANTE_GRANDE_DEMAIS`; a remissão não conta como página anexada
- [x] Documento excluído do processo ou página fora de `1..page_count` vira `ORIGINAL_INDISPONIVEL` com documento e página
- [x] PNG de 12 megapixels passa, de 12 megapixels e 1 pixel recusa com `IMAGEM_GRANDE_DEMAIS` citando o documento; JPEG de 40 megapixels passa
- [x] Documento com `ARQUIVO_EXCLUIDO` recusa o Comprovante com `ORIGINAIS_EXCLUIDOS`, mas o plano da Tabela (só metadados) continua calculável
- [x] `plan_hash` é o mesmo para o mesmo plano e muda quando a ordem muda
- [x] Gate quick passa; 12+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add comprovante plan limits and hash`

---

#### T19: Desatualização do arranjo

**What**: `layout_staleness(layout, activities, evidences) -> Staleness`: atividade validada que saiu, foi revalidada ou mudou de item e vínculo novo.
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T18
**Reuses**: `Staleness`
**Requirement**: ARR-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Atividade rejeitada depois do arranjo, mudança de item e vínculo novo marcam T19; arranjo igual às atividades atuais não marca
- [x] A geração usa só as atividades atuais; entrada de documento excluído é marcada inválida
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): detect a stale comprovante layout`

---

#### T20: Validação do arranjo salvo

**What**: `validate_layout(layout, process_documents, activities)`: documento ou página fora do processo, página fora de `1..page_count` e atividade movida para item diferente do da pontuação.
**Where**: `backend/app/domain/rules/comprovante_plan.py`
**Depends on**: T19
**Reuses**: `LayoutPage`
**Requirement**: ARR-02, ARR-03, ARR-04, ARR-05, ARR-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Documento de outro processo é recusado como não encontrado e página 0 ou acima de `page_count` como `PAGINA_FORA_DO_DOCUMENTO`
- [x] Mover atividade para outro item é recusado; reordenar atividades dentro do item e páginas dentro da atividade é aceito e preserva a nova ordem
- [x] Remover página do arranjo não toca no vínculo atividade-página (a função não escreve)
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): validate the saved comprovante layout`

---

### Phase 5: Regras puras: rascunho e redação do Relatório

#### T21: Proposta do rascunho por seção

**What**: `propose_draft(template, activities, group_map)`: distribui as atividades validadas pelo mapa de grupo para seção, organiza 1.1 e 1.2 por período letivo e o 1.3 por modalidade, concluídas e em andamento, e lista as seções sem atividade como vazias.
**Where**: `backend/app/domain/rules/report_draft.py`
**Depends on**: T7 (fase 2), T10 (fase 3)
**Reuses**: `ReportTemplate`, `normalize_title`, `pt_format`
**Requirement**: REL-01, REL-02, REL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Grupo I.1 vai a 1.1 e I.2 a 1.2 por período letivo; II a 1.3; III e VII a 6 com os subtítulos; IV a 3; V a 2; VI a 4; VIII a 6; a seção 5 recebe só o que for movido
- [x] Seção sem atividade é marcada vazia e fica fora do documento
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): propose the report draft by section`

---

#### T22: Texto-modelo determinístico

**What**: `template_text(entry_spec, activity)`: preenche `line` ou `fields` da configuração e omite o campo sem valor; o curso só aparece se estiver no título ou na descrição.
**Where**: `backend/app/domain/rules/report_draft.py`
**Depends on**: T21
**Reuses**: `pt_format`
**Requirement**: REL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Atividade sem fonte do recurso, colaboradores ou número de portaria não ganha essas linhas nem valores inventados
- [x] Carga horária, período letivo e datas saem formatados em português
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add the deterministic report entry text`

---

#### T23: Reconciliar o rascunho com as atividades

**What**: `reconcile_draft(draft, activities)` e a operação de mover atividade de seção: acrescenta ao fim as atividades novas, nunca toca texto de fonte `USUARIO` e gera `RASCUNHO_DESATUALIZADO`.
**Where**: `backend/app/domain/rules/report_draft.py`
**Depends on**: T22
**Reuses**: `DraftEntry`
**Requirement**: REL-07, REL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Texto editado pelo usuário permanece idêntico depois de `reconcile_draft`
- [x] Mover atividade guarda a seção escolhida e o rascunho reconciliado a mantém lá
- [x] Atividade nova ou removida desde a última edição gera `RASCUNHO_DESATUALIZADO`
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): reconcile the report draft with the activities`

---

#### T24: Conferência da redação: números e datas

**What**: `check_wording` parte 1: todo número (inteiro, decimal, ordinal, data em `dd/mm/aaaa` e por extenso, ano, período letivo) precisa estar nos campos enviados, comparados normalizados.
**Where**: `backend/app/domain/rules/report_grounding.py`
**Depends on**: T23
**Reuses**: `numerals_from_words`, `hours_in_text`, `date_in_text`, `grounding.py`
**Requirement**: REL-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Número inventado (`120 horas` quando o campo diz 60) e data inventada são reprovados com `NUMERO` e `DATA`
- [x] Formatos fiéis em variações (`60h`, `sessenta horas`, `1º semestre de 2023`, `23 de novembro de 2024`) são aceitos
- [x] Gate quick passa; 14+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): check numbers and dates in generated wording`

---

#### T25: Conferência da redação: nomes, vocabulário e comprimento

**What**: `check_wording` parte 2: nome próprio ou sigla fora dos campos e de `allowed_terms`, mais de `max_new_words` palavras novas, comprimento acima de duas vezes o texto-modelo mais 120 caracteres e palavras proibidas.
**Where**: `backend/app/domain/rules/report_grounding.py`
**Depends on**: T24
**Reuses**: `WordingCheck`
**Requirement**: REL-04, REL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nome novo reprova com `NOME`; `objetivo`, `resultado`, `metodologia`, `excelente`, `relevante`, `visando` e `contribuindo` reprovam com `PALAVRA_PROIBIDA`
- [x] Palavra de conteúdo nova além do limite reprova com `VOCABULARIO`; texto longo reprova com `COMPRIMENTO`
- [x] Sigla e nome presentes nos campos ou em `allowed_terms` (UFPA, Universidade Federal do Pará, unidade) são aceitos; reprovação devolve o texto-modelo
- [x] Gate quick passa; 14+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): check names and vocabulary in generated wording`

---

#### T26: Campos enviados à MariTalk

**What**: `build_wording_items(activities)`: por atividade, `id` opaco, tipo do critério, título, datas, carga horária, período letivo, quantidade e descrição após `mask_identifiers`; nada mais.
**Where**: `backend/app/domain/rules/report_wording.py`
**Depends on**: T25
**Reuses**: `mask_identifiers`
**Requirement**: REL-03, REL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O dicionário enviado não contém texto de página, nome do docente, SIAPE nem `evidence_note`, mesmo quando a atividade os tem
- [x] A descrição mascarada não contém CPF, e-mail ou telefone
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): build the fields sent for report wording`

---

#### T27: Aplicação do resultado da redação

**What**: `apply_wording(draft, section_key, results)`: aplica o texto só às entradas sem fonte `USUARIO`, usa o texto-modelo quando a conferência reprova e devolve os avisos `REDACAO_REJEITADA` com o motivo.
**Where**: `backend/app/domain/rules/report_wording.py`
**Depends on**: T26
**Reuses**: `check_wording`, `template_text`
**Requirement**: REL-04, REL-05, REL-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Resposta fiel vira fonte `IA`; resposta com número inventado vira texto-modelo com `REDACAO_REJEITADA` e o motivo `NUMERO`
- [x] Entrada editada pelo usuário permanece idêntica e fora do envio
- [x] Sem resposta (indisponível) todas as entradas sem `USUARIO` ficam com o texto-modelo e a seção ganha `REDACAO_INDISPONIVEL`
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): apply checked wording to the report draft`

---

### Phase 6: Regras puras: conclusão do processo

#### T28: Verificação da conclusão

**What**: `check_conclusion(ready_kinds, active_operations)`: `ARTEFATOS_PENDENTES` com os tipos que faltam e `OPERACAO_EM_ANDAMENTO`.
**Where**: `backend/app/domain/rules/conclusion_rules.py`
**Depends on**: T9 (fase 2), T6 (fase 2)
**Reuses**: `ConclusionCheck`, `DocumentKind`
**Requirement**: DEL-01, DEL-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem Comprovante `PRONTO` a verificação recusa com `ARTEFATOS_PENDENTES` listando só `COMPROVANTE`; sem nenhum, lista os três na ordem Tabela, Relatório, Comprovante
- [x] Geração, redação ou processamento de documento em andamento recusa com `OPERACAO_EM_ANDAMENTO`
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): check whether a process can be concluded`

---

#### T29: Prévia e resultado da exclusão

**What**: `summarize_purge(documents)` (arquivos e bytes dos documentos sem `file_deleted_at`) e `purge_outcome(removed, failed, bytes)` com `EXCLUSAO_PARCIAL` quando há pendentes.
**Where**: `backend/app/domain/rules/conclusion_rules.py`
**Depends on**: T28
**Reuses**: `ConclusionPreview`, `ConclusionResult`
**Requirement**: DEL-03, DEL-08, DEL-09, DEL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Prévia conta só os documentos ainda com arquivo e soma `size_bytes`; processo sem documentos dá zero arquivos e zero bytes
- [x] Resultado com um pendente traz `EXCLUSAO_PARCIAL` e o processo continua EM_ANDAMENTO; sem pendente, o status vira CONCLUIDO
- [x] Repetir o resultado de um processo já concluído devolve zeros e o mesmo status (idempotência)
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): summarize and judge the input document purge`

---

### Phase 7: Banco: migração, modelos e portas

#### T30: Migração 0006: documentos gerados

**What**: Enums `generated_kind`, `generated_state`, `generated_format`, tabelas `generated_documents` e `generated_files`, índice parcial único `(process_id, kind)` em `GERANDO`, índice de histórico e gatilhos de imutabilidade.
**Where**: `backend/alembic/versions/0006_generated_documents.py`
**Depends on**: T6 (fase 2)
**Reuses**: `0003_documents.py:90` (gatilho de `extraction_runs`)
**Requirement**: VER-01, VER-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Duas linhas `GERANDO` do mesmo processo e tipo: a segunda falha por violação do índice único; tipos diferentes coexistem
- [x] `UPDATE` de linha `PRONTO` ou `FALHOU` e `DELETE` de `generated_documents` falham; `UPDATE` e `DELETE` de `generated_files` falham; `GERANDO` para `PRONTO` funciona
- [x] `upgrade` e `downgrade` rodam em PostgreSQL real e o modelo ORM de `0004` segue íntegro; gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the generated documents migration`

---

#### T31: Migração 0006: redação, rascunho, arranjo e marca de exclusão

**What**: Tabelas `report_wording_jobs` (índice parcial único `(process_id, section_key)` em `GERANDO`), `report_drafts` e `comprovante_layouts` (unique por processo, JSONB e `version`) e a coluna `documents.file_deleted_at`.
**Where**: `backend/alembic/versions/0006_generated_documents.py`
**Depends on**: T30
**Reuses**: `0003_documents.py` (padrões de índice e FK)
**Requirement**: REL-13, ARR-07, DEL-05, DEL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Segundo `GERANDO` da mesma seção falha; seções diferentes coexistem
- [x] Um rascunho e um arranjo por processo; segundo insert falha por unique
- [x] `documents.file_deleted_at` aceita nulo e data; documentos existentes ficam com nulo; `downgrade` remove tudo sem afetar `0004`
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add wording jobs, drafts, layouts and the file purge mark`

---

#### T32: Modelos ORM das tabelas novas

**What**: Modelos de `generated_documents`, `generated_files`, `report_wording_jobs`, `report_drafts`, `comprovante_layouts` e a coluna `file_deleted_at` de `documents`.
**Where**: `backend/app/infrastructure/database/models.py`
**Depends on**: T31
**Reuses**: padrão de `DocumentModel`
**Requirement**: VER-02, REL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `Base.metadata` concorda com a migração (o teste de esquema existente passa) e cada modelo grava e lê uma linha de exemplo
- [x] Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the generated documents models`

---

#### T33: Portas e repositórios abstratos

**What**: Protocolos `GenerationRepository`, `WordingJobRepository`, `ReportDraftRepository`, `LayoutRepository`, `DocumentWriter`, `ComprovanteAssembler`, `ReportWriter`, `GeneratedFileStorage` e os métodos novos de `DocumentRepository`, `ExtractionRepository` e `EvidenceRepository`; `UnitOfWork` ganha os repositórios.
**Where**: `backend/app/domain/repositories/ports.py`
**Depends on**: T32
**Reuses**: protocolos existentes (`JobRepository`, `FileStorage`)
**Requirement**: VER-01, REL-03, CMP-01, DEL-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os Protocolos existem com as assinaturas do design (`claim_next`, `finish`, `recover_stuck`, `mark_file_deleted`, `delete_pages`, `clear_excerpts_for_document`, `list_for_activities`)
- [x] O teste de arquitetura segue verde; gate quick passa e nenhum teste existente quebra

**Tests**: none
**Gate**: quick

**Commit**: `feat(domain): add the generated documents ports`

---

### Phase 8: Repositórios

#### T34: Repositório das gerações

**What**: Implementar `add`, `get`, `list_for_process`, `claim_next` (`SKIP LOCKED`), `finish_ready` (número da versão `max + 1` por processo e tipo, arquivos, instantâneo, alertas), `finish_failed`, `recover_interrupted` e `latest_ready_by_kind`.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T33 (fase 7), T32 (fase 7)
**Reuses**: `JobRepository.claim_next` e `recover_stuck` (`repositories.py:1085`)
**Requirement**: VER-01, VER-02, VER-04, VER-05, VER-08, DEL-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Duas gerações do mesmo processo e tipo terminando em `PRONTO` recebem as versões 1 e 2; uma que falha não gasta número
- [x] Duas chamadas concorrentes de `claim_next` nunca pegam a mesma linha; só a linha com `started_at` preenchido vira `FALHOU/INTERROMPIDA` na recuperação
- [x] `latest_ready_by_kind` devolve a versão mais recente `PRONTO` por tipo ou nada
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the generation repository`

---

#### T35: Repositório das tarefas de redação

**What**: `add`, `get`, `claim_next`, `finish`, `recover_interrupted` e `latest_by_section`.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T34
**Reuses**: T34
**Requirement**: REL-03, REL-13, REL-14, REL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Segunda tarefa `GERANDO` da mesma seção levanta conflito; seção diferente passa
- [x] `recover_interrupted` fecha como `FALHOU/INTERROMPIDA` só a tarefa com `started_at` preenchido; `latest_by_section` devolve a mais recente por seção
- [x] Gate full passa; 7+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the wording job repository`

---

#### T36: Repositório do rascunho

**What**: `get`, `create` (versão 1) e `update_entry`, `update_section`, `move_entry` com bloqueio otimista por `version`, e `apply_wording_locked` (trava a linha e não incrementa `version`).
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T35
**Reuses**: bloqueio otimista de `DocumentRepository.update`
**Requirement**: REL-07, REL-08, REL-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `expected_version` desatualizada levanta `StaleVersion`; a primeira gravação exige `expected_version = 0`; segundo create do mesmo processo levanta conflito
- [x] `apply_wording_locked` troca só entradas que continuam sem fonte `USUARIO` e não muda `version`
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the report draft repository`

---

#### T37: Repositório do arranjo

**What**: `get`, `create` e `update` do arranjo com bloqueio otimista por `version`.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T36
**Reuses**: T36
**Requirement**: ARR-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `expected_version` desatualizada levanta `StaleVersion` e não sobrescreve; `expected_version = 0` cria
- [x] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the comprovante layout repository`

---

#### T38: Métodos de exclusão e leitura em lote

**What**: `mark_file_deleted`, `delete_pages`, `clear_excerpts_for_document`, `list_for_activities` e a leitura de jobs de processamento ativos do processo.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T37
**Reuses**: `DocumentRepository.delete`, `EvidenceRepository`, `ExtractionRepository.replace_pages`
**Requirement**: DEL-05, DEL-06, DEL-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Depois dos três métodos o documento mantém metadados e `file_deleted_at`, as páginas somem, o trecho vira `''` e `document_id` e `page_number` do vínculo ficam; repetir os métodos é inofensivo
- [x] `list_for_activities` devolve os vínculos de várias atividades numa só consulta
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add document purge and bulk evidence queries`

---

#### T39: Unidade de trabalho com os repositórios novos

**What**: Expor `generations`, `wording_jobs`, `report_drafts` e `comprovante_layouts` na `UnitOfWork` concreta.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T38
**Reuses**: `SqlUnitOfWork` (`repositories.py:1242`)
**Requirement**: VER-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada repositório é acessível por `uow.<nome>` e participa do commit e do rollback da mesma transação
- [x] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): expose the new repositories in the unit of work`

---

### Phase 9: Armazenamento e configuração

#### T40: Armazenamento dos arquivos gerados

**What**: `LocalGeneratedStorage`: `storage/generated/{process_id}/{uuid4}.{docx|pdf}` com 0700/0600, `new_temp_path`, `commit` por `os.replace` e limpeza de temporários.
**Where**: `backend/app/infrastructure/storage/generated_storage.py`
**Depends on**: T33 (fase 7)
**Reuses**: `LocalFileStorage` (`local_storage.py`)
**Requirement**: VER-01, VER-05, CMP-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Permissões 0700 no diretório e 0600 no arquivo; o nome interno não leva o nome do docente
- [x] `commit` renomeia no mesmo diretório; `cleanup` remove `.tmp-*` e arquivos sem linha; nada é lido para a memória
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(storage): add the generated file storage`

---

#### T41: Configurações novas

**What**: `generation_max_pages` (400), `generation_max_output_mb` (60), `generation_png_max_megapixels` (12), `generation_min_free_mb` (200), `wording_timeout_seconds` (60) e `report_template_id`.
**Where**: `backend/app/core/config.py`
**Depends on**: T40
**Reuses**: `load_settings` e `test_config_documents.py`
**Requirement**: CMP-09, CMP-13, REL-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os padrões valem sem variável de ambiente e as variáveis `GENERATION_*` e `WORDING_TIMEOUT_SECONDS` os sobrescrevem; valor inválido derruba o carregamento com mensagem clara
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(config): add the generation settings`

---

#### T42: Carregador e validação da configuração

**What**: `config_loader`: lê `report_templates.json` e `dossier_order.json` e valida a estrutura; JSON inválido ou seção sem `key` derruba o carregamento com mensagem clara.
**Where**: `backend/app/infrastructure/documents/config_loader.py`
**Depends on**: T41
**Reuses**: `load_settings` (mensagens claras de configuração)
**Requirement**: ORD-02, REL-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Arquivo com JSON inválido, seção sem `key` ou `group_map` apontando para seção inexistente levanta erro com o nome do arquivo e do campo
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): add the report configuration loader`

---

#### T43: Modelo institucional do Relatório

**What**: `report_templates.json`: página A4, margens, Times New Roman 9 pt, cabeçalho institucional, identificação, seções 1.1, 1.2, 1.3, 2, 3, 4, 5, 6, `group_map`, `entry` por seção, `allowed_terms`, `formal_vocabulary`, `forbidden_words`, `max_new_words` e `entry_style: campos`.
**Where**: `backend/app/infrastructure/documents/config/report_templates.json`
**Depends on**: T42
**Reuses**: `Modelo Relatorio Atividades 2.docx` como fonte do formato (só o formato, sem dado real)
**Requirement**: REL-01, REL-02, REL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O carregador aceita o arquivo; o teste confere as 8 seções na ordem, o mapa de grupo para seção da spec e a lista de palavras proibidas
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): add the institutional report template`

---

#### T44: Ordem do dossiê

**What**: `dossier_order.json`: requerimento à CPPD, portaria da última progressão, declaração de pagamento de exercícios anteriores, relatório, Tabela de Pontuação, documentação comprobatória numerada e currículo Lattes, com a marca de quem é gerado pelo sistema.
**Where**: `backend/app/infrastructure/documents/config/dossier_order.json`
**Depends on**: T43
**Reuses**: `ordenamentodecomoosdocumentosdevemestarsequenciadosnorelatrio.pdf` (lista, sem dado real)
**Requirement**: ORD-01, ORD-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A ordem do arquivo é a ordem do dossiê e só `RELATORIO`, `TABELA` e `COMPROVANTE` têm `generated_by`
- [x] A posição da Tabela de Pontuação fica marcada no design como a confirmar pelo usuário
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): add the dossier order list`

---

### Phase 10: Escritores da Tabela e do Relatório

#### T45: Fonte e estilos de PDF

**What**: Versionar Liberation Serif (Regular, Bold, Italic, BoldItalic, licença OFL 1.1) e registrar fonte, estilos e margens do reportlab.
**Where**: `backend/app/infrastructure/documents/pdf_styles.py`
**Depends on**: T1 (fase 1)
**Reuses**: design (Fonte); `Modelo Relatorio Atividades 2.docx` (margens)
**Requirement**: TAB-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os quatro TTF e o texto da licença estão em `fonts/`
- [ ] PDF de teste com `Ação, Ñandú, Zoë, ç, ü, ª` extraído pelo PyMuPDF devolve exatamente o texto escrito e a fonte está embutida em subconjunto
- [ ] Gate quick passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): add the pdf font and styles`

---

#### T46: PDF da Tabela

**What**: `write_table(model, 'PDF', target)` com reportlab: 7 colunas, faixa de grupo, linha de título repetida, `Página N de M`, seção de horas e alertas.
**Where**: `backend/app/infrastructure/documents/table_pdf.py`
**Depends on**: T45
**Reuses**: `TableDocument` e `pdf_styles`
**Requirement**: TAB-01, TAB-03, TAB-04, TAB-05, TAB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] PDF do cenário de 211 pontos: o texto extraído traz 211, os subtotais 52, 7, 62, 0, 30, 4 e 56 e as horas 24, 24, 24, 20 (92)
- [ ] O cabeçalho da tabela repete em cada página (1000 linhas) e o rodapé numera `Página N de M`; acentos corretos
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): write the scoring table as pdf`

---

#### T47: DOCX da Tabela

**What**: `write_table(model, 'DOCX', target)` com python-docx: largura de colunas em `tblGrid` com `tblLayout fixed`, `w:tblHeader` na primeira linha, faixa de grupo e rodapé com campos `PAGE` e `NUMPAGES`.
**Where**: `backend/app/infrastructure/documents/table_docx.py`
**Depends on**: T46
**Reuses**: `TableDocument`
**Requirement**: TAB-01, TAB-03, TAB-04, TAB-05, TAB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O XML do DOCX tem 7 colunas, `tblHeader`, `tblGrid` com as larguras e `fldChar` de página; o texto lido de volta traz 211 e os mesmos subtotais e horas do PDF
- [ ] Acentos e caracteres fora do latim básico saem corretos
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): write the scoring table as docx`

---

#### T48: DOCX do Relatório

**What**: `write_report(model, 'DOCX', target)`: A4, Times New Roman, cabeçalho institucional centralizado, identificação, seções omitindo as vazias e textos do rascunho.
**Where**: `backend/app/infrastructure/documents/report_docx.py`
**Depends on**: T47
**Reuses**: `report_templates.json` e `pt_format`
**Requirement**: REL-09, REL-11, REL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O DOCX traz o cabeçalho, a identificação do docente e do interstício e todas as seções com atividade na ordem do modelo; seção vazia não aparece
- [ ] O texto do documento é o texto do rascunho, sem objetivo, resultado nem metodologia acrescentados
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): write the activities report as docx`

---

#### T49: PDF do Relatório

**What**: `write_report(model, 'PDF', target)` com reportlab: parágrafos justificados, marcadores, margens do modelo e `Página N de M`.
**Where**: `backend/app/infrastructure/documents/report_pdf.py`
**Depends on**: T48
**Reuses**: `pdf_styles`, `report_docx.py` (mesmo modelo de conteúdo)
**Requirement**: REL-09, REL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O texto extraído do PDF tem as mesmas seções, na mesma ordem e com o mesmo texto do DOCX do mesmo modelo
- [ ] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): write the activities report as pdf`

---

### Phase 11: Montagem do PDF do Comprovante

#### T50: Capa, sumário e separadores

**What**: `front_matter`: capa de identificação, sumário com linhas de altura fixa (a atividade ocupa duas linhas) e separadores de grupo, todos com o próprio número no pé.
**Where**: `backend/app/infrastructure/documents/front_matter.py`
**Depends on**: T18 (fase 4), T45 (fase 10)
**Reuses**: `ComprovantePlan`, `pdf_styles`
**Requirement**: CMP-01, CMP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O sumário tem exatamente as páginas previstas pelo plano com 1, `capacidade` e `capacidade + 1` linhas
- [ ] Cada entrada traz o número da primeira página; capa, sumário e separadores imprimem o próprio número no rodapé (menos a capa)
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): draw the comprovante cover, index and separators`

---

#### T51: Anexar página original sem alterar o conteúdo

**What**: `source_pages.attach` caminho comum: página sem rotação nem anotação entra por `show_pdf_page` na área `(0, 0, w, h)` de uma folha de altura `h + 24 pt`, com a faixa `Comprovante p. N` abaixo e a divisória dentro da faixa.
**Where**: `backend/app/infrastructure/documents/source_pages.py`
**Depends on**: T50
**Reuses**: protótipo do design (faixa em `y = h`, divisória em `h + 0,5`)
**Requirement**: CMP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Renderizada a 2x, a área do original da página de saída é idêntica pixel a pixel à página de origem; o texto extraído é igual e a faixa traz o número
- [ ] Os bytes das imagens embutidas na saída são idênticos aos da origem (sem recompressão)
- [ ] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): attach original pages without changing them`

---

#### T52: Rotação, anotações e campos

**What**: `source_pages.attach`: página com `/Rotate`, anotações ou campos passa por um PDF temporário de uma página (`insert_pdf(annots=True, widgets=True)`, `bake`, `remove_rotation`).
**Where**: `backend/app/infrastructure/documents/source_pages.py`
**Depends on**: T51
**Reuses**: protótipo do design (`remove_rotation` e `bake`)
**Requirement**: CMP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Rotação de 90, 180 e 270 graus: área do original idêntica pixel a pixel à página de origem renderizada
- [ ] Carimbo, texto livre, destaque, campo preenchido e aparência de assinatura continuam visíveis (diferença máxima de 1 nível de cinza na região)
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): keep rotation and annotations of original pages`

---

#### T53: Imagens, PNG grande e página rasterizada

**What**: `source_pages`: JPEG e PNG viram página do tamanho da imagem (150 dpi quando ausente, no máximo 14 400 pt de lado) sem decodificar o JPEG; PNG acima de 12 megapixels é recusado; página rotacionada com recorte menor que a página é rasterizada a 200 dpi (JPEG 92) com o alerta `PAGINA_RASTERIZADA`.
**Where**: `backend/app/infrastructure/documents/source_pages.py`
**Depends on**: T52
**Reuses**: `FileInspector` (dimensões), `GenerationAlertCode`
**Requirement**: CMP-08, CMP-12, CMP-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] JPEG de 40 megapixels entra e o pico de memória sobe menos de 40 MB; PNG de 12 megapixels entra e o de 12 megapixels mais um pixel levanta `IMAGEM_GRANDE_DEMAIS` antes de decodificar
- [ ] Página rotacionada com CropBox menor sai rasterizada com o conteúdo visível preservado e o alerta traz documento e página
- [ ] Página PDF de 52 megapixels (JPEG de 5 MB) é anexada sem rasterizar e sem falhar
- [ ] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): handle images and rasterized pages`

---

#### T54: Montagem incremental do Comprovante

**What**: `ComprovanteAssembler.assemble(plan, resolver, target, on_progress) -> AssemblyResult`: abre uma origem por vez, `store_shrink(100)` a cada página, salvamento incremental a cada 25 páginas, `garbage=3, deflate=True` no fim e conferência dos 60 MB.
**Where**: `backend/app/infrastructure/documents/comprovante_assembler.py`
**Depends on**: T53
**Reuses**: `front_matter`, `source_pages`
**Requirement**: CMP-01, CMP-02, CMP-03, CMP-09, CMP-10, CMP-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Processo sintético de 3 grupos e 5 atividades (uma sem página, duas na mesma página): ordem, sumário, numeração contínua, remissão e alerta conferem e as páginas anexadas são idênticas às originais
- [ ] Saída acima de 60 MB falha com `COMPROVANTE_GRANDE_DEMAIS` sem deixar arquivo parcial; original ausente falha com `ORIGINAL_INDISPONIVEL` citando documento e página
- [ ] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(documents): assemble the comprovante pdf incrementally`

---

#### T55: Teste de pico de memória

**What**: Teste que gera 400 páginas "digitalizadas" sintéticas (JPEG 1240x1754 em 10 PDFs), monta o Comprovante num subprocesso e mede `ru_maxrss`.
**Where**: `backend/tests/integration/documents/test_comprovante_memory.py`
**Depends on**: T54
**Reuses**: `synthetic_docs.py`
**Requirement**: CMP-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O pico do subprocesso fica abaixo de 320 MB com 400 páginas de 224 KB, a saída tem 411 páginas e a numeração das 411 confere
- [ ] O teste tem marca própria (`memory`) para rodar à parte, mas roda no gate full
- [ ] Gate full passa; 2+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): assert the comprovante memory ceiling`

---

### Phase 12: Executor e adaptador de redação

#### T56: Executor com vários runners

**What**: `DocumentWorker` recebe `runners: Sequence[Callable[[], bool]]`; `run_once` tenta geração, redação e OCR nessa ordem; `start()` chama os recuperadores; exceção do runner fecha a linha como `FALHOU/ERRO_INTERNO` e o log leva só o tipo.
**Where**: `backend/app/infrastructure/jobs/worker.py`
**Depends on**: T39 (fase 8)
**Reuses**: `DocumentWorker.run_once` (`worker.py:43`) e os testes existentes do executor
**Requirement**: VER-04, VER-08, REL-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes existentes do executor passam sem alteração com o OCR como único runner
- [ ] Com uma geração e um documento pendentes, a geração roda primeiro; runner que levanta exceção não derruba a thread e o log não traz texto de documento
- [ ] Gate full passa; 6+ testes novos

**Tests**: integration
**Gate**: full

**Commit**: `refactor(worker): run several kinds of jobs in the worker`

---

#### T57: Adaptador MariTalk da redação

**What**: `MariTalkReportWriter.draft(section_title, items) -> Mapping[UUID, str]`: `temperature` 0, `response_format` JSON estrito `{items: [{id, texto}]}`, `max_tokens` 4000, prazo de 60 s, sem repetição além do modelo reserva; erro ou prazo levanta `AiWritingError('REDACAO_INDISPONIVEL')`.
**Where**: `backend/app/infrastructure/ai/report_writer.py`
**Depends on**: T56, T5 (fase 1)
**Reuses**: `MariTalkClient`
**Requirement**: REL-03, REL-05, REL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Com transporte simulado: resposta válida devolve os textos por `id`; erro HTTP, JSON fora do schema e prazo de 60 s levantam `REDACAO_INDISPONIVEL`
- [ ] O corpo enviado só contém os campos do item (nenhum texto de página nem nome do docente) e o prompt proíbe objetivos, resultados e metodologias
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ai): add the MariTalk report writer`

---

### Phase 13: Aplicação: geração dos documentos

#### T58: Leitura das entradas da geração

**What**: `load_generation_inputs(uow, process) -> GenerationInputs`: processo, docente, unidade, `ProcessScore`, atividades `VALIDADA` com grupo e item, vínculos por atividade, documentos (nome, mime, páginas, nome interno, `file_deleted_at`) e a contagem do que fica de fora por motivo, numa unidade de trabalho de leitura.
**Where**: `backend/app/application/services/generation_inputs.py`
**Depends on**: T2 (fase 1), T38 (fase 8), T39 (fase 8)
**Reuses**: `compute_process_score`, `list_for_activities`
**Requirement**: TAB-01, TAB-02, UIG-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Atividades `AGUARDANDO_REVISAO` e `REJEITADA` ficam fora e são contadas por motivo; a pontuação vem de `compute_process_score`
- [ ] A leitura não deixa transação aberta depois de devolver o resultado
- [ ] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): load the inputs of a generation`

---

#### T59: Pedido de geração

**What**: `RequestGeneration.execute(actor, process_id, kind)`: acesso (404), tabela escolhida, atividades validadas, linha `GERANDO` com índice parcial único (409 `GERACAO_EM_ANDAMENTO`) e auditoria; retorna 202.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T58, T34 (fase 8), T56 (fase 12)
**Reuses**: `_ScoringUseCase._readable`, `AuditService`
**Requirement**: TAB-01, TAB-07, TAB-08, VER-04, VER-06, VER-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Processo sem atividade `VALIDADA` recusa com `SEM_ATIVIDADES_VALIDADAS` e sem tabela escolhida com `TABELA_NAO_ESCOLHIDA`, sem criar linha
- [ ] Segundo pedido igual com linha `GERANDO` responde 409 `GERACAO_EM_ANDAMENTO`; tipos diferentes coexistem; processo de outro docente responde 404
- [ ] Evento de auditoria `CREATE` com `kind` e `state` e nenhum texto de documento
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): request the generation of a document`

---

#### T60: Recusas específicas do pedido

**What**: `RequestGeneration`: `ATIVIDADE_SEM_DESCRICAO` (Relatório, citando a atividade), plano do Comprovante (`COMPROVANTE_GRANDE_DEMAIS`, `ORIGINAL_INDISPONIVEL`, `IMAGEM_GRANDE_DEMAIS`, `ORIGINAIS_EXCLUIDOS`) e `ESPACO_INSUFICIENTE`.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T59, T18 (fase 4), T40 (fase 9), T41 (fase 9)
**Reuses**: `plan_comprovante`, `GeneratedFileStorage`
**Requirement**: REL-10, CMP-09, CMP-10, CMP-13, DEL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Atividade validada sem descrição e sem título recusa o Relatório com `ATIVIDADE_SEM_DESCRICAO` e o `id` da atividade
- [ ] Comprovante com 401 páginas, original ausente, PNG acima de 12 megapixels ou documento `ARQUIVO_EXCLUIDO` recusa com o código certo e sem criar linha; a Tabela de processo concluído é aceita
- [ ] Menos de `generation_min_free_mb` livres recusa com `ESPACO_INSUFICIENTE`
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): refuse generation requests that cannot succeed`

---

#### T61: Execução da geração: Tabela

**What**: `RunGeneration.execute(generation_id)` para `TABELA`: monta o modelo com o plano atual, escreve DOCX e PDF em arquivo temporário, calcula o SHA-256, renomeia e, numa transação, grava versão, arquivos, instantâneo, alertas e `PRONTO`, com auditoria.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T60, T46 (fase 10), T47 (fase 10), T40 (fase 9), T14 (fase 3), T13 (fase 3)
**Reuses**: `build_table_document`, `table_docx.py`, `table_pdf.py`, `LocalGeneratedStorage`
**Requirement**: TAB-01, VER-01, VER-02, VER-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A geração termina em `PRONTO` com versão 1, dois arquivos com hash e tamanho e instantâneo com o total 211; a segunda dá a versão 2
- [ ] Os dois formatos refletem o mesmo resultado; o evento `STATUS` traz hash e tamanho por formato e nenhum texto
- [ ] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): run the scoring table generation`

---

#### T62: Execução da geração: Relatório

**What**: `RunGeneration` para `RELATORIO`: usa o texto guardado no rascunho (reconciliado), escreve DOCX e PDF e grava a versão com `report` no instantâneo.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T61, T48 (fase 10), T49 (fase 10), T23 (fase 5), T36 (fase 8)
**Reuses**: `report_docx.py`, `report_pdf.py`, `reconcile_draft`
**Requirement**: REL-09, REL-10, REL-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O documento usa o texto editado pelo usuário, sem sobrescrevê-lo, e o instantâneo guarda seções, atividades e fonte de cada texto
- [ ] Sem rascunho salvo gera a partir da proposta com texto-modelo
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): run the activities report generation`

---

#### T63: Execução da geração: Comprovante

**What**: `RunGeneration` para `COMPROVANTE`: abre os originais por `resolver`, monta o PDF com o plano, atualiza `on_progress` e grava a versão com `plan_hash` e o alerta `NUMERACAO_DIVERGENTE` quando a Tabela mais recente tem outro `plan_hash`.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T62, T54 (fase 11), T18 (fase 4)
**Reuses**: `ComprovanteAssembler`, `plan_comprovante`
**Requirement**: CMP-01, CMP-02, CMP-05, CMP-07, VER-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Processo sintético: PDF final com a numeração do plano, `plan_hash` no instantâneo e alerta `ATIVIDADE_SEM_COMPROVANTE`
- [ ] Tabela e Comprovante gerados com o mesmo arranjo têm o mesmo `plan_hash`; depois de mudar o arranjo, o `NUMERACAO_DIVERGENTE` aparece
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): run the comprovante generation`

---

#### T64: Falha da geração sem arquivo parcial

**What**: `RunGeneration`: falha em qualquer ponto apaga temporários e arquivos já renomeados e fecha a linha como `FALHOU` com código e mensagem fixa por código; exceção inesperada vira `ERRO_INTERNO`.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T63
**Reuses**: `GeneratedFileStorage.cleanup`
**Requirement**: VER-05, CMP-09, CMP-10, VER-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Original apagado depois do pedido: `FALHOU/ORIGINAL_INDISPONIVEL` com mensagem sem nome de pessoa e nenhum arquivo em `storage/generated`
- [ ] Exceção simulada no segundo formato apaga o primeiro; o número de versão não é gasto e um novo pedido é aceito
- [ ] Evento de auditoria `STATUS` com `error_code` e sem conteúdo; log sem texto de documento
- [ ] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): fail a generation without leaving partial files`

---

#### T65: Recuperação na partida

**What**: `RecoverInterruptedGenerations.execute()`: linhas `GERANDO` com `started_at` em `generated_documents` e `report_wording_jobs` viram `FALHOU/INTERROMPIDA` com auditoria; temporários `.tmp-*` e arquivos sem linha são removidos.
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T64
**Reuses**: `RecoverStuckJobs`
**Requirement**: VER-08, REL-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Geração e redação iniciadas e interrompidas ficam `FALHOU/INTERROMPIDA`; a linha ainda não iniciada continua na fila e nenhuma é reenfileirada
- [ ] Temporários e arquivo sem linha somem do armazenamento; texto do rascunho não é alterado
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): recover generations interrupted by a restart`

---

#### T66: Listagem, detalhe e download das versões

**What**: `ListGeneratedDocuments`, `GetGeneratedDocument` e `DownloadGeneratedFile` (audita `DOWNLOAD`, entrega o arquivo gravado e o `ETag` com o SHA-256).
**Where**: `backend/app/application/use_cases/generated_documents.py`
**Depends on**: T65
**Reuses**: `DownloadDocument` (`documents.py:379`)
**Requirement**: VER-03, VER-06, VER-09, DEL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A lista vem em ordem decrescente, em andamento primeiro, com estado, versão, alertas, arquivos e `size_bytes` de cada um
- [ ] Baixar a versão 1 depois de mudar uma atividade devolve o arquivo original byte a byte, sem regerar; linha que não é `PRONTO` ou arquivo ausente responde 404; outro docente, 404
- [ ] Em processo CONCLUIDO as versões continuam listadas e baixáveis
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): list and download generated document versions`

---

### Phase 14: Aplicação: rascunho, arranjo e redação

#### T67: Leitura do rascunho

**What**: `GetReportDraft`: devolve a proposta (`saved: false`, `version: 0`) sem gravar, ou o rascunho salvo reconciliado, com as seções vazias listadas e o aviso `RASCUNHO_DESATUALIZADO`.
**Where**: `backend/app/application/use_cases/report_draft.py`
**Depends on**: T36 (fase 8), T21 (fase 5), T23 (fase 5), T58 (fase 13)
**Reuses**: `propose_draft`, `reconcile_draft`, `ReportDraftRepository`
**Requirement**: REL-01, REL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET` não grava: duas leituras seguidas continuam sem linha em `report_drafts`; as atividades validadas chegam distribuídas pelo mapa de grupo para seção
- [ ] Seção sem atividade vem listada como vazia; atividade nova depois da última edição gera `RASCUNHO_DESATUALIZADO`; fora do acesso, 404
- [ ] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): read the report draft`

---

#### T68: Gravação do texto do rascunho

**What**: `SaveReportEntry` e `SaveReportSection` com `expected_version`, limite de 20 000 caracteres e fonte `USUARIO`.
**Where**: `backend/app/application/use_cases/report_draft.py`
**Depends on**: T67
**Reuses**: `GetReportDraft`, `ReportDraftRepository`
**Requirement**: REL-07, REL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A primeira gravação usa `expected_version: 0` e cria o rascunho; `expected_version` desatualizada responde 409 `VERSAO_DESATUALIZADA`; mais de 20 000 caracteres responde 422
- [ ] O texto salvo vira fonte `USUARIO` e permanece depois de uma nova leitura; processo CONCLUIDO ou ARQUIVADO responde 409 `PROCESSO_SOMENTE_LEITURA`
- [ ] Gate full passa; 7+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): edit the report draft text`

---

#### T69: Mover atividade de seção

**What**: `MoveReportEntry` com `expected_version`.
**Where**: `backend/app/application/use_cases/report_draft.py`
**Depends on**: T68
**Reuses**: `SaveReportEntry`
**Requirement**: REL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Mover guarda a seção no rascunho e a geração a usa; seção inexistente responde 422; versão desatualizada, 409
- [ ] Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): move an activity between report sections`

---

#### T70: Pedido de redação em segundo plano

**What**: `RequestSectionWording` (grava o rascunho se só existe proposta, cria a tarefa `GERANDO` e responde 202; 409 `REDACAO_EM_ANDAMENTO`) e `ListWordingJobs`.
**Where**: `backend/app/application/use_cases/report_draft.py`
**Depends on**: T69, T35 (fase 8)
**Reuses**: `WordingJobRepository`
**Requirement**: REL-03, REL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O pedido responde na hora sem chamar a MariTalk, com a tarefa `GERANDO`; segundo pedido da mesma seção com `GERANDO` responde 409 `REDACAO_EM_ANDAMENTO` e outra seção é aceita
- [ ] Processo somente leitura responde 409 `PROCESSO_SOMENTE_LEITURA`; `ListWordingJobs` devolve a tarefa mais recente por seção
- [ ] Gate full passa; 7+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): request report wording in the background`

---

#### T71: Execução da redação

**What**: `RunWording.execute(job_id)`: lê os campos, chama `ReportWriter` com o prazo, confere com `check_wording`, aplica às entradas sem fonte `USUARIO` sem incrementar `version` e termina em `PRONTO` com avisos; exceção inesperada vira `FALHOU/ERRO_INTERNO`.
**Where**: `backend/app/application/use_cases/report_draft.py`
**Depends on**: T70, T57 (fase 12), T27 (fase 5), T26 (fase 5), T35 (fase 8)
**Reuses**: `apply_wording`, `build_wording_items`, `MariTalkReportWriter`
**Requirement**: REL-03, REL-04, REL-05, REL-06, REL-07, REL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Com a MariTalk simulada devolvendo um número inventado e outra resposta fiel: a primeira vira texto-modelo com `REDACAO_REJEITADA`, a segunda vira fonte `IA`; a tarefa termina em `PRONTO`
- [ ] Indisponível, erro ou 60 s: texto-modelo, `REDACAO_INDISPONIVEL` e `PRONTO`; edição do usuário feita durante a tarefa permanece e a `version` do rascunho não muda
- [ ] Exceção inesperada: `FALHOU/ERRO_INTERNO` e o rascunho fica como estava; auditoria `WORDING` sem texto
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): run report wording with the deterministic check`

---

#### T72: Leitura do arranjo

**What**: `GetComprovanteLayout`: arranjo salvo ou derivado (`saved`, `version`, T19, `invalid`) com o plano e a numeração prevista.
**Where**: `backend/app/application/use_cases/comprovante_layout.py`
**Depends on**: T71, T15 (fase 4), T16 (fase 4), T19 (fase 4), T37 (fase 8)
**Reuses**: `derive_layout`, `plan_comprovante`, `layout_staleness`
**Requirement**: ARR-01, ARR-08, CMP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem arranjo salvo devolve `saved: false` e `version: 0` montado dos vínculos; com arranjo e uma atividade revalidada depois, `stale: true` e o aviso `ARRANJO_DESATUALIZADO`
- [ ] `GET` não grava; documento excluído depois aparece como entrada inválida
- [ ] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): read the comprovante layout`

---

#### T73: Gravação do arranjo

**What**: `SaveComprovanteLayout` com `expected_version`: valida com `validate_layout`, guarda `base_evidence_keys` e audita as contagens.
**Where**: `backend/app/application/use_cases/comprovante_layout.py`
**Depends on**: T72, T20 (fase 4), T37 (fase 8)
**Reuses**: `validate_layout`, `LayoutRepository`
**Requirement**: ARR-02, ARR-03, ARR-04, ARR-05, ARR-06, ARR-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Acrescentar, remover e reordenar páginas e atividades dentro do item é guardado e a geração usa a nova ordem; o vínculo atividade-página permanece
- [ ] Documento ou página fora do processo responde 404; mover atividade de item é recusado; versão desatualizada responde 409 sem sobrescrever o arranjo mais novo
- [ ] Processo somente leitura responde 409 `PROCESSO_SOMENTE_LEITURA`; auditoria só com contagens
- [ ] Gate full passa; 9+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): save the comprovante layout`

---

### Phase 15: Aplicação: conclusão e arquivos excluídos

#### T74: Auxiliar de teste para concluir o processo

**What**: Criar `conclude_for_test(uow_factory, process_id)` que leva o processo a CONCLUIDO pela unidade de trabalho e trocar nos testes existentes a chamada à rota genérica de status para CONCLUIDO.
**Where**: `backend/tests/support/process_status.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `test_process_updates_api.py:98-132` e `test_scoring_process_api.py:179`
**Requirement**: DEL-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes que levavam o processo a CONCLUIDO pela rota genérica usam o auxiliar e passam sem mudar o que verificam
- [ ] Gate full passa; contagem de testes igual à anterior

**Tests**: integration
**Gate**: full

**Commit**: `test(process): conclude processes through a helper in tests`

---

#### T75: Recusar CONCLUIDO na rota genérica

**What**: `ChangeProcessStatus` levanta `Conflict(code='CONCLUSAO_EXIGE_EXCLUSAO')` para o alvo CONCLUIDO e a verificação de transição vira função do módulo, compartilhada com a conclusão.
**Where**: `backend/app/application/use_cases/processes.py`
**Depends on**: T74
**Reuses**: `ChangeProcessStatus` (`processes.py:182`), `can_transition`
**Requirement**: DEL-14, DEL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `POST /status` com `CONCLUIDO` responde 409 com o código `CONCLUSAO_EXIGE_EXCLUSAO` e o processo não muda; RASCUNHO para EM_ANDAMENTO e ARQUIVADO seguem como antes
- [ ] Teste novo da função compartilhada: transição, dono e `expected_version`
- [ ] Gate full passa; 5+ testes novos

**Tests**: integration
**Gate**: full

**Commit**: `feat(process): refuse the generic transition to concluded`

---

#### T76: Exclusão dos documentos de entrada

**What**: `PurgeInputDocuments`: por documento, `storage.delete` (ausente conta como removido) e, na unidade de trabalho própria, `delete_pages`, `clear_excerpts_for_document` e `mark_file_deleted`; devolve removidos, pendentes e bytes.
**Where**: `backend/app/application/services/purge_inputs.py`
**Depends on**: T75, T38 (fase 8), T29 (fase 6)
**Reuses**: `FileStorage.delete`, métodos de T38
**Requirement**: DEL-05, DEL-06, DEL-08, DEL-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Três documentos: os três arquivos somem do armazenamento, as páginas e os trechos somem, os metadados e os vínculos (números) ficam e `file_deleted_at` é preenchido
- [ ] Um arquivo cuja remoção falha fica pendente sem marca, os outros seguem; repetir remove o que falta e arquivo já ausente conta como removido
- [ ] Queda simulada entre a remoção do arquivo e o commit: a nova tentativa fecha o documento
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): purge the input documents of a process`

---

#### T77: Prévia da conclusão

**What**: `GetConclusionPreview.execute(actor, process_id)`: arquivos e bytes a liberar e se há versão `PRONTO` de cada tipo.
**Where**: `backend/app/application/use_cases/conclusion.py`
**Depends on**: T76
**Reuses**: `summarize_purge`, `latest_ready_by_kind`
**Requirement**: DEL-03, DEL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A prévia do cenário com 3 documentos informa 3 arquivos e a soma dos tamanhos e marca cada tipo; fora do acesso responde 404
- [ ] Depois da conclusão informa zero arquivos e zero bytes
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): preview the process conclusion`

---

#### T78: Conclusão do processo

**What**: `ConcludeProcess.execute(actor, process_id, expected_version, confirm, justification)`: verificação, exclusão, auditoria `PURGE`, nova checagem na transação e mudança para CONCLUIDO com auditoria `STATUS`.
**Where**: `backend/app/application/use_cases/conclusion.py`
**Depends on**: T77, T28 (fase 6), T29 (fase 6), T34 (fase 8)
**Reuses**: `check_conclusion`, `PurgeInputDocuments`, `can_transition`, `AuditService`
**Requirement**: DEL-01, DEL-02, DEL-04, DEL-05, DEL-07, DEL-08, DEL-09, DEL-10, DEL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem confirmação responde 422 `CONFIRMACAO_OBRIGATORIA`; sem os três `PRONTO`, 422 `ARTEFATOS_PENDENTES` com os tipos; com geração, redação ou OCR em curso, 409 `OPERACAO_EM_ANDAMENTO`; em todos nenhum arquivo é excluído
- [ ] Com tudo pronto: arquivos excluídos, processo CONCLUIDO, `generated/` intacto e eventos `PURGE` e `STATUS` com contagens e sem nomes
- [ ] Remoção que falha deixa o processo EM_ANDAMENTO com `EXCLUSAO_PARCIAL`, os já excluídos continuam, a repetição conclui; repetir num processo CONCLUIDO responde 200 sem alterar; documento enviado durante a conclusão impede a transição com `EXCLUSAO_PARCIAL`
- [ ] Papel, acesso e versão como `ChangeProcessStatus`: fora do acesso 404, versão desatualizada 409, processo que não está EM_ANDAMENTO 409
- [ ] Gate full passa; 14+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(app): conclude a process and purge its input documents`

---

#### T79: Documento excluído nos casos de uso de documentos

**What**: `DownloadDocument`, leitura de detalhe e de texto de página, `ReprocessDocument` e `ReplaceDocument` levantam `Gone('ARQUIVO_EXCLUIDO')` quando `file_deleted_at` está preenchido; o detalhe traz `arquivo_excluido` e não traz o texto.
**Where**: `backend/app/application/use_cases/documents.py`
**Depends on**: T78
**Reuses**: `DownloadDocument` (`documents.py:379`)
**Requirement**: DEL-12, DEL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Arquivo e página de documento excluído respondem `Gone` com o código; reprocessar e substituir também; documento comum segue como antes
- [ ] O detalhe de documento excluído mostra nome, tipo e páginas (metadados) e `arquivo_excluido: true`
- [ ] Gate full passa; 7+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): answer gone for deleted input files`

---

#### T80: Documento excluído na leitura de evidências

**What**: `evidences.py:69` e a leitura de trechos deixam de procurar texto de página quando o documento está excluído e levantam `Gone`; vínculos existentes seguem listados só com números.
**Where**: `backend/app/application/use_cases/evidences.py`
**Depends on**: T79
**Reuses**: `evidences.py:45-69`
**Requirement**: DEL-12, DEL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Listar os vínculos de uma atividade cujo documento foi excluído devolve documento e página sem trecho; ler o texto da página responde `Gone`
- [ ] Criar vínculo novo com página de documento excluído é recusado
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(evidences): handle links to deleted input documents`

---

### Phase 16: API

#### T81: Container e executor com os casos de uso novos

**What**: Construir os casos de uso novos no container, passar os runners de geração e de redação ao `DocumentWorker` no `lifespan`, chamar `RecoverInterruptedGenerations` na partida e registrar os routers novos.
**Where**: `backend/app/presentation/dependencies.py`
**Depends on**: T65 (fase 13), T71 (fase 14), T78 (fase 15), T56 (fase 12)
**Reuses**: `build_container` e o `lifespan` de `main.py`
**Requirement**: VER-04, VER-08, REL-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A aplicação sobe com `worker_enabled` e com o executor desligado; o container expõe cada caso de uso novo
- [ ] Linha `GERANDO` com `started_at` antes da partida vira `FALHOU/INTERROMPIDA` ao subir
- [ ] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): wire the document generation use cases`

---

#### T82: Esquemas da geração

**What**: `schemas/generated.py`: pedido, linha de geração (estado, versão, alertas, arquivos com tamanho), job de redação, rascunho, arranjo e plano, prévia e resultado da conclusão.
**Where**: `backend/app/presentation/schemas/generated.py`
**Depends on**: T81
**Reuses**: `schemas/documents.py`
**Requirement**: VER-03, VER-09, UIG-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os esquemas serializam os objetos de domínio sem dados pessoais nem caminho de arquivo e rejeitam campos extras no corpo
- [ ] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(api): add the generated documents schemas`

---

#### T83: Rotas de geração e download

**What**: `POST` e `GET` de `/processes/{id}/generated-documents`, `GET /generated-documents/{gid}` e o download por formato com `attachment`, `nosniff` e `ETag`.
**Where**: `backend/app/presentation/api/generated_documents.py`
**Depends on**: T82, T66 (fase 13), T63 (fase 13), T62 (fase 13), T64 (fase 13)
**Reuses**: `documents.py` (rotas de arquivo)
**Requirement**: TAB-01, TAB-07, TAB-08, VER-03, VER-04, VER-06, DEL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Pedido responde 202; `SEM_ATIVIDADES_VALIDADAS` e `TABELA_NAO_ESCOLHIDA` respondem 422 com `field`, `code` e `message`; segundo pedido, 409 `GERACAO_EM_ANDAMENTO`
- [ ] Download devolve o arquivo com o tipo de conteúdo do formato, nome legível sem o docente e `ETag` com o SHA-256; fora do acesso, 404
- [ ] Em processo CONCLUIDO o download funciona e o pedido do Comprovante responde 422 `ORIGINAIS_EXCLUIDOS`
- [ ] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the generation and download routes`

---

#### T84: Rotas do rascunho e da redação

**What**: `GET` e `PUT` do rascunho (entrada e seção), `POST .../move`, `POST .../sections/{key}/wording` (202) e `GET .../report-draft/wording`.
**Where**: `backend/app/presentation/api/report_draft.py`
**Depends on**: T83, T67 (fase 14), T68 (fase 14), T69 (fase 14), T70 (fase 14)
**Reuses**: `activities.py` (padrões de rota)
**Requirement**: REL-03, REL-07, REL-08, REL-13, UIG-02, UIG-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O pedido de redação responde 202 sem esperar a MariTalk; segundo pedido da seção, 409 `REDACAO_EM_ANDAMENTO`; a consulta devolve o estado de cada seção
- [ ] `PUT` com versão desatualizada responde 409 e com mais de 20 000 caracteres, 422; fora do acesso, 404
- [ ] Gate full passa; 9+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the report draft and wording routes`

---

#### T85: Rotas do arranjo

**What**: `GET` e `PUT /processes/{id}/comprovante-layout`.
**Where**: `backend/app/presentation/api/comprovante_layout.py`
**Depends on**: T84, T72 (fase 14), T73 (fase 14)
**Reuses**: T84
**Requirement**: ARR-01, ARR-02, ARR-06, ARR-07, UIG-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET` devolve `saved`, `version`, T19, `invalid` e `plan` com a numeração prevista; `PUT` desatualizado responde 409 `VERSAO_DESATUALIZADA`; documento de outro processo, 404
- [ ] Gate full passa; 7+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the comprovante layout routes`

---

#### T86: Rota da ordem do dossiê

**What**: `GET /dossier-order` lê `dossier_order.json` por `config_loader`.
**Where**: `backend/app/presentation/api/dossier.py`
**Depends on**: T85, T44 (fase 9)
**Reuses**: `config_loader`
**Requirement**: ORD-01, ORD-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A resposta traz a lista na ordem do arquivo com a marca `generated_by`; exige sessão autenticada
- [ ] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the dossier order route`

---

#### T87: Rotas da conclusão

**What**: `GET` e `POST /processes/{id}/conclusion`.
**Where**: `backend/app/presentation/api/conclusion.py`
**Depends on**: T86, T77 (fase 15)
**Reuses**: `processes.py` (rota de status)
**Requirement**: DEL-01, DEL-02, DEL-03, DEL-04, DEL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET` devolve arquivos, bytes e o estado de cada tipo; `POST` sem `confirmar` responde 422 `CONFIRMACAO_OBRIGATORIA`; `ARTEFATOS_PENDENTES` responde 422; `OPERACAO_EM_ANDAMENTO` e versão desatualizada respondem 409; fora do acesso, 404
- [ ] `POST` com tudo pronto responde 200 com `status`, `arquivos_removidos`, `arquivos_pendentes` e `bytes_liberados`
- [ ] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the conclusion routes`

---

#### T88: Documento excluído nas rotas de documentos

**What**: `DocumentOut` ganha `arquivo_excluido` e as rotas de arquivo e de página respondem 410 com o código `ARQUIVO_EXCLUIDO`.
**Where**: `backend/app/presentation/schemas/documents.py`
**Depends on**: T87
**Reuses**: `DocumentOut`, `get_file`
**Requirement**: DEL-12, DEL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Listagem e detalhe trazem `arquivo_excluido`; `GET /documents/{id}/file` e a página de documento excluído respondem 410 com `field`, `code` e `message`
- [ ] Documento comum responde como antes; gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): expose and answer deleted input documents`

---

### Phase 17: Aceitação do backend

#### T89: Aceitação: Tabela de 211 pontos

**What**: Teste ponta a ponta: com o cenário do `test_scoring_golden.py`, gerar a Tabela pela API e conferir DOCX e PDF baixados.
**Where**: `backend/tests/integration/api/test_generated_table_acceptance.py`
**Depends on**: T83 (fase 16)
**Reuses**: `test_scoring_golden.py`, `docx` e PyMuPDF para ler os arquivos
**Requirement**: TAB-01, TAB-04, TAB-05, TAB-06, TAB-07, TAB-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] DOCX e PDF baixados trazem o total 211, os subtotais 52, 7, 62, 0, 30, 4 e 56 e as horas 24, 24, 24, 20 (92), iguais à resposta de `/scoring`
- [ ] Sem atividade validada responde `SEM_ATIVIDADES_VALIDADAS`; sem tabela, `TABELA_NAO_ESCOLHIDA`
- [ ] Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): accept the scoring table of the 211 point case`

---

#### T90: Aceitação: Comprovante sintético

**What**: Teste ponta a ponta: processo com 3 grupos e 5 atividades (uma sem página, duas na mesma página), arranjo reordenado e uma página removida; gerar e conferir.
**Where**: `backend/tests/integration/api/test_generated_comprovante_acceptance.py`
**Depends on**: T89, T85 (fase 16)
**Reuses**: `synthetic_docs.py`, T85
**Requirement**: CMP-01, CMP-03, CMP-04, CMP-05, CMP-07, ARR-03, ARR-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Ordem, sumário, numeração contínua, remissão e `ATIVIDADE_SEM_COMPROVANTE` conferem no PDF; cada página anexada é idêntica ao original
- [ ] A página removida do arranjo está ausente e o vínculo ainda existe na Etapa 3; a nova ordem é a do PDF
- [ ] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): accept the synthetic comprovante`

---

#### T91: Aceitação: versões imutáveis

**What**: Teste ponta a ponta: gerar a Tabela duas vezes, mudar uma atividade e baixar a versão 1.
**Where**: `backend/tests/integration/api/test_generated_versions_acceptance.py`
**Depends on**: T90, T83 (fase 16)
**Reuses**: T83
**Requirement**: VER-01, VER-02, VER-03, VER-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Versões 1 e 2 com hashes e instantâneos diferentes; a versão 1 baixada depois da mudança é igual byte a byte ao arquivo gravado
- [ ] Tentativa direta de `UPDATE` ou `DELETE` de versão no banco é recusada; o histórico traz o tamanho de cada versão
- [ ] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): accept immutable generated versions`

---

#### T92: Aceitação: Relatório com redação

**What**: Teste ponta a ponta com a MariTalk simulada: pedir a redação de uma seção, consultar até `PRONTO`, editar, pedir de novo e gerar o Relatório.
**Where**: `backend/tests/integration/api/test_generated_report_acceptance.py`
**Depends on**: T91, T84 (fase 16)
**Reuses**: T71, T84
**Requirement**: REL-03, REL-04, REL-05, REL-07, REL-09, REL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Resposta com número inventado vira texto-modelo com `REDACAO_REJEITADA` e a fiel é aceita; indisponível termina `PRONTO` com `REDACAO_INDISPONIVEL`
- [ ] O texto editado permanece depois de uma nova redação e é o que vai ao DOCX e ao PDF gerados
- [ ] Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): accept the report wording flow`

---

#### T93: Aceitação: conclusão e exclusão

**What**: Teste ponta a ponta: processo sintético EM_ANDAMENTO com 3 documentos e as três versões `PRONTO`; concluir, repetir com um arquivo travado e conferir o que fica.
**Where**: `backend/tests/integration/api/test_conclusion_acceptance.py`
**Depends on**: T92, T87 (fase 16), T88 (fase 16)
**Reuses**: T87, T83
**Requirement**: DEL-05, DEL-06, DEL-07, DEL-08, DEL-09, DEL-11, DEL-12, DEL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Depois da conclusão `uploads/{process_id}` não tem arquivo, `generated/` está intacto, o espaço informado é igual ao removido, o processo é CONCLUIDO e o Comprovante responde `ORIGINAIS_EXCLUIDOS`
- [ ] Visualizar uma página responde 410 `ARQUIVO_EXCLUIDO`; Tabela e Relatório geram de novo e todas as versões baixam byte a byte
- [ ] Com um arquivo travado: `EXCLUSAO_PARCIAL`, processo EM_ANDAMENTO e a segunda tentativa conclui
- [ ] Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(documents): accept the process conclusion and purge`

---

### Phase 18: Interface: base

#### T94: Mensagem do 422 com código

**What**: `errorMessage` passa a ler a `message` do primeiro item do `detail` que tem `code`, em vez de mostrar sempre `Verifique os campos destacados`.
**Where**: `frontend/src/api/client.ts`
**Depends on**: T83 (fase 16)
**Reuses**: `client.ts:68`
**Requirement**: TAB-07, UIG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 422 com `SEM_ATIVIDADES_VALIDADAS` mostra a mensagem em português; 422 de validação de campo continua mostrando o aviso dos campos destacados
- [ ] Gate quick passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `fix(web): show the message of coded validation errors`

---

#### T95: Hook `usePolling`

**What**: Extrair o consulta-a-cada-3-segundos de `ProcessDocuments.tsx` para `hooks/usePolling.ts` e usá-lo na tela de documentos.
**Where**: `frontend/src/hooks/usePolling.ts`
**Depends on**: T94
**Reuses**: `ProcessDocuments.tsx:13,102` e `ProcessDocuments.test.tsx`
**Requirement**: UIG-04, UIG-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes de `ProcessDocuments` passam sem alteração
- [ ] Teste novo: o hook consulta a cada 3 s com relógio falso, para quando a condição de parada é verdadeira e para ao desmontar
- [ ] Gate quick passa; 4+ testes novos

**Tests**: unit
**Gate**: quick

**Commit**: `refactor(web): extract the polling hook`

---

#### T96: Tipos da API de documentos gerados

**What**: Tipos de geração, versão, arquivo, alerta, rascunho, job de redação, arranjo, plano, prévia e resultado da conclusão.
**Where**: `frontend/src/api/types.ts`
**Depends on**: T95
**Reuses**: tipos existentes de documentos e pontuação
**Requirement**: UIG-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os tipos refletem os esquemas do backend e o `tsc -b` passa
- [ ] Gate build passa

**Tests**: none
**Gate**: build

**Commit**: `feat(web): add the generated documents api types`

---

#### T97: Rótulos em português

**What**: `GENERATION_STATE_LABELS`, `GENERATION_CODE_LABELS` e os textos dos alertas e erros novos (inclui `EXCLUSAO_PARCIAL`, `ARTEFATOS_PENDENTES`, `ARQUIVO_EXCLUIDO`).
**Where**: `frontend/src/labels.ts`
**Depends on**: T96
**Reuses**: rótulos existentes (`labels.ts`)
**Requirement**: UIG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Todo código e alerta do design tem rótulo em português; `labels.test` (ou teste novo) falha se um código do tipo ficar sem rótulo
- [ ] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the labels of generated documents`

---

#### T98: Etapa 5 na navegação

**What**: `STEP_TITLES[5]` (`Documentos gerados`), `stepPath(5)` (`processos/:id/gerados`), `enabled` com 5 e a rota da página.
**Where**: `frontend/src/components/StepNav.tsx`
**Depends on**: T97
**Reuses**: `StepNav.test.tsx`
**Requirement**: UIG-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O menu mostra a Etapa 5 com o título certo e a Etapa 4 segue como Pontuação; a rota abre a página da etapa
- [ ] Gate quick passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add step five to the navigation`

---

### Phase 19: Interface: Relatório e Comprovante

#### T99: Editor do rascunho do Relatório

**What**: `ReportDraftEditor`: cartão por seção, textarea por atividade com contador de 20 000, selo da fonte (modelo, IA, editado), avisos, `Mover para` e gravação por entrada com `expected_version`.
**Where**: `frontend/src/components/ReportDraftEditor.tsx`
**Depends on**: T96 (fase 18), T97 (fase 18), T94 (fase 18)
**Reuses**: `ActivityForm.tsx`, `AlertList.tsx`
**Requirement**: UIG-02, REL-07, REL-08, REL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Editar e sair do campo grava a entrada com a versão e o selo passa a `editado`; 409 recarrega e avisa
- [ ] Seção vazia aparece como vazia; mover atividade grava e a leva para a seção escolhida; contador bloqueia acima de 20 000
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the report draft editor`

---

#### T100: Redação por seção com consulta

**What**: `ReportDraftEditor`: botão `Pedir redação` por seção, estado GERANDO com consulta a cada 3 s até PRONTO ou FALHOU, recarga do texto da seção ao terminar e avisos `REDACAO_REJEITADA` e `REDACAO_INDISPONIVEL`.
**Where**: `frontend/src/components/ReportDraftEditor.tsx`
**Depends on**: T99
**Reuses**: `usePolling`
**Requirement**: UIG-08, REL-03, REL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Com a API simulada: pedir mostra GERANDO, a consulta de 3 s mostra PRONTO e o texto da seção é recarregado sem perder o que foi digitado e não salvo nas outras seções
- [ ] O botão fica desligado enquanto a seção gera; 409 `REDACAO_EM_ANDAMENTO` mostra a mensagem; `FALHOU` mostra o aviso e permite pedir de novo
- [ ] Gate quick passa; 7+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): request and follow report wording by section`

---

#### T101: Editor do arranjo: ordem e remoção

**What**: `ComprovanteLayoutEditor`: por grupo, item e atividade, a lista de páginas com subir, descer e remover, a numeração prevista do plano e a gravação com `expected_version`.
**Where**: `frontend/src/components/ComprovanteLayoutEditor.tsx`
**Depends on**: T100
**Reuses**: `ActivityReviewList.tsx` (padrões de lista)
**Requirement**: UIG-03, ARR-03, ARR-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Reordenar duas páginas e remover uma, salvar e ver a ordem nova e a numeração prevista; acessível por teclado, sem arrastar e soltar
- [ ] 409 recarrega e avisa; atividade não muda de item
- [ ] Gate quick passa; 7+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the comprovante layout editor`

---

#### T102: Editor do arranjo: acrescentar, repetir e aviso

**What**: `ComprovanteLayoutEditor`: `Acrescentar página` (documento e número), `repetir com justificativa` e o aviso `ARRANJO_DESATUALIZADO`.
**Where**: `frontend/src/components/ComprovanteLayoutEditor.tsx`
**Depends on**: T101
**Reuses**: T101
**Requirement**: UIG-03, ARR-02, ARR-08, CMP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Acrescentar página de documento do processo grava na posição pedida; página fora do documento mostra o erro; repetir exige justificativa
- [ ] Arranjo desatualizado mostra o aviso e as entradas inválidas marcadas
- [ ] Gate quick passa; 7+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add pages and repeats to the layout editor`

---

### Phase 20: Interface: documentos, conclusão e página

#### T103: Bloco de documento gerado

**What**: `GeneratedBlock` (um por tipo): aviso de atividades fora, botão Gerar, estado, alertas em português, histórico com links por formato e tamanho de cada versão, consulta a cada 3 s enquanto houver `GERANDO`.
**Where**: `frontend/src/components/GeneratedBlock.tsx`
**Depends on**: T100 (fase 19), T102 (fase 19)
**Reuses**: `AlertList.tsx`, `usePolling`
**Requirement**: UIG-01, UIG-04, UIG-05, UIG-06, VER-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Gerar mostra GERANDO, depois PRONTO e os links de download em cada formato com o tamanho; `FALHOU` mostra o código em português e permite tentar de novo
- [ ] Aviso `N atividades ficam de fora` antes do botão; alertas da geração listados
- [ ] Gate quick passa; 9+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the generated document block`

---

#### T104: Ordem do dossiê

**What**: `DossierOrder`: lista da API na ordem do arquivo, com os três documentos gerados marcados.
**Where**: `frontend/src/components/DossierOrder.tsx`
**Depends on**: T103
**Reuses**: T97
**Requirement**: ORD-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A lista aparece na ordem recebida e marca `Tabela`, `Relatório` e `Comprovante` como gerados pelo sistema
- [ ] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the dossier order reminder`

---

#### T105: Diálogo de conclusão

**What**: `ConcludeDialog`: prévia, lista do que falta, texto de ação irreversível com número de arquivos e espaço, confirmação marcada, `EXCLUSAO_PARCIAL` com tentar de novo e recarga do processo ao concluir.
**Where**: `frontend/src/components/ConcludeDialog.tsx`
**Depends on**: T104
**Reuses**: diálogos de justificativa de `ActivityReviewList.tsx`
**Requirement**: UIG-09, DEL-03, DEL-04, DEL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Com um tipo sem versão `PRONTO` o botão fica desligado e o tipo faltante aparece; o texto traz `N arquivos, X MB serão excluídos de forma irreversível`
- [ ] Só envia `confirmar: true` depois de marcar a confirmação; `EXCLUSAO_PARCIAL` mostra quantos faltam e permite repetir; sucesso mostra o processo concluído e some o botão de gerar o Comprovante
- [ ] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the conclusion dialog`

---

#### T106: Documento excluído nas telas de documentos

**What**: `DocumentList` e `DocumentViewer` mostram `Arquivo excluído` e não oferecem visualizar nem baixar quando `arquivo_excluido`; o cliente trata 410 como mensagem de tela.
**Where**: `frontend/src/components/DocumentList.tsx`
**Depends on**: T105
**Reuses**: `DocumentViewer.tsx`, `client.ts`
**Requirement**: DEL-12, DEL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Documento excluído mostra nome, tipo e páginas e o selo `Arquivo excluído`, sem botões de visualizar e baixar; 410 mostra a mensagem em português
- [ ] Gate quick passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): show deleted input documents in the list`

---

#### T107: Página da Etapa 5

**What**: `ProcessGenerated`: três blocos, editor do rascunho dentro do Relatório, arranjo dentro do Comprovante, ordem do dossiê e o botão `Concluir e excluir documentos de entrada`.
**Where**: `frontend/src/pages/ProcessGenerated.tsx`
**Depends on**: T106
**Reuses**: `ProcessScoring.tsx` (estrutura de etapa)
**Requirement**: UIG-01, UIG-02, UIG-03, UIG-09, ORD-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A página mostra os três blocos, abre o editor do Relatório com as seções, abre o arranjo do Comprovante e a lista do dossiê
- [ ] Em processo CONCLUIDO os blocos de Tabela e Relatório geram e todos baixam, o Comprovante some ou fica desligado com `ORIGINAIS_EXCLUIDOS` e rascunho e arranjo ficam somente leitura
- [ ] Gate quick passa; 7+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(web): add the generated documents step page`

---

#### T108: Largura de 360 px

**What**: Estilos da etapa nova (cartões empilhados, tabelas viram listas) e o teste estático de 360 px.
**Where**: `frontend/src/styles.css`
**Depends on**: T107
**Reuses**: `styles.test.ts`
**Requirement**: UIG-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O teste estático confere que nenhuma regra da etapa nova impõe largura mínima acima de 360 px nem rolagem horizontal da página
- [ ] Gate build passa (lint, build e testes com `REQUIRE_DIST=1`)

**Tests**: unit
**Gate**: build

**Commit**: `style(web): make the generated documents step fit 360 px`

---

### Phase 21: Encerramento: implantação, corpus e verificação

#### T109: Notas de implantação

**What**: Registrar em `docs/deploy/vm.md` o que o deploy desta feature exige: pinos de `python-docx==1.2.0`, `lxml==6.1.3` e `reportlab==5.1.0` (queda para `reportlab==4.5.1`), fonte Liberation Serif no repositório, `client_max_body_size 120m` já em vigor, migração `0006` (a 0005 já está no ar), volume `storage/generated` e o aviso de que a conclusão é irreversível e a VM não tem backup.
**Where**: `docs/deploy/vm.md`
**Depends on**: T31 (fase 7)
**Reuses**: `docs/deploy/vm.md` (seções de migração e imagem)
**Requirement**: VER-01, DEL-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O texto lista a migração `0006_generated_documents`, as dependências novas, a fonte, o espaço do volume gerado e o ponto de retorno antes de aplicar
- [ ] Nenhum push, deploy ou acesso à VM é feito por esta tarefa; ela só escreve a nota
- [ ] Gate build passa

**Tests**: none
**Gate**: build

**Commit**: `docs(deploy): add the generated documents deployment notes`

---

#### T110: Contagem local de páginas com rotação e recorte

**What**: Rodar, a pedido explícito do usuário, um script local fora do repositório sobre o corpus real para contar as páginas com rotação e CropBox menor que a MediaBox, e registrar só a contagem no design.
**Where**: `.specs/features/documentos-gerados/design.md`
**Depends on**: T109, T53 (fase 11)
**Reuses**: `corpus-reports/` (fora do git) e a regra do `STATE.md` sobre `Documentos/`
**Requirement**: CMP-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O usuário autorizou a leitura do corpus; o script não é versionado e nenhum nome, texto ou caminho de documento vai ao design
- [ ] O design registra a contagem e a decisão (manter o fallback ou tratá-lo melhor) em Risks
- [ ] Gate build passa

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record the rotated and cropped page count`

---

#### T111: Verificador independente

**What**: Despachar o Verificador com contexto novo: conferência dos resultados contra a spec, sensor de discriminação e relatório `validation.md` com PASS ou FAIL e evidência `arquivo:linha`.
**Where**: `.specs/features/documentos-gerados/validation.md`
**Depends on**: T110, T108 (fase 20)
**Reuses**: `validation.md` das features anteriores
**Requirement**: TAB-01, CMP-01, ARR-01, REL-01, VER-01, UIG-01, DEL-01, ORD-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cada AC da spec tem evidência e o relatório traz o resultado do sensor; falhas viram tarefas de correção (no máximo 3 iterações)
- [ ] `validate_state.py documentos-gerados` termina sem erro; a spec marca os requisitos como `Verified`
- [ ] Gate build passa

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): add the documentos-gerados validation report`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11 → Phase 12 → Phase 13 → Phase 14 → Phase 15 → Phase 16 → Phase 17 → Phase 18 → Phase 19 → Phase 20 → Phase 21
```

Execução estritamente sequencial: um agente (ou o trabalhador de um lote) cumpre uma tarefa por vez, em ordem, e cada tarefa termina em um commit atômico com a marca de concluída neste arquivo e a tabela de rastreabilidade da spec atualizadas no mesmo commit.

---

## Diagram-Definition Cross-Check

Verificado por `validate_tasks.py` (dentro de cada fase, cada seta do diagrama tem o `Depends on` correspondente e vice-versa; dependência de fase anterior não precisa de seta). A tabela abaixo é gerada do mesmo dado.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | - | - (mesma fase) | ✅ Match |
| T2 | T1 | T1 (mesma fase) | ✅ Match |
| T3 | T2 | T2 (mesma fase) | ✅ Match |
| T4 | T3 | T3 (mesma fase) | ✅ Match |
| T5 | T4 | T4 (mesma fase) | ✅ Match |
| T6 | - | - (mesma fase) | ✅ Match |
| T7 | T6 | T6 (mesma fase) | ✅ Match |
| T8 | T7 | T7 (mesma fase) | ✅ Match |
| T9 | T8 | T8 (mesma fase) | ✅ Match |
| T10 | T6 | - (mesma fase) | ✅ Match |
| T11 | T10 | T10 (mesma fase) | ✅ Match |
| T12 | T11 | T11 (mesma fase) | ✅ Match |
| T13 | T12 | T12 (mesma fase) | ✅ Match |
| T14 | T13 | T13 (mesma fase) | ✅ Match |
| T15 | T8 | - (mesma fase) | ✅ Match |
| T16 | T15 | T15 (mesma fase) | ✅ Match |
| T17 | T16 | T16 (mesma fase) | ✅ Match |
| T18 | T17 | T17 (mesma fase) | ✅ Match |
| T19 | T18 | T18 (mesma fase) | ✅ Match |
| T20 | T19 | T19 (mesma fase) | ✅ Match |
| T21 | T7, T10 | - (mesma fase) | ✅ Match |
| T22 | T21 | T21 (mesma fase) | ✅ Match |
| T23 | T22 | T22 (mesma fase) | ✅ Match |
| T24 | T23 | T23 (mesma fase) | ✅ Match |
| T25 | T24 | T24 (mesma fase) | ✅ Match |
| T26 | T25 | T25 (mesma fase) | ✅ Match |
| T27 | T26 | T26 (mesma fase) | ✅ Match |
| T28 | T9, T6 | - (mesma fase) | ✅ Match |
| T29 | T28 | T28 (mesma fase) | ✅ Match |
| T30 | T6 | - (mesma fase) | ✅ Match |
| T31 | T30 | T30 (mesma fase) | ✅ Match |
| T32 | T31 | T31 (mesma fase) | ✅ Match |
| T33 | T32 | T32 (mesma fase) | ✅ Match |
| T34 | T33, T32 | - (mesma fase) | ✅ Match |
| T35 | T34 | T34 (mesma fase) | ✅ Match |
| T36 | T35 | T35 (mesma fase) | ✅ Match |
| T37 | T36 | T36 (mesma fase) | ✅ Match |
| T38 | T37 | T37 (mesma fase) | ✅ Match |
| T39 | T38 | T38 (mesma fase) | ✅ Match |
| T40 | T33 | - (mesma fase) | ✅ Match |
| T41 | T40 | T40 (mesma fase) | ✅ Match |
| T42 | T41 | T41 (mesma fase) | ✅ Match |
| T43 | T42 | T42 (mesma fase) | ✅ Match |
| T44 | T43 | T43 (mesma fase) | ✅ Match |
| T45 | T1 | - (mesma fase) | ✅ Match |
| T46 | T45 | T45 (mesma fase) | ✅ Match |
| T47 | T46 | T46 (mesma fase) | ✅ Match |
| T48 | T47 | T47 (mesma fase) | ✅ Match |
| T49 | T48 | T48 (mesma fase) | ✅ Match |
| T50 | T18, T45 | - (mesma fase) | ✅ Match |
| T51 | T50 | T50 (mesma fase) | ✅ Match |
| T52 | T51 | T51 (mesma fase) | ✅ Match |
| T53 | T52 | T52 (mesma fase) | ✅ Match |
| T54 | T53 | T53 (mesma fase) | ✅ Match |
| T55 | T54 | T54 (mesma fase) | ✅ Match |
| T56 | T39 | - (mesma fase) | ✅ Match |
| T57 | T56, T5 | T56 (mesma fase) | ✅ Match |
| T58 | T2, T38, T39 | - (mesma fase) | ✅ Match |
| T59 | T58, T34, T56 | T58 (mesma fase) | ✅ Match |
| T60 | T59, T18, T40, T41 | T59 (mesma fase) | ✅ Match |
| T61 | T60, T46, T47, T40, T14, T13 | T60 (mesma fase) | ✅ Match |
| T62 | T61, T48, T49, T23, T36 | T61 (mesma fase) | ✅ Match |
| T63 | T62, T54, T18 | T62 (mesma fase) | ✅ Match |
| T64 | T63 | T63 (mesma fase) | ✅ Match |
| T65 | T64 | T64 (mesma fase) | ✅ Match |
| T66 | T65 | T65 (mesma fase) | ✅ Match |
| T67 | T36, T21, T23, T58 | - (mesma fase) | ✅ Match |
| T68 | T67 | T67 (mesma fase) | ✅ Match |
| T69 | T68 | T68 (mesma fase) | ✅ Match |
| T70 | T69, T35 | T69 (mesma fase) | ✅ Match |
| T71 | T70, T57, T27, T26, T35 | T70 (mesma fase) | ✅ Match |
| T72 | T71, T15, T16, T19, T37 | T71 (mesma fase) | ✅ Match |
| T73 | T72, T20, T37 | T72 (mesma fase) | ✅ Match |
| T74 | - | - (mesma fase) | ✅ Match |
| T75 | T74 | T74 (mesma fase) | ✅ Match |
| T76 | T75, T38, T29 | T75 (mesma fase) | ✅ Match |
| T77 | T76 | T76 (mesma fase) | ✅ Match |
| T78 | T77, T28, T29, T34 | T77 (mesma fase) | ✅ Match |
| T79 | T78 | T78 (mesma fase) | ✅ Match |
| T80 | T79 | T79 (mesma fase) | ✅ Match |
| T81 | T65, T71, T78, T56 | - (mesma fase) | ✅ Match |
| T82 | T81 | T81 (mesma fase) | ✅ Match |
| T83 | T82, T66, T63, T62, T64 | T82 (mesma fase) | ✅ Match |
| T84 | T83, T67, T68, T69, T70 | T83 (mesma fase) | ✅ Match |
| T85 | T84, T72, T73 | T84 (mesma fase) | ✅ Match |
| T86 | T85, T44 | T85 (mesma fase) | ✅ Match |
| T87 | T86, T77 | T86 (mesma fase) | ✅ Match |
| T88 | T87 | T87 (mesma fase) | ✅ Match |
| T89 | T83 | - (mesma fase) | ✅ Match |
| T90 | T89, T85 | T89 (mesma fase) | ✅ Match |
| T91 | T90, T83 | T90 (mesma fase) | ✅ Match |
| T92 | T91, T84 | T91 (mesma fase) | ✅ Match |
| T93 | T92, T87, T88 | T92 (mesma fase) | ✅ Match |
| T94 | T83 | - (mesma fase) | ✅ Match |
| T95 | T94 | T94 (mesma fase) | ✅ Match |
| T96 | T95 | T95 (mesma fase) | ✅ Match |
| T97 | T96 | T96 (mesma fase) | ✅ Match |
| T98 | T97 | T97 (mesma fase) | ✅ Match |
| T99 | T96, T97, T94 | - (mesma fase) | ✅ Match |
| T100 | T99 | T99 (mesma fase) | ✅ Match |
| T101 | T100 | T100 (mesma fase) | ✅ Match |
| T102 | T101 | T101 (mesma fase) | ✅ Match |
| T103 | T100, T102 | - (mesma fase) | ✅ Match |
| T104 | T103 | T103 (mesma fase) | ✅ Match |
| T105 | T104 | T104 (mesma fase) | ✅ Match |
| T106 | T105 | T105 (mesma fase) | ✅ Match |
| T107 | T106 | T106 (mesma fase) | ✅ Match |
| T108 | T107 | T107 (mesma fase) | ✅ Match |
| T109 | T31 | - (mesma fase) | ✅ Match |
| T110 | T109, T53 | T109 (mesma fase) | ✅ Match |
| T111 | T110, T108 | T110 (mesma fase) | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Fixar as dependências de documentos | Docs | none | none | ✅ OK |
| T2: Extrair `compute_process_score` com testes de caracterização | Use cases + API routes | integration | integration | ✅ OK |
| T3: Erros de geração e de arquivo excluído | Domain (entities, rules) | unit | unit | ✅ OK |
| T4: Mapear os erros novos para HTTP | Use cases + API routes | integration | integration | ✅ OK |
| T5: Extrair `MariTalkClient` do extrator | Adapters (storage, AI client) | unit | unit | ✅ OK |
| T6: Entidades de documento gerado | Domain (entities, rules) | unit | unit | ✅ OK |
| T7: Entidades do rascunho do Relatório | Domain (entities, rules) | unit | unit | ✅ OK |
| T8: Entidades do arranjo do Comprovante | Domain (entities, rules) | unit | unit | ✅ OK |
| T9: Entidades da conclusão | Domain (entities, rules) | unit | unit | ✅ OK |
| T10: Formatação em português | Domain (entities, rules) | unit | unit | ✅ OK |
| T11: Nome de arquivo do download | Domain (entities, rules) | unit | unit | ✅ OK |
| T12: Modelo da Tabela: linhas e faixas de grupo | Domain (entities, rules) | unit | unit | ✅ OK |
| T13: Modelo da Tabela: totais, horas e alertas | Domain (entities, rules) | unit | unit | ✅ OK |
| T14: Instantâneo da versão | Domain (entities, rules) | unit | unit | ✅ OK |
| T15: Arranjo derivado dos vínculos | Domain (entities, rules) | unit | unit | ✅ OK |
| T16: Plano do Comprovante: páginas e numeração | Domain (entities, rules) | unit | unit | ✅ OK |
| T17: Plano do Comprovante: página repetida e atividade sem página | Domain (entities, rules) | unit | unit | ✅ OK |
| T18: Plano do Comprovante: limites, origens indisponíveis e hash | Domain (entities, rules) | unit | unit | ✅ OK |
| T19: Desatualização do arranjo | Domain (entities, rules) | unit | unit | ✅ OK |
| T20: Validação do arranjo salvo | Domain (entities, rules) | unit | unit | ✅ OK |
| T21: Proposta do rascunho por seção | Domain (entities, rules) | unit | unit | ✅ OK |
| T22: Texto-modelo determinístico | Domain (entities, rules) | unit | unit | ✅ OK |
| T23: Reconciliar o rascunho com as atividades | Domain (entities, rules) | unit | unit | ✅ OK |
| T24: Conferência da redação: números e datas | Domain (entities, rules) | unit | unit | ✅ OK |
| T25: Conferência da redação: nomes, vocabulário e comprimento | Domain (entities, rules) | unit | unit | ✅ OK |
| T26: Campos enviados à MariTalk | Domain (entities, rules) | unit | unit | ✅ OK |
| T27: Aplicação do resultado da redação | Domain (entities, rules) | unit | unit | ✅ OK |
| T28: Verificação da conclusão | Domain (entities, rules) | unit | unit | ✅ OK |
| T29: Prévia e resultado da exclusão | Domain (entities, rules) | unit | unit | ✅ OK |
| T30: Migração 0006: documentos gerados | Repositories / migrations / worker | integration | integration | ✅ OK |
| T31: Migração 0006: redação, rascunho, arranjo e marca de exclusão | Repositories / migrations / worker | integration | integration | ✅ OK |
| T32: Modelos ORM das tabelas novas | Repositories / migrations / worker | integration | integration | ✅ OK |
| T33: Portas e repositórios abstratos | Ports | none | none | ✅ OK |
| T34: Repositório das gerações | Repositories / migrations / worker | integration | integration | ✅ OK |
| T35: Repositório das tarefas de redação | Repositories / migrations / worker | integration | integration | ✅ OK |
| T36: Repositório do rascunho | Repositories / migrations / worker | integration | integration | ✅ OK |
| T37: Repositório do arranjo | Repositories / migrations / worker | integration | integration | ✅ OK |
| T38: Métodos de exclusão e leitura em lote | Repositories / migrations / worker | integration | integration | ✅ OK |
| T39: Unidade de trabalho com os repositórios novos | Repositories / migrations / worker | integration | integration | ✅ OK |
| T40: Armazenamento dos arquivos gerados | Adapters (storage, AI client) | unit | unit | ✅ OK |
| T41: Configurações novas | Settings and configuration files | unit | unit | ✅ OK |
| T42: Carregador e validação da configuração | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T43: Modelo institucional do Relatório | Settings and configuration files | unit | unit | ✅ OK |
| T44: Ordem do dossiê | Settings and configuration files | unit | unit | ✅ OK |
| T45: Fonte e estilos de PDF | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T46: PDF da Tabela | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T47: DOCX da Tabela | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T48: DOCX do Relatório | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T49: PDF do Relatório | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T50: Capa, sumário e separadores | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T51: Anexar página original sem alterar o conteúdo | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T52: Rotação, anotações e campos | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T53: Imagens, PNG grande e página rasterizada | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T54: Montagem incremental do Comprovante | Document writers (DOCX, PDF, assembler) | unit | unit | ✅ OK |
| T55: Teste de pico de memória | Use cases + API routes | integration | integration | ✅ OK |
| T56: Executor com vários runners | Repositories / migrations / worker | integration | integration | ✅ OK |
| T57: Adaptador MariTalk da redação | Adapters (storage, AI client) | unit | unit | ✅ OK |
| T58: Leitura das entradas da geração | Use cases + API routes | integration | integration | ✅ OK |
| T59: Pedido de geração | Use cases + API routes | integration | integration | ✅ OK |
| T60: Recusas específicas do pedido | Use cases + API routes | integration | integration | ✅ OK |
| T61: Execução da geração: Tabela | Use cases + API routes | integration | integration | ✅ OK |
| T62: Execução da geração: Relatório | Use cases + API routes | integration | integration | ✅ OK |
| T63: Execução da geração: Comprovante | Use cases + API routes | integration | integration | ✅ OK |
| T64: Falha da geração sem arquivo parcial | Use cases + API routes | integration | integration | ✅ OK |
| T65: Recuperação na partida | Use cases + API routes | integration | integration | ✅ OK |
| T66: Listagem, detalhe e download das versões | Use cases + API routes | integration | integration | ✅ OK |
| T67: Leitura do rascunho | Use cases + API routes | integration | integration | ✅ OK |
| T68: Gravação do texto do rascunho | Use cases + API routes | integration | integration | ✅ OK |
| T69: Mover atividade de seção | Use cases + API routes | integration | integration | ✅ OK |
| T70: Pedido de redação em segundo plano | Use cases + API routes | integration | integration | ✅ OK |
| T71: Execução da redação | Use cases + API routes | integration | integration | ✅ OK |
| T72: Leitura do arranjo | Use cases + API routes | integration | integration | ✅ OK |
| T73: Gravação do arranjo | Use cases + API routes | integration | integration | ✅ OK |
| T74: Auxiliar de teste para concluir o processo | Use cases + API routes | integration | integration | ✅ OK |
| T75: Recusar CONCLUIDO na rota genérica | Use cases + API routes | integration | integration | ✅ OK |
| T76: Exclusão dos documentos de entrada | Use cases + API routes | integration | integration | ✅ OK |
| T77: Prévia da conclusão | Use cases + API routes | integration | integration | ✅ OK |
| T78: Conclusão do processo | Use cases + API routes | integration | integration | ✅ OK |
| T79: Documento excluído nos casos de uso de documentos | Use cases + API routes | integration | integration | ✅ OK |
| T80: Documento excluído na leitura de evidências | Use cases + API routes | integration | integration | ✅ OK |
| T81: Container e executor com os casos de uso novos | Use cases + API routes | integration | integration | ✅ OK |
| T82: Esquemas da geração | API schemas | unit | unit | ✅ OK |
| T83: Rotas de geração e download | Use cases + API routes | integration | integration | ✅ OK |
| T84: Rotas do rascunho e da redação | Use cases + API routes | integration | integration | ✅ OK |
| T85: Rotas do arranjo | Use cases + API routes | integration | integration | ✅ OK |
| T86: Rota da ordem do dossiê | Use cases + API routes | integration | integration | ✅ OK |
| T87: Rotas da conclusão | Use cases + API routes | integration | integration | ✅ OK |
| T88: Documento excluído nas rotas de documentos | Use cases + API routes | integration | integration | ✅ OK |
| T89: Aceitação: Tabela de 211 pontos | Use cases + API routes | integration | integration | ✅ OK |
| T90: Aceitação: Comprovante sintético | Use cases + API routes | integration | integration | ✅ OK |
| T91: Aceitação: versões imutáveis | Use cases + API routes | integration | integration | ✅ OK |
| T92: Aceitação: Relatório com redação | Use cases + API routes | integration | integration | ✅ OK |
| T93: Aceitação: conclusão e exclusão | Use cases + API routes | integration | integration | ✅ OK |
| T94: Mensagem do 422 com código | Frontend components/pages | unit | unit | ✅ OK |
| T95: Hook `usePolling` | Frontend components/pages | unit | unit | ✅ OK |
| T96: Tipos da API de documentos gerados | Types | none | none | ✅ OK |
| T97: Rótulos em português | Frontend components/pages | unit | unit | ✅ OK |
| T98: Etapa 5 na navegação | Frontend components/pages | unit | unit | ✅ OK |
| T99: Editor do rascunho do Relatório | Frontend components/pages | unit | unit | ✅ OK |
| T100: Redação por seção com consulta | Frontend components/pages | unit | unit | ✅ OK |
| T101: Editor do arranjo: ordem e remoção | Frontend components/pages | unit | unit | ✅ OK |
| T102: Editor do arranjo: acrescentar, repetir e aviso | Frontend components/pages | unit | unit | ✅ OK |
| T103: Bloco de documento gerado | Frontend components/pages | unit | unit | ✅ OK |
| T104: Ordem do dossiê | Frontend components/pages | unit | unit | ✅ OK |
| T105: Diálogo de conclusão | Frontend components/pages | unit | unit | ✅ OK |
| T106: Documento excluído nas telas de documentos | Frontend components/pages | unit | unit | ✅ OK |
| T107: Página da Etapa 5 | Frontend components/pages | unit | unit | ✅ OK |
| T108: Largura de 360 px | Frontend components/pages | unit | unit | ✅ OK |
| T109: Notas de implantação | Docs | none | none | ✅ OK |
| T110: Contagem local de páginas com rotação e recorte | Docs | none | none | ✅ OK |
| T111: Verificador independente | Docs | none | none | ✅ OK |

---

## Requirement Coverage

Cada requisito da spec aparece em pelo menos uma tarefa (verificado por script contra a tabela de rastreabilidade).

| Requirement | Tasks |
| ----------- | ----- |
| ARR-01 | T8, T15, T72, T85, T111 |
| ARR-02 | T20, T73, T85, T102 |
| ARR-03 | T20, T73, T90, T101 |
| ARR-04 | T20, T73, T90, T101 |
| ARR-05 | T15, T20, T73 |
| ARR-06 | T20, T73, T85 |
| ARR-07 | T31, T37, T73, T85 |
| ARR-08 | T19, T72, T102 |
| CMP-01 | T16, T33, T50, T54, T63, T90, T111 |
| CMP-02 | T16, T54, T63 |
| CMP-03 | T51, T52, T54, T90 |
| CMP-04 | T8, T16, T50, T72, T90 |
| CMP-05 | T17, T63, T90 |
| CMP-06 | T17, T102 |
| CMP-07 | T17, T63, T90 |
| CMP-08 | T53 |
| CMP-09 | T18, T40, T41, T54, T60, T64 |
| CMP-10 | T18, T54, T60, T64 |
| CMP-11 | T54, T55 |
| CMP-12 | T53, T110 |
| CMP-13 | T18, T41, T53, T60 |
| DEL-01 | T28, T34, T78, T87, T111 |
| DEL-02 | T28, T38, T78, T87 |
| DEL-03 | T9, T29, T77, T87, T105 |
| DEL-04 | T78, T87, T105 |
| DEL-05 | T31, T33, T38, T76, T78, T93, T109 |
| DEL-06 | T31, T38, T76, T79, T80, T88, T93, T106 |
| DEL-07 | T78, T93 |
| DEL-08 | T9, T29, T76, T78, T93, T105 |
| DEL-09 | T29, T76, T78, T93 |
| DEL-10 | T78 |
| DEL-11 | T18, T60, T93 |
| DEL-12 | T3, T4, T79, T80, T88, T93, T106 |
| DEL-13 | T29, T66, T83, T93 |
| DEL-14 | T4, T74, T75 |
| DEL-15 | T75, T77, T78, T87 |
| ORD-01 | T44, T86, T104, T107, T111 |
| ORD-02 | T42, T44, T86 |
| REL-01 | T7, T21, T42, T43, T67, T111 |
| REL-02 | T10, T21, T43 |
| REL-03 | T5, T26, T33, T35, T36, T57, T70, T71, T84, T92, T100 |
| REL-04 | T24, T25, T27, T71, T92 |
| REL-05 | T5, T27, T41, T57, T71, T92 |
| REL-06 | T26, T57, T71 |
| REL-07 | T7, T23, T27, T36, T68, T71, T84, T92, T99 |
| REL-08 | T23, T36, T69, T84, T99 |
| REL-09 | T48, T49, T62, T92 |
| REL-10 | T60, T62 |
| REL-11 | T21, T48, T49, T67, T68, T99 |
| REL-12 | T22, T25, T43, T48, T62 |
| REL-13 | T6, T31, T32, T35, T70, T84, T92, T100 |
| REL-14 | T35, T56, T65, T81 |
| REL-15 | T35, T71 |
| TAB-01 | T1, T2, T45, T46, T47, T58, T59, T61, T83, T89, T111 |
| TAB-02 | T10, T12, T58 |
| TAB-03 | T12, T46, T47 |
| TAB-04 | T2, T13, T46, T47, T89 |
| TAB-05 | T13, T46, T47, T89 |
| TAB-06 | T13, T46, T47, T89 |
| TAB-07 | T3, T4, T59, T83, T89, T94 |
| TAB-08 | T59, T83, T89 |
| UIG-01 | T82, T96, T98, T103, T107, T111 |
| UIG-02 | T84, T99, T107 |
| UIG-03 | T85, T101, T102, T107 |
| UIG-04 | T95, T103 |
| UIG-05 | T94, T97, T103 |
| UIG-06 | T58, T103 |
| UIG-07 | T108 |
| UIG-08 | T84, T95, T100 |
| UIG-09 | T105, T107 |
| VER-01 | T6, T30, T33, T34, T39, T40, T61, T91, T109, T111 |
| VER-02 | T14, T32, T34, T61, T63, T91 |
| VER-03 | T11, T66, T82, T83, T91 |
| VER-04 | T4, T6, T30, T34, T56, T59, T81, T83 |
| VER-05 | T6, T34, T40, T64 |
| VER-06 | T59, T66, T83 |
| VER-07 | T59, T61, T64 |
| VER-08 | T34, T56, T65, T81 |
| VER-09 | T66, T82, T91, T103 |


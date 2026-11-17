# Inteligência Documental Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/inteligencia-documental/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: requisitos do usuário, seção 19; AD-001 (teste de arquitetura); AD-004 (integração em PostgreSQL real); AD-009 (saída da IA é não confiável); suites e comandos de `fundacao` e `pontuacao`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules) | unit | All branches; 1:1 to spec ACs; every listed edge case and each boundary value | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Adapters (storage, files, OCR, AI client) | unit | Key paths + error paths with temporary files, synthetic documents and a simulated HTTP transport | `backend/tests/unit/infrastructure/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Analyzer service | unit | Fake ports; every AC; the AI that invents data must be caught | `backend/tests/unit/application/test_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Repositories / migrations / worker | integration | Key query paths, concurrency (`SKIP LOCKED`), error paths | `backend/tests/integration/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Use cases + API routes | integration | All routes in scope: happy + every listed edge case + error paths (401/403/404/409/422/429) | `backend/tests/integration/{documents,api}/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend components/pages | unit | Each TELA AC: render + interaction + error display | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Docker / nginx | e2e smoke | PIPE-06 e DOC-03 verified against the running stack | `scripts/smoke*.sh` | `./scripts/smoke.sh` |
| Ports / config | none | build gate only | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or config-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm test -- --run && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Domínio, entidades e regras de arquivo e texto

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
```

### Phase 2: Regras de sugestão, portas, configuração e banco

```
T9 → T10 → T11 → T12 → T13 → T14 → T15
```

### Phase 3: Arquivos, OCR e texto

```
T16 → T17 → T18 → T19 → T20 → T21
```

### Phase 4: Extração com a IA e analisador

```
T22 → T23 → T24 → T25
```

### Phase 5: Casos de uso de documentos

```
T26 → T27 → T28 → T29
```

### Phase 6: Processamento, vínculos e integração com a pontuação

```
T30 → T31 → T32 → T33 → T34
```

### Phase 7: Executor em segundo plano e API de documentos

```
T35 → T36 → T37 → T38 → T39 → T40 → T41
```

### Phase 8: Interface, envio e lista de documentos

```
T42 → T43 → T44 → T45 → T46 → T47
```

### Phase 9: Páginas das Etapas 2 e 3

```
T48 → T49 → T50
```

### Phase 10: Imagem, nginx e aceitação com os documentos reais

```
T51 → T52 → T53 → T54
```

---

## Task Breakdown

### T1: Entidades de documento

**What**: `DocumentStatus` com `can_transition`, `Document`, `PageText`, `ExtractionRun` e `DocAlertCode` (incluindo `SEM_ITEM_DE_PONTUACAO`).
**Where**: `backend/app/domain/entities/document.py`
**Depends on**: None
**Reuses**: padrão de `entities/activity.py`
**Requirement**: PIPE-02, DOC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Transições válidas: PENDENTE→PROCESSANDO→(PROCESSADO|REQUER_REVISAO|EXTRAIDO_SEM_IA|FALHOU); qualquer outra é recusada
- [x] Os 11 códigos de alerta existem com o nome exato do design
- [x] Nada importa framework (teste de arquitetura verde)
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add document entities and status transitions`

---

### T2: Entidades de extração e taxonomia

**What**: `DocumentType`, `TaxonomyCode` (todos os códigos da tabela do design) e `ExtractedActivity`.
**Where**: `backend/app/domain/entities/extraction.py`
**Depends on**: T1
**Reuses**: -
**Requirement**: CLS-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A taxonomia tem exatamente os códigos da tabela de regras do design, incluindo `OUTRA`
- [x] `ExtractedActivity` guarda página, trecho e confiança
- [x] Gate quick passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add extraction entities and activity taxonomy`

---

### T3: Validação de envio

**What**: `validate_upload(facts, declared_mime, ext, limits)`: extensão, MIME, assinatura, tamanho, páginas, megapixels e conteúdo ativo; nome original só para exibição.
**Where**: `backend/app/domain/rules/upload_validation.py`
**Depends on**: T2
**Reuses**: -
**Requirement**: DOC-02, DOC-03, DOC-04, edge case do nome de arquivo

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `.pdf`, `.jpg`, `.jpeg` e `.png` passam; `.exe`, `.docx` e extensão trocada (PDF com assinatura PNG) são recusados com o campo `arquivo`
- [x] 20 MB passa e 20 MB + 1 byte é recusado; 100 páginas passa e 101 é recusado; 100 megapixels passa e acima é recusado
- [x] PDF com JavaScript, lançamento, arquivo embutido ou criptografado: recusado com `ARQUIVO_INVALIDO`
- [x] Nome com `../` ou mais de 255 caracteres nunca forma caminho
- [x] Gate quick passa; 16+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add upload validation rules`

---

### T4: Qualidade da camada de texto

**What**: `is_text_layer_usable(text)` e `ocr_needs_review(confidence, text)`.
**Where**: `backend/app/domain/rules/text_quality.py`
**Depends on**: T3
**Reuses**: -
**Requirement**: PIPE-05, PIPE-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Menos de 50 caracteres úteis: inutilizável; 50 exatos: utilizável
- [x] Mais de 30% de símbolos: inutilizável; 30% exatos: utilizável
- [x] Texto de portaria sintético com lixo (como `7 r:rjo;:N *P-7-44`) é inutilizável; texto normal em português é utilizável
- [x] Confiança do OCR abaixo de 60 ou sem texto pede revisão (`TEXTO_ILEGIVEL`); 60 exatos não pede
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add text layer quality rules`

---

### T5: Máscara de identificadores

**What**: `mask_identifiers(text)`: CPF, RG, e-mail e telefone viram marcadores; nomes e matrícula SIAPE ficam.
**Where**: `backend/app/domain/rules/masking.py`
**Depends on**: T4
**Reuses**: -
**Requirement**: EXT-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] CPF com e sem pontuação viram `[CPF]`; RG vira `[RG]`; e-mail vira `[EMAIL]`; telefone (com DDD, com e sem parênteses) vira `[TELEFONE]`
- [x] Nome próprio e matrícula SIAPE de 7 dígitos não mudam
- [x] O texto original não é alterado (a função devolve cópia)
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add personal identifier masking`

---

### T6: Tipo de documento por palavras-chave

**What**: `detect_document_type(text)` escolhe o schema: ata de defesa, declaração de banca, declaração de orientação, declaração de disciplinas, certificado, portaria, artigo, registro de software ou outro.
**Where**: `backend/app/domain/rules/document_type.py`
**Depends on**: T5
**Reuses**: -
**Requirement**: EXT-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Textos sintéticos de cada tipo, no estilo dos documentos reais, resultam no tipo esperado
- [x] Texto sem nenhuma palavra-chave resulta em `OUTRO`
- [x] Gate quick passa; 12+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add keyword based document type detection`

---

### T7: Verificação no texto e identidade do docente

**What**: `ground(extracted, pages)` confere data, horas, identificador, título e nome no texto da página citada, e `same_person(...)` compara o docente.
**Where**: `backend/app/domain/rules/grounding.py`
**Depends on**: T6
**Reuses**: `normalize_title` de `scoring_periods.py`
**Requirement**: EXT-10, EXT-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Data em `dd/mm/aaaa`, `dd.mm.aaaa`, "23 de março de 2026" e `Mai/22` presentes no texto passam; data ausente vira `null` com `NAO_ENCONTRADO_NO_TEXTO(campo)`
- [x] Horas, número de portaria, ISSN e DOI ausentes do texto viram `null`; presentes passam
- [x] Título com 90% ou mais dos termos no texto passa; abaixo disso vira `null`
- [x] `same_person`: nome do docente do processo contido no nome extraído ou matrícula SIAPE no texto dá verdadeiro; nome de outra pessoa dá falso
- [x] Devolve a fração de campos verificáveis encontrados; Gate quick passa; 25+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add grounding of extracted values in source text`

---

### T8: Confiança final

**What**: `final_confidence(llm_confidence, grounded_ratio)` e `needs_review(confidence)`.
**Where**: `backend/app/domain/rules/confidence.py`
**Depends on**: T7
**Reuses**: -
**Requirement**: EXT-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A confiança final é o menor dos dois valores (0,94 e 0,60 dão 0,60)
- [x] 0,70 não pede revisão; 0,69 pede
- [x] Valores fora de 0 a 1 são recusados
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add extraction confidence rules`

---

### T9: Regras de sugestão de item

**What**: `suggest_item(taxonomy, extras)` com a tabela do design e `confirm_extension_course(taxonomy, text)`.
**Where**: `backend/app/domain/rules/suggestion_rules.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: tabela de regras do design; numeração do Anexo I
**Requirement**: CLS-02, CLS-03, CLS-04, CLS-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada linha da tabela do design dá o principal e os alternativos exatos (ex.: `BANCA_TCC_GRADUACAO` é III.4; `PALESTRA` é VIII.28 sem alternativas; `TREINAMENTO_INTERNO` e `PARTICIPACAO_EVENTO` são VII.10)
- [x] `COORIENTACAO_TCC_GRADUACAO` e `OUTRA` devolvem principal `None`
- [x] `CURSO_EXTENSAO_CONCLUIDO` com texto sem "extensão" vira `CURSO_CONCLUIDO` (VII.10); com "extensão" fica VII.9
- [x] Todo tipo da taxonomia tem uma regra; cada regra cita a fonte
- [x] Gate quick passa; 30+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring item suggestion rules`

---

### T10: Quantidade e horas por regra

**What**: `derive_quantity(taxonomy, extracted)`: banca e orientação = 1; carga horária em horas; Grupo I com nível, período e CH docente; "por ano" em anos inteiros com `QUANTIDADE_ESTIMADA`.
**Where**: `backend/app/domain/rules/quantity_rules.py`
**Depends on**: T9
**Reuses**: -
**Requirement**: CLS-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Banca e orientação: quantidade 1
- [x] Curso com 21 horas: horas 21; Grupo I: horas = CH docente, nível e período letivo preservados
- [x] Projeto de 2022-08 a 2023-07: 0 anos inteiros viram 1 com aviso; 2022-08 a 2024-08: 2 anos
- [x] A função nunca chama IA e nunca devolve pontos
- [x] Gate quick passa; 12+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add deterministic quantity derivation`

---

### T11: Portas de documentos e IA

**What**: Protocols `DocumentRepository`, `ExtractionRepository`, `JobRepository`, `EvidenceRepository`, `FileStorage`, `FileInspector`, `TextExtractor`, `AiExtractor` e `UnitOfWork` estendido.
**Where**: `backend/app/domain/repositories/ports.py`
**Depends on**: T10
**Reuses**: portas existentes do arquivo
**Requirement**: PIPE-01, DOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] As portas existem com os métodos do design (claim de tarefa, contagem de envios por usuário no último minuto, existência por hash)
- [x] Teste de arquitetura continua passando
- [x] Build gate passa

**Tests**: none
**Gate**: build

**Commit**: `feat(domain): add document and extraction ports`

---

### T12: Configuração de armazenamento, limites e executor

**What**: Campos `storage_dir`, `worker_enabled`, limites de envio e tempos da IA em `Settings`.
**Where**: `backend/app/core/config.py`
**Depends on**: T11
**Reuses**: `Settings` existente (`maritalk_*`)
**Requirement**: EXT-02, DOC-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Modelo efetivo é `maritalk_model` quando preenchido e `sabia-4-br-sp` quando vazio
- [x] Limites têm os padrões da spec (20 MB, 120 MB, 100 páginas, 100 MP, 200 documentos, 60 envios/min)
- [x] Nenhum valor secreto aparece em `repr(settings)`
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(core): add storage, limits and worker settings`

---

### T13: Geradores de documentos sintéticos

**What**: Funções que geram PDF com texto, PDF digitalizado, JPG, PNG, PDF com camada de texto ruidosa, PDF com JavaScript, PDF criptografado e imagem enorme, sem dado real.
**Where**: `backend/tests/support/synthetic_docs.py`
**Depends on**: T12
**Reuses**: PyMuPDF e Pillow
**Requirement**: ACC-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada gerador produz um arquivo que abre e tem a assinatura certa
- [x] O PDF digitalizado não tem camada de texto; o ruidoso tem texto com mais de 30% de símbolos
- [x] Nenhum texto gerado contém nome, SIAPE ou CPF reais
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `test(support): add synthetic document generators`

---

### T14: Modelos ORM e migração 0003

**What**: Tabelas `documents`, `extraction_runs` (com gatilho de imutabilidade), `document_pages`, `processing_jobs`, `activity_evidences` e `activities.extraction_run_id`.
**Where**: `backend/app/infrastructure/database/models.py`
**Depends on**: T13
**Reuses**: `0002_scoring.py`, gatilho de `audit_logs`
**Requirement**: DOC-01, DOC-07, PIPE-01, EXT-13, VINC-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `alembic upgrade head` e `downgrade -1` funcionam no Postgres de teste
- [x] Único (processo, hash) e único (atividade, documento, página); índice parcial de uma tarefa ativa por documento
- [x] UPDATE do conteúdo de `extraction_runs` é recusado; só o `status` muda
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add document schema and migration 0003`

---

### T15: Repositórios de documentos

**What**: `SqlDocumentRepository`, `SqlExtractionRepository`, `SqlJobRepository` e `SqlEvidenceRepository` com `FOR UPDATE SKIP LOCKED` e recuperação de tarefas.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T14
**Reuses**: padrão de `SqlProcessRepository`
**Requirement**: PIPE-01, PIPE-03, DOC-07, DOC-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Dois claims concorrentes não pegam a mesma tarefa
- [x] `recover_stuck` recoloca `PROCESSANDO` em `PENDENTE`
- [x] Mesmo hash no mesmo processo dá `Conflict` com o id do existente; processos diferentes aceitam
- [x] Contagem de documentos do processo e de envios do usuário no último minuto corretas
- [x] Gate full passa; 14+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(db): add document, extraction, job and evidence repositories`

---

### T16: Armazenamento local

**What**: `LocalFileStorage`: caminho `uploads/{processo}/{uuid4}{ext}`, permissões 0600, leitura e remoção.
**Where**: `backend/app/infrastructure/storage/local_storage.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: -
**Requirement**: DOC-05, DOC-06, edge case do nome

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O caminho nunca contém o nome original; nome com `../` é só texto de exibição
- [x] Gravar e ler devolve os mesmos bytes; o arquivo tem modo 0600
- [x] Excluir remove o arquivo e é idempotente
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(storage): add private local file storage`

---

### T17: Inspeção de arquivos

**What**: `FileInspector.inspect(path) -> FileFacts`: assinatura, páginas, criptografia, JavaScript, lançamento, arquivo embutido, megapixels; adiciona `pymupdf` e `pillow` aos requisitos.
**Where**: `backend/app/infrastructure/files/inspector.py`
**Depends on**: T16
**Reuses**: geradores sintéticos de T13
**Requirement**: DOC-02, DOC-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os geradores sintéticos produzem os fatos esperados (PDF com JS: ação ativa; criptografado; imagem acima de 100 MP; JPG e PNG válidos)
- [x] PDF corrompido devolve fatos de arquivo inválido sem lançar exceção
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(files): add file inspector`

---

### T18: Texto de PDF por página

**What**: `extract_pdf_pages(path)` com PyMuPDF: texto, página e contagem de caracteres.
**Where**: `backend/app/infrastructure/ocr/pdf_text.py`
**Depends on**: T17
**Reuses**: -
**Requirement**: PIPE-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] PDF sintético com texto devolve o texto de cada página, com número e contagem
- [x] PDF digitalizado devolve texto vazio
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ocr): add per page pdf text extraction`

---

### T19: Renderização de página

**What**: `render_page(path, page, dpi=300)` e pré-processamento em tons de cinza com autocontraste (Pillow).
**Where**: `backend/app/infrastructure/ocr/render.py`
**Depends on**: T18
**Reuses**: -
**Requirement**: PIPE-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A página A4 a 300 dpi tem cerca de 2480 × 3508 pixels e fica em tons de cinza
- [x] Imagem JPG ou PNG passa pelo mesmo pré-processamento
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ocr): add page rendering and preprocessing`

---

### T20: OCR com Tesseract

**What**: `ocr_image(image)`: Tesseract em português por subprocesso, saída TSV, texto e confiança média, tempo máximo de 60 s.
**Where**: `backend/app/infrastructure/ocr/tesseract.py`
**Depends on**: T19
**Reuses**: -
**Requirement**: PIPE-06, PIPE-07, PIPE-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Imagem sintética com texto em português devolve esse texto e confiança acima de 60
- [x] Imagem em branco devolve texto vazio
- [x] Estouro de 60 s devolve `TEMPO_ESGOTADO` sem travar (processo filho encerrado)
- [x] Gate quick passa; 7+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ocr): add tesseract ocr adapter`

---

### T21: Extrator de texto do documento

**What**: `DocumentTextExtractor` (porta `TextExtractor`): por página, `TEXTO` quando a camada é utilizável e `OCR` caso contrário; imagem sempre por OCR; limite de 10 minutos.
**Where**: `backend/app/infrastructure/ocr/extractor.py`
**Depends on**: T20
**Reuses**: `is_text_layer_usable`, `ocr_image`
**Requirement**: PIPE-04, PIPE-05, PIPE-06, PIPE-07, PIPE-08, edge case de PDF misto

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] PDF com texto: método `TEXTO` em todas as páginas; PDF digitalizado: `OCR`; PDF misto: `TEXTO` nas primeiras e `OCR` nas demais
- [x] PDF com camada ruidosa usa `OCR` nessa página
- [x] PNG e JPG sintéticos usam `OCR`
- [x] Documento que passa de 10 minutos devolve `TEMPO_ESGOTADO` mantendo as páginas já extraídas (relógio injetado)
- [x] Build gate passa; 12+ testes

**Tests**: unit
**Gate**: build

**Commit**: `feat(ocr): add document text extractor with ocr fallback`

---

### T22: Schemas JSON por tipo de documento

**What**: Schemas estritos para cada `DocumentType`, com `null` permitido nos campos factuais.
**Where**: `backend/app/infrastructure/ai/schemas.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: taxonomia de T2
**Requirement**: EXT-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Todo tipo tem schema; todos os campos factuais aceitam `null`; `additionalProperties` falso
- [x] `taxonomy` é um enum fechado com os códigos da taxonomia
- [x] Resposta de exemplo válida passa e resposta com campo extra é recusada
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ai): add strict json schemas per document type`

---

### T23: Adaptador da MariTalk

**What**: `MariTalkExtractor` (porta `AiExtractor`) com `httpx`: modelo da configuração, reserva `sabia-4-br-sp`, repetições, orçamento de tokens e nunca vazar a chave.
**Where**: `backend/app/infrastructure/ai/maritalk.py`
**Depends on**: T22
**Reuses**: `maritalk_*` de `Settings`; `test/test_maritalk.py`
**Requirement**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, EXT-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Chama `POST {base}/chat/completions` com `Authorization: Bearer` e o modelo configurado, ou `sabia-4-br-sp` quando vazio (transporte simulado)
- [x] 400 ou 404 de modelo repete uma vez com `sabia-4-br-sp`; 401 e 403 não repetem e dão `IA_CREDENCIAL_RECUSADA`
- [x] 429, 5xx e tempo esgotado repetem 2 vezes com espera de 2 e 6 s e depois dão `IA_INDISPONIVEL` (espera injetada)
- [x] `content` vazio ou `finish_reason: length` repete com `max_tokens` dobrado (8000 para 16000); `reasoning_content` nunca é lido
- [x] A chave não aparece em mensagens de erro, `repr` nem logs capturados
- [x] Gate quick passa; 16+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(ai): add maritalk extraction adapter`

---

### T24: Analisador: texto, IA e verificação

**What**: `DocumentAnalyzer.analyze` do texto à verificação: máscara, 6 páginas, schema, nova tentativa, verificação no texto, docente e confiança.
**Where**: `backend/app/application/services/document_analyzer.py`
**Depends on**: T23
**Reuses**: portas `TextExtractor` e `AiExtractor`, regras de T3 a T8
**Requirement**: EXT-07, EXT-08, EXT-09, EXT-10, EXT-11, EXT-12, EXT-13, PIPE-07, edge case de lista vazia

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Com IA falsa: o texto enviado está mascarado (CPF vira `[CPF]`) e tem no máximo 6 páginas; o aviso `TRUNCADO` aparece acima disso
- [x] IA falsa que inventa uma data: o campo vira `null` com `NAO_ENCONTRADO_NO_TEXTO` e a atividade não carrega a data
- [x] Nome de outro docente: alerta `DOCENTE_DIVERGENTE` e `REQUER_REVISAO`
- [x] JSON fora do schema: uma nova tentativa e depois `REQUER_REVISAO` com `RESPOSTA_INVALIDA`
- [x] Lista vazia em documento legível: `PROCESSADO` com `NENHUMA_ATIVIDADE_ENCONTRADA`
- [x] Confiança abaixo de 0,70 marca revisão; o JSON bruto, o modelo e a duração são devolvidos
- [x] Gate quick passa; 20+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(analysis): add document analyzer text to verified extraction`

---

### T25: Analisador: classificação e quantidade

**What**: `DocumentAnalyzer` aplica as regras de sugestão e de quantidade e sinaliza interstício.
**Where**: `backend/app/application/services/document_analyzer.py`
**Depends on**: T24
**Reuses**: `suggest_item`, `derive_quantity`, `evaluate_period`
**Requirement**: CLS-01, CLS-02, CLS-03, CLS-04, CLS-05, CLS-06, CLS-07, CLS-08, CLS-09, CLS-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Declaração de banca de TCC dá III.4 como escolhido, sem candidatos, origem `SUGERIDA_IA` e status `AGUARDANDO_REVISAO`
- [x] Declaração de disciplinas com 3 ofertas dá 3 atividades do Grupo I com nível, período e CH docente
- [x] Coorientação de TCC, treinamento sem item e `OUTRA` não criam atividade e dão `SEM_ITEM_DE_PONTUACAO`
- [x] Item inexistente na versão da tabela do processo: atividade com `SEM_ENQUADRAMENTO`
- [x] Data fora do interstício: sinalizada na sugestão e a atividade é mantida
- [x] Curso de extensão sem a palavra "extensão" no texto cai em VII.10
- [x] Build gate passa; 18+ testes

**Tests**: unit
**Gate**: build

**Commit**: `feat(analysis): add classification and quantity to the analyzer`

---

### T26: Enviar documentos

**What**: `UploadDocuments`: validação, hash, gravação, tarefa, resultado por arquivo, limites e auditoria.
**Where**: `backend/app/application/use_cases/documents.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `AccessPolicy`, `AuditService`, portas de T11
**Requirement**: DOC-01, DOC-02, DOC-03, DOC-05, DOC-06, DOC-07, DOC-12, DOC-13, DOC-14, edge case de arquivo repetido na requisição

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Lote de três (válido, duplicado, extensão trocada): resultados 201, 409 com o id do existente e 422 no campo `arquivo`; o válido é gravado e vira tarefa `PENDENTE`
- [x] O mesmo arquivo duas vezes na requisição: o primeiro grava e o segundo dá 409
- [x] 200 documentos no processo: 422 em `limite`; 61º envio no minuto: 429
- [x] Processo `CONCLUIDO` ou `ARQUIVADO`: 409; sem acesso: 404
- [x] Auditoria registra usuário, hora, documento e operação, sem conteúdo
- [x] Gate full passa; 16+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): add document upload use case`

---

### T27: Consultar, listar e baixar documentos

**What**: `GetDocument`, `ListDocuments` e `DownloadDocument` (anexo ou em linha).
**Where**: `backend/app/application/use_cases/documents.py`
**Depends on**: T26
**Reuses**: -
**Requirement**: DOC-08, DOC-13, DOC-15, REV-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Lista com filtros por status e tipo, em ordem de envio, com categoria sugerida e confiança
- [x] Detalhe devolve texto por página (método e confiança), JSON extraído e atividades vinculadas
- [x] Download audita; visualização só para PDF e imagem; sem acesso: 404
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): add document read and download use cases`

---

### T28: Substituir e excluir documentos

**What**: `ReplaceDocument` e `DeleteDocument` com justificativa e auditoria.
**Where**: `backend/app/application/use_cases/documents.py`
**Depends on**: T27
**Reuses**: `FileStorage`
**Requirement**: DOC-09, DOC-10, DOC-12, DOC-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Substituir valida o novo arquivo, mantém o id, remove o arquivo anterior, reinicia a tarefa e audita nome e hash anterior e novo
- [x] Excluir sem justificativa: 422; com justificativa: remove arquivo, texto e vínculos, mantém as atividades e audita
- [x] Processo concluído: 409
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): add document replace and delete use cases`

---

### T29: Classificação manual e reprocessamento

**What**: `ClassifyDocumentManually` e `ReprocessDocument`.
**Where**: `backend/app/application/use_cases/documents.py`
**Depends on**: T28
**Reuses**: `ChangeActivityStatus`
**Requirement**: DOC-11, PIPE-09, edge case de reprocessamento concorrente

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Classificação manual grava o tipo e a categoria sem apagar os sugeridos e audita
- [x] Reprocessar marca a execução anterior `SUBSTITUIDA`, rejeita com justificativa automática os rascunhos não editados e mantém os validados ou editados
- [x] Duas solicitações simultâneas: a primeira vale e a segunda dá 409
- [x] Build gate passa; 12+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(documents): add manual classification and reprocessing`

---

### T30: Processar documento e recuperar tarefas

**What**: `ProcessDocument.execute(job_id)` e `RecoverStuckJobs`: analisa, grava páginas e execução e cria atividades e vínculos.
**Where**: `backend/app/application/use_cases/document_processing.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `DocumentAnalyzer`, `CreateActivity`
**Requirement**: PIPE-01, PIPE-02, PIPE-03, PIPE-10, PIPE-11, VINC-01, CLS-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Documento de banca com IA falsa: status `PROCESSADO`, atividade `SUGERIDA_IA` e `AGUARDANDO_REVISAO` com vínculo (documento, página e trecho de até 300 caracteres)
- [x] IA indisponível: `EXTRAIDO_SEM_IA` e o cadastro manual segue funcionando
- [x] Documento sem item: `PROCESSADO`, nenhuma atividade, aviso `SEM_ITEM_DE_PONTUACAO`
- [x] `RecoverStuckJobs` volta `PROCESSANDO` para `PENDENTE`
- [x] Logs capturados não contêm texto, nomes nem números de documento
- [x] Gate full passa; 14+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): add document processing use case`

---

### T31: Vínculos entre atividade e documento

**What**: `LinkEvidence` e `UnlinkEvidence`.
**Where**: `backend/app/application/use_cases/evidences.py`
**Depends on**: T30
**Reuses**: `AuditService`
**Requirement**: VINC-02, VINC-03, VINC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Um documento comprova várias atividades e uma atividade tem vários documentos; (atividade, documento, página) é único
- [x] Vincular documento já ligado a outra atividade sem justificativa: 422 em `justificativa`
- [x] Remover o vínculo audita e mantém a atividade
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): add evidence link use cases`

---

### T32: Validação em lote

**What**: `BulkValidateActivities` com uma justificativa e uma auditoria por atividade.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T31
**Reuses**: `ChangeActivityStatus`
**Requirement**: REV-02, REV-03, REV-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Três atividades selecionadas ficam `VALIDADA` com a mesma justificativa e três eventos de auditoria
- [x] Sem justificativa: 422; atividade de outro processo na lista: 404 sem validar nenhuma
- [x] Nada é validado sem a chamada explícita
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add bulk activity validation`

---

### T33: Motor: contagem de comprovantes

**What**: `calculate` recebe `evidence_counts` e conta `with_evidence` e `SEM_COMPROVANTE` por vínculo ou nota.
**Where**: `backend/app/domain/rules/scoring_engine.py`
**Depends on**: T32
**Reuses**: `calculate` existente
**Requirement**: VINC-04, VINC-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Atividade com um vínculo e sem nota: conta em `with_evidence` e não emite `SEM_COMPROVANTE`
- [x] Sem vínculo e sem nota: emite `SEM_COMPROVANTE`
- [x] Com nota e sem vínculo: conta e não emite (comportamento anterior preservado)
- [x] Os testes existentes do motor continuam passando sem alteração; Gate quick passa; 6+ testes novos

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): count linked documents as evidence in the scoring engine`

---

### T34: Cálculo da pontuação com vínculos

**What**: `CalculateProcessScore` carrega a contagem de vínculos por atividade e a repassa ao motor; as linhas trazem `evidence_count`.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T33
**Reuses**: `SqlEvidenceRepository`
**Requirement**: VINC-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Resultado do processo mostra `evidence_count` por linha e `counters.with_evidence` coerente com os vínculos
- [x] O teste do caso real FASI continua com 414
- [x] Build gate passa; 6+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(scoring): feed linked documents into the process score`

---

### T35: Executor em segundo plano

**What**: Thread única iniciada no `lifespan` quando `worker_enabled`, com claim por `SKIP LOCKED`, espera de 2 s e parada limpa; `RecoverStuckJobs` na partida.
**Where**: `backend/app/infrastructure/jobs/worker.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `lifespan` de `app/main.py`
**Requirement**: PIPE-01, PIPE-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Tarefa `PENDENTE` inserida é processada e termina `CONCLUIDA` (analisador falso)
- [x] Duas tarefas são processadas uma por vez, na ordem de criação
- [x] Na partida, tarefa `PROCESSANDO` volta para `PENDENTE` e é reprocessada
- [x] Com `worker_enabled` falso nada roda; a parada do app encerra a thread
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(jobs): add background document worker`

---

### T36: Rotas: enviar, listar e consultar

**What**: `POST` e `GET /api/processes/{id}/documents` e `GET /api/documents/{id}`, com esquemas.
**Where**: `backend/app/presentation/api/documents.py`
**Depends on**: T35
**Reuses**: padrão de `presentation/api/activities.py`
**Requirement**: DOC-01, DOC-02, DOC-03, DOC-07, DOC-12, DOC-14, DOC-15, REV-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Envio multipart com vários arquivos: 201 com o resultado de cada um; recusados mostram o campo `arquivo` e o código
- [x] 409 do duplicado traz o id do existente; 429 acima de 60 envios por minuto
- [x] Lista filtrada por status e tipo; detalhe com páginas, JSON extraído e atividades
- [x] 401 sem sessão; 403 sem CSRF; 404 sem acesso ao processo
- [x] Gate full passa; 16+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add document upload, list and detail routes`

---

### T37: Rotas: arquivo, substituir e excluir

**What**: `GET /api/documents/{id}/file`, `PUT /api/documents/{id}/file` e `DELETE /api/documents/{id}?justificativa=`.
**Where**: `backend/app/presentation/api/documents.py`
**Depends on**: T36
**Reuses**: -
**Requirement**: DOC-05, DOC-06, DOC-08, DOC-09, DOC-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Download devolve o arquivo original byte a byte com `Content-Disposition: attachment` e `X-Content-Type-Options: nosniff`
- [x] Visualização em linha só de PDF e imagem, com `Content-Security-Policy: sandbox`
- [x] Substituir e excluir seguem as regras de T28; excluir sem justificativa: 422
- [x] Gate full passa; 12+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add document file, replace and delete routes`

---

### T38: Rotas: reprocessar e classificar

**What**: `POST /api/documents/{id}/reprocess` e `PUT /api/documents/{id}/classification`.
**Where**: `backend/app/presentation/api/documents.py`
**Depends on**: T37
**Reuses**: -
**Requirement**: DOC-11, PIPE-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Reprocessar devolve 202 e cria uma tarefa; concorrente dá 409
- [x] Classificação manual grava tipo e categoria e devolve o documento
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add document reprocess and classification routes`

---

### T39: Rotas de vínculos

**What**: `POST /api/activities/{id}/evidences` e `DELETE /api/activities/{id}/evidences/{evidence_id}`.
**Where**: `backend/app/presentation/api/evidences.py`
**Depends on**: T38
**Reuses**: casos de uso de T31
**Requirement**: VINC-02, VINC-03, VINC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Vincular, listar no detalhe da atividade e remover
- [x] Vínculo de documento já ligado a outra atividade exige `justificativa` (422 no campo)
- [x] Sem acesso: 404; sem sessão: 401
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add evidence routes`

---

### T40: Rota de validação em lote

**What**: `POST /api/processes/{id}/activities/validate-batch`.
**Where**: `backend/app/presentation/api/activities.py`
**Depends on**: T39
**Reuses**: `BulkValidateActivities`
**Requirement**: REV-02, REV-03, REV-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Valida as atividades listadas com a justificativa e devolve o resultado de cada uma
- [x] Lista com atividade de outro processo: 404 e nenhuma validada; sem justificativa: 422
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add bulk activity validation route`

---

### T41: Aceitação do fluxo de documentos

**What**: Teste de ponta a ponta pela API com documentos sintéticos e IA e OCR reais ou falsos conforme o caso.
**Where**: `backend/tests/integration/api/test_documents_flow.py`
**Depends on**: T40
**Reuses**: `tests/support/synthetic_docs.py`
**Requirement**: EXT-06, PIPE-10, CLS-03, VINC-04, REV-03, edge case de lote com documentos sem item

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Envia PDF com texto, PDF digitalizado e PNG, processa com o executor e confere o texto por página e o método
- [x] Declaração de banca vira atividade rascunho vinculada; validar em lote muda o total da pontuação; um documento sem item e a coorientação de TCC ficam sem atividade
- [x] Em todas as respostas e nos logs capturados a chave da MariTalk não aparece
- [x] Build gate passa; 6+ testes

**Tests**: integration
**Gate**: build

**Commit**: `test(documents): add end to end documents flow acceptance test`

---

### T42: Cliente com envio de arquivos

**What**: `api/client.ts` aceita corpo `FormData` mantendo credenciais e CSRF.
**Where**: `frontend/src/api/client.ts`
**Depends on**: None (fase anterior concluída)
**Reuses**: `request` existente
**Requirement**: TELA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Corpo `FormData` é enviado sem forçar `Content-Type` e com `X-CSRF-Token`
- [x] Chamadas JSON existentes continuam iguais (testes existentes sem alteração)
- [x] Gate quick (frontend) passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): support file uploads in the api client`

---

### T43: Envio de CSV usa o cliente

**What**: `ScoringAdminForms` passa a usar a opção `FormData` do cliente.
**Where**: `frontend/src/components/ScoringAdminForms.tsx`
**Depends on**: T42
**Reuses**: `api/client.ts`
**Requirement**: TELA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O envio do CSV continua funcionando e mostra os erros por linha
- [x] Não há `fetch` direto no componente
- [x] Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `refactor(frontend): use the api client for csv upload`

---

### T44: Navegação com Etapas 2 e 3

**What**: `StepNav` habilita as Etapas 2 e 3 e liga a `processos/:id/documentos` e `processos/:id/atividades`.
**Where**: `frontend/src/components/StepNav.tsx`
**Depends on**: T43
**Reuses**: `StepNav` existente
**Requirement**: TELA-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Etapas 1 a 4 habilitadas, etapas 5 a 9 desabilitadas com "em breve"
- [x] Links corretos para cada etapa
- [x] Teste de etapas ajustado de forma explícita, sem enfraquecer; Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): enable steps 2 and 3 in the process navigation`

---

### T45: Área de envio

**What**: Componente de arrastar e soltar e seletor, com resultado por arquivo.
**Where**: `frontend/src/components/UploadDropzone.tsx`
**Depends on**: T44
**Reuses**: `FieldError`
**Requirement**: TELA-02, TELA-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Aceita vários arquivos por arrastar e soltar e pelo seletor
- [x] Resposta com 201, 409 e 422: o motivo aparece ao lado do arquivo, sem impedir os demais
- [x] Gate quick (frontend) passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add document upload dropzone`

---

### T46: Lista de documentos

**What**: Lista com nome, tipo, tamanho, status, categoria sugerida, confiança e ações.
**Where**: `frontend/src/components/DocumentList.tsx`
**Depends on**: T45
**Reuses**: `AlertList`
**Requirement**: TELA-02, TELA-04, TELA-07, TELA-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Mostra as colunas e as ações visualizar, baixar, substituir, excluir (com justificativa), reprocessar e classificar
- [x] Documento `EXTRAIDO_SEM_IA` mostra o aviso da IA indisponível com a orientação do cadastro manual
- [x] Documento com aviso `SEM_ITEM_DE_PONTUACAO` mostra o aviso e a ação "criar atividade deste documento"
- [x] Em 360 px vira cartões; Gate quick (frontend) passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add document list`

---

### T47: Visualizador de documento

**What**: PDF e imagem em linha, texto por página com o método e a confiança, JSON extraído em somente leitura e alertas.
**Where**: `frontend/src/components/DocumentViewer.tsx`
**Depends on**: T46
**Reuses**: -
**Requirement**: TELA-04, REV-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Mostra o arquivo em linha e a lista de páginas com método (`TEXTO` ou `OCR`) e confiança
- [x] O JSON extraído é somente leitura
- [x] Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add document viewer`

---

### T48: Lista de revisão das atividades

**What**: Atividades com origem, status, item, pontuação potencial, documentos vinculados (nome e página) e ações.
**Where**: `frontend/src/components/ActivityReviewList.tsx`
**Depends on**: None (fase anterior concluída)
**Reuses**: `ScoringTable`, `ActivityForm`
**Requirement**: TELA-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Mostra origem, status, grupo e item, pontuação potencial e os documentos vinculados com a página
- [x] Ações validar, rejeitar, editar com justificativa, vincular documento e validar as selecionadas (uma justificativa)
- [x] Em 360 px vira cartões; Gate quick (frontend) passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add activity review list`

---

### T49: Página da Etapa 2

**What**: Reúne a área de envio, a lista, o visualizador e a atualização automática a cada 3 segundos enquanto há documento pendente ou em processamento.
**Where**: `frontend/src/pages/ProcessDocuments.tsx`
**Depends on**: T48
**Reuses**: `UploadDropzone`, `DocumentList`, `DocumentViewer`
**Requirement**: TELA-01, TELA-02, TELA-03, TELA-04, TELA-05, TELA-07, TELA-08, TELA-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A lista atualiza sozinha a cada 3 s enquanto há `PENDENTE` ou `PROCESSANDO` e para quando não há (relógio simulado)
- [x] Todas as ações funcionam e a lista recarrega
- [x] "Criar atividade deste documento" abre o formulário com o documento vinculado
- [x] Rota `processos/:id/documentos`; Gate quick (frontend) passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add step 2 documents page`

---

### T50: Página da Etapa 3

**What**: Lista de atividades com revisão, vínculos e validação em lote, ligada à Etapa 4.
**Where**: `frontend/src/pages/ProcessActivities.tsx`
**Depends on**: T49
**Reuses**: `ActivityReviewList`
**Requirement**: TELA-06, TELA-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Carrega as atividades do processo e atualiza após validar, rejeitar ou editar
- [x] Validar as selecionadas chama a rota em lote com uma justificativa
- [x] Rota `processos/:id/atividades`; Build gate passa (lint, testes, build); 6+ testes

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): add step 3 activities page`

---

### T51: Imagem do backend com Tesseract

**What**: `Dockerfile` instala `tesseract-ocr` e `tesseract-ocr-por`.
**Where**: `backend/Dockerfile`
**Depends on**: None (fase anterior concluída)
**Reuses**: `Dockerfile` existente
**Requirement**: PIPE-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A imagem constrói e `tesseract --list-langs` lista `por`
- [x] O contêiner continua rodando como usuário sem privilégios
- [x] `./scripts/smoke_backend.sh` passa
- [x] Build gate passa

**Tests**: e2e
**Gate**: build

**Commit**: `build(backend): install tesseract with portuguese data in the image`

---

### T52: Limite de envio de 120 MB

**What**: `client_max_body_size 120m` no nginx do compose; teste de fumaça com envio de 25 MB.
**Where**: `nginx/nginx.conf`
**Depends on**: T51
**Reuses**: `scripts/smoke.sh`
**Requirement**: DOC-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Envio de um corpo de 25 MB chega ao backend (não recebe 413 do nginx)
- [ ] Envio acima de 120 MB recebe 413
- [ ] `./scripts/smoke.sh` passa; Build gate passa

**Tests**: e2e
**Gate**: build

**Commit**: `build(nginx): raise upload body limit to 120 MB`

---

### T53: Script de corpus real

**What**: `scripts/process_corpus.py <pasta> --start AAAA-MM-DD --end AAAA-MM-DD --table <nome> --professor <nome> [--siape N]` processa os arquivos pelo analisador e gera relatório JSON sem imprimir texto; modo `--fake-ai` para teste. Os dados pessoais entram só pela linha de comando.
**Where**: `scripts/process_corpus.py`
**Depends on**: T52
**Reuses**: `DocumentAnalyzer`
**Requirement**: ACC-01, ACC-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sobre uma pasta sintética com `--fake-ai` e o interstício 2024-11-23 a 2026-11-23: relatório por arquivo com método por página, status, tipo, item sugerido ou `SEM_ITEM_DE_PONTUACAO`, dentro ou fora do interstício, quantidade de atividades, avisos e tempo
- [ ] A saída e o relatório não contêm texto dos documentos
- [ ] `Documentos/` e `Modelos/` estão no `.gitignore` e a suíte automática não executa o script
- [ ] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scripts): add local corpus processing script`

---

### T54: Teste de contrato com a MariTalk real

**What**: Teste marcado `maritalk_live`, que só roda com credencial e não roda por padrão.
**Where**: `backend/tests/live/test_maritalk_live.py`
**Depends on**: T53
**Reuses**: `test/test_maritalk.py`
**Requirement**: ACC-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O marcador `maritalk_live` está registrado e a suíte padrão o exclui
- [ ] Com credencial válida, extrai de um texto sintético com schema estrito e recebe `null` para o dado ausente
- [ ] Build gate passa

**Tests**: integration
**Gate**: build

**Commit**: `test(live): add opt-in maritalk contract test`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10

Phase 1:  T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
Phase 2:  T9 → T10 → T11 → T12 → T13 → T14 → T15
Phase 3:  T16 → T17 → T18 → T19 → T20 → T21
Phase 4:  T22 → T23 → T24 → T25
Phase 5:  T26 → T27 → T28 → T29
Phase 6:  T30 → T31 → T32 → T33 → T34
Phase 7:  T35 → T36 → T37 → T38 → T39 → T40 → T41
Phase 8:  T42 → T43 → T44 → T45 → T46 → T47
Phase 9:  T48 → T49 → T50
Phase 10:  T51 → T52 → T53 → T54
```


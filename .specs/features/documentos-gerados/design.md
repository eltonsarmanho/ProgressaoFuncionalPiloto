# Documentos Gerados Design

**Spec**: `.specs/features/documentos-gerados/spec.md`
**Status**: Draft

Lições confirmadas aplicáveis: nenhuma (`lessons.py list --status confirmed` vazio). Decisões ativas respeitadas: AD-001 (camadas e teste de arquitetura), AD-005 (MariTalk), AD-006 (resultado calculado, sem tabela de resultados), AD-008 (executor em processo, estados no banco), AD-009 (saída da IA não confiável). Decisões novas deste design, gravadas em `STATE.md`: AD-011 a AD-015.

**Revisão de 2026-11-18 (decisões do usuário aplicadas):** (1) a etapa nova é a Etapa 5; (2) PNG de origem aceito até 12 megapixels (`IMAGEM_GRANDE_DEMAIS`), alerta `PAGINA_RASTERIZADA`, Tabela de 7 colunas com o grupo em faixa; (3) licença AGPL do PyMuPDF aceita; (4) a conclusão do processo exclui os documentos de entrada (história DEL); (5) a redação por IA roda como tarefa em segundo plano com estado na seção (sem `proxy_read_timeout`); (6) todas as versões geradas ficam, com o tamanho no histórico.

---

## Architecture Overview

Três geradores compartilham um mesmo fluxo: o pedido cria uma linha de geração no estado `GERANDO`, o executor em processo a pega, lê o processo numa única unidade de trabalho, monta o documento a partir de **funções puras do domínio** (modelo da Tabela, plano do Comprovante, seções do Relatório) e entrega o modelo a **adaptadores de infraestrutura** que escrevem DOCX (python-docx), PDF (reportlab) e o PDF montado com as páginas originais (PyMuPDF). O arquivo vai para o armazenamento por arquivo temporário e renomeação; só então a linha vira `PRONTO` com versão numerada, hash e instantâneo. O resultado da pontuação é sempre recalculado na hora (AD-006) pelo mesmo caminho da tela.

```mermaid
graph TD
    UI[Etapa 5 Documentos gerados - React] -->|/api| API[presentation: geração, rascunho, arranjo, ordem do dossiê, conclusão]
    API --> RG[application: RequestGeneration]
    API --> RD[application: ReportDraft, ComprovanteLayout]
    API --> CC[application: ConcludeProcess + PurgeInputDocuments]
    CC --> OR
    CC --> DB
    RG --> DB[(postgres: generated_documents, generated_files, report_wording_jobs)]
    W[executor em segundo plano: thread única] -->|claim GERANDO| RUN[application: RunGeneration]
    W -->|claim GERANDO| RW[application: RunWording]
    RW --> AIW
    RUN --> IN[application.services: load_generation_inputs]
    IN --> SC[compute_process_score - mesmo caminho da tela]
    RUN --> DOM[domain.rules: table_document, comprovante_plan, report_draft, report_grounding]
    RUN --> WR[porta DocumentWriter: python-docx + reportlab]
    RUN --> AS[porta ComprovanteAssembler: PyMuPDF + reportlab]
    RUN --> FS[(GeneratedFileStorage: storage/generated)]
    RD -->|enfileira| DB
    AIW[porta ReportWriter: adaptador MariTalk]
    RD --> DOM
    AS --> OR[(FileStorage: originais; só a conclusão os apaga)]
```

### Abordagens consideradas (arquitetura de geração)

| Abordagem | Resumo | Veredito |
| --- | --- | --- |
| **A. Linha de geração própria + executor existente com um segundo runner** | Tabela `generated_documents` guarda estado e versão; o `DocumentWorker` ganha um runner de geração além do de OCR | **Recomendada**: semântica de `INTERROMPIDA` difere da de `processing_jobs`, que reenfileira (AD-008); a thread única continua única |
| B. Reusar `processing_jobs` com `document_id` anulável | Uma tabela de tarefas para tudo | Descartada: `document_id` é obrigatório com `ON DELETE CASCADE` e a recuperação reenfileira até 3 vezes; a spec exige `FALHOU/INTERROMPIDA` sem repetir (VER-08) |
| C. Gerar dentro da requisição | Síncrono | Descartada: o Comprovante de 400 páginas e a espera do nginx tornam a requisição frágil (CMP-11, VER-04) |

### Abordagens consideradas (redação em segundo plano e conclusão)

| Abordagem | Resumo | Veredito |
| --- | --- | --- |
| **A. Tabela própria `report_wording_jobs` e um terceiro runner no mesmo executor** | Uma linha por pedido de redação, com estado, partida e código; índice parcial único por (processo, seção) em `GERANDO` | **Recomendada**: o estado vive na seção, a recuperação na partida repete o padrão de `generated_documents` e a thread continua única (AD-008) |
| B. Generalizar `generated_documents` com `kind = REDACAO` | Uma só tabela de tarefas | Descartada: a linha tem versão numerada, hash e gatilho de imutabilidade; a redação não é um documento entregue e o acoplamento criaria colunas anuláveis em excesso |
| C. Thread separada para a redação | A MariTalk não bloqueia a geração | Descartada: contraria a AD-008; o custo é a espera de até 60 s de uma geração que chega durante uma redação (ver Risks) |
| **D. Conclusão síncrona, arquivo a arquivo** | `POST` que remove os arquivos e responde com as contagens | **Recomendada**: `unlink` é local e rápido; cada documento tem a própria transação; o estado parcial é o do banco e do disco, sem tarefa nova |
| E. Conclusão como tarefa em segundo plano | Estado GERANDO na conclusão | Descartada: acrescenta um estado, polling e recuperação por uma operação de milissegundos |

---

## Pesquisa de bibliotecas (medida, com dados sintéticos)

Máquina de desenvolvimento (16 núcleos, Python 3.12.3), venv temporário fora do repositório, PyMuPDF 1.28.2 (o pino atual) e Pillow 13.0.0. Os tempos valem como ordem de grandeza: a VM tem 1 CPU com `cpus: 0.75`. Os picos são `ru_maxrss` do processo inteiro, incluindo o interpretador e as importações. O contêiner da VM não foi medido (sem acesso à VM).

### (a) DOCX

| Abordagem | Dependências novas (instaladas) | Resultado do protótipo | Veredito |
| --- | --- | --- | --- |
| **python-docx 1.2.0** (MIT, 2025-06-16) | `lxml` 6.1.3 (12 MB, roda por wheel `manylinux`, sem compilador) e a própria lib (3 MB); `typing_extensions` já vem com o pydantic | Tabela de 140 linhas em 0,19 s, 40 KB, pico 34 MB. Linha de título repetida (`w:tblHeader`), rodapé "Página X de Y" por campos `PAGE` e `NUMPAGES`, acentos corretos. Convertido por LibreOffice (só no meu ambiente, para conferir o desenho) o arquivo abre em 4 páginas, com o cabeçalho repetido | **Recomendada** |
| DOCX montado à mão (`zipfile` + XML) | Nenhuma | Não prototipado | Descartada: o Word é estrito com o XML e não há como validar sem o Word; o ganho é evitar 15 MB |
| `docxtpl` (modelo `.docx` com Jinja) | python-docx, jinja2 | Não prototipado | Descartada: o modelo recebido é um texto de exemplo sem marcadores; o formato por seção vem da configuração |

Armadilhas encontradas e tratadas no design: com `autofit` o python-docx ignora a largura das células e o LibreOffice divide as colunas em partes iguais (a Tabela saiu com 12 páginas em vez de 4). Cabe gravar a largura em `tblGrid` (`table.columns[i].width`) e `w:tblLayout fixed`. Não há API para campo de página: o rodapé usa `fldChar` e `instrText`. **Incerteza**: não testei a abertura no Word; só em LibreOffice.

### (b) PDF da Tabela e do Relatório, sem LibreOffice

| Abordagem | Dependências novas | Medido (Tabela, 8 colunas, quebra de página) | Veredito |
| --- | --- | --- | --- |
| **reportlab 5.1.0** (BSD, 2026-10-22; última 4.x: 4.5.1, 2026-05-12) | `charset-normalizer` (pequena); 9 MB instalados; Pillow já existe | 140 linhas: 0,13 s, pico 32 MB, PDF de 60 KB. 1000 linhas: 0,92 s, 52 MB. `Table(repeatRows=1)` repete o cabeçalho, larguras em porcentagem, "Página N de M" por segundo passe do canvas, fonte TTF embutida em subconjunto, acentos corretos. Relatório (A4, margens do modelo, parágrafos justificados, marcadores): 0,03 s, 44 KB | **Recomendada** |
| PyMuPDF `Story` (HTML e CSS) | Nenhuma | 140 linhas: 0,07 s, pico 57 MB (inclui a importação do PyMuPDF). **Não repete o cabeçalho** da tabela; largura de coluna só em pontos absolutos (`%` e `<colgroup>` são ignorados); o cabeçalho precisou ser redesenhado a cada página por `pagefn` com a altura medida | Descartada: funciona, mas com contorno frágil; seria código de layout próprio |
| fpdf2 2.9.0 (LGPL-3.0, 2026-10-29) | `fonttools` (29 MB instalados) | 140 linhas: 0,38 s, pico 55 MB; 1000 linhas: 2,35 s. Repete o cabeçalho e tem `{nb}` | Descartada: mais lenta, 3 vezes mais pesada em dependências e licença LGPL sem ganho |

Recomendação: reportlab para tudo que é gerado (Tabela, Relatório, capa, sumário e separadores do Comprovante) e PyMuPDF só para juntar páginas originais. Efeito na imagem do backend: cerca de +24 MB (lxml, python-docx, reportlab, charset-normalizer), sem pacote `apt`. **Incerteza**: reportlab 5.1.0 tem 27 dias; a tarefa de pino roda a suíte em 5.1.0 e, se algo falhar, cai para 4.5.1, que tem a mesma API usada aqui.

### Fonte

A imagem `python:3.12-slim` não tem fontes. O PDF usa **Liberation Serif** (Regular, Bold, Italic, BoldItalic; SIL OFL 1.1, 1,5 MB), com métricas do Times New Roman, versionada em `backend/app/infrastructure/documents/fonts/` com o texto da licença. As fontes do PyMuPDF (Base 14) só cobrem Latin-1 e não servem para nomes com outros caracteres. O DOCX apenas nomeia "Times New Roman", que o Word resolve.

### Comprovante: memória e conteúdo original (protótipo)

Fontes sintéticas: 400 páginas "digitalizadas" (um JPEG por página, 1240 x 1754 px) em 10 PDFs.

| Cenário | Saída | Pico do processo | Acima da linha de base |
| --- | --- | --- | --- |
| 400 páginas, 126 KB por página, acumulando num documento só | 50 MB | 127 MB | +73 MB |
| 400 páginas, 224 KB por página, acumulando | 88 MB | 179 MB | +125 MB |
| 400 páginas, 126 KB, **salvamento incremental a cada 25 páginas** | 50 MB | 62 MB | +8 MB |
| 400 páginas, 224 KB, incremental | 88 MB | 65 MB | +11 MB |
| **Fluxo completo** (capa, sumário de 2 páginas, 8 separadores, 400 originais, 411 páginas), incremental | 50 MB (88 MB no caso pesado) | **74 MB (75 MB)** | +11 MB |

A linha de base (54 a 63 MB) é só `import pymupdf` mais reportlab; no backend real o PyMuPDF já está carregado (repouso de 96 MB no `STATE.md`). Tempo do fluxo completo: 1,1 s. O limite da spec (320 MB) fica muito acima. `store_shrink(100)` entre páginas não mudou nada nas medições (as imagens JPEG passam sem decodificar); fica como seguro barato para o caminho de PNG.

Fora do caminho comum, medido:

| Caso | Resultado |
| --- | --- |
| Página PDF de 52 megapixels (JPEG de 5 MB) | pico +10 MB, 0,0 s: anexa sem rasterizar (edge case da spec confirmado) |
| JPEG de 40 megapixels como origem | +17 MB, 0,0 s: o JPEG entra sem decodificar |
| **PNG de 12 megapixels** como origem | **+103 MB** |
| **PNG de 40 megapixels** como origem | **+324 MB**, 6,1 s: o PyMuPDF decodifica o PNG inteiro |

O custo do PNG é linear (cerca de 8 MB por megapixel). Esse número decide o limite de imagem (ver Tech Decisions).

Conferência de que o conteúdo original não muda (400 páginas e amostras de 50 a 60 por rodada):

- Os bytes das imagens embutidas na saída são idênticos aos da origem (nenhuma recompressão), em todas as páginas amostradas.
- A área do original, renderizada a 2x, é **idêntica pixel a pixel** à página de origem; o texto extraído é igual; a faixa leva o número ("Comprovante p. N") e a numeração, em ordem, confere nas 411 páginas; as entradas do sumário apontam as páginas certas.
- Primeira versão falhou: a linha divisória de 0,5 pt desenhada em `y = h` invadia 0,25 pt do original (uma linha de pixels diferente, delta até 63). A faixa passa a começar em `y = h` sem borda e a divisória fica dentro dela (`y = h + 0,5`). Com isso o teste de igualdade passa.
- `show_pdf_page` não preserva três coisas, todas verificadas:
  1. **`/Rotate`**: a página rotacionada sai sem rotação e deformada. Correção: copiar a página para um PDF temporário de uma página e chamar `remove_rotation()`; fica idêntica pixel a pixel em 90, 180 e 270 graus.
  2. **Anotações e campos** (carimbo, texto livre, destaque, campo preenchido, aparência de assinatura): somem. Correção: no mesmo PDF temporário, `bake(annots=True, widgets=True)` antes de anexar. A página sai visualmente igual (diferença máxima de 1 nível de cinza em 2 590 bytes de uma região de anotação); perde a interatividade, o que não importa num Comprovante.
  3. **Página rotacionada e com CropBox menor que a MediaBox** (combinação rara): `remove_rotation()` perde o recorte e o ajuste que tentei não ficou idêntico. Fallback do design: rasterizar essa página a 200 dpi em JPEG qualidade 92 e emitir o alerta `PAGINA_RASTERIZADA` com a página; o conteúdo visível é preservado, a página deixa de ser vetorial. Uma tarefa conta quantas páginas do corpus real caem nesse caso, por script local.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --- | --- | --- |
| `calculate`, `ScoringResult`, `ScoringRow`, `Counters`, `Alert` | `backend/app/domain/rules/scoring_engine.py`, `process_verification.py` | Entrada do modelo da Tabela; o total só soma `VALIDADA` (`scoring_engine.py:240`, `_subtotals`), então a Tabela e a tela batem por construção |
| `CalculateProcessScore` | `backend/app/application/use_cases/scoring.py:646` | O corpo vira a função `compute_process_score(uow, process) -> ProcessScore`; o caso de uso a chama com o ator, o executor a chama sem ator (o acesso já foi checado no pedido) |
| `AccessPolicy`, `AuditService` | `backend/app/application/services/` | 404 fora do acesso; auditoria só com identificadores |
| `ProcessStatus`, `can_transition`, `ChangeProcessStatus`, `evaluate` | `backend/app/domain/entities/process.py:12-35`, `backend/app/application/use_cases/processes.py:182-215` | A conclusão reaproveita `can_transition` (papel e dono), `_readable`, `_check_version` e o registro de auditoria `STATUS`; a rota genérica passa a recusar o alvo CONCLUIDO |
| `FileStorage.delete` (idempotente), `FileStorage.path`, `DeleteDocument` | `backend/app/infrastructure/storage/local_storage.py:62`, `backend/app/application/use_cases/documents.py:560-602` | A exclusão dos arquivos usa `delete` e `path(...).exists()`; o padrão "transação do banco, depois o arquivo" do `DeleteDocument` é invertido aqui (arquivo primeiro, banco depois, ver Fluxos) |
| `ExtractionRepository.replace_pages`, `EvidenceRepository`, `DocumentRepository.update` | `backend/app/domain/repositories/ports.py:226-327` | Ganham `delete_pages(document_id)`, `clear_excerpts_for_document(document_id)` e `mark_file_deleted(document_id, now)` |
| `DocumentWorker`, `claim_next` com `SKIP LOCKED` | `backend/app/infrastructure/jobs/worker.py:43`, `repositories.py:1085` | Mesma thread; ganha um segundo runner de geração |
| `extraction_runs` e seu gatilho de imutabilidade | `backend/alembic/versions/0003_documents.py:90` | Mesmo padrão para `generated_documents` e `generated_files` |
| `LocalFileStorage` | `backend/app/infrastructure/storage/local_storage.py` | Padrão de permissões 0700/0600 e nome interno aleatório; o regex atual só aceita `pdf/jpg/png` (linha 15), então nasce `LocalGeneratedStorage` ao lado |
| `ActivityEvidence`, `EvidenceRepository` | `ports.py`, `repositories.py:1146` | Origem das páginas; ganha `list_for_activities(ids)` para evitar N+1 |
| `MariTalkExtractor` (`_post`, tentativa com modelo reserva) | `backend/app/infrastructure/ai/maritalk.py` | O envio HTTP vira `MariTalkClient` compartilhado; `MariTalkReportWriter` é um segundo adaptador |
| `mask_identifiers`, `normalize_title`, `numerals_from_words`, `date_in_text` | `backend/app/domain/rules/{masking,scoring_periods,number_words,grounding}.py` | Máscara da descrição enviada à IA e a normalização da conferência da redação |
| `DocAlertCode`, `Alert`, enums `StrEnum` | `domain/entities/document.py` | Novo `GenerationCode` e alertas no mesmo formato |
| Erros de domínio e mapeamento HTTP | `domain/errors.py`, `presentation/errors.py` | Novo `GenerationRefused(code, message)` mapeado para 422 com `{field, code, message}` (a mesma forma que `documents.py` já usa) |
| `StepNav`, `AlertList`, `FieldError`, `api/client.ts`, `labels.ts` | `frontend/src/` | A etapa nova segue as telas 2 a 4 |
| Polling a cada 3 s | `frontend/src/pages/ProcessDocuments.tsx:13,102` | Extraído para `hooks/usePolling.ts`, usado pela etapa nova |
| Fixtures de integração, `synthetic_docs.py` | `backend/tests/integration/`, `backend/tests/support/` | PostgreSQL efêmero (AD-004); PDFs e imagens sintéticos existentes servem de origem |

### Integration Points

| System | Integration Method |
| --- | --- |
| `functional_processes`, `activities`, `activity_evidences`, `documents` | Só leitura na geração; `generated_documents.process_id` com FK sem cascata. A conclusão escreve em `documents` (coluna nova `file_deleted_at`), apaga `document_pages` e esvazia `activity_evidences.excerpt` |
| Pontuação | `compute_process_score` e `ScoringResult` |
| MariTalk | Porta `ReportWriter`; `MARITALK_*` já existentes |
| nginx | Nada a mudar: a redação é tarefa em segundo plano e nenhuma requisição passa de poucos segundos (o limite de envio de 120 MB já está no ar) |
| Imagem do backend | `python-docx==1.2.0`, `lxml==6.1.3`, `reportlab==5.1.0` em `requirements.txt` |

---

## Components

### Domain: entidades

- **Purpose**: tipos e estados, sem dependência de framework.
- **Location**: `backend/app/domain/entities/{generated.py,report.py,comprovante.py,conclusion.py}`
- **Interfaces**:
  - `DocumentKind` (`TABELA`, `RELATORIO`, `COMPROVANTE`), `DocumentFormat` (`DOCX`, `PDF`), `GenerationState` (`GERANDO`, `PRONTO`, `FALHOU`) e `can_transition` (`GERANDO` para `PRONTO` ou `FALHOU`; nada mais)
  - `GeneratedDocument(id, process_id, kind, state, version_number, requested_by, requested_at, started_at, finished_at, error_code, error_message, snapshot, alerts, plan_hash, files)` e `GeneratedFile(format, internal_name, sha256, size_bytes)`
  - `WordingJob(id, process_id, section_key, state, requested_by, requested_at, started_at, finished_at, error_code, warnings)`, com o mesmo `GenerationState` e `can_transition`
  - `GenerationCode` e `GenerationAlertCode` (lista em Error Handling Strategy); `Gone(code)` em `domain/errors.py` (410), ao lado de `NotFound` e `Conflict`
  - `Conclusion`: `ConclusionPreview(files, bytes, artifacts: dict[DocumentKind, bool])` e `ConclusionResult(status, files_removed, files_pending, bytes_freed, alerts)`
  - `ReportTemplate` (página, linhas do cabeçalho, identificação, seções com `match`, `group_by`, formato da entrada), `ReportDraft(process_id, template_id, template_version, sections, version)`, `DraftSection(key, title, free_text, entries, warnings)`, `DraftEntry(activity_id, text, source: MODELO|IA|USUARIO, warnings)`
  - `ComprovanteLayout(process_id, activities: tuple[LayoutActivity, ...], base_evidence_keys, version)`, `LayoutActivity(activity_id, pages: tuple[LayoutPage, ...])`, `LayoutPage(document_id, page, repeat_justification)`

### Domain: regras puras

- **Purpose**: tudo que decide conteúdo, ordem e numeração; nada lê arquivo nem banco.
- **Location**: `backend/app/domain/rules/{table_document.py,comprovante_plan.py,report_draft.py,report_grounding.py,generation_snapshot.py,download_names.py,pt_format.py,conclusion_rules.py}`
- **Interfaces**:
  - `build_table_document(header, version, result, activities, comprovante_numbers, excluded) -> TableDocument`: 7 colunas (item "I.1", atividade, quantidade, pontos unitários, total, comprovante, status); o grupo vira uma faixa com o nome da tabela e o subtotal, também para grupos vazios (zero); seção de horas de PIT separada (TAB-05); contagens e alertas iguais aos do motor
  - `derive_layout(activities, evidences, documents) -> ComprovanteLayout`: ordem dos grupos e itens da tabela, e dentro do item por data (ARR-01)
  - `plan_comprovante(layout, activities, documents, toc_capacity) -> ComprovantePlan`: lista ordenada de páginas (`CAPA`, `SUMARIO`, `SEPARADOR`, `ORIGINAL`) com o número de cada uma, a primeira página de cada grupo, item e atividade, as remissões (mesma página em outra atividade, CMP-05) ou a repetição justificada (CMP-06), a atividade sem página (CMP-07) e o `plan_hash`. As verificações de limite (`COMPROVANTE_GRANDE_DEMAIS`) e de documento ausente (`ORIGINAL_INDISPONIVEL`) saem do plano como erros tipados
  - `layout_staleness(layout, activities, evidences) -> Staleness`: atividade validada que saiu, revalidada ou mudou de item, ou vínculo novo (ARR-08); o arranjo mostra o aviso e a geração usa só as atividades atuais
  - `propose_draft(template, activities, group_map) -> ReportDraft` e `reconcile_draft(draft, activities) -> ReportDraft`: distribui pelo mapa de grupo para seção, ordena e acrescenta ao fim as atividades novas; o texto de cada entrada é o texto-modelo (`template_text`); o que o usuário já editou nunca é tocado (REL-07)
  - `check_wording(wording, facts, vocabulary) -> WordingCheck(accepted, reasons)`: ver "Redação pela MariTalk"
  - `build_snapshot(...) -> dict` e `plan_hash(plan) -> str` (SHA-256 do plano em JSON canônico)
  - `check_conclusion(ready_kinds, active_operations) -> ConclusionCheck`: `ARTEFATOS_PENDENTES` com os tipos que faltam (DEL-01) e `OPERACAO_EM_ANDAMENTO` (DEL-02), sem ler banco; `summarize_purge(documents) -> ConclusionPreview` (conta só documentos sem `file_deleted_at`, soma `size_bytes`; DEL-03); `purge_outcome(removed, failed, bytes) -> ConclusionResult` com `EXCLUSAO_PARCIAL` quando há pendentes (DEL-08)
  - `download_name(kind, fmt, interstice, version) -> str`: por exemplo `Tabela_de_Pontuacao_2020-2024_v2.pdf`, sem o nome do docente (VER-03)
  - `pt_format`: datas `dd/mm/aaaa`, decimais com vírgula, "1º Período de 2023"
- **Dependencies**: stdlib e as regras de pontuação existentes
- **Reuses**: `ScoringResult`, `normalize_title`, `numerals_from_words`, `Interstice`, `ProcessStatus`
- **Regra do plano**: `plan_comprovante` usa só metadados (identificador do documento, número de páginas, título e ordem); nunca abre arquivo. Por isso a Tabela continua mostrando a numeração do Comprovante depois que os originais foram excluídos

### Application: casos de uso

- **Location**: `backend/app/application/use_cases/{generated_documents.py,report_draft.py,comprovante_layout.py}` e `application/services/generation_inputs.py`
- **Interfaces**:
  - `load_generation_inputs(uow, process) -> GenerationInputs`: processo, docente, unidade, `ProcessScore`, atividades `VALIDADA` com grupo e item, vínculos por atividade, documentos (nome original, mime, páginas, nome interno), contagem do que fica de fora e por quê. Uma unidade de trabalho de leitura; a renderização roda sem conexão aberta (como `ProcessDocument`)
  - `RequestGeneration.execute(actor, process_id, kind) -> GeneratedDocument`: confere acesso (404), tabela escolhida (`TABELA_NAO_ESCOLHIDA`), atividades (`SEM_ATIVIDADES_VALIDADAS`), descrição (`ATIVIDADE_SEM_DESCRICAO`, só Relatório), `ORIGINAIS_EXCLUIDOS` (só Comprovante, quando algum documento tem `file_deleted_at`), limites e plano (só Comprovante, com `IMAGEM_GRANDE_DEMAIS`), espaço livre em disco; cria a linha `GERANDO` (o índice parcial único devolve 409 `GERACAO_EM_ANDAMENTO` sem corrida, VER-04) e audita. Retorna 202
  - `RunGeneration.execute(generation_id)`: o executor; monta o modelo, escreve em arquivo temporário, calcula o hash, renomeia, e numa transação grava a versão, os arquivos, o instantâneo e a auditoria. Falha: apaga temporários e marca `FALHOU` com código e mensagem fixa por código, sem texto de documento (VER-05)
  - `RecoverInterruptedGenerations.execute()`: na partida, toda linha `GERANDO` com `started_at` preenchido, em `generated_documents` e em `report_wording_jobs`, vira `FALHOU` com `INTERROMPIDA` e auditoria (VER-08, REL-14); a linha ainda não iniciada continua na fila; temporários `.tmp-*` e arquivos sem linha são removidos
  - `ListGeneratedDocuments`, `GetGeneratedDocument`, `DownloadGeneratedFile` (audita `operation: DOWNLOAD`, como `DownloadDocument`)
  - `GetReportDraft`, `SaveReportEntry`, `SaveReportSection`, `MoveReportEntry`
  - `RequestSectionWording.execute(actor, process_id, section_key) -> WordingJob`: confere acesso, processo gravável, seção existente; grava o rascunho se ainda só existe a proposta (`version` 1); cria a linha `GERANDO` (o índice parcial único devolve 409 `REDACAO_EM_ANDAMENTO`, REL-13) e audita; retorna 202. `RunWording.execute(job_id)` é o runner: lê os campos da seção, chama a porta `ReportWriter` com o prazo de 60 s, passa o resultado por `check_wording` e aplica o texto às entradas que continuam sem fonte `USUARIO`; termina em `PRONTO` (com `REDACAO_INDISPONIVEL` ou `REDACAO_REJEITADA` nos avisos da seção, REL-04, REL-05) ou em `FALHOU/ERRO_INTERNO` (REL-15). `ListWordingJobs` devolve o último job por seção, para a consulta de 3 s (UIG-08)
  - `GetConclusionPreview.execute(actor, process_id) -> ConclusionPreview` (DEL-03) e `ConcludeProcess.execute(actor, process_id, expected_version, confirm, justification) -> ConclusionResult` (DEL-01 a DEL-10, DEL-14, DEL-15); `PurgeInputDocuments` é o serviço de aplicação que remove arquivo, texto e trecho de um documento por vez e é idempotente. `ChangeProcessStatus` passa a levantar `Conflict("CONCLUSAO_EXIGE_EXCLUSAO")` para o alvo CONCLUIDO (DEL-14)
  - `GetComprovanteLayout`, `SaveComprovanteLayout` (bloqueio otimista, 404 para documento ou página fora do processo, ARR-05: o servidor recusa mover atividade de item)
- **Dependencies**: portas `DocumentWriter`, `ComprovanteAssembler`, `ReportWriter`, `GeneratedFileStorage`, `FileStorage`, `Clock`; `AccessPolicy`, `AuditService`
- **Reuses**: `compute_process_score`, `_ScoringUseCase._readable`, `ChangeProcessStatus` (verificação de `can_transition`, dono e versão, extraída para uma função do módulo `processes.py` que as duas classes usam)
- **Casos de uso existentes que mudam** (DEL-11, DEL-12): `DownloadDocument` (`documents.py:379`) e a leitura de texto de página levantam `Gone("ARQUIVO_EXCLUIDO")` quando `file_deleted_at` está preenchido; `ReprocessDocument` e `ReplaceDocument` recusam com o mesmo `Gone`; `DocumentOut` ganha `arquivo_excluido`

### Infrastructure: documentos

- **Location**: `backend/app/infrastructure/documents/`
  - `pdf_styles.py` (fonte, estilos, margens), `table_docx.py`, `table_pdf.py`, `report_docx.py`, `report_pdf.py` (implementam `DocumentWriter`), `front_matter.py` (capa, sumário e separadores com reportlab), `comprovante_assembler.py` e `source_pages.py` (PyMuPDF), `config_loader.py`, `fonts/`, `config/`
- **Interfaces**:
  - `DocumentWriter.write_table(model, fmt, target)` e `write_report(model, fmt, target)`
  - `ComprovanteAssembler.assemble(plan, resolver, target, on_progress) -> AssemblyResult(pages, size_bytes, alerts)`; `resolver` abre o original por `(document_id)` e devolve o caminho
  - `source_pages.attach(out, src, pno, number)`: o procedimento por página validado no protótipo: página sem rotação nem anotação vai direto por `show_pdf_page` na área `(0, 0, w, h)` da folha de altura `h + 24 pt`; com rotação ou anotações passa antes por um PDF temporário de uma página (`insert_pdf(annots=True, widgets=True)`, `bake`, `remove_rotation`); rotacionada com recorte cai no fallback rasterizado; imagem JPEG vira PDF por `convert_to_pdf` e entra pelo mesmo caminho; PNG acima de 12 megapixels é recusado antes de começar
  - Montagem: abre uma origem por vez, `store_shrink(100)` a cada página, salvamento incremental a cada 25 páginas (`save` na primeira, `saveIncr` depois, reabrindo o arquivo), e uma passada final de `garbage=3, deflate=True`. Páginas geradas (capa, sumário, separadores) entram com `insert_pdf` de um PDF de reportlab
  - Capa, sumário e separadores desenham linhas de altura fixa direto no canvas (sem fluxo), de modo que `toc_pages = ceil(linhas / LINHAS_POR_PAGINA)` é cálculo do domínio e o renderizador só confere (o protótipo mostrou que um fluxo de reportlab quebra linhas e erra a previsão; a solução de duas passadas funcionou, mas a capacidade fixa elimina a segunda passada)
- **Reuses**: PyMuPDF 1.28.2 e Pillow já instalados

### Infrastructure: armazenamento, IA, executor, banco

- **Armazenamento**: `LocalGeneratedStorage` em `storage/generated/{process_id}/{uuid4}.{docx|pdf}`, 0700/0600; `new_temp_path(process_id)` devolve `.tmp-{uuid}`; `commit(temp, ext) -> internal_name` por `os.replace` no mesmo diretório; nada é lido para a memória (o `FileStorage.save(bytes)` atual não serve para 60 MB)
- **MariTalk**: `MariTalkClient` (extraído de `maritalk.py`: cabeçalho, mapeamento de status, modelo reserva) com um prazo total por chamada; `MariTalkReportWriter` implementa `ReportWriter.draft(section_title, items) -> Mapping[UUID, str]`, levanta `AiWritingError(code)` com `REDACAO_INDISPONIVEL`; `temperature` 0, `response_format` JSON estrito `{items: [{id, texto}]}`, `max_tokens` 4000, prazo de 60 s, sem repetição. A chamada acontece no runner de redação, nunca dentro de uma requisição HTTP
- **Executor**: `DocumentWorker` recebe `runners: Sequence[Callable[[], bool]]`; `run_once` tenta primeiro a geração (o usuário espera por ela), depois a redação e por fim o OCR; `start()` chama os dois recuperadores. Um runner que levanta exceção fecha a linha como `FALHOU/ERRO_INTERNO`; o log leva só o tipo da exceção e os identificadores
- **Banco**: modelos e repositórios `generations`, `wording_jobs`, `report_drafts`, `comprovante_layouts` na `UnitOfWork`; migração `0005_generated_documents.py` (também acrescenta `documents.file_deleted_at`)

### Presentation

- **Location**: `backend/app/presentation/api/{generated_documents.py,report_draft.py,comprovante_layout.py,dossier.py}`, `presentation/schemas/generated.py`
- **Rotas** (todas sob `/api`, sessão e CSRF existentes; recurso fora do acesso responde 404):

| Método e caminho | Função | Respostas |
| --- | --- | --- |
| `POST /processes/{id}/generated-documents` `{kind}` | pede a geração | 202 com a linha `GERANDO`; 409 `GERACAO_EM_ANDAMENTO`; 422 com `code` |
| `GET /processes/{id}/generated-documents?kind=` | linhas em ordem decrescente (em andamento primeiro) com estado, versão, alertas, arquivos | 200 |
| `GET /generated-documents/{gid}` | uma linha, com o resumo do instantâneo (total, subtotais, contagens) | 200 / 404 |
| `GET /generated-documents/{gid}/files/{docx\|pdf}` | download do arquivo gravado | 200 `FileResponse`, `attachment`, `nosniff`, `ETag` com o SHA-256; 404 se a linha não é `PRONTO` ou o arquivo sumiu |
| `GET /processes/{id}/report-draft` | rascunho salvo ou proposta (`saved: false`, `version: 0`), com seções, entradas, avisos e atividades novas | 200 |
| `PUT /processes/{id}/report-draft/entries/{activity_id}` `{expected_version, text}` | edita o texto de uma atividade (fonte vira `USUARIO`) | 200 / 409 / 422 (mais de 20 000 caracteres) |
| `PUT /processes/{id}/report-draft/sections/{key}` `{expected_version, free_text}` | texto livre da seção | idem |
| `POST /processes/{id}/report-draft/entries/{activity_id}/move` `{expected_version, section_key}` | move a atividade (REL-08) | idem |
| `POST /processes/{id}/report-draft/sections/{key}/wording` | pede a redação da seção em segundo plano | 202 com o job `GERANDO`; 409 `REDACAO_EM_ANDAMENTO`; 409 `PROCESSO_SOMENTE_LEITURA` |
| `GET /processes/{id}/report-draft/wording` | último job de redação por seção (estado, código, avisos); a tela consulta a cada 3 s enquanto houver `GERANDO` e recarrega o rascunho quando termina | 200 |
| `GET /processes/{id}/comprovante-layout` | arranjo salvo ou derivado (`saved`, `version`, `stale`, `invalid`, `plan` com a numeração prevista) | 200 |
| `PUT /processes/{id}/comprovante-layout` `{expected_version, activities}` | salva o arranjo | 200 / 409 `VERSAO_DESATUALIZADA` / 404 / 422 |
| `GET /dossier-order` | lista ordenada da configuração, com a marca de "gerado pelo sistema" | 200 |
| `GET /processes/{id}/conclusion` | prévia da conclusão: arquivos, bytes, e se há versão `PRONTO` de cada tipo (DEL-03) | 200 / 404 |
| `POST /processes/{id}/conclusion` `{expected_version, confirmar, justificativa?}` | conclui e exclui os documentos de entrada | 200 com `status`, `arquivos_removidos`, `arquivos_pendentes`, `bytes_liberados` e alertas; 422 `ARTEFATOS_PENDENTES` ou `CONFIRMACAO_OBRIGATORIA`; 409 `OPERACAO_EM_ANDAMENTO` ou `VERSAO_DESATUALIZADA`; 404 |

  Rotas existentes que mudam: `POST /processes/{id}/status` com `CONCLUIDO` responde 409 `CONCLUSAO_EXIGE_EXCLUSAO`; `GET /documents/{id}/file` e a leitura de texto de página respondem 410 `ARQUIVO_EXCLUIDO` com a mesma forma de erro `{field, code, message}`; `GET /documents/{id}` e a listagem trazem `arquivo_excluido: true` e não trazem o texto das páginas.

  Os `GET` nunca gravam. A primeira gravação do rascunho ou do arranjo usa `expected_version: 0`. Processo concluído ou arquivado: gerar e baixar valem; as rotas de gravação respondem 409 `PROCESSO_SOMENTE_LEITURA`.

### Frontend

- **Location**: `frontend/src/pages/ProcessGenerated.tsx`; `frontend/src/components/{GeneratedBlock.tsx,ReportDraftEditor.tsx,ComprovanteLayoutEditor.tsx,DossierOrder.tsx}`; `frontend/src/hooks/usePolling.ts`; tipos em `api/types.ts`; rótulos em `labels.ts` (`GENERATION_STATE_LABELS`, `GENERATION_CODE_LABELS`)
- A etapa nova é a **Etapa 5 · Documentos gerados** (`processos/:id/gerados`), `STEP_TITLES[5]` e `stepPath(5)` em `StepNav.tsx`, `enabled` passa a incluir 5. A spec chama a etapa de "Etapa 4", mas a Etapa 4 é a Pontuação e a Etapa 2 já se chama Documentos (decisão do usuário, ver abaixo)
- `GeneratedBlock` (um por tipo): aviso de atividades fora (UIG-06), botão Gerar, estado, alertas em português (UIG-05), histórico com links por formato (links `<a href>`, o cookie de sessão basta no `GET`). Enquanto houver linha `GERANDO`, `usePolling` consulta a lista a cada 3 s e para em `PRONTO` ou `FALHOU` (UIG-04)
- `ReportDraftEditor`: uma seção por cartão, textarea por atividade com contador de 20 000, selo da fonte (modelo, IA, editado), avisos, "Pedir redação" por seção, "Mover para" por atividade; gravação por entrada com `expected_version`; 409 recarrega e avisa
- `ComprovanteLayoutEditor`: por grupo, item e atividade, a lista de páginas com subir, descer, remover, "Acrescentar página" (documento e número) e "repetir com justificativa"; aviso de arranjo desatualizado; mostra a numeração prevista do plano. Sem arrastar e soltar (nenhuma dependência nova, acessível por teclado)
- `DossierOrder`: lista da API, com os três documentos gerados marcados
- `ConcludeDialog` (`frontend/src/components/ConcludeDialog.tsx`), aberta pelo botão "Concluir e excluir documentos de entrada" no fim da Etapa 5: busca a prévia, lista o que falta (botão desligado com `ARTEFATOS_PENDENTES`), mostra "N arquivos, X MB serão excluídos de forma irreversível", exige marcar a confirmação e envia `confirmar: true` com `expected_version`; mostra `EXCLUSAO_PARCIAL` com o botão de tentar de novo e, no sucesso, recarrega o processo (somente leitura) e esconde "Gerar Comprovante"
- `ReportDraftEditor` usa `usePolling` por seção em `GERANDO` (3 s, UIG-08); o botão de redação fica desligado enquanto a seção gera, e as demais seções seguem editáveis. Ao terminar, recarrega o texto só da seção e mantém o texto digitado e não salvo das outras
- `DocumentList` e `DocumentViewer` mostram "Arquivo excluído" e não oferecem visualizar nem baixar quando `arquivo_excluido`; o cliente trata 410 como mensagem de tela, sem erro genérico
- 360 px: cartões empilhados, tabelas viram listas; teste estático como o de `styles.test.ts`

---

## Fluxos

### Geração (vale para os três tipos)

1. `RequestGeneration` valida e grava `GERANDO` (202). A resposta devolve o `id`; a tela passa a consultar.
2. O executor pega a linha mais antiga com `started_at IS NULL` (`SKIP LOCKED`), marca `started_at`, chama `RunGeneration`.
3. `load_generation_inputs` lê tudo numa unidade de trabalho e a fecha.
4. O modelo é montado por função pura: Tabela e Comprovante pelo mesmo `plan_comprovante` (a numeração da coluna "comprovante" da Tabela é a do plano atual; o `plan_hash` vai no instantâneo das duas versões e a tela avisa `NUMERACAO_DIVERGENTE` se o último Comprovante `PRONTO` tem outro `plan_hash`).
5. Escrita em `.tmp-*`; hash SHA-256 e tamanho; confere os 60 MB (Comprovante); renomeia.
6. Numa transação: `version_number = max(version_number) + 1` por (processo, tipo) (o índice único recusa corrida; uma nova tentativa), linhas de arquivo, instantâneo, alertas, `PRONTO`, auditoria. A versão só ganha número aqui: uma geração que falha não gasta número.
7. Falha em qualquer ponto: temporários e arquivos já renomeados são apagados, a linha vira `FALHOU` com código e mensagem fixa. Nenhum arquivo parcial (CMP-09, CMP-10, VER-05).

### Redação pela MariTalk, em segundo plano (REL-03 a REL-07, REL-12 a REL-15)

1. `POST .../sections/{key}/wording` cria a linha `GERANDO` em `report_wording_jobs` (gravando o rascunho se ele ainda é só proposta) e responde 202 na hora. Um segundo pedido da mesma seção enquanto há `GERANDO` recebe 409 `REDACAO_EM_ANDAMENTO` pelo índice parcial único (sem corrida).
2. O executor pega a linha mais antiga com `started_at IS NULL` (`SKIP LOCKED`), marca `started_at` e chama `RunWording`. A ordem do executor é geração, redação, OCR.
3. `RunWording` lê o rascunho e as atividades da seção numa unidade de trabalho e a fecha; separa as entradas cuja fonte não é `USUARIO` (o texto editado nunca vai à IA nem é reescrito).
4. Envia só, por atividade: `id` opaco, tipo do critério da tabela (descrição institucional), título, datas, carga horária, período letivo, quantidade, descrição **após `mask_identifiers`**. Nunca o texto das páginas, nunca o nome do docente, nunca SIAPE, nunca o `evidence_note`. Prazo total de 60 s, uma chamada por seção, sem repetição além do modelo reserva já previsto na AD-005. Erro, resposta fora do schema ou prazo: `REDACAO_INDISPONIVEL`, texto-modelo e job em `PRONTO` (o pedido não falhou, a seção saiu com aviso).
5. Cada texto passa por `check_wording` contra os campos enviados; reprovado, vale o texto-modelo e a seção ganha `REDACAO_REJEITADA` com o motivo (`NUMERO`, `DATA`, `NOME`, `VOCABULARIO`, `COMPRIMENTO`, `PALAVRA_PROIBIDA`).
6. Nova unidade de trabalho: trava a linha do rascunho (`SELECT ... FOR UPDATE`), aplica o texto só às entradas que continuam sem fonte `USUARIO` e **não incrementa `version`**: a aplicação por entrada não conflita com a edição do usuário, que também é por entrada (nenhum 409 espúrio e nenhuma perda de edição). O job vira `PRONTO` com os avisos; exceção inesperada vira `FALHOU/ERRO_INTERNO` e o rascunho fica como estava.
7. A tela consulta `GET .../report-draft/wording` a cada 3 s enquanto houver job `GERANDO` e, ao ver `PRONTO` ou `FALHOU`, recarrega a seção. Na partida, `RecoverInterruptedGenerations` fecha como `FALHOU/INTERROMPIDA` o job `GERANDO` que já tinha `started_at`; o ainda não iniciado segue na fila.

`check_wording` (AD-009, no sentido da geração): (i) todo número (inteiros, decimais, ordinais, datas em `dd/mm/aaaa` e por extenso, ano, período letivo) tem de aparecer nos campos enviados, comparados já normalizados (acentos, `numerals_from_words`, `hours_in_text`, `date_in_text`); (ii) todo nome próprio (palavra capitalizada fora do início da frase, ou sigla) tem de aparecer nos campos ou na lista `allowed_terms` da configuração (UFPA, "Universidade Federal do Pará" e a unidade); (iii) no máximo `max_new_words` palavras de conteúdo (5 letras ou mais) fora dos campos e do vocabulário permitido (verbos e conectivos formais da configuração e do texto-modelo); (iv) comprimento até duas vezes o texto-modelo mais 120 caracteres; (v) lista de palavras proibidas da configuração (avaliativas e de resultado: "objetivo", "resultado", "metodologia", "excelente", "relevante", "visando", "contribuindo"). **Limite honesto**: a conferência pega número, data, nome e palavra nova; uma afirmação qualitativa feita só de palavras já permitidas passaria. A revisão humana na tela e o prompt restritivo cobrem o resto, e o risco fica registrado (REL-12).

Texto-modelo determinístico: por seção, o `entry.line` ou `entry.fields` da configuração preenchido com os campos da atividade; a linha ou o campo que não tem valor não aparece (assunção da spec sobre campos que o sistema não tem). O campo "curso" do 1.1 e 1.2 só aparece se estiver no título ou na descrição, pois a atividade não guarda o curso.

### Comprovante

Página de saída = folha com a altura do original mais uma faixa de 24 pt. O original ocupa `(0, 0, w, h)` sem alteração; a faixa, abaixo, leva "Comprovante  p. N". Estrutura: capa (página 1, sem número impresso), sumário (grupos, itens e atividades; a atividade ocupa duas linhas: título e "origem: arquivo, p. X; Comprovante p. N a M" ou "ver p. N"), um separador por grupo (só o título, como no `Comprovante Documentos_2020_2024.pdf` recebido), originais. Todas as páginas geradas imprimem o próprio número no pé. O plano calcula tudo antes de escrever (CMP-04).

---

### Conclusão e exclusão dos documentos de entrada (DEL-01 a DEL-15)

`ConcludeProcess` não é tarefa em segundo plano (alternativa D): cada passo é local e rápido, e o estado parcial fica no banco e no disco.

1. **Verificação** (uma unidade de trabalho, depois fechada): `_readable` (404), `can_transition(EM_ANDAMENTO, CONCLUIDO, papel, dono)` e `expected_version` (409), a confirmação (`CONFIRMACAO_OBRIGATORIA`), `check_conclusion` com a última linha `PRONTO` de cada tipo (`ARTEFATOS_PENDENTES`) e a ausência de linha `GERANDO` em `generated_documents` e `report_wording_jobs` e de job `PENDENTE` ou `PROCESSANDO` em `processing_jobs` dos documentos do processo (`OPERACAO_EM_ANDAMENTO`). Processo já `CONCLUIDO`: devolve 200 com zeros, sem alterar nada (DEL-09).
2. **Exclusão, um documento por vez** (só os de `file_deleted_at` nulo): (a) `storage.delete` (arquivo ausente conta como removido); (b) numa unidade de trabalho própria: `delete_pages(document_id)`, `clear_excerpts_for_document(document_id)` (a coluna é `NOT NULL`, o trecho vira `''`) e `mark_file_deleted(document_id, now)`; commit. O arquivo sai antes do banco: uma queda entre os dois passos deixa um documento sem arquivo e sem marca, que a nova tentativa fecha (o inverso deixaria arquivo órfão ocupando espaço). Falha de `OSError` no passo (a) ou (b) conta o documento como pendente e segue para o próximo.
3. **Auditoria da tentativa**: `process` `UPDATE` com `operation: PURGE`, contagens de removidos e pendentes e bytes (nunca nomes) (DEL-10).
4. **Transição** (nova unidade de trabalho, com a linha do processo travada): relê os documentos; se algum ainda não tem `file_deleted_at` (pendente ou enviado durante a conclusão), responde com `EXCLUSAO_PARCIAL` sem mudar o status. Senão, `uow.processes.update(status=CONCLUIDO, expected_version)`, auditoria `STATUS` no formato de `ChangeProcessStatus` com as contagens, commit (DEL-07). A transição só acontece quando o disco e o banco concordam: depois do passo (a) confere-se `not path.exists()`.
5. Resposta: `status`, `arquivos_removidos`, `arquivos_pendentes`, `bytes_liberados` e os alertas. A prévia (`GET`) usa `summarize_purge` e custa uma consulta.

Depois da conclusão: o plano do Comprovante e a Tabela continuam funcionando (só metadados), o Comprovante é recusado com `ORIGINAIS_EXCLUIDOS` (DEL-11), o arquivo e as páginas respondem 410 (DEL-12) e os arquivos em `storage/generated/` não são tocados (DEL-06, DEL-13, VER-09).

---

## Data Models

Migração `0005_generated_documents.py` (a última é a `0004`).

```python
# enums: generated_kind(TABELA, RELATORIO, COMPROVANTE), generated_state(GERANDO, PRONTO, FALHOU),
#        generated_format(DOCX, PDF)
generated_documents(
    id uuid pk, process_id fk functional_processes, kind generated_kind, state generated_state,
    version_number int null,            # só em PRONTO; unique(process_id, kind, version_number) onde não nulo
    requested_by fk users, requested_at timestamptz, started_at timestamptz null, finished_at timestamptz null,
    error_code varchar(40) null, error_message varchar(300) null,   # mensagem fixa por código, sem dados pessoais
    snapshot jsonb null, alerts jsonb null, plan_hash char(64) null)
# índice parcial único (process_id, kind) WHERE state = 'GERANDO'   -> VER-04
# índice (process_id, kind, requested_at desc)
generated_files(
    id uuid pk, generated_document_id fk generated_documents, format generated_format,
    internal_name varchar(64) unique, sha256 char(64), size_bytes bigint, created_at timestamptz,
    unique(generated_document_id, format))
report_wording_jobs(
    id uuid pk, process_id fk functional_processes, section_key varchar(20),
    state generated_state,              # o mesmo enum GERANDO, PRONTO, FALHOU
    requested_by fk users, requested_at timestamptz, started_at timestamptz null, finished_at timestamptz null,
    error_code varchar(40) null,        # INTERROMPIDA, ERRO_INTERNO
    warnings jsonb null)                # [{code: REDACAO_REJEITADA|REDACAO_INDISPONIVEL, reason?}]
# índice parcial único (process_id, section_key) WHERE state = 'GERANDO'   -> REL-13
# índice (process_id, section_key, requested_at desc)
documents(... , file_deleted_at timestamptz null)   # coluna nova; `ARQUIVO_EXCLUIDO` é "file_deleted_at IS NOT NULL"
report_drafts(
    id uuid pk, process_id fk unique, template_id varchar(60), template_version int,
    content jsonb,                       # {sections: [{key, title, free_text, warnings, entries: [{activity_id, text, source, warnings}]}]}
    version int, created_by fk users, created_at, updated_by fk users, updated_at)
comprovante_layouts(
    id uuid pk, process_id fk unique, content jsonb,   # {activities: [{activity_id, pages: [{document_id, page, repeat_justification}]}], base_evidence_keys: [...]}
    version int, updated_by fk users, updated_at)
```

A exclusão da conclusão não muda o modelo de `document_pages` (as linhas são apagadas), de `activity_evidences` (`excerpt` vira `''`, os números `document_id` e `page_number` ficam) nem de `extraction_runs` (o gatilho de imutabilidade fica como está; `raw_json` e `warnings` permanecem, ver a assunção da spec). `documents.file_deleted_at` só vai de nulo para preenchido, nunca volta.

Gatilhos, no padrão do `extraction_runs`: `generated_documents` só aceita `UPDATE` quando `OLD.state = 'GERANDO'` e recusa `DELETE`; `generated_files` recusa `UPDATE` e `DELETE`. Sem `ON DELETE CASCADE` para o processo (a versão é o registro do que foi entregue). Os documentos de origem não têm FK no arranjo: o `document_id` guardado no JSON que aponta para um documento excluído vira `ORIGINAL_INDISPONIVEL` na geração e entrada inválida no arranjo (edge case da spec).

Instantâneo (`snapshot`), igual nos três tipos com acréscimos por tipo:

```json
{"table_version": {"id": "...", "name": "...", "norm_reference": "..."},
 "interstice": {"start": "2020-01-01", "end": "2024-12-31"},
 "total": "211.00", "subtotals": {"1": "0.00", "2": "52.00"}, "pit_hours": {"2023.1": "24"}, "pit_total_hours": "92",
 "activities": [{"id": "...", "group": 2, "item": 3, "quantity": "1", "points": "20.00", "status": "PONTUADA"}],
 "excluded": {"pendentes": 2, "sem_enquadramento": 1},
 "alerts": ["SEM_COMPROVANTE"], "template": {"id": "ufpa-modelo-2", "version": 1},
 "layout": {"plan_hash": "...", "entries": [...]},        // Tabela e Comprovante
 "report": {"sections": [{"key": "1.1", "entries": [{"activity_id": "...", "text": "...", "source": "IA"}]}]}   // Relatório
}
```

Configuração versionada (`backend/app/infrastructure/documents/config/`):

- `report_templates.json`: `default`, e por modelo `version`, `page` (A4, margens 31,75 mm laterais e 25,4 mm verticais, Times New Roman, 9 pt, lidos do `Modelo Relatorio Atividades 2.docx`), `header_lines` (`Serviço Público Federal`, `Universidade Federal do Pará`, `{unit_name}`), `title`, `identification` (Nome, Professor com classe e nível, unidade, período de interstício, "ATIVIDADES DESENVOLVIDAS"), `group_map` e `sections`. Cada seção: `key`, `title`, `match` (lista de `{group, item?}`), `group_by` (`academic_period` | `item` | `none`), `period_label`, `entry` (`line` ou `fields`, com marcadores como `{title}`, `{course_hours}`, `{period}`), `subtitle` opcional e `order_items` para separar concluídas e em andamento no 1.3. `entry_style` aceita `campos` (modelo 2) e `narrativo` (modelo 1: parágrafo corrido sob o item, com a coluna "Nº documentação" apontando o número do Comprovante); só o estilo `campos` é entregue. Também: `allowed_terms`, `formal_vocabulary`, `forbidden_words`, `max_new_words`
- Mapa de grupo para seção (spec): I.1 para 1.1, I.2 para 1.2, II para 1.3, III para 6 ("Participação em bancas e comissões examinadoras"), IV para 3, V para 2, VI para 4, VII para 6 ("Capacitação"), VIII para 6; a 5 só recebe atividades movidas
- `dossier_order.json`: lista de `{order, title, generated_by: null | TABELA | RELATORIO | COMPROVANTE}` com os itens do `ordenamentodecomoosdocumentosdevemestarsequenciadosnorelatrio.pdf`: requerimento à CPPD (conforme modelo), portaria da última progressão, declaração de pagamento de exercícios anteriores preenchida, relatório de progressão funcional, documentação comprobatória em ordem e numerada, currículo Lattes atualizado. O modelo não cita a Tabela de Pontuação; a configuração a coloca depois do Relatório e antes da documentação comprobatória (a confirmar pelo usuário)
- Validação do arquivo na partida: JSON inválido ou seção sem `key` derruba o carregamento com mensagem clara (como `load_settings`)

Novas variáveis de `Settings` (valores padrão entre parênteses): `generation_max_pages` (400), `generation_max_output_mb` (60), `generation_png_max_megapixels` (12), `generation_min_free_mb` (200), `wording_timeout_seconds` (60), `report_template_id` (do arquivo). A conclusão não tem variável nova.

---

## Error Handling Strategy

Códigos novos (domínio: `GenerationCode` e `GenerationAlertCode`). Recusas de pedido saem como 422 `{"detail": [{"field": "geracao", "code": "...", "message": "..."}]}`; falhas do executor ficam na linha como `error_code` e `error_message`.

| Código | Quando | Onde aparece |
| --- | --- | --- |
| `SEM_ATIVIDADES_VALIDADAS` | Nenhuma atividade `VALIDADA` com grupo e item (TAB-07) | 422 no pedido |
| `TABELA_NAO_ESCOLHIDA` | Processo sem versão de tabela (TAB-08) | 422 |
| `ATIVIDADE_SEM_DESCRICAO` | Atividade validada sem descrição e sem título, citando o `id` (REL-10) | 422 |
| `COMPROVANTE_GRANDE_DEMAIS` | Mais de 400 páginas anexadas, ou saída acima de 60 MB (estimada no pedido pela soma proporcional dos tamanhos de origem; conferida de novo no arquivo final) (CMP-09) | 422 ou `FALHOU` |
| `IMAGEM_GRANDE_DEMAIS` | Origem PNG acima de 12 megapixels (CMP-13) | 422, citando documento |
| `ORIGINAL_INDISPONIVEL` | Arquivo ausente do armazenamento, documento excluído ou página inexistente, com documento e página (CMP-10) | `FALHOU`; no pedido já sai 422 quando o plano acusa |
| `INTERROMPIDA` | Servidor reiniciou durante a geração (VER-08) ou a redação (REL-14) | `FALHOU` |
| `ESPACO_INSUFICIENTE` | Menos de `generation_min_free_mb` livres no volume | 422 |
| `ARTEFATOS_PENDENTES` | Conclusão sem versão `PRONTO` de Tabela, Relatório ou Comprovante; lista os tipos (DEL-01) | 422 |
| `CONFIRMACAO_OBRIGATORIA` | Conclusão sem `confirmar: true` (DEL-04) | 422 |
| `OPERACAO_EM_ANDAMENTO` | Conclusão com geração, redação ou processamento de documento em curso (DEL-02) | 409 |
| `CONCLUSAO_EXIGE_EXCLUSAO` | Rota genérica de status com alvo CONCLUIDO (DEL-14) | 409 |
| `ORIGINAIS_EXCLUIDOS` | Geração do Comprovante com documento `ARQUIVO_EXCLUIDO` (DEL-11) | 422 |
| `ARQUIVO_EXCLUIDO` | Arquivo ou página de documento já excluído (DEL-12) | 410 |
| `REDACAO_EM_ANDAMENTO` | Segundo pedido de redação da mesma seção com `GERANDO` (REL-13) | 409 |
| `ERRO_INTERNO` | Exceção inesperada na geração ou na redação (REL-15); só o tipo é registrado | `FALHOU` |
| `GERACAO_EM_ANDAMENTO` | Segundo pedido igual enquanto há `GERANDO` (VER-04) | 409 |
| `VERSAO_DESATUALIZADA` | `expected_version` diferente (ARR-07) | 409 |
| `PROCESSO_SOMENTE_LEITURA` | Gravação de rascunho ou arranjo em processo concluído ou arquivado | 409 |
| `PAGINA_FORA_DO_DOCUMENTO` | Página fora de `1..page_count` | 422 |
| (404) | Processo, documento, atividade, linha ou arquivo fora do acesso ou inexistente | 404 sem distinguir |

Alertas do resultado (listados no bloco, em português, UIG-05): `ATIVIDADE_SEM_COMPROVANTE` (CMP-07), `REDACAO_REJEITADA` e `REDACAO_INDISPONIVEL` (REL-04, REL-05), `ARRANJO_DESATUALIZADO` (ARR-08), `NUMERACAO_DIVERGENTE` (Tabela e Comprovante com `plan_hash` diferente), `ATIVIDADES_FORA_DO_DOCUMENTO` (contagem por motivo), `PAGINA_REPETIDA_JUSTIFICADA`, `PAGINA_RASTERIZADA` (CMP-12), `RASCUNHO_DESATUALIZADO`, `EXCLUSAO_PARCIAL` (resposta da conclusão, DEL-08) (atividades novas ou removidas desde a última edição do Relatório), além dos alertas de pontuação da Tabela (TAB-06) com o texto da tela.

| Cenário | Tratamento | Impacto para o usuário |
| --- | --- | --- |
| MariTalk indisponível, erro ou mais de 60 s | Texto-modelo e `REDACAO_INDISPONIVEL`; o job termina em `PRONTO` | A seção sai preenchida e avisada |
| Falha ao remover um arquivo na conclusão | O documento fica pendente, os demais seguem; processo continua EM_ANDAMENTO com `EXCLUSAO_PARCIAL` | A tela mostra quantos faltam e oferece tentar de novo |
| Queda do servidor no meio da conclusão | Documentos já processados ficam excluídos; o processo continua EM_ANDAMENTO | Repetir a conclusão termina o que falta |
| Resposta da IA com número, data, nome ou palavra nova | Texto-modelo e `REDACAO_REJEITADA` | O usuário vê o motivo e edita |
| Edição concorrente do rascunho ou do arranjo | 409 `VERSAO_DESATUALIZADA` | A tela recarrega e avisa |
| Arquivo gerado sumiu do volume | 404 no download; log com `generation_id` | Pede nova geração |
| Reinício no meio da geração | `INTERROMPIDA` | Botão de gerar de novo |

---

## Observabilidade e auditoria

- **Auditoria** (`AuditService`, só identificadores e códigos): `generated_document` `CREATE` no pedido (`kind`, `state`), `STATUS` no fim (`state`, `version_number`, `error_code`, hash e tamanho por formato), `UPDATE` com `operation: DOWNLOAD`; `report_draft` `UPDATE` com as chaves de seção e a contagem de entradas alteradas, `operation: WORDING` com a seção, a fonte e os códigos dos avisos; `comprovante_layout` `UPDATE` com contagens de páginas acrescentadas, removidas, reordenadas e repetições justificadas; `process` `UPDATE` com `operation: PURGE` (arquivos e bytes removidos e pendentes) e `STATUS` na transição para CONCLUIDO, sem nomes de arquivo; o job de redação audita `operation: WORDING` no pedido (seção) e ao terminar (estado e códigos). Texto de atividade, do rascunho e justificativas não vão para a auditoria.
- **Logs** (`app.documents.generation`): `generation_id`, `kind`, `state`, `duration_ms`, `pages`, `size_bytes`, `error_code` e `peak_rss_mb` (`resource.getrusage`) ao fim de cada geração, para confirmar o CMP-11 na VM sem instrumentação extra. Nenhum nome, título, texto ou caminho.
- A auditoria da geração e do download não duplica o log de acesso existente.

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| --- | --- | --- | --- |
| `CalculateProcessScore` exige ator e abre a própria unidade de trabalho; o executor não tem ator | `backend/app/application/use_cases/scoring.py:646` | Duplicar o cálculo faria a Tabela divergir da tela | Extrair `compute_process_score(uow, process)` sem mudar o comportamento; os testes existentes de pontuação seguem como rede de proteção; um teste novo compara a Tabela com a resposta de `/scoring` |
| `show_pdf_page` descarta `/Rotate`, anotações e campos (verificado) | `source_pages.py` (novo) | Página rotacionada deformada; carimbo ou aparência de assinatura some do Comprovante | `remove_rotation` e `bake` num PDF temporário; teste de igualdade por pixel com rotação 90, 180, 270, anotação e campo; fallback rasterizado para rotação com recorte, com alerta |
| PNG grande decodifica inteiro: +324 MB com 40 megapixels (verificado) | `source_pages.py`; limites em `inspector.py` (100 megapixels aceitos no envio) | Estouro dos 384 MB do contêiner | Decidido pelo usuário (2026-11-18): `IMAGEM_GRANDE_DEMAIS` acima de 12 MP (+103 MB) antes de começar (CMP-13); o JPEG passa sem decodificar. O PNG já enviado acima do limite continua guardado e só impede o Comprovante |
| Montar acumulando num documento só custa até +125 MB com 88 MB de saída (verificado) | `comprovante_assembler.py` | Pico alto se o limite de 60 MB for contornado por estimativa errada | Salvamento incremental a cada 25 páginas (+8 a +11 MB); a estimativa de 60 MB é conferida no arquivo final e a geração falha sem arquivo parcial |
| Pontos de memória fora do Comprovante: `UnitOfWork` aberta durante a renderização | `generated_documents.py` (novo) | Conexão presa por segundos | Ler tudo em uma unidade de trabalho, fechar, renderizar (como `ProcessDocument`) |
| Thread única: o Comprovante atrasa o OCR e vice-versa | `backend/app/infrastructure/jobs/worker.py:43` | Espera de alguns segundos | Medido: 1,1 s para 400 páginas; a geração roda antes do OCR porque o usuário a espera; o OCR em curso termina a página antes |
| `GET` não grava, mas o rascunho precisa existir para a redação | `report_draft.py` (novo) | Corrida na primeira gravação | `expected_version: 0` cria; unique em `process_id` devolve 409 e a tela recarrega |
| Redação em segundo plano ocupa a thread única por até 60 s; uma geração pedida nesse intervalo espera | `backend/app/infrastructure/jobs/worker.py:43` (runner novo) | Espera de até 60 s por um Comprovante que leva 1,1 s | A ordem do executor põe a geração antes da redação, mas não interrompe a redação em curso; o prazo de 60 s é o teto; thread própria foi descartada por contrariar a AD-008; a tela mostra o estado GERANDO e consulta a cada 3 s, então a espera é visível, não um erro |
| A conferência da redação pega número, data, nome e palavra nova, não toda afirmação qualitativa | `report_grounding.py` (novo) | Texto plausível mas não escrito nos dados passa | Prompt restritivo, vocabulário fechado e `max_new_words`, lista de palavras proibidas, comprimento limitado, texto sempre editável e rótulo "IA" na tela; testes com respostas falsas (número inventado, nome novo, elogio) e com respostas fiéis em vários formatos |
| Conferência pode recusar texto fiel por formato (data por extenso, número com ponto) | `report_grounding.py` | Muita seção cai no texto-modelo | Normalizar como o `grounding.py` existente; tarefa de medição com respostas sintéticas de formatos variados |
| `MariTalkExtractor` mistura transporte e regras de extração | `backend/app/infrastructure/ai/maritalk.py:72-127` (`extract` e `_post`) | Duplicar o laço de tentativas e o modelo reserva num segundo adaptador | Extrair `MariTalkClient`; os testes do extrator (transporte falso) seguem como cobertura |
| `FileStorage.save(bytes)` carrega o conteúdo inteiro | `backend/app/infrastructure/storage/local_storage.py:35` | 60 MB em memória | `LocalGeneratedStorage` grava por caminho, nunca por `bytes` |
| Volume cresce sem retenção (até 60 MB por versão de Comprovante) | `docker-compose.yml` (volume `storage`) | Disco da VM compartilhada | Decidido pelo usuário (2026-11-18): todas as versões ficam e o tamanho aparece no histórico (VER-09); pré-checagem de espaço livre (`ESPACO_INSUFICIENTE`); a conclusão libera o espaço dos originais, que é a maior parte do volume |
| PyMuPDF é AGPL-3.0 (ou licença comercial da Artifex); já é dependência desde `inteligencia-documental` | `backend/requirements.txt:13` | Obrigação de oferecer o código a quem usa o serviço pela rede | Aceito pelo usuário em 2026-11-18 (assunção confirmada na spec; não é parecer jurídico); o repositório é público |
| `api/client.ts` mostra "Verifique os campos destacados" para todo 422 | `frontend/src/api/client.ts:68` | A recusa `SEM_ATIVIDADES_VALIDADAS` ficaria sem texto | `errorMessage` passa a ler `message` do primeiro item com `code`; teste do cliente |
| Nomes de arquivo de download com dados do docente | `presentation/api/generated_documents.py` (novo) | Dado pessoal em cabeçalho e histórico do navegador | Nome sem o docente (`download_name`), montado no servidor |
| A exclusão é irreversível e a VM não tem backup (dívida do `STATE.md`) | `conclusion.py` (novo) | Perda de originais que o docente ainda queria | Confirmação com o número de arquivos e o espaço; só com os três documentos `PRONTO`; texto da confirmação diz "irreversível"; registro em AD-015 |
| Exclusão parcial por falha de disco ou queda do servidor | `PurgeInputDocuments` (novo) | Processo meio limpo e ainda EM_ANDAMENTO | Arquivo antes do banco, cada documento numa transação, ausente conta como removido, conferência final na transição; teste de queda simulada entre os dois passos |
| Existem testes e uma rota que levam o processo a CONCLUIDO pela rota genérica | `backend/tests/integration/api/test_process_updates_api.py:98-132`, `test_scoring_process_api.py:179` | Quebram quando a rota genérica recusar CONCLUIDO | Tarefa própria, antes da recusa, que cria o auxiliar de teste que conclui pela unidade de trabalho e ajusta os testes; a rota nova ganha os próprios testes |
| `activity_evidences.excerpt` é `NOT NULL` e o texto de página é lido por `evidences.py:69` e `documents.py:341` | `backend/app/application/use_cases/evidences.py:69`, `documents.py:341` | Erro ou lista vazia silenciosa ao ler documento excluído | Esvaziar o trecho com `''` e fazer os casos de uso levantar `Gone` antes de ler texto; teste de cada leitura sobre documento excluído |
| `extraction_runs.raw_json` fica depois da exclusão (gatilho de imutabilidade) | `backend/alembic/versions/0003_documents.py:90` | O JSON estruturado da IA ainda guarda campos extraídos (títulos, nomes de participantes) | Registrado como assunção não confirmada na spec; apagar exigiria mudar o gatilho; o usuário decide |
| Upload durante a conclusão | `ConcludeProcess` (novo), `backend/app/application/use_cases/documents.py` | Arquivo novo fica fora da exclusão | A transição relê os documentos na transação e responde `EXCLUSAO_PARCIAL`; teste de concorrência |
| Pino de `reportlab==5.1.0` com 27 dias | `backend/requirements.txt` | Regressão numa versão jovem | Suíte roda no pino; queda para 4.5.1 se falhar |
| Não testei o DOCX no Word | `table_docx.py`, `report_docx.py` | Diferença de layout no Word | Testes leem o XML (`tblHeader`, `tblGrid`, campos) e a abertura é conferida em LibreOffice em ambiente de desenvolvimento; a spec já aceita que PDF e DOCX divirjam na aparência |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Bibliotecas | python-docx (DOCX), reportlab (PDF gerado), PyMuPDF (juntar originais) | Medido acima; reportlab dá cabeçalho repetido, largura em porcentagem e numeração "N de M" sem contorno |
| Fonte do PDF | Liberation Serif versionada no repositório | A imagem slim não tem fontes; a licença OFL permite; evita variação entre ambientes |
| Linha da geração | `generated_documents` própria, não `processing_jobs` | Semântica de `INTERROMPIDA` e FK obrigatória para documento |
| Versão numerada | Atribuída só em `PRONTO` | Falha não gasta número; o índice único resolve corrida |
| Imutabilidade | Gatilho no banco, como em `extraction_runs` | VER-01 vale mesmo contra erro de código |
| Rascunho e arranjo | JSONB com bloqueio otimista por `version` (um documento por processo), não linhas por entrada | São documentos editados por uma pessoa e lidos inteiros; ao contrário dos critérios da tabela (AD-007), nada os consulta por campo |
| `GET` do rascunho e do arranjo | Devolve proposta sem gravar; a primeira gravação usa `expected_version: 0` | `GET` sem efeito colateral e a mesma regra para os dois |
| Numeração do Comprovante | Função pura de plano, compartilhada pela Tabela e pelo Comprovante, com capacidade fixa de linhas no sumário | A Tabela cita números antes de o Comprovante existir; capacidade fixa elimina a previsão por renderização |
| Tabela com 7 colunas | Grupo vira faixa, item vira coluna ("I.1") | Atende TAB-03 e cabe em A4 paisagem |
| Redação | Tarefa em segundo plano por seção (`report_wording_jobs`), uma chamada por seção, só campos da atividade, conferência determinística, texto-modelo de reserva; o resultado não incrementa `version` do rascunho | REL-03 a REL-06, REL-13 a REL-15 e AD-009; a requisição não espera a MariTalk e a edição por entrada não conflita com a aplicação do job |
| Conclusão | Operação síncrona que exclui arquivo, depois banco, por documento, e só então muda o status; a rota genérica recusa CONCLUIDO | Reaproveita `can_transition`, auditoria e versão; deixa o estado parcial recuperável por repetição |
| Marca de arquivo excluído | Coluna `documents.file_deleted_at`, não um valor novo de `DocumentStatus` | `DocumentStatus` é o estado do processamento; a exclusão é ortogonal e nunca desfaz o resultado da extração |
| Retenção das versões | Guardar todas, tamanho no histórico | Decisão do usuário (2026-11-18) |
| Origem em imagem | JPEG passa sem decodificar; PNG até 12 MP, acima recusado com `IMAGEM_GRANDE_DEMAIS`; página com a dimensão do `dpi` da imagem (150 dpi quando ausente), no máximo 14 400 pt de lado | O custo de memória do PNG é linear e medido; limite decidido pelo usuário |
| Nome do download | Tipo, interstício e versão, sem o docente | LGPD |
| Página rotacionada | `remove_rotation` num PDF temporário; anotações incorporadas | Medido: a única forma que manteve o conteúdo idêntico |
| Hash no download | `ETag` com o SHA-256 gravado; o arquivo não é relido | Evita ler 60 MB a cada download; o teste confere byte a byte |

> **Decisões de projeto gravadas em `STATE.md` (2026-11-18):** AD-011 (documentos gerados sem LibreOffice: python-docx, reportlab e PyMuPDF, com fonte versionada e pinos), AD-012 (versão de documento gerado imutável, numerada só em `PRONTO`, com `INTERROMPIDA` na partida), AD-013 (páginas originais do Comprovante sem alteração de conteúdo e plano puro compartilhado com a Tabela), AD-014 (redação por IA só com campos da atividade, conferência determinística e tarefa em segundo plano) e AD-015 (exclusão dos documentos de entrada na conclusão do processo).

---

## Cobertura dos requisitos

| Requisitos | Onde são atendidos |
| --- | --- |
| TAB-01 a TAB-08 | `compute_process_score`, `build_table_document`, `table_docx.py`, `table_pdf.py`, `RequestGeneration` (códigos de recusa) |
| CMP-01 a CMP-04, CMP-08 | `plan_comprovante`, `front_matter.py`, `source_pages.attach`, conversão de imagem |
| CMP-05 a CMP-07 | `plan_comprovante` (remissão, repetição justificada, atividade sem página) |
| CMP-09 a CMP-11 | Limites em `RequestGeneration` e no arquivo final; `ORIGINAL_INDISPONIVEL`; montagem incremental (74 MB medidos) |
| ARR-01 a ARR-08 | `derive_layout`, `SaveComprovanteLayout`, `layout_staleness`, `GET`/`PUT /comprovante-layout` |
| REL-01 a REL-12 | `propose_draft`, `reconcile_draft`, `RequestSectionWording`, `check_wording`, `report_*.py`, rotas do rascunho |
| VER-01 a VER-08 | `generated_documents`, gatilhos, índice parcial, `RunGeneration`, `RecoverInterruptedGenerations`, auditoria |
| UIG-01 a UIG-07 | `ProcessGenerated`, `GeneratedBlock`, `ReportDraftEditor`, `ComprovanteLayoutEditor`, `usePolling` |
| ORD-01, ORD-02 | `dossier_order.json`, `GET /dossier-order`, `DossierOrder` |
| CMP-12, CMP-13 | `source_pages.attach` (fallback rasterizado), `RequestGeneration` (`IMAGEM_GRANDE_DEMAIS`) |
| REL-13 a REL-15 | `report_wording_jobs`, `RequestSectionWording`, `RunWording`, `RecoverInterruptedGenerations` |
| VER-09 | Nenhuma exclusão de `generated_files`; coluna de tamanho no histórico |
| UIG-08, UIG-09 | `ReportDraftEditor` com `usePolling`, `ConcludeDialog` |
| DEL-01 a DEL-15 | `conclusion_rules.py`, `ConcludeProcess`, `PurgeInputDocuments`, `GetConclusionPreview`, `ChangeProcessStatus` (recusa), `DownloadDocument` e leituras de página (410), `RequestGeneration` (`ORIGINAIS_EXCLUIDOS`), `ConcludeDialog` |

## Decisões do usuário aplicadas (2026-11-18)

1. UIG-01 e o título da história: Etapa 5, "Documentos gerados". Aplicado na spec e neste design.
2. `IMAGEM_GRANDE_DEMAIS` e o limite de 12 megapixels para PNG (CMP-08, CMP-13 e edge case); alerta `PAGINA_RASTERIZADA` (CMP-03 e CMP-12); Tabela de 7 colunas com o grupo em faixa (TAB-03).
3. Licença AGPL do PyMuPDF aceita (assunção confirmada).
4. Exclusão dos documentos de entrada na conclusão (história DEL, AD-015). A interpretação do que sai e do que fica está nas assunções com `Confirmed = n`.
5. Redação em segundo plano (REL-03, REL-05, REL-13 a REL-15, UIG-08); o risco do `proxy_read_timeout` deixou de existir.
6. Retenção: todas as versões ficam, com o tamanho no histórico (VER-09).

## Fora deste design

Tarefas e ordem de implementação estão em `tasks.md`. Os scripts de protótipo ficaram fora do repositório; o que vale vira teste: igualdade por pixel e por bytes de imagem do Comprovante, numeração e sumário, limites, pico de memória (400 páginas sintéticas, `ru_maxrss` abaixo de 320 MB), conferência da redação e imutabilidade da versão.

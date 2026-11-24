# Documentos Gerados: verificação independente A (artefatos gerados)

**Data**: 2026-11-18
**Spec**: `.specs/features/documentos-gerados/spec.md`, famílias TAB-01..08, CMP-01..13, ARR-01..08 e VER-01..09 (38 requisitos)
**Escopo**: Tabela de Pontuação, Comprovante, arranjo do Comprovante, versões imutáveis e download. REL, DEL, ORD e UIG são do Verificador B.
**Diff range**: HEAD `4628f08` (branch `feat/inteligencia-documental`), backend sem alteração do verificador
**Verificador**: sub-agente independente (autor ≠ verificador). Só leitura sobre o repositório; mutantes, servidor e bancos ficaram em cópias isoladas no scratchpad.

Convenção: caminhos de teste são relativos a `backend/`; `E2E` é o fluxo real descrito na seção 3 (uvicorn + worker + PostgreSQL descartável, PDFs gerados em código, sem MariTalk).

---

## 1. Resumo

| Item | Resultado |
| --- | --- |
| Requisitos do escopo | 38: **36 PASS, 2 PARTIAL (CMP-01, ARR-06), 0 FAIL** |
| Gate de backend `ruff check . && pytest -q` | ruff `All checks passed!`; pytest **5013 passed**, 3 desmarcados (`maritalk_live`), 17 min 54 s |
| Conjuntos usados nos mutantes | unitário 387 passed; integração 208 passed (linha de base limpa antes de qualquer mutante) |
| Sensor de discriminação | **135 mutantes, 116 mortos, 19 sobreviventes** (85.9% mortos; 90.6% descontados os 7 equivalentes); 12 sobreviventes são lacunas de teste reais, 0 mutantes inválidos. Profundidade: P0 (dados e integridade), manual com mais de 30 mutantes. Resultado: **PASS**, com os 12 sobreviventes reais convertidos nas tarefas de reforço F1 a F6 e F9 (seção 7) |
| Fluxo real ponta a ponta | Tabela, Relatório e Comprovante gerados e baixados; páginas originais conferidas por pixel; imagens renderizadas e vistas |
| Defeitos | 0 Blocker, 0 High, 3 Medium, 8 Low (seção 6) |
| **Recomendação** | **PASS** (sem Blocker nem High), com as tarefas de correção F1 a F9 da seção 7 |

Nenhum arquivo de `Documentos/` ou `Modelos/` foi aberto. `git status --porcelain` ficou idêntico ao de antes da verificação.

---

## 2. Critérios de aceitação (evidência por requisito)

Legenda: PASS = o comportamento foi observado no E2E ou por cálculo independente **e** há teste cuja asserção mira o resultado da spec; PARTIAL = o comportamento difere em parte do texto da spec.

### TAB: Tabela de Pontuação

| Req | Resultado da spec | Evidência (`arquivo:linha` + asserção; E2E) | Veredito |
| --- | --- | --- | --- |
| TAB-01 | DOCX e PDF com o resultado do motor, calculado no pedido | `tests/integration/api/test_generated_table_acceptance.py:37-39` (`status_code == 200` e `"Pontuação geral: 211,00" in text` no DOCX e no PDF baixados); `:47-61` compara com `GET /scoring` (`f"Pontuação geral: {pt(scored['total'])}"`); `tests/integration/doc_usecases/test_run_generation_table.py:97-107` (211,00 e subtotais nos dois formatos). E2E: v1 = 211,00; após alterar uma atividade a v2 saiu 221,00 e a v1 continuou 211,00 | PASS |
| TAB-02 | Cabeçalho: docente, classe e nível atuais e pretendidos, unidade, interstício, tabela e referência normativa | `tests/unit/infrastructure/test_table_pdf.py:64-75` (7 linhas `in text`); `tests/unit/infrastructure/test_table_docx.py:132`; `tests/unit/domain/test_table_document_rows.py:31-41`. E2E: PDF e DOCX trazem `Docente: Maria Docente da Silva`, `Classe e nível atuais: C, nível 4`, `Interstício: 23/11/2022 a 23/11/2024`, `Referência normativa: ...` | PASS |
| TAB-03 | 7 colunas, uma linha por atividade, grupo em faixa com subtotal (também vazio), comprovante como número ou "sem comprovante" | `tests/unit/infrastructure/test_table_pdf.py:50-56` (cabeçalho da tabela `== COLUMNS`); `:88-91` (`V. Pesquisa Subtotal: 0,00`); `tests/unit/infrastructure/test_table_docx.py:79,146`; `tests/unit/domain/test_table_document_rows.py:88-117` (colunas e ordem). E2E: python-docx lê 7 colunas, `w:tblHeader` na primeira linha, `tblLayout fixed`; faixa V com 0,00; coluna comprovante coincide com a página real do Comprovante (cruzado no PDF, seção 4). Nota: atividade com várias páginas mostra só a primeira (F5) | PASS |
| TAB-04 | Subtotais, total e contagens iguais aos do motor | `tests/unit/domain/test_table_document_totals.py:47-52` (`document.total == "211,00"`), `:54-69` (`document.counters == result.counters`); `tests/unit/domain/test_table_document_rows.py:44-50` (subtotais 52, 7, 62, 0, 30, 4, 56). E2E: PDF e DOCX com `Subtotal` 52, 7, 62, 0, 30, 4, 56 e `Pontuação geral: 211,00`, igual ao `GET /scoring`. Lacuna de discriminação do total sob limite (M50, F1) e do rótulo "Com comprovante" (M64, F4); o comportamento está correto | PASS |
| TAB-05 | Horas de PIT por semestre e total numa seção separada, sem somar aos pontos | `tests/unit/domain/test_table_document_totals.py:72-79` (`["24,00","24,00","24,00","20,00"]`, total `"92,00"`), `:92-97`, `:99-111`; `tests/integration/api/test_generated_table_acceptance.py:43` (`== [*PIT_HOURS, "92,00"]`). E2E: PDF `Horas de PIT por semestre ... 24,00 24,00 24,00 20,00 Total em horas 92,00` | PASS |
| TAB-06 | Alertas da pontuação com o texto da tela | `tests/unit/domain/test_table_document_totals.py:122-130` (limite), `:149-159` (limite de grupo), `:162-180` (`DATA_FIM_AUSENTE`), `:183-198` (`"Carga horária abaixo do mínimo do item"`), `:226-238`; `tests/unit/infrastructure/test_table_pdf.py:112` | PASS |
| TAB-07 | Sem atividade validada: recusa `SEM_ATIVIDADES_VALIDADAS` | `tests/integration/doc_usecases/test_request_generation.py:44-50` (`error.code == SEM_ATIVIDADES_VALIDADAS`, `rows(world) == []`); `tests/integration/api/test_generated_documents_api.py:49-59` (422, `("geracao","SEM_ATIVIDADES_VALIDADAS")`) | PASS |
| TAB-08 | Sem tabela escolhida: recusa `TABELA_NAO_ESCOLHIDA` | `tests/integration/doc_usecases/test_request_generation.py:53-60`; `tests/integration/api/test_generated_documents_api.py:38-46`; `tests/integration/api/test_generated_table_acceptance.py:82-89` | PASS |

### CMP: Comprovante

| Req | Resultado da spec | Evidência | Veredito |
| --- | --- | --- | --- |
| CMP-01 | Capa, sumário e, por grupo e item com atividade, o título com a nomenclatura da tabela | `tests/integration/api/test_generated_comprovante_acceptance.py:136-137` (`"COMPROVANTE DE DOCUMENTOS" in pages[0]`, `"SUMÁRIO" in pages[1]`); `tests/unit/infrastructure/test_front_matter.py:107-114` (separador só com o título do grupo), `:143-151` (capa). E2E: capa, 3 páginas de sumário, 7 separadores de grupo (I, II, III, IV, VI, VII, VIII). O título do **item** só aparece no sumário e é cortado com reticências em cerca de 85 caracteres (`II.7 Orientação de trabalho de conclusão ... (5 pont…`), logo a nomenclatura da tabela sai incompleta (D4) | PARTIAL |
| CMP-02 | Por atividade: título, nome do arquivo de origem e página, páginas anexadas | `tests/unit/infrastructure/test_front_matter.py:117-128` (`"origem: certificado.pdf, p. 4; certificado.pdf, p. 5"` e `Comprovante p. N a N+1`). E2E: `origem: alfa.pdf, p. 1; alfa.pdf, p. 2 - Comprovante p. 7 a 8`. O teste não separa página de origem de página do Comprovante (M43, F3) | PASS |
| CMP-03 | Página original sem alterar conteúdo, posição e tamanho; rotação, anotações e campos mantidos; número numa faixa abaixo | `tests/unit/infrastructure/test_source_pages.py:26` (`render(out[0], clip=original_area(out[0])) == render(src[0])`, pixel a pixel), `:29-47` (faixa de 24 pt e número `Comprovante p. 12`), `:49-55` (bytes das imagens idênticos); `tests/unit/infrastructure/test_source_pages_rotation.py:28-41` (90, 180 e 270 idêntico pixel a pixel), `:44-55` (anotações e campos, `max_difference <= 1`); `tests/unit/infrastructure/test_comprovante_assembler.py:116-134`. E2E: 6 páginas de PDF (uma rotacionada 90 graus com carimbo) com `maxdiff 0` na área original, texto igual, bytes JPEG idênticos. Sondas próprias (mediabox deslocado, cropbox sem rotação, campo preenchido, link, página vazia): `maxdiff 0`. Nota: carimbos e campos viram conteúdo estático e links são descartados | PASS |
| CMP-04 | Numeração contínua desde a capa; sumário com a primeira página de grupo, item e atividade | `tests/unit/domain/test_comprovante_plan_pages.py:94-99` (`[p.number ...] == list(range(1, 15))`), `:116-133`; `tests/unit/infrastructure/test_comprovante_assembler.py:103-106` (`[foot(page) for page in pdf[1:]] == [f"Comprovante p. {n}" ...]`); `tests/unit/infrastructure/test_front_matter.py:78-94`. E2E: páginas 2 a 20 trazem `Comprovante p. N` igual à posição; a capa é a página 1 e não imprime número (decisão do design, `test_front_matter.py:97-104`) | PASS |
| CMP-05 | Mesma página em duas atividades: anexada uma vez, remissão na outra | `tests/unit/domain/test_comprovante_plan_sharing.py:51-65`; `tests/integration/api/test_generated_comprovante_acceptance.py:154` (`"ver comprovante nº 5, p. 1" in toc`). E2E: `ver comprovante nº 7, p. 1` na atividade 2.7 nº 2, e `3.2` aponta para a página 9 | PASS |
| CMP-06 | Repetição justificada anexa de novo e registra a justificativa | `tests/unit/domain/test_comprovante_plan_sharing.py:139-158`; `tests/unit/infrastructure/test_comprovante_assembler.py:252-270`; `tests/integration/api/test_comprovante_layout_api.py:102-112` (`repeat_justification` mantida) | PASS |
| CMP-07 | Atividade sem página: linha "Sem comprovante anexado" e alerta `ATIVIDADE_SEM_COMPROVANTE` | `tests/integration/api/test_generated_comprovante_acceptance.py:155-156`; `tests/unit/domain/test_comprovante_plan_sharing.py:194-212`. E2E: 30 alertas na v1 (um por atividade sem página) | PASS |
| CMP-08 | JPEG e PNG até 12 MP viram página do tamanho da imagem com a faixa, sem decodificar o JPEG | `tests/unit/infrastructure/test_source_images.py:35-71`, `:89-100` (JPEG de 40 MP sem decodificar, pico de memória); `tests/integration/doc_usecases/test_request_refusals.py:131-137`. E2E: JPEG 1200x800 (150 dpi) virou página de 576x384 mais a faixa de 24 pt (576x408 medido), PNG 800x600 virou 384x288 mais a faixa (384x312), bytes do JPEG idênticos; JPEG de 4000x3100 aceito. Nota: a orientação EXIF é ignorada (D1) | PASS |
| CMP-09 | Mais de 400 páginas ou PDF acima de 60 MB: `COMPROVANTE_GRANDE_DEMAIS`, sem arquivo parcial | `tests/integration/doc_usecases/test_request_refusals.py:77-94` (401 recusa, 400 aceita); `tests/unit/domain/test_comprovante_plan_limits.py:41-55`; `tests/unit/infrastructure/test_comprovante_assembler.py:195-208` (`max_output_bytes=size-1` recusa e `iterdir()` sem sobra). E2E: 401 páginas = 422 `COMPROVANTE_GRANDE_DEMAIS` sem linha criada; 400 páginas (46 MB) = PRONTO; 400 páginas de cerca de 420 KB (168 MB de origem) = pedido aceito, assembleia roda e a linha termina FALHOU `COMPROVANTE_GRANDE_DEMAIS` sem arquivo (diretório de gerados sem sobra). A estimativa no pedido que o design cita não existe (D6) | PASS |
| CMP-10 | Original ausente ou página inexistente: `ORIGINAL_INDISPONIVEL` com documento e página, sem arquivo parcial | `tests/integration/doc_usecases/test_request_refusals.py:97-107`; `tests/integration/doc_usecases/test_run_generation_failure.py:42-57` (original apagado depois do pedido: FALHOU, `version_number is None`, `files == ()`, `stored_files == []`); `tests/unit/infrastructure/test_comprovante_assembler.py:211-250`. E2E: arquivo movido do armazenamento = 422 `O documento foto.jpg não está disponível (página 1).`, nenhuma linha criada | PASS |
| CMP-11 | Uma página por vez, pico até 320 MB com 400 páginas digitalizadas | `tests/integration/documents/test_comprovante_memory.py:58-62` (`peak_mb < 320`, 411 páginas, processo separado); `tests/unit/infrastructure/test_comprovante_assembler.py:159-190` (salva a cada 25 páginas, uma origem aberta por vez). Medido por mim: 400 páginas de 223 KB em 10 PDFs = pico de 82 MB (63 MB na linha de base), 411 páginas, saída de 92 MB. O `peak_rss_mb=306` do log do servidor é o máximo acumulado do processo inteiro e inclui o OCR, não a montagem | PASS |
| CMP-12 | Página rotacionada com recorte menor: rasterizada a 200 dpi, JPEG 92, alerta `PAGINA_RASTERIZADA` | `tests/unit/infrastructure/test_source_images.py:120-133` (`alert.code is PAGINA_RASTERIZADA`, `ext == "jpeg"`, largura `== round(w*200/72)`), `:136-148`, `:151-160`. E2E: página 4 do Alfa (rotação 270, recorte) saiu como imagem na página 13 com o alerta; diferença média de 2,3 níveis contra o original; vista na imagem. Qualidade 92 e recorte em um só eixo sem teste (M28, M29, F2) | PASS |
| CMP-13 | PNG acima de 12 MP: `IMAGEM_GRANDE_DEMAIS` citando o documento, antes de montar, sem arquivo | `tests/integration/doc_usecases/test_request_refusals.py:110-137` (4001x3000 recusa e cita o documento, 4000x3000 aceita, JPEG de mesmo tamanho aceita); `tests/unit/infrastructure/test_source_images.py:74-86` (recusa só pelo cabeçalho). E2E: PNG 4000x3100 = 422 `IMAGEM_GRANDE_DEMAIS` `A imagem grande.png tem mais de 12 megapixels.` | PASS |

### ARR: arranjo do Comprovante

| Req | Resultado da spec | Evidência | Veredito |
| --- | --- | --- | --- |
| ARR-01 | Sem arranjo salvo, deriva dos vínculos por grupo, item e data | `tests/unit/domain/test_comprovante_layout_derivation.py:18-26` (`ids(layout) == [other_group, other_item, early, late]`); `tests/integration/doc_usecases/test_comprovante_layout_read.py:34-52`, `:79` (leitura não grava). E2E: `GET` devolveu `saved False`, `version 0`, plano de 20 páginas | PASS |
| ARR-02 | Acrescentar página de documento do processo, na posição pedida | `tests/integration/doc_usecases/test_comprovante_layout_save.py:64-79` (`pages(...) == [(doc,4),(doc,1)]`, nenhum vínculo criado). E2E: Beta p. 3 acrescentada à atividade 2.12 nº 3 e presente na página 13 do PDF | PASS |
| ARR-03 | Remover página deixa fora do Comprovante sem apagar vínculo | `tests/integration/doc_usecases/test_comprovante_layout_save.py:82-93`; `tests/integration/api/test_generated_comprovante_acceptance.py:179-188` (`"Beta pagina 3" not in pdf_text`, vínculos `[2, 3]`). E2E: Beta p. 3 removida da atividade 2.8 nº 1; a atividade seguiu com `evidences [2, 3]` | PASS |
| ARR-04 | Reordenar atividades e páginas, e a geração usa | `tests/integration/doc_usecases/test_comprovante_layout_save.py:96-111`; `tests/integration/api/test_generated_comprovante_acceptance.py:200-201` (`in_pdf == ["Alfa 2", "Alfa 1"]`). E2E: páginas de 2.7 nº 1 invertidas; o PDF trouxe Alfa 2 e depois Alfa 1 | PASS |
| ARR-05 | Ordem de grupos e itens da tabela; recusa mover atividade de item | `tests/unit/domain/test_comprovante_layout_validation.py:104-125`; `tests/integration/doc_usecases/test_comprovante_layout_save.py:191-202`. E2E: mudar o item = 422 `Uma atividade não muda de item no arranjo.`; trocar a ordem dos itens = 422 `Os grupos e itens seguem a ordem da tabela de pontuação.` | PASS |
| ARR-06 | Documento ou página fora do processo: 404 | `tests/unit/domain/test_comprovante_layout_validation.py:45-51`; `tests/integration/api/test_comprovante_layout_api.py:169-181` (documento de outro processo = 404). E2E: documento desconhecido = 404. **Página 99 de documento de 3 páginas = 422 `PAGINA_FORA_DO_DOCUMENTO`**, não 404 (o design lista 422; a spec diz 404) (D5) | PARTIAL |
| ARR-07 | Versão desatualizada: 409 sem sobrescrever | `tests/integration/api/test_comprovante_layout_api.py:115-132` (`409`, `code == "VERSAO_DESATUALIZADA"`, arranjo mais novo mantido); `tests/integration/doc_usecases/test_comprovante_layout_save.py:204-226`. E2E: segundo `PUT` com `expected_version 0` = 409 | PASS |
| ARR-08 | Atividade revalidada, rejeitada ou movida: aviso de desatualizado e geração só com as atuais | `tests/unit/domain/test_comprovante_staleness.py:37-100`, `:131-170`; `tests/integration/api/test_comprovante_layout_api.py:185-198`. E2E: rejeitar uma atividade deu `stale True` e `ARRANJO_DESATUALIZADO`; o Comprovante v3 trouxe 37 atividades no instantâneo (v2: 38) | PASS |

### VER: versões imutáveis e download

| Req | Resultado da spec | Evidência | Veredito |
| --- | --- | --- | --- |
| VER-01 | Versão numerada (tipo, formato, número, SHA-256, tamanho, autor, data), nunca alterada | `tests/integration/documents/test_generated_schema.py:202-248` (UPDATE de linha final recusado por `immutable`, DELETE por `cannot be deleted`), `:251-281` (`generated_files`); `tests/integration/api/test_generated_versions_acceptance.py:60-79` (`(1, 2)` e hashes diferentes e iguais ao armazenado), `:98-118` (5 comandos SQL diretos recusados). E2E: `psql` no banco real recusou os 5 comandos com as mensagens do gatilho; versões 1 a 5 da Tabela contíguas e a linha FALHOU sem número | PASS |
| VER-02 | Instantâneo: tabela, total e subtotais, atividades (grupo, item, quantidade), arranjo, alertas | `tests/unit/domain/test_generation_snapshot.py:44-90`, `:129-153`. E2E (consulta ao banco): chaves `table_version, interstice, total, subtotals, pit_hours, pit_total_hours, activities, excluded, layout, alerts`; `total "211.00"`, 38 atividades `{group, item, quantity, points, status}` | PASS |
| VER-03 | Download do arquivo gravado, tipo de conteúdo, nome montado no servidor | `tests/integration/api/test_generated_versions_acceptance.py:82-95` (`download.content == stored`, `etag == f'"{sha256}"'`, v1 após as mudanças); `tests/integration/doc_usecases/test_generated_versions.py:105-116` (`"Tabela_de_Pontuacao_2022-2024_v1.pdf"`); `tests/unit/domain/test_download_names.py:34-59`. E2E: `Content-Disposition: attachment; filename*=UTF-8''Tabela_de_Pontuacao_2022-2024_v2.pdf`, tipo `application/pdf` e `...wordprocessingml.document`, sem o nome do docente; v1 baixada depois da v2 e da mudança = bytes idênticos e SHA-256 igual ao gravado | PASS |
| VER-04 | Em andamento: estado GERANDO; segundo pedido igual = 409 | `tests/integration/api/test_generated_documents_api.py:62-70` (409, `GERACAO_EM_ANDAMENTO`, outro tipo 202); `tests/integration/documents/test_generated_schema.py:100-105` (índice parcial único). E2E: pedido duplicado durante GERANDO = 409 nos três tipos | PASS |
| VER-05 | Falha: FALHOU com código e mensagem sem dados pessoais, sem arquivo parcial, nova tentativa | `tests/integration/doc_usecases/test_run_generation_failure.py:74-84` (falha no 2º formato apaga o 1º, não gasta versão, nova tentativa = versão 1), `:101-110`, `:113-126`; `tests/integration/doc_usecases/test_request_generation.py:85`. E2E: FALHOU `COMPROVANTE_GRANDE_DEMAIS` com mensagem fixa e diretório sem sobra | PASS |
| VER-06 | Fora do acesso: 404 em qualquer operação | `tests/integration/api/test_generated_documents_api.py:172-181` (4 rotas = 404); `tests/integration/doc_usecases/test_generated_versions.py:166-178`. E2E: download sem sessão = 401 | PASS |
| VER-07 | Auditoria ao pedir, terminar e falhar, sem texto | `tests/integration/doc_usecases/test_request_generation.py:139-154` (`changes == {"kind":..., "state":...}`); `tests/integration/doc_usecases/test_run_generation_table.py:110-127`; `tests/integration/doc_usecases/test_run_generation_failure.py:113-126`; `tests/integration/doc_usecases/test_generated_versions.py:119-137`. E2E: `audit_logs` com CREATE, STATUS e UPDATE (DOWNLOAD); nenhuma linha contém nome do docente, do arquivo ou título | PASS |
| VER-08 | Reinício com geração em andamento: FALHOU `INTERROMPIDA` | `tests/integration/doc_usecases/test_recover_generations.py:58-81`, `:84-98`, `:106-127`. E2E: linha GERANDO iniciada + servidor morto com SIGKILL + nova partida = FALHOU `INTERROMPIDA` (`A geração foi interrompida pela reinicialização do servidor.`), a linha ainda não iniciada rodou e virou PRONTO, `removed_files=2` (um `.tmp-` e um arquivo órfão), auditoria `INTERROMPIDA` | PASS |
| VER-09 | Todas as versões ficam e o tamanho aparece no histórico | `tests/integration/api/test_generated_versions_acceptance.py:121-130` (`file["size_bytes"] == len(content) > 0`); `tests/integration/doc_usecases/test_generated_versions.py:189`. E2E: lista com as 5 versões da Tabela e `size_bytes` de cada arquivo | PASS |

---

## 3. Fluxo real ponta a ponta

Ambiente: `uvicorn --factory app.main:create_app` (cópia exata de `backend/`) com o worker ligado, PostgreSQL 16 descartável, `MARITALK_*` ausente, armazenamento no scratchpad. Dados 100% sintéticos (docente e processo inventados, PDFs e imagens gerados em código).

1. Processo FASI 2022-2024 com a tabela oficial escolhida e as 38 atividades do cenário de 211 pontos: `GET /scoring` = 211,00 e subtotais 0, 52, 7, 62, 0, 30, 4, 56.
2. Quatro documentos enviados: `alfa.pdf` (4 páginas: texto com JPEG; rotacionada 90 graus com carimbo; paisagem; recorte com rotação 270), `beta.pdf` (3 páginas), `foto.jpg` (1200x800) e `recibo.png` (800x600). 11 vínculos criados.
3. Tabela, Relatório e Comprovante gerados e baixados. Tabela: PDF de 2 páginas e DOCX de 2 páginas (LibreOffice em modo sem cabeça só para renderizar). Comprovante: 20 páginas, 3 de sumário, 7 separadores, 9 originais.
4. Arranjo editado e salvo (inversão, remoção, acréscimo), 409 e 422 conferidos, Comprovante e Tabela regerados, atividade rejeitada, regeração.
5. Limites: 401 páginas, 400 páginas distintas (46 MB), PNG 4000x3100, JPEG 4000x3100, saída acima de 60 MB.
6. Reinício forçado com linhas GERANDO e arquivos órfãos.

Imagens renderizadas e vistas: Tabela p. 1 (PDF e a conversão do DOCX), sumário do Comprovante p. 2, página 8 (original rotacionada com carimbo e faixa "Comprovante p. 8") e página 13 (rasterizada). Sem defeito visual além dos listados em D4, D7 e D11.

## 4. Cálculos independentes

- **Numeração do Comprovante do E2E**, derivada da spec sem olhar o PDF: linhas do sumário = 7 grupos + 14 itens + 2 x 38 atividades = 97; capacidade de 44 linhas por página => 3 páginas de sumário; capa 1, sumário 2 a 4, separador do grupo I na 5, separador do II na 6, Alfa 1 e Alfa 2 nas 7 e 8, Beta 1 na 9 (a atividade 2.7 nº 2 remete à 7), Beta 2 e 3 nas 10 e 11, Alfa 3 na 12, Alfa 4 na 13, separador do III na 14 (a atividade 3.2 remete à 9), IV na 15, foto e recibo nas 16 e 17, VI, VII e VIII nas 18, 19 e 20. O PDF e o plano da API coincidem página a página (20 páginas).
- **Tabela x Comprovante**: cada número da coluna "Comprovante" da Tabela regerada (9, 10, 11, 12, 13, 16, 17) cai na página do Comprovante que traz o documento citado na mesma atividade; o `plan_hash` gravado coincide entre a Tabela v3 e o Comprovante v2 (`c0bafefa1c96`) e entre a Tabela v4 e o Comprovante v3 (`512ce77f73e1`), e a Tabela v3 saiu sem `NUMERACAO_DIVERGENTE`.
- **211 pontos**: 52 + 7 + 62 + 0 + 30 + 4 + 56 = 211; horas de PIT 24 + 24 + 24 + 20 = 92, lidas do PDF e do DOCX.
- **Comprovante de 400 páginas**: 1 capa + 2 sumários + 1 + 8 separadores + 400 = 411 páginas na medição de memória; no E2E de 400 originais em 10 documentos o PDF saiu com 404 páginas.

---

## 5. Sensor de discriminação (mutantes)

Método: cópia isolada de `backend/` no scratchpad (a árvore do repositório nunca foi tocada); cada mutante troca um trecho exato (padrão confirmado uma única vez), roda os testes do escopo e é desfeito. Conjunto unitário primeiro (387 testes); se sobrevive, o conjunto de integração em PostgreSQL (208 testes, 3 containers descartáveis); mutantes de migração rodam em banco novo. `KILLED` = algum teste falhou; a coluna "Teste que matou" é o primeiro a falhar.

| ID | Req | Arquivo | Mutação | Rodou | Resultado | Primeiro teste que falhou |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | CMP-04 | `domain/rules/comprovante_plan.py` | TOC pages floor instead of ceil | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_the_plan_of_the_tabela_is_still_computed_when_the_originals_are_gone` |
| M02 | CMP-04 | `domain/rules/comprovante_plan.py` | TOC page numbers start at 1 | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_400_attached_pages_pass` |
| M03 | CMP-04 | `domain/rules/comprovante_plan.py` | original page number off by one | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_400_attached_pages_pass` |
| M04 | CMP-04 | `domain/rules/comprovante_plan.py` | separator numbered one too high | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_400_attached_pages_pass` |
| M05 | CMP-06 | `domain/rules/comprovante_plan.py` | justified repeat ignored (always remission) | unitário | morto | `u/domain/test_comprovante_plan_sharing.py::test_a_justified_repeat_attaches_the_page_again` |
| M06 | CMP-05 | `domain/rules/comprovante_plan.py` | remission points to wrong page | unitário | morto | `u/domain/test_comprovante_plan_sharing.py::test_the_first_activity_attaches_the_page_and_the_second_points_to_it` |
| M07 | CMP-04 | `domain/rules/comprovante_plan.py` | TOC lines of an activity counted as 1 | unitário | morto | `u/domain/test_comprovante_plan_pages.py::test_the_cover_is_page_one_and_the_table_of_contents_follows` |
| M08 | CMP-04 | `domain/rules/comprovante_plan.py` | activity range includes remissions | unitário | morto | `u/domain/test_comprovante_plan_sharing.py::test_the_range_of_an_activity_counts_only_the_pages_attached_for_it` |
| M09 | CMP-07 | `domain/rules/comprovante_plan.py` | no ATIVIDADE_SEM_COMPROVANTE alert | unitário | morto | `u/domain/test_comprovante_plan_sharing.py::test_an_activity_without_a_page_raises_atividade_sem_comprovante` |
| M10 | CMP-05 | `domain/rules/comprovante_plan.py` | plan hash ignores the document of a page | unitário+integração | **sobreviveu** | — |
| M11 | CMP-09 | `domain/rules/comprovante_plan.py` | 400 pages refused (boundary) | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_400_attached_pages_pass` |
| M12 | CMP-13 | `domain/rules/comprovante_plan.py` | 12 MP PNG refused (boundary) | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_a_png_of_12_megapixels_passes` |
| M13 | CMP-10 | `domain/rules/comprovante_plan.py` | last page of a document unavailable | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_a_page_beyond_the_document_is_original_indisponivel_with_document_and_page` |
| M14 | CMP-09 | `domain/rules/comprovante_plan.py` | default page limit 401 | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_401_attached_pages_are_refused_with_comprovante_grande_demais` |
| M15 | CMP-13 | `domain/rules/comprovante_plan.py` | default PNG limit 13 MP | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_a_png_of_12_megapixels_and_one_pixel_is_refused_citing_the_document` |
| M16 | CMP-07 | `domain/rules/comprovante_plan.py` | activity without page has no note | unitário | morto | `u/domain/test_comprovante_plan_sharing.py::test_an_activity_without_a_page_enters_with_the_line_sem_comprovante_anexado` |
| M17 | CMP-13 | `domain/rules/comprovante_plan.py` | JPEG refused instead of PNG | unitário | morto | `u/domain/test_comprovante_plan_limits.py::test_a_png_of_12_megapixels_and_one_pixel_is_refused_citing_the_document` |
| M20 | CMP-03 | `infra/documents/source_pages.py` | divider line drawn over the original (invades 0.25pt) | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_the_attached_pages_are_identical_to_the_originals` |
| M21 | CMP-03 | `infra/documents/source_pages.py` | strip 20 pt | unitário | morto | `u/infrastructure/test_source_pages.py::test_the_sheet_is_the_page_plus_a_strip_of_24_points` |
| M22 | CMP-03 | `infra/documents/source_pages.py` | original shifted down, strip above | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_the_attached_pages_are_identical_to_the_originals` |
| M23 | CMP-03 | `infra/documents/source_pages.py` | rotation not prepared | unitário | morto | `u/infrastructure/test_source_pages_rotation.py::test_a_rotated_page_keeps_its_rotation_pixel_by_pixel[90]` |
| M24 | CMP-03 | `infra/documents/source_pages.py` | annotations and fields not prepared | unitário | morto | `u/infrastructure/test_source_pages_rotation.py::test_annotations_and_fields_stay_visible_within_one_gray_level[stamp]` |
| M25 | CMP-03 | `infra/documents/source_pages.py` | annotations not baked | unitário | morto | `u/infrastructure/test_source_pages_rotation.py::test_annotations_and_fields_stay_visible_within_one_gray_level[stamp]` |
| M26 | CMP-03 | `infra/documents/source_pages.py` | rasterize any rotated or cropped page | unitário | morto | `u/infrastructure/test_source_pages_rotation.py::test_a_rotated_page_keeps_its_rotation_pixel_by_pixel[90]` |
| M27 | CMP-12 | `infra/documents/source_pages.py` | raster dpi 150 | unitário | morto | `u/infrastructure/test_source_images.py::test_a_rotated_page_with_a_smaller_crop_is_rasterized_at_200_dpi_with_an_alert` |
| M28 | CMP-12 | `infra/documents/source_pages.py` | raster jpeg quality 60 | unitário+integração | **sobreviveu** | — |
| M29 | CMP-12 | `infra/documents/source_pages.py` | crop check needs both axes | unitário+integração | **sobreviveu** | — |
| M30 | CMP-13 | `infra/documents/source_pages.py` | attach_image PNG boundary | unitário | morto | `u/infrastructure/test_source_images.py::test_a_png_of_12_megapixels_enters_and_one_more_pixel_is_refused_before_decoding` |
| M31 | CMP-08 | `infra/documents/source_pages.py` | JPEG also refused above the limit | unitário | morto | `u/infrastructure/test_source_images.py::test_a_jpeg_of_40_megapixels_enters_without_being_decoded` |
| M32 | CMP-08 | `infra/documents/source_pages.py` | default image dpi 72 | unitário | morto | `u/infrastructure/test_source_images.py::test_an_image_without_dpi_is_taken_as_150_dpi` |
| M33 | CMP-12 | `infra/documents/source_pages.py` | huge image page not scaled down | unitário | morto | `u/infrastructure/test_source_images.py::test_a_huge_page_is_scaled_down_to_14400_points_on_the_longest_side` |
| M34 | CMP-03 | `infra/documents/comprovante_assembler.py` | footer number off by one | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_a_process_of_three_groups_and_five_activities_is_assembled_as_planned` |
| M35 | CMP-09 | `infra/documents/comprovante_assembler.py` | output limit not enforced | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_an_output_above_the_limit_fails_and_leaves_no_file` |
| M36 | CMP-09 | `infra/documents/comprovante_assembler.py` | default output limit 61 MB | unitário+integração | **sobreviveu** | — |
| M37 | CMP-09 | `infra/documents/comprovante_assembler.py` | partial target left on failure | unitário+integração | **sobreviveu** | — |
| M38 | CMP-10 | `infra/documents/comprovante_assembler.py` | last page of a PDF source unavailable | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_the_file_is_saved_every_25_pages_while_it_is_built` |
| M39 | CMP-10 | `infra/documents/comprovante_assembler.py` | missing original not detected by assembler | unitário+integração | **sobreviveu** | — |
| M40 | CMP-11 | `infra/documents/comprovante_assembler.py` | no incremental checkpoint (memory) | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_the_file_is_saved_every_25_pages_while_it_is_built` |
| M41 | CMP-04 | `infra/documents/front_matter.py` | TOC shows 'p. N a N' for single pages | unitário+integração | **sobreviveu** | — |
| M42 | CMP-04 | `infra/documents/front_matter.py` | footer label off by one | unitário | morto | `u/infrastructure/test_front_matter.py::test_the_table_of_contents_has_the_pages_the_plan_predicts[1]` |
| M43 | CMP-02 | `infra/documents/front_matter.py` | TOC origin shows comprovante page as source page | unitário+integração | **sobreviveu** | — |
| M50 | TAB-04 | `domain/rules/table_document.py` | total re-summed from rows | unitário+integração | **sobreviveu** | — |
| M51 | TAB-04 | `domain/rules/table_document.py` | subtotal re-summed from rows | unitário | morto | `u/domain/test_table_document_rows.py::test_the_band_subtotal_is_the_one_of_the_engine_even_when_a_limit_cuts_the_rows` |
| M52 | TAB-03 | `domain/rules/table_document.py` | group I band shown | unitário | morto | `u/domain/test_table_document_rows.py::test_the_211_scenario_has_seven_bands_with_the_group_subtotals` |
| M53 | TAB-05 | `domain/rules/table_document.py` | PIT hours section inverted | unitário | morto | `u/domain/test_table_document_totals.py::test_the_pit_hours_of_the_scenario_are_24_24_24_and_20_with_a_total_of_92` |
| M54 | TAB-05 | `domain/rules/table_document.py` | PIT rows in the bands | unitário+integração | **sobreviveu** | — |
| M55 | TAB-03 | `domain/rules/table_document.py` | comprovante column inverted | unitário | morto | `u/domain/test_table_document_rows.py::test_the_columns_of_a_row_are_item_title_quantity_unit_total_voucher_and_status` |
| M56 | TAB-06 | `domain/rules/table_document.py` | limit alerts inverted | unitário | morto | `u/domain/test_table_document_totals.py::test_a_limit_applied_appears_with_the_text_of_the_engine` |
| M57 | TAB-03 | `domain/rules/table_document.py` | quantity and unit points swapped | unitário | morto | `u/domain/test_table_document_rows.py::test_the_columns_of_a_row_are_item_title_quantity_unit_total_voucher_and_status` |
| M58 | TAB-03 | `domain/rules/table_document.py` | bands in reverse group order | unitário | morto | `u/domain/test_table_document_rows.py::test_the_211_scenario_has_seven_bands_with_the_group_subtotals` |
| M59 | TAB-03 | `domain/rules/table_document.py` | wrong roman numeral | unitário | morto | `u/infrastructure/test_table_docx.py::test_the_211_scenario_has_the_total_the_subtotals_and_the_pit_hours` |
| M60 | TAB-03 | `domain/rules/table_document.py` | items in reverse order | unitário | morto | `u/domain/test_table_document_rows.py::test_rows_follow_the_items_of_the_group_and_keep_the_order_inside_an_item` |
| M61 | TAB-03 | `infra/documents/table_pdf.py` | PDF header row not repeated | unitário | morto | `u/infrastructure/test_table_pdf.py::test_the_header_row_repeats_on_every_page_of_a_thousand_rows` |
| M62 | TAB-03 | `infra/documents/table_docx.py` | DOCX header row not repeated | unitário | morto | `u/infrastructure/test_table_docx.py::test_the_first_row_is_a_header_row_that_repeats_and_no_other_row_is` |
| M63 | TAB-02 | `infra/documents/table_text.py` | norm reference missing from the header | unitário | morto | `u/infrastructure/test_table_docx.py::test_the_header_names_the_professor_the_classes_the_unit_the_interstice_and_the_table` |
| M64 | TAB-04 | `infra/documents/table_text.py` | counter of vouchers wrong | unitário+integração | **sobreviveu** | — |
| M70 | VER-02 | `domain/rules/generation_snapshot.py` | snapshot lists activities left out | unitário | morto | `u/domain/test_generation_snapshot.py::test_only_the_listed_activities_are_in_the_snapshot` |
| M71 | VER-02 | `domain/rules/generation_snapshot.py` | Comprovante snapshot without layout | unitário | morto | `u/domain/test_generation_snapshot.py::test_layout_and_report_only_appear_in_their_own_kinds[COMPROVANTE-layout-report]` |
| M72 | VER-03 | `domain/rules/download_names.py` | download name version off by one | unitário | morto | `u/domain/test_download_names.py::test_the_six_names_follow_kind_interstice_and_version[TABELA-PDF-Tabela_de_Pontuacao_2020-2024_v2.pdf]` |
| M73 | VER-03 | `domain/rules/download_names.py` | download name interstice wrong | unitário | morto | `u/domain/test_download_names.py::test_the_six_names_follow_kind_interstice_and_version[TABELA-PDF-Tabela_de_Pontuacao_2020-2024_v2.pdf]` |
| M74 | VER-01 | `infra/database/repositories.py` | version number skips | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_a_failure_in_the_second_format_removes_the_first_and_spends_no_version` |
| M75 | VER-01 | `infra/database/repositories.py` | close() accepts a finished row (app guard) | unitário+integração | morto | `int/documents/test_generation_repository.py::test_a_finished_generation_cannot_be_finished_again` |
| M76 | VER-08 | `infra/database/repositories.py` | recovers rows not started instead of started | unitário+integração | morto | `int/doc_usecases/test_recover_generations.py::test_started_generations_and_wordings_are_interrupted_and_the_waiting_ones_stay_queued` |
| M77 | VER-08 | `infra/database/repositories.py` | interrupted gets ERRO_INTERNO | unitário+integração | morto | `int/doc_usecases/test_recover_generations.py::test_started_generations_and_wordings_are_interrupted_and_the_waiting_ones_stay_queued` |
| M78 | VER-04 | `infra/database/repositories.py` | claim_next reclaims started rows | unitário+integração | morto | `int/doc_usecases/test_recover_generations.py::test_started_generations_and_wordings_are_interrupted_and_the_waiting_ones_stay_queued` |
| M79 | VER-04 | `infra/database/repositories.py` | duplicate GERANDO not mapped to 409 | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_a_second_equal_request_while_one_is_generating_is_a_conflict` |
| M80 | ARR-07 | `infra/database/repositories.py` | stale layout version accepted | unitário+integração | morto | `int/doc_usecases/test_comprovante_layout_save.py::test_an_outdated_version_is_a_409_and_the_newer_arrangement_is_not_overwritten` |
| M81 | ARR-07 | `infra/database/repositories.py` | first save with version != 0 accepted | unitário+integração | morto | `int/documents/test_layout_repository.py::test_a_first_save_with_a_version_other_than_0_is_stale_and_stores_nothing` |
| M90 | TAB-08 | `use_cases/generated_documents.py` | TABELA_NAO_ESCOLHIDA check removed | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_a_process_without_a_chosen_table_is_refused_and_no_row_is_created` |
| M91 | TAB-07 | `use_cases/generated_documents.py` | SEM_ATIVIDADES_VALIDADAS check removed | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_a_process_with_no_validated_activity_is_refused_and_no_row_is_created` |
| M92 | CMP-09 | `use_cases/generated_documents.py` | free-space check inverted | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_a_request_stores_a_generating_row_of_the_kind_for_the_actor[TABELA]` |
| M93 | VER-05 | `use_cases/generated_documents.py` | refusal codes collapse into ERRO_INTERNO | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_an_original_deleted_after_the_request_fails_with_a_fixed_message_and_no_file` |
| M94 | VER-05 | `use_cases/generated_documents.py` | temporary files left after a failure | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_a_failure_in_the_second_format_removes_the_first_and_spends_no_version` |
| M95 | VER-05 | `use_cases/generated_documents.py` | renamed files left after a failure | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_a_file_already_renamed_is_deleted_when_a_later_step_fails` |
| M96 | TAB-03 | `use_cases/generated_documents.py` | Tabela quotes the last page instead of the first | unitário+integração | **sobreviveu** | — |
| M97 | CMP-04 | `use_cases/generated_documents.py` | NUMERACAO_DIVERGENTE inverted | unitário+integração | morto | `int/doc_usecases/test_run_generation_comprovante.py::test_table_and_comprovante_from_the_same_layout_share_the_hash_and_do_not_diverge` |
| M98 | VER-01 | `use_cases/generated_documents.py` | hash not updated by chunks (constant hash) | unitário+integração | morto | `int/doc_usecases/test_run_generation_table.py::test_each_file_has_the_hash_and_the_size_of_what_is_stored` |
| M99 | VER-06 | `use_cases/generated_documents.py` | download/read without access check | unitário+integração | morto | `int/doc_usecases/test_generated_versions.py::test_another_professor_gets_not_found_for_list_read_and_download` |
| M100 | VER-07 | `use_cases/generated_documents.py` | audit payload of the request gains an extra key | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_the_request_is_audited_with_the_kind_and_the_state_and_no_text` |
| M101 | VER-08 | `use_cases/generated_documents.py` | recovery leaves temp files and orphans | unitário+integração | morto | `int/doc_usecases/test_recover_generations.py::test_temporary_files_and_files_without_a_row_go_and_the_files_of_a_row_stay` |
| M102 | VER-07 | `use_cases/generated_documents.py` | no audit when a generation fails | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_the_failure_is_audited_with_the_code_and_no_content` |
| M103 | VER-07 | `use_cases/generated_documents.py` | no audit when a generation is requested | unitário+integração | morto | `int/doc_usecases/test_request_generation.py::test_the_request_is_audited_with_the_kind_and_the_state_and_no_text` |
| M104 | VER-07 | `use_cases/generated_documents.py` | no audit when a generation ends | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_an_output_above_the_limit_fails_and_leaves_no_file` |
| M105 | VER-03 | `use_cases/generated_documents.py` | no audit on download | unitário+integração | morto | `int/doc_usecases/test_generated_versions.py::test_a_download_is_audited_with_the_operation_and_the_format_and_no_content` |
| M106 | VER-03 | `use_cases/generated_documents.py` | wrong PDF content type | unitário+integração | morto | `int/doc_usecases/test_generated_versions.py::test_the_download_has_the_server_made_name_the_type_and_the_hash_for_the_etag` |
| M107 | VER-03 | `presentation/api/generated_documents.py` | no nosniff header | unitário+integração | morto | `int/api/test_generated_documents_api.py::test_the_download_gives_the_stored_file_with_its_type_a_plain_name_and_the_sha256_etag[docx-application/vnd.openxmlformats-officedocument.wordprocessingml.document-PK]` |
| M108 | VER-03 | `presentation/api/generated_documents.py` | ETag is not the SHA-256 | unitário+integração | morto | `int/api/test_generated_versions_acceptance.py::test_version_1_downloaded_after_the_changes_is_the_stored_file_byte_for_byte` |
| M110 | VER-05 | `infra/storage/generated_storage.py` | cleanup deletes referenced files | unitário | morto | `u/infrastructure/test_generated_storage.py::test_cleanup_removes_temp_files_and_files_without_a_row_and_keeps_the_referenced` |
| M111 | VER-05 | `infra/storage/generated_storage.py` | generated files world-readable | unitário | morto | `u/infrastructure/test_generated_storage.py::test_committed_file_lives_in_generated_process_dir_with_permissions_0700_and_0600` |
| M112 | VER-05 | `infra/storage/generated_storage.py` | commit accepts any path | unitário | morto | `u/infrastructure/test_generated_storage.py::test_commit_refuses_a_file_that_is_not_a_temp_of_the_process` |
| M113 | ARR-05 | `domain/rules/comprovante_plan.py` | activities may be out of group/item order | unitário | morto | `u/domain/test_comprovante_layout_validation.py::test_putting_the_items_out_of_the_order_of_the_table_is_refused` |
| M114 | ARR-05 | `domain/rules/comprovante_plan.py` | activity may move to another item | unitário | morto | `u/domain/test_comprovante_layout_validation.py::test_moving_an_activity_to_another_item_is_refused` |
| M115 | ARR-06 | `domain/rules/comprovante_plan.py` | last page of a document rejected in layout | unitário | morto | `u/domain/test_comprovante_layout_validation.py::test_a_layout_with_documents_and_pages_of_the_process_is_accepted` |
| M116 | ARR-06 | `domain/rules/comprovante_plan.py` | foreign document silently skipped (no 404) | unitário | morto | `u/domain/test_comprovante_layout_validation.py::test_a_document_of_another_process_is_not_found` |
| M117 | ARR-01 | `domain/rules/comprovante_plan.py` | derived layout sorted by title not table order | unitário | morto | `u/domain/test_comprovante_layout_derivation.py::test_without_a_saved_layout_activities_come_by_group_item_and_date` |
| M118 | ARR-01 | `domain/rules/activity_order.py` | undated activities first | unitário | morto | `u/domain/test_comprovante_layout_derivation.py::test_an_undated_activity_goes_after_the_dated_ones_of_its_item` |
| M119 | ARR-08 | `domain/rules/comprovante_plan.py` | moved item not detected as stale | unitário | morto | `u/domain/test_comprovante_staleness.py::test_an_activity_that_changed_item_makes_it_stale` |
| M120 | ARR-08 | `domain/rules/comprovante_plan.py` | new link not detected as stale | unitário | morto | `u/domain/test_comprovante_staleness.py::test_a_new_link_makes_the_layout_stale` |
| M121 | ARR-08 | `domain/rules/comprovante_plan.py` | current_layout keeps stale item numbers | unitário | morto | `u/domain/test_comprovante_staleness.py::test_the_generation_layout_takes_the_current_item_of_an_activity_that_moved` |
| M122 | ARR-03 | `domain/rules/comprovante_plan.py` | layout derivation indexes an unknown activity (KeyError) | unitário | morto | `u/domain/test_comprovante_layout_derivation.py::test_the_links_of_activities_left_out_are_ignored` |
| M123 | TAB-07 | `domain/rules/activity_order.py` | pending activities enter the documents | unitário | morto | `u/domain/test_comprovante_layout_derivation.py::test_only_validated_activities_with_group_and_item_are_arranged` |
| M130 | VER-01 | `alembic/0006_generated_documents.py` | trigger lets a finished version change (0006) | integração | **sobreviveu** | — |
| M131 | VER-01 | `alembic/0006_generated_documents.py` | generated_files UPDATE allowed (0006) | integração | **sobreviveu** | — |
| M132 | VER-04 | `alembic/0006_generated_documents.py` | partial unique index of GERANDO not unique | integração | morto | `int/doc_usecases/test_request_generation.py::test_a_second_equal_request_while_one_is_generating_is_a_conflict` |
| M133 | VER-01 | `alembic/0006_generated_documents.py` | no unique (process, kind, version) | integração | morto | `int/documents/test_generated_schema.py::test_the_version_number_is_unique_per_process_and_kind` |
| M134 | VER-01 | `alembic/0007_process_purge.py` | generated_documents DELETE allowed everywhere (0007) | integração | morto | `int/documents/test_generated_schema.py::test_a_generated_document_cannot_be_deleted[generating]` |
| M135 | VER-01 | `alembic/0007_process_purge.py` | generated_files DELETE allowed everywhere (0007) | integração | morto | `int/documents/test_generated_schema.py::test_a_generated_file_cannot_be_deleted` |
| B01 | CMP-09 | `core/config.py` | default output limit setting 61 MB | unitário | morto | `u/test_config_generation.py::test_defaults_hold_without_any_environment_variable` |
| B02 | CMP-09 | `core/config.py` | default page limit setting 401 | unitário | morto | `u/test_config_generation.py::test_defaults_hold_without_any_environment_variable` |
| B03 | CMP-13 | `core/config.py` | default PNG limit setting 13 | unitário | morto | `u/test_config_generation.py::test_defaults_hold_without_any_environment_variable` |
| B04 | CMP-09 | `presentation/dependencies.py` | wiring: output limit x100 | unitário+integração | **sobreviveu** | — |
| B05 | CMP-09 | `presentation/dependencies.py` | wiring: page limit ignored | unitário+integração | **sobreviveu** | — |
| B06 | CMP-13 | `presentation/dependencies.py` | wiring: PNG limit ignored | unitário+integração | **sobreviveu** | — |
| B12 | VER-04 | `infra/database/repositories.py` | latest ready = oldest ready | unitário+integração | morto | `int/documents/test_generation_repository.py::test_the_latest_ready_version_per_kind_ignores_failed_and_generating_rows` |
| B13 | VER-09 | `infra/database/repositories.py` | history lists the running row last | unitário+integração | morto | `int/doc_usecases/test_generated_versions.py::test_the_list_has_the_running_one_first_then_the_newest_with_the_data_of_each` |
| B14 | VER-02 | `domain/rules/generation_snapshot.py` | snapshot total zero | unitário | morto | `u/domain/test_generation_snapshot.py::test_the_snapshot_keeps_the_interstice_total_and_every_group_subtotal` |
| B16 | VER-02 | `domain/rules/generation_snapshot.py` | snapshot pit hours = total | unitário | morto | `u/domain/test_generation_snapshot.py::test_the_snapshot_keeps_the_pit_hours_by_period_and_in_total` |
| B17 | VER-03 | `use_cases/generated_documents.py` | download name always v1 | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_an_output_above_the_limit_fails_and_leaves_no_file` |
| B19 | VER-05 | `infra/storage/generated_storage.py` | generated directories world-readable | unitário | morto | `u/infrastructure/test_generated_storage.py::test_committed_file_lives_in_generated_process_dir_with_permissions_0700_and_0600` |
| B22 | CMP-01 | `infra/documents/front_matter.py` | cover without the interstice | unitário | morto | `u/infrastructure/test_front_matter.py::test_the_cover_identifies_the_professor_class_level_unit_and_interstice` |
| B23 | CMP-01 | `infra/documents/front_matter.py` | group title with arabic numeral | unitário | morto | `u/infrastructure/test_front_matter.py::test_every_entry_of_the_table_of_contents_shows_its_first_page` |
| B24 | CMP-04 | `infra/documents/front_matter.py` | separator without its number | unitário | morto | `u/infrastructure/test_front_matter.py::test_the_cover_has_no_number_and_the_other_generated_pages_have_their_own` |
| B27 | TAB-04 | `use_cases/generated_documents.py` | left-out alert inverted | unitário+integração | morto | `int/doc_usecases/test_run_generation_comprovante.py::test_a_page_linked_only_to_a_document_outside_the_interstice_is_not_attached` |
| B28 | CMP-09 | `use_cases/generated_documents.py` | no plan check at request time | unitário+integração | morto | `int/doc_usecases/test_request_refusals.py::test_401_attached_pages_refuse_the_comprovante` |
| B29 | CMP-13 | `use_cases/generated_documents.py` | big unused PNG blocks the Comprovante | unitário+integração | **sobreviveu** | — |
| B31 | VER-05 | `use_cases/generated_documents.py` | failure message leaks the exception text | unitário+integração | morto | `int/doc_usecases/test_run_generation_failure.py::test_an_original_deleted_after_the_request_fails_with_a_fixed_message_and_no_file` |
| B32 | VER-01 | `use_cases/generated_documents.py` | size counted by chunks | unitário+integração | morto | `int/doc_usecases/test_run_generation_table.py::test_each_file_has_the_hash_and_the_size_of_what_is_stored` |
| B34 | CMP-04 | `domain/rules/comprovante_plan.py` | TOC group line count | unitário | morto | `u/domain/test_comprovante_plan_pages.py::test_the_table_of_contents_takes_ceil_of_its_lines_over_the_capacity[17]` |
| B35 | CMP-04 | `domain/rules/comprovante_plan.py` | TOC item line count | unitário | morto | `u/domain/test_comprovante_plan_pages.py::test_the_table_of_contents_takes_ceil_of_its_lines_over_the_capacity[17]` |
| B38 | ARR-06 | `domain/rules/comprovante_plan.py` | unknown activity silently skipped in layout | unitário | morto | `u/domain/test_comprovante_layout_validation.py::test_an_activity_that_is_not_validated_in_the_process_is_not_found` |
| B39 | ARR-08 | `use_cases/comprovante_layout.py` | layout saved without its base links | unitário+integração | morto | `int/doc_usecases/test_comprovante_layout_save.py::test_the_saved_arrangement_reads_back_as_saved_and_not_stale` |
| B40 | CMP-03 | `infra/documents/comprovante_assembler.py` | generated pages all copied from page 0 | unitário | morto | `u/infrastructure/test_comprovante_assembler.py::test_a_process_of_three_groups_and_five_activities_is_assembled_as_planned` |
| B41 | CMP-03 | `infra/documents/comprovante_assembler.py` | encrypted original not refused | unitário+integração | **sobreviveu** | — |
| C01 | VER-01 | `alembic/0007_process_purge.py` | effective trigger (0007) lets a finished version change | integração | morto | `int/documents/test_generated_schema.py::test_a_finished_generation_cannot_be_updated[ready]` |
| C02 | VER-01 | `alembic/0007_process_purge.py` | effective trigger (0007) lets a generated file change | integração | morto | `int/documents/test_generated_schema.py::test_a_generated_file_cannot_be_updated` |

Mortos por família: TAB: 16/20, CMP: 45/58, ARR: 14/14, VER: 41/43. Mortos já no conjunto unitário: 78; só pela integração ou pelo PostgreSQL: 38.

Áreas pedidas: plano de numeração compartilhado (M01 a M10, M96, B34, B35), faixa de rodapé e pixels originais (M20 a M22, M34, B40), rotação e anotações (M23 a M29), limites 400 páginas, 60 MB e 12 MP (M11 a M17, M30, M35, M36, B01 a B06), versão e gatilho de imutabilidade (M74, M75, M130 a M135, C01, C02), `INTERROMPIDA` (M76, M77, M101), nome de download sem o docente (M72, M73, B17), totais e 211 pontos da Tabela (M50 a M64), transições de estado indevidas (M75, M78, M79).

---

## 6. Defeitos e achados

Severidade: Blocker (impede o uso), High (dado errado ou perda), Medium (resultado errado em caso plausível ou lacuna de teste em regra central), Low (cosmético, caso raro ou lacuna de teste menor).

| ID | Sev. | Achado | Evidência | Requisito |
| --- | --- | --- | --- | --- |
| D1 | Medium | A orientação EXIF de um JPEG é ignorada: uma foto de celular com orientação 6 entra no Comprovante deitada. Nada no sistema trata EXIF (`grep -rni "exif\|orientation\|transpose" app` não acha tratamento) | Sonda: JPEG 1200x800 com EXIF 6 e um bloco vermelho no canto superior esquerdo gera página 576x408 (paisagem) com o bloco à esquerda; honrando o EXIF seria 384x576 com o bloco à direita | CMP-08 (spec silenciosa) |
| D2 | Medium | Teste ausente: se o total da Tabela passasse a ser recalculado pela soma das linhas, nada falharia (M50). Com um limite de critério a 40 pontos o documento diria `Pontuação geral: 160,00` e `Subtotal: 40,00` | M50 sobreviveu; sonda manual com o cenário de `test_table_document_rows.py:165-180` deu `total 160,00` com `subtotal 40,00` | TAB-04 |
| D3 | Medium | Teste ausente: a Tabela cita o número da primeira página da atividade; trocar por última página não falha nenhum teste (M96), pois todos os cenários usam uma página só. A spec não diz se a coluna leva a primeira página ou a faixa ("7 a 8") | M96 sobreviveu; E2E: atividade com páginas 7 e 8 mostra `7` | TAB-03 |
| D4 | Low | O título do item é cortado com reticências no sumário em cerca de 85 caracteres; a nomenclatura da tabela sai incompleta e o item não tem título completo em nenhum outro lugar do PDF | Imagem do sumário p. 2: `II.7 Orientação de trabalho de conclusão de curso de graduação, técnico e tecnológico defendido (5 pont…` | CMP-01 |
| D5 | Low | Página inexistente de um documento do processo responde 422 `PAGINA_FORA_DO_DOCUMENTO`; a spec diz 404 e a tabela de erros do design diz 422. Alinhar a spec | E2E: `PUT` com página 99 = 422; `tests/integration/api/test_comprovante_layout_api.py:135-144` fixa o 422 | ARR-06 |
| D6 | Low | O design promete estimar os 60 MB no pedido (soma proporcional dos tamanhos de origem); não foi implementado: o pedido de 400 páginas de 168 MB de origem foi aceito, a montagem rodou e só falhou no fim. O caso pesado medido no design (400 páginas de 224 KB = 88 a 92 MB) passa dos 60 MB da spec: um dossiê assim é recusado no fim da montagem | E2E: 202 e depois FALHOU `COMPROVANTE_GRANDE_DEMAIS`; medição de 92 MB em `comprovante_memory_runner` com limite de 200 MB | CMP-09, CMP-11 |
| D7 | Low | Uma atividade pode começar numa página do sumário e terminar na seguinte (o título no pé de uma página, "Sem comprovante anexado" no topo da próxima) | Sumário p. 2 termina em `Item 2.8 número 4 —` e a p. 3 começa por `Sem comprovante anexado` (design aceita; ver docstring de `front_matter.py`) | CMP-04 |
| D8 | Low | Caracteres que a Liberation Serif não tem (CJK, emoji) saem como glifo ausente sem aviso; latim estendido, grego e cirílico saem certos | Sonda: `Docente: 张伟` virou `\x00\x00` no PDF | borda da spec (caracteres fora do latim básico) |
| D9 | Low | Um título de atividade acima de cerca de 5 000 caracteres derruba o PDF da Tabela (`reportlab LayoutError`, linha mais alta que a página) e a geração termina FALHOU `ERRO_INTERNO`; o título não tem limite de tamanho no schema | Sonda: 500 palavras (3 999 caracteres) ok; 700 palavras (5 599) `LayoutError` | TAB-01 |
| D10 | Low | A linha de contagens diz `Com comprovante: 38` (conta o `evidence_note` do motor) enquanto 30 linhas da coluna dizem `sem comprovante`; coerente com TAB-04 ("iguais aos do motor"), confuso para o leitor | E2E: Tabela p. 1 | TAB-04 |
| D11 | Low | No DOCX a tabela de horas de PIT se parte na quebra de página (o PDF a mantém junta) | Conversão do DOCX pelo LibreOffice, p. 1 e 2 | TAB-05 |

Observações sem severidade: (a) o gerador espera a thread única do worker acabar o OCR em curso (no E2E um pedido esperou cerca de 25 s atrás do OCR de documentos recém-enviados), risco já registrado no design; (b) `can_transition` de `domain/entities/generated.py` não é usado pelo código de produção, a regra vale pelo `WHERE state = 'GERANDO'` de `_close` e pelo gatilho; (c) tarefa T110 (contagem de páginas reais no caso de rasterização) segue pendente porque exige autorização do usuário para ler `Documentos/`; (d) o DOCX só foi aberto em python-docx e LibreOffice, não no Word.

---

## 7. Tarefas de correção propostas

| Tarefa | Sai de | Ação |
| --- | --- | --- |
| F1 | D2, M50 | Teste: com limite de critério, `document.total == "40,00"` e o texto `Pontuação geral: 40,00` no PDF e no DOCX |
| F2 | M28, M29 | Testes: rasterização com recorte em um só eixo (largura ou altura) e qualidade 92 do JPEG da página rasterizada |
| F3 | M41, M43 | Testes: atividade de página única no sumário mostra `Comprovante p. N` sem `a N`; origem usa a página de origem com número diferente do número do Comprovante |
| F4 | M64 | Teste: contagens com valores distintos no PDF e no DOCX (`Com comprovante` diferente de `Atividades`) |
| F5 | D3, M96 | Decidir com o usuário o que a coluna cita para atividade de várias páginas e fixar com teste |
| F6 | B04, B05, B06 | Teste de ligação: `GENERATION_MAX_PAGES`, `GENERATION_MAX_OUTPUT_MB` e `GENERATION_PNG_MAX_MEGAPIXELS` chegam aos limites do pedido e do montador |
| F7 | D1 | Honrar a orientação EXIF do JPEG (sem decodificar o pixel: girar a página e a imagem na inserção) ou registrar a decisão de não honrar |
| F8 | D5 | Alinhar a spec de ARR-06 ao 422 `PAGINA_FORA_DO_DOCUMENTO` |
| F9 | M37, B41 | Testes do montador: falha depois de um ponto de salvamento deixa o alvo ausente (hoje só o `_Scratch.discard` limpa); original cifrado dá `ORIGINAL_INDISPONIVEL` |

### Sobreviventes classificados

| Mutante | Classe |
| --- | --- |
| M10 | Equivalente: o `document_id` das páginas também entra no hash pelas fontes do sumário |
| M36 | Equivalente: em produção o limite vem de `settings.generation_max_output_mb` (padrão 60 testado); a constante do montador é padrão morto. A ligação é o gap B04 |
| M39 | Equivalente: sem a checagem, `path.open('rb')` levanta `FileNotFoundError` e o mesmo `ORIGINAL_INDISPONIVEL` sai |
| M54 | Equivalente: o grupo I em horas não tem faixa, então o filtro é redundante hoje |
| B29 | Equivalente: `check_comprovante` só olha os documentos das páginas anexadas; muda só o custo da inspeção |
| M130 | Equivalente: a função do gatilho de 0006 é substituída por `CREATE OR REPLACE` em 0007 (C01 e C02 mutam a versão efetiva e morreram) |
| M131 | Equivalente: idem M130 |
| B41 | Lacuna de teste de defesa em profundidade (F9): sem a checagem um original cifrado levanta `ValueError` no `attach` e a linha termina `ERRO_INTERNO` em vez de `ORIGINAL_INDISPONIVEL` (confirmado por sonda); o envio já recusa PDF cifrado (`upload_validation.py:139`), por isso o impacto é baixo |
| M29 | Lacuna de teste real (F2): confirmado por sonda, a página girada com recorte em um só eixo sai com geometria errada (`maxdiff 255`) |
| M28 | Lacuna de teste real (F2): o teste aceita desvio médio abaixo de 4, qualidade 60 também passa |
| M41 | Lacuna de teste real (F3) |
| M43 | Lacuna de teste real (F3): no cenário a página de origem coincide com a do Comprovante (4 e 5) |
| M50 | Lacuna de teste real (F1): confirmado por sonda (`160,00` contra subtotal `40,00`) |
| M64 | Lacuna de teste real (F4): no cenário `Atividades` e `Com comprovante` valem o mesmo |
| M96 | Lacuna de teste real (F5): todos os cenários têm uma página por atividade |
| B04 | Lacuna de teste real (F6) |
| B05 | Lacuna de teste real (F6) |
| B06 | Lacuna de teste real (F6) |
| M37 | Lacuna de teste de unidade (F9): no sistema o `_Scratch.discard` apaga o alvo, então o efeito fica mascarado |

---

## 8. Estado dos requisitos (rastreabilidade)

A atualização de `spec.md` fica com o orquestrador; sugestão: TAB-01..08, CMP-02..13, ARR-01..05, ARR-07, ARR-08 e VER-01..09 para `Verified`; CMP-01 e ARR-06 ficam `Implementing` até D4 e D5.

**Recomendação do Verificador A: PASS.** Os 38 requisitos do escopo têm comportamento verificado no ambiente real e por teste; os dois PARTIAL são de texto de spec, não de falha funcional. As lacunas dos mutantes sobreviventes (F1 a F4, F6, F9) e os achados D1 a D3 viram tarefas de correção antes de declarar a feature concluída.

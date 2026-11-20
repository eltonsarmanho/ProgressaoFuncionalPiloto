# Grupo I no total, Tabela sem Status nem Comprovante e resumo da Etapa 4 Validation

**Date**: 2026-11-20
**Spec**: `.specs/features/grupo-i-no-total/spec.md` (29 requisitos: GI-01..12, GTAB-01..08, GRES-01..09)
**Diff range**: `4845ba3..f0bbc08` (T1 `ce32505` a T33 `f0bbc08`; 33 commits, 104 arquivos, +4213 -897; código e testes em `backend/` e `frontend/`: 94 arquivos, +3974 -704).
**Verifier**: sub-agente independente (autor diferente), volta 1 de 3. Não leu `Documentos/`, `Modelos/`, `requeriment.txt` nem `test/`; sem push, deploy nem VM; o `stash@{0}` antigo não foi tocado. Sensor em worktree temporária isolada (nunca `git stash`); `git status --porcelain` da árvore real igual ao de antes (só `requeriment.txt` e `test/`).

**Result**: FAIL na volta 1. 29 de 29 requisitos têm evidência `arquivo:linha` e o gate está verde, mas o sensor achou 1 lacuna real de discriminação (GI-09, fronteira do ano): 2 mutantes sobreviventes com efeito observável (M03 e M04). Dos 49 mutantes, 45 morreram, 2 sobreviveram sem efeito observável (equivalentes) e 2 sobreviveram com efeito (M03, M04). Corrigir com a tarefa FT1 (dois testes, sem mudança de código) e reverificar na volta 2.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1..T4 (motor e validade) | Done | `ce32505`, `eb8d952`, `161573b`, `7848718` |
| T5..T11 (versão substituída, 0009, seed, troca automática, cenário 303) | Done | `fee9798`, `b8863a1`, `c82e35a`, `720da25`, `9cdbf41`, `bb9e669`, `2afd193` |
| T12..T16 (Tabela de Pontuação) | Done | `83cc0eb`, `e0a2f06`, `61d7734`, `f76362a`, `f0546bd` |
| T17..T19 (API e tipos) | Done | `0845ec8`, `aca30a8`, `79c292b` |
| T20..T26 (painel da Etapa 4) | Done | `7591710`, `3862fc5`, `2aecdcc`, `7fe8626`, `f1afbb8`, `f74956a`, `57064e8` |
| T27..T30 (telas e aviso da Etapa 5) | Done | `442e817`, `2c37512`, `7eca5bb`, `a4efac0` |
| T31..T33 (documentação e deploy descrito) | Done | `93aa44d`, `acef442`, `f0bbc08` |
| T34 (Verifier) | Em curso | este relatório; fica aberta até a volta 2 passar |

Testes removidos no intervalo: 22 funções de backend (e 12 `it` de frontend), todas substituídas por teste da regra nova: os sete testes de Tabela com sete colunas, Comprovante e status viram os de cinco colunas (`test_table_docx.py:87`, `test_table_pdf.py:53`); o alerta de numeração divergente e a citação de página do Comprovante saem junto com a coluna (GTAB-08); `points_override` no Grupo I deixa de ser aceito (GI-05, `test_activity_group1_pit.py:163`); o Grupo I fora do total vira o teste da versão nova (`test_seed_ufpa.py:92`). Nenhum teste foi apagado sem substituto nem enfraquecido.

---

## Spec-Anchored Acceptance Criteria

Notação: T: teste, C: código. Cada linha cita a asserção que fixa o valor que a spec define.

### P1: Grupo I conta no total (GI-01..GI-12)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| GI-01 pontos = horas de PIT | 68 h grad = 8,00; 34 h = 4,00; 68 h pós = 12,00; 2 casas, meio para cima | T: `backend/tests/unit/domain/test_scoring_engine_group1_total.py:54` `row.points == D("8.00")`, `:62` `D("4.00")`, `:70` `D("12.00")`, `:78` (0,0425 h dá `D("0.01")`, não 0,00 nem meio-par); C: `scoring_engine.py:197-262`, `scoring_points.py:70`; M01, M02, M26, M28 mortos | PASS |
| GI-02 subtotal e total | subtotal = soma das ofertas dentro; total = soma dos grupos I a VIII | T: `test_scoring_engine_group1_total.py:101` (`group_subtotals[1] == D("24.00")`, `total == D("51.00")`, `total == sum(...range(1, 9))`), `:112` (potencial fora de subtotal e total), `:123` (subtotal = soma das linhas arredondadas); C: `scoring_engine.py:272,350`; M26 morto | PASS |
| GI-03 horas por período e total | horas por período e total, iguais aos pontos | T: `test_scoring_engine_group1_total.py:136` (`{"2023.1": 12.00, "2023.2": 8.00}`, total 20,00 = subtotal), `:150` (com teto o subtotal é menor que as horas), `backend/tests/unit/domain/test_scenario_303.py:28` (24, 24, 24, 20); C: `scoring_engine.py:302-317`; M27 morto | PASS |
| GI-04 oferta fora do interstício | 0 ponto, 0 hora, `FORA_DO_INTERSTICIO`, fora do subtotal e do total | T: `test_scoring_engine_group1_total.py:164` (sem linha, `reason is InvalidReason.FORA_DO_INTERSTICIO`, subtotal, total e horas 0, `group1_hours_by_period == {}`), `:178`; C: `activity_validity.py:90-91`, `scoring_engine.py:343`; `backend/tests/unit/domain/test_activity_validity.py:380` (versão antiga e nova) | PASS |
| GI-05 `points_override` recusado | 422 em `points_override` em qualquer critério de carga semanal do Grupo I, nas duas versões | T: `backend/tests/integration/scoring/test_activity_group1_pit.py:78` (versão antiga), `:163` (versão nova, graduação e pós), `:186` (edição), `:206` (sem pontos informados é aceita); `backend/tests/integration/api/test_activities_api.py:171`; `test_scoring_engine_group1_total.py:191` (valor gravado nunca substitui o cálculo); C: `scoring.py:306-316`, `scoring_engine.py:202`; M02, M06 mortos | PASS |
| GI-06 versão anterior intacta | resultado e regras da versão antiga sem mudança | T: `test_scoring_engine_group1_total.py:214` (`points == D("0")`, `pit_hours == D("8.00")`, `outside_total is True`, subtotal 0, total 20), `:229`; `backend/tests/integration/api/test_scoring_golden.py:283` (o mesmo processo na versão antiga dá 211 com o Grupo I fora); `backend/tests/integration/doc_usecases/test_run_generation_table.py:59`; M01, M33 mortos | PASS |
| GI-07 versão nova única sugerida e escolhível; antiga substituída | só a nova é sugerida e escolhível; 422 `VERSAO_SUBSTITUIDA`; a antiga marcada | T: `backend/tests/integration/scoring/test_table_choice.py:208` (sugestão é a não substituída mesmo com o mesmo início), `:217` (inverter a marca inverte a sugestão), `:226` (só substituídas dá `suggested is None`), `:234` (`error.value.code == "VERSAO_SUBSTITUIDA"`, mensagem exata, nada gravado, auditoria igual); `backend/tests/integration/api/test_scoring_process_api.py:152` (HTTP 422, `(field, code) == ("version_id", "VERSAO_SUBSTITUIDA")`); `backend/tests/integration/scoring/test_admin_versions.py:157,185,195` (regras de versão aberta, sobreposição e base de importação); `backend/tests/integration/test_seed_scoring.py:150,204`; `backend/tests/integration/api/test_scoring_tables_api.py:157`; `frontend/src/components/TablePicker.test.tsx:132,145,161`; C: `scoring.py:121-129,185-190`, `scoring_admin.py:135-138,417-420`, `entities/scoring.py:62-67`; M07..M11, M16, M18, M20, M39, F02 mortos | PASS |
| GI-08 percentual sem alerta | percentual do Grupo I sobre o total, sem alerta | T: `test_scoring_engine_group1_total.py:250` (`group1_percent == D("28.57")`), `:258` (`77.42`, `limit_adjustments == ()`, nenhuma linha com alerta); `test_scoring_golden.py:264-268` (`body["alerts"] == []`, `"30.36"` em `:252`); `frontend/src/components/PanelHeadline.test.tsx:54` (`30,36%`) | PASS |
| GI-09 ano inteiro fora | sem data e sem período de datas, ano inteiro do período fora do interstício vira `FORA_DO_INTERSTICIO`; sem inventar datas de semestre | T: `backend/tests/unit/domain/test_scoring_periods.py:158` (2019.1 contra 2022-2024 é FORA), `:162` (ano que cruza o início é SEM_DATA), `:167` (ano após o fim é FORA), `:171`, `:175-197` (fronteiras 01/01 do início e 31/12 do fim), `:199-215` (data ou período de datas vencem o período letivo), `:219` e `:225` (outro grupo e período malformado seguem SEM_DATA); `test_activity_validity.py:329,339,348`; `test_scoring_engine_group1_total.py:275,289`; C: `scoring_periods.py:97-127`; M05 morto; **M03 e M04 sobreviveram**: as fronteiras 31/12 como início e 01/01 como fim do interstício não têm teste (G1) | GAP (G1) |
| GI-10 troca automática | `RASCUNHO` e `EM_ANDAMENTO` passam para a nova com auditoria; `CONCLUIDO`, `ARQUIVADO` e documentos gerados não mudam; idempotente | T: `backend/tests/integration/scoring/test_adopt_superseding_version.py:66` (`moved == 2`, `user_id is None`, `justification == JUSTIFICATION`, `changes == {"scoring_table_version_id": {"before": legacy, "after": new}}`, um evento por processo), `:88` (marca), `:95` (concluído e arquivado: `moved == 0`, sem evento), `:109,118` (outra tabela e sem tabela não mudam), `:127` (segunda execução: `moved == 0`, auditoria igual), `:150` (falha no meio não muda processo nem marca: atomicidade), `:182` (gerações iguais), `:199`; `test_seed_scoring.py:252` (o seed troca o processo uma vez); C: `scoring_adoption.py:12-56`, `seed.py:176-178`; M12..M17, M19 mortos | PASS |
| GI-11 aviso da Etapa 5 | aviso quando a última Tabela gerada usou versão diferente da escolhida | T: `backend/tests/unit/presentation/test_generated_schemas.py:328` (`table_version_id == str(version_id)`), `:337`, `:345`; `backend/tests/integration/api/test_generated_documents_api.py:118` (`("PRONTO", str(OFICIAL.id))`); `frontend/src/pages/ProcessGenerated.test.tsx:239-320` (aviso exato "Gerada com outra versão da tabela de pontuação; gere de novo" só para a Tabela, só com versão diferente, não some com geração mais nova que falhou, sem tabela escolhida não há aviso); C: `schemas/generated.py:112-115`, `GeneratedBlock.tsx:75,106`; M23, F01 mortos | PASS |
| GI-12 VI.14 = 3 | 3 pontos por ano na versão nova, 6 na antiga | T: `backend/tests/unit/test_seed_ufpa.py:36-39` (soma 1311), `:136,143`; `backend/tests/unit/test_seed_ufpa_items.py:177`; `backend/tests/integration/test_seed_scoring.py:166` (`unit_points == Decimal("3")`), `:204-250` (a antiga fica com `Decimal("6")` e intacta); C: `ufpa.json:837`; M21 morto | PASS |

### P1: Tabela de Pontuação (GTAB-01..GTAB-08)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| GTAB-01 faixa e subtotal do Grupo I | a lista abre com "I. Docência/..." e o subtotal | T: `backend/tests/unit/domain/test_table_document_rows.py:232` (`bands[0]` é o grupo 1, `subtotal == "92,00"`, bandas 1 a 8), `backend/tests/integration/api/test_generated_table_acceptance.py:60` (DOCX e PDF: `"Subtotal: 92,00"` e a faixa antes de "II. "); C: `table_document.py:184-193,255-262` | PASS |
| GTAB-02 uma linha por oferta | `I.1`/`I.2`, disciplina e período, horas, 1,00, total = horas; ordem por período e título | T: `test_table_document_rows.py:250` (`("I.1", "Cálculo I (1º Período de 2023)", "8,00", "1,00", "8,00")`), `:266` (ordem por período e depois por título, ignorando caixa e acento), `:283` (sem período por último), `:296` (título de 401 caracteres cortado em 400 com reticências e o período depois); `test_generated_table_acceptance.py:70` (12 ofertas em 4 períodos nos dois formatos, `["8,00"] * 11 + ["4,00"]`); M29, M30, M31 mortos | PASS |
| GTAB-03 Pontuação geral I a VIII | soma dos grupos I a VIII | T: `test_table_document_rows.py:243` (`document.total == "303,00"`), `backend/tests/unit/domain/test_table_document_totals.py:217`; `test_generated_table_acceptance.py:60` (`"Pontuação geral: 303,00"`); M37 morto | PASS |
| GTAB-04 cinco colunas, sem Status e Comprovante, DOCX e PDF | `Item, Atividade, Quantidade, Pontuação unitária, Total`; nenhum "Pontuada", "Potencial", "Não pontuada", "sem comprovante" | T: `backend/tests/unit/infrastructure/test_table_docx.py:87` (`tblGrid` com 5 colunas, cabeçalho `== COLUMNS`), `:172` (nenhuma célula diz as palavras removidas), `backend/tests/unit/infrastructure/test_table_pdf.py:53,89`; `test_generated_table_acceptance.py:90` (arquivo gerado, `HEADERS in text`, `REMOVED_WORDS` ausentes, nas duas extensões); `backend/tests/integration/doc_usecases/test_run_generation_table.py:146,176`; conferência visual do DOCX (via LibreOffice) e do PDF da Tabela sintética de 303 pontos: 5 colunas, seção I, nenhum Status nem Comprovante; M36 morto | PASS |
| GTAB-05 linha sem pontos | Total 0,00 e o motivo em Alertas | T: `test_table_document_rows.py:314` (`("I.99", "0,00")` e alerta `SEM_ENQUADRAMENTO` com o assunto), `test_table_document_totals.py:282`; M38 sobreviveu por equivalência (ver tabela do sensor) | PASS |
| GTAB-06 título das horas por semestre | "Horas de PIT por semestre (Grupo I)" com as horas de cada período e o total | T: `test_table_docx.py:280`, `test_table_pdf.py:232` (versão nova sem "fora do total"), `test_table_document_rows.py:351`, `test_generated_table_acceptance.py:90` (`NEW_HEADING in text`, `OLD_HEADING not in text`); M34 morto | PASS |
| GTAB-07 versão antiga | sem seção I, sem Status e Comprovante, título antigo | T: `test_table_document_rows.py:78,342`, `test_table_docx.py:292`, `test_table_pdf.py:244`, `test_generated_table_acceptance.py:106` (211, sem seção I, cinco colunas, `OLD_HEADING in text`); M33 morto | PASS |
| GTAB-08 sem referência a Comprovante nem status | sem alerta de numeração, sem alertas "sem comprovante", sem contadores no rodapé | T: `test_table_document_totals.py:187,198` (só o alerta `SEM_COMPROVANTE` sai), `test_table_docx.py:172` e `test_table_pdf.py:89` (rodapé só com "Atividades" e "Com divergências", um separador), `backend/tests/unit/domain/test_generation_snapshot.py:131` (layout só no Comprovante), `test_run_generation_table.py:146,221` e `test_run_generation_comprovante.py:119` (a Tabela não leva arranjo nem número do Comprovante); C: `table_document.py:230`, `table_text.py:45-48`, `generation_snapshot.py:18`; M24, M32, M35 mortos | PASS |

### P1: Resumo da Etapa 4 em painel (GRES-01..GRES-09)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| GRES-01 total e mínimo no topo | "Total geral", rótulo "Grupos I a VIII", mínimo em texto curto | T: `frontend/src/components/PanelHeadline.test.tsx:17` (`toHaveTextContent("Grupos I a VIII")`), `:30` ("Atinge o mínimo (100,00)", "Não atinge o mínimo (100,00)"); C: `PanelHeadline.tsx:23-31`; F03 morto | PASS |
| GRES-02 "Mínimo não definido" em texto comum | sem destaque de valor | T: `PanelHeadline.test.tsx:42` (`className` vazio, sem `.panel-value` nem `.panel-minimum` no mínimo, só o total leva a classe de destaque) | PASS (o tamanho de fonte real é por CSS; ver G4) |
| GRES-03 uma linha por grupo com barra | nome, subtotal, barra proporcional ao total, 0,00 discreto | T: `frontend/src/components/GroupBars.test.tsx:22` (8 linhas), `:34` (subtotais em pt-BR, ordem I a VIII), `:48` (barra `aria-hidden`, largura `30,36%` e `52/303`), `:57` (`toHaveClass("muted")` e "0,00" em texto), `:65` (total 0: `"0%"` sem NaN nem Infinity); F04 sobreviveu por equivalência (G3) | PASS |
| GRES-04 bloco Docência (PIT) | ofertas por período, disciplina, nível, horas, total do período, total geral; "Aguardando validação" fora das horas | T: `frontend/src/components/TeachingBlock.test.tsx:38,57,68,78,102`; `frontend/src/pages/ProcessScoring.test.tsx:448`; `frontend/src/components/ScoringPanel.test.tsx:54`; M27, F05, F06 mortos | PASS |
| GRES-05 sem ofertas | "Nenhuma disciplina lançada no Grupo I" | T: `TeachingBlock.test.tsx:89,96`; `ProcessScoring.test.tsx:494` | PASS |
| GRES-06 potencial em cartões | só com potencial maior que 0 | T: `frontend/src/components/PotentialCards.test.tsx:10,17`; `ScoringPanel.test.tsx:78` (a seção some); F07 morto | PASS |
| GRES-07 contadores em faixa única | atividades, com comprovante, pendentes, não pontuadas, com divergências | T: `ScoringPanel.test.tsx:66` (`["Atividades: 20", "Com comprovante: 15", "Pendentes: 3", "Não pontuadas: 4", "Com divergências: 6"]`), `:54` (ordem dos blocos) | PASS |
| GRES-08 sem depender de cor, sem rolagem a 360 px | texto em cada valor; sem rolagem horizontal da página | T: `ScoringPanel.test.tsx:97` (sem elemento focável), `GroupBars.test.tsx:48,57` (valor em texto), `frontend/src/styles.test.ts:190` (regras estáticas); **medição em Chrome**: página de medição de escopo temporário (não versionada) com o `ScoringPanel` e dados de estresse (total de 7 dígitos, títulos de 90 caracteres, pós-graduação, oferta aguardando) em iframes: 360 px `clientWidth 345 == scrollWidth 345`, 320 px `305 == 305`, sem rolagem horizontal; controle negativo (um `div` de 640 px na mesma página): `scrollWidth 656 > 345`, overflow detectado nas duas larguras | PASS |
| GRES-09 versão antiga | "Grupos II a VIII", Docência em horas, fora do total | T: `PanelHeadline.test.tsx:23`, `GroupBars.test.tsx:40` (7 linhas), `TeachingBlock.test.tsx:83`, `ScoringPanel.test.tsx:85`, `frontend/src/components/ScoringTable.test.tsx:184`; F03, F10 mortos | PASS |

**Status**: 28 de 29 requisitos com teste que fixa o resultado da spec; GI-09 com lacuna de discriminação nas fronteiras 31/12 e 01/01 (G1). Nenhum requisito sem evidência.

**Edge cases**: semestre só fora omitido (`test_table_document_rows.py:328`, `TeachingBlock.test.tsx:102`); arredondamento meio para cima antes de somar (`test_scoring_engine_group1_total.py:78,123`); título de 400 caracteres cortado como nas outras linhas (`test_table_document_rows.py:296`, `test_table_docx.py:189`, `test_table_pdf.py:110`).

**Critérios de sucesso da spec**: 24, 24, 24 e 20 de Grupo I e 211 + 92 = 303 (`test_scenario_303.py:16`, `test_scoring_golden.py:252`); a Tabela gerada com seção I, total 303 e sem Status nem Comprovante, em DOCX e PDF (`test_generated_table_acceptance.py:60,90`); painel em blocos com Docência por período e disciplina (`ScoringPanel.test.tsx:54`).

---

## Discrimination Sensor

Sensor de 49 mutantes de comportamento (39 de backend, 10 de frontend) numa worktree temporária (`git worktree add --detach`, removida no fim), um mutante por vez, restaurado com `git checkout -- .` entre as rodadas, rodando só os testes que cobrem o trecho (backend em PostgreSQL real; frontend em vitest). Cobre os mutantes pedidos pelo design: `counts_in_total` do Grupo I ignorado (M20, M26), arredondamento (M28), `outside_total` sempre falso (M33, M01), `pit_hours` e filtro de previsão da Etapa 3 (M25, M27), `is_group1_load_criterion` trocado pelo predicado da versão antiga (M06), versão substituída de volta à sugestão, à escolha e às regras de administração (M07..M11, M39, F02), troca alcançando `CONCLUIDO` (M12, M17), troca sem auditoria (M13), ano inteiro trocado por "qualquer parte do ano" (M03, M04, M05), aviso da Etapa 5 invertido (F01), `SEM_COMPROVANTE` e contador de status de volta (M32, M35), ordem por período (M30), coluna Status de volta (M36), título das horas igual nas duas versões (M34), rótulo "II a VIII" trocado (F03), barra com divisão por zero (F04), oferta `POTENCIAL` nas horas (M27, F05, F06) e versão substituída aceita no `PUT /scoring/table` (M08, M09).

| Mutation | Requisito | File:line | Description | Killed? | Killed by / nota |
| -------- | --------- | --------- | ----------- | ------- | ---------------- |
| M01 | GI-04/GI-06 | `backend/app/domain/rules/scoring_engine.py:258` | a group I row outside the total keeps its points | morto | test_scoring_engine_group1_total.py::test_group_outside_the_total_keeps_zero_points_hours_and_the_out |
| M02 | GI-05 | `backend/app/domain/rules/scoring_engine.py:202` | informed points replace the PIT calculation when the group counts | morto | test_scoring_engine_group1_total.py::test_stored_informed_points_are_ignored_in_both_versions |
| M03 | GI-09 | `backend/app/domain/rules/scoring_periods.py:103` | year ending on the interstice start counted as outside | sobreviveu | SOBREVIVEU, efeito observável: intervalo iniciado em 31/12 e oferta do ano anterior sem datas vira FORA (o certo é SEM_DATA); sem teste na fronteira. Gap G1. |
| M04 | GI-09 | `backend/app/domain/rules/scoring_periods.py:103` | year starting on the interstice end counted as outside | sobreviveu | SOBREVIVEU, efeito observável: intervalo terminado em 01/01 e oferta do ano seguinte sem datas vira FORA (o certo é SEM_DATA). Gap G1. |
| M05 | GI-09 | `backend/app/domain/rules/scoring_periods.py:119` | whole-year rule applied to every group | morto | test_scoring_periods.py::test_activity_of_another_group_with_an_academic_period_and_no_da |
| M06 | GI-05 | `backend/app/application/use_cases/scoring.py:310` | informed points refused only while the group is outside the total | morto | test_activity_group1_pit.py::test_create_with_informed_points_in_a_group1_that_counts_in_the_ |
| M07 | GI-07 | `backend/app/application/use_cases/scoring.py:128` | superseded version suggested | morto | test_table_choice.py::test_with_only_superseded_versions_there_is_no_suggestion |
| M08 | GI-07 | `backend/app/application/use_cases/scoring.py:185` | superseded version accepted | morto | test_table_choice.py::test_choosing_a_superseded_version_is_422_with_its_code_and_save |
| M09 | GI-07 | `backend/app/application/use_cases/scoring.py:189` | wrong 422 code | morto | test_table_choice.py::test_choosing_a_superseded_version_is_422_with_its_code_and_save |
| M10 | GI-07 | `backend/app/application/use_cases/scoring_admin.py:137` | latest_version keeps superseded | morto | test_admin_versions.py::test_latest_version_skips_the_superseded_one_with_the_same_start |
| M11 | GI-07 | `backend/app/application/use_cases/scoring_admin.py:137` | superseded version back in open-version/overlap rules | morto | test_admin_versions.py::test_a_new_version_closes_the_superseding_one_and_neither_confli |
| M12 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:12` | concluded processes moved | morto | test_adopt_superseding_version.py::test_concluded_and_archived_processes_keep_the_previous_version_ |
| M13 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:45` | move without audit | morto | test_adopt_superseding_version.py::test_draft_and_in_progress_processes_move_to_the_new_version_wit |
| M14 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:44` | no process moved | morto | test_adopt_superseding_version.py::test_draft_and_in_progress_processes_move_to_the_new_version_wit |
| M15 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:38` | already-superseded version taken over again | morto | test_adopt_superseding_version.py::test_a_version_already_superseded_by_another_one_is_left_alone |
| M16 | GI-07/GI-10 | `backend/app/application/use_cases/scoring_adoption.py:40` | previous version never marked | morto | test_adopt_superseding_version.py::test_the_previous_version_is_marked_as_superseded_by_the_new_one |
| M17 | GI-10 | `backend/app/infrastructure/database/repositories.py:363` | repository ignores the status filter | morto | test_adopt_superseding_version.py::test_concluded_and_archived_processes_keep_the_previous_version_ |
| M18 | GI-07 | `backend/app/infrastructure/database/repositories.py:634` | mark lost on read | morto | test_table_choice.py::test_with_only_superseded_versions_there_is_no_suggestion |
| M19 | GI-10 | `backend/app/infrastructure/database/seed.py:176` | seed does not switch versions | morto | test_seed_scoring.py::test_seeding_over_the_previous_version_marks_it_and_moves_the_dr |
| M20 | GI-07 | `backend/app/infrastructure/database/seed_data/ufpa.json:22` | seeded group I outside total | morto | test_seed_ufpa.py::test_group_one_is_pit_hours_counting_in_the_total |
| M21 | GI-12 | `backend/app/infrastructure/database/seed_data/ufpa.json:837` | VI.14 back to 6 | morto | test_seed_ufpa.py::test_group_sums_ii_to_viii_and_grand_total |
| M22 | GI-07 (downgrade) | `backend/alembic/versions/0009_version_superseded.py:34` | downgrade keeps the column | morto | test_migration_version_superseded.py::test_downgrade_one_revision_drops_the_column_and_keeps_the_versi |
| M23 | GI-11 | `backend/app/presentation/schemas/generated.py:114` | table_version_id never returned | morto | test_generated_schemas.py::test_a_generation_with_a_snapshot_returns_the_id_of_the_table_ve |
| M24 | GTAB-08 | `backend/app/domain/rules/generation_snapshot.py:18` | Tabela snapshot carries the Comprovante layout again | morto | test_generation_snapshot.py::test_layout_and_report_only_appear_in_their_own_kinds[TABELA-tab |
| M25 | GI-05/D4 | `backend/app/application/use_cases/scoring.py:761` | Etapa 3 prediction skips group I offers | morto | test_activities_api.py::test_predicted_points_of_a_group1_offer_exist_only_where_group1_ |
| M26 | GI-01/GI-02 | `backend/app/domain/rules/scoring_engine.py:272` | potential rows counted in subtotals | morto | test_scoring_engine_group1_total.py::test_a_potential_offer_stays_out_of_the_subtotal_and_the_total |
| M27 | GI-03 | `backend/app/domain/rules/scoring_engine.py:313` | awaiting-validation offers counted in PIT hours | morto | test_scoring_engine.py::test_pit_hours_of_awaiting_review_and_rejected_offers_stay_out_o |
| M28 | GI-01 | `backend/app/domain/rules/scoring_points.py:70` | PIT hours rounded half-even | morto | test_scoring_engine_group1_total.py::test_a_hundredth_is_rounded_half_up_not_half_even_nor_down |
| M29 | GTAB-02 | `backend/app/domain/rules/table_document.py:42` | unit points of section I rows wrong | morto | test_table_document_rows.py::test_each_group_one_offer_is_a_row_with_item_title_period_hours_ |
| M30 | GTAB-02 | `backend/app/domain/rules/table_document.py:160` | offers without term first | morto | test_table_document_rows.py::test_an_offer_without_a_term_comes_last_and_has_only_its_title |
| M31 | GTAB-02 | `backend/app/domain/rules/table_document.py:149` | section I quantity is not the PIT hours | morto | test_table_document_rows.py::test_each_group_one_offer_is_a_row_with_item_title_period_hours_ |
| M32 | GTAB-08 | `backend/app/domain/rules/table_document.py:230` | voucher alert back in the table | morto | test_table_document_totals.py::test_no_alert_says_that_an_activity_has_no_voucher |
| M33 | GTAB-06/07 | `backend/app/domain/rules/table_document.py:211` | old version hours not marked outside total | morto | test_table_document_rows.py::test_the_old_version_has_no_section_i_and_marks_the_hours_as_out |
| M34 | GTAB-06 | `backend/app/infrastructure/documents/table_text.py:30` | heading by version inverted | morto | test_table_pdf.py::test_the_new_version_titles_the_hours_section_without_saying_out |
| M35 | GTAB-08 | `backend/app/infrastructure/documents/table_text.py:47` | status counter back in the footer | morto | test_table_pdf.py::test_no_cell_says_voucher_or_status_and_the_footer_has_no_vouche |
| M36 | GTAB-04 | `backend/app/infrastructure/documents/table_text.py:7` | last column named Status | morto | test_table_pdf.py::test_the_table_has_the_five_columns_in_the_order_of_the_spec |
| M37 | GTAB-03 | `backend/app/domain/rules/table_document.py:272` | Pontuação geral without group I | morto | test_table_document_rows.py::test_the_scenario_303_total_is_the_sum_of_groups_i_to_viii |
| M38 | GTAB-05 | `backend/app/domain/rules/table_document.py:151` | unscored offer row shows hours as total | sobreviveu | SOBREVIVEU, equivalente: toda linha do Grupo I de carga semanal que entra numa faixa tem `points == pit_hours` (`scoring_engine.py:258,262`); a linha fora do total não tem faixa. |
| M39 | GI-07 (admin) | `backend/app/domain/entities/scoring.py:67` | is_superseded always false | morto | test_table_choice.py::test_with_only_superseded_versions_there_is_no_suggestion |
| F01 | GI-11 | `frontend/src/components/GeneratedBlock.tsx:75` | warning compares with the wrong condition | morto | ProcessGenerated.test.tsx > a última Tabela pronta com versão diferente da escolhida mos |
| F02 | GI-07 | `frontend/src/components/TablePicker.tsx:53` | superseded version offered in the picker | morto | TablePicker.test.tsx > a lista de escolha só traz a versão nova |
| F03 | GRES-01/09 | `frontend/src/components/PanelHeadline.tsx:27` | II a VIII / I a VIII labels swapped | morto | PanelHeadline.test.tsx > GRES-01: mostra o total geral em pontos com o rótulo 'Grupos |
| F04 | GRES-03 | `frontend/src/components/GroupBars.tsx:16` | bar divides by zero total | sobreviveu | SOBREVIVEU, equivalente sob o invariante da API: `part > 0` implica `total >= part > 0`; a guarda `whole > 0` só age com dado inconsistente. Gap G3 (baixo). |
| F05 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:44` | awaiting-validation label dropped | morto | TeachingBlock.test.tsx > GRES-04: a oferta aguardando validação leva a etiqueta e o t |
| F06 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:21` | awaiting offers not listed | morto | TeachingBlock.test.tsx > GRES-04: a oferta aguardando validação leva a etiqueta e o t |
| F07 | GRES-06 | `frontend/src/components/PotentialCards.tsx:11` | potential cards shown with zero potential | morto | PotentialCards.test.tsx > GRES-06: com todos os valores em 0 não renderiza nada |
| F08 | GI-01 | `frontend/src/components/ScoringTable.tsx:43` | counted group I rows show quantity instead of PIT hours | morto | ScoringTable.test.tsx > a linha mostra as horas em Quantidade, 1,00 na unitária e os |
| F09 | GI-05 | `frontend/src/components/ScoreEditor.tsx:13` | no 1-point note | morto | ScoreEditor.test.tsx > GI-05: no Grupo I que conta no total a nota diz que cada hor |
| F10 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:55` | outside-total mark dropped | morto | TeachingBlock.test.tsx > GRES-09: na versão antiga o total diz 'fora do total' e não  |

**Sensor depth**: P0-full, 49 mutantes manuais (caminho de integridade de dados: total da pontuação e migração).
**Result**: 45 de 49 mortos; 2 sobreviventes equivalentes (M38, F04); 2 sobreviventes com efeito observável (M03, M04): FAIL.

**Prova do efeito de M03 e M04** (sonda no scratch, código real contra código mutado): intervalo 31/12/2022 a 30/12/2024 e oferta `2022.2` sem datas: real `SEM_DATA`, mutante `FORA`; intervalo 02/01/2023 a 01/01/2025 e oferta `2025.1`: real `SEM_DATA`, mutante `FORA`. Com `FORA` a oferta sai do subtotal, das horas e da Tabela embora o dia 31/12 (ou 01/01) do ano do período caia dentro do interstício, contra o texto de GI-09 ("o ano inteiro ... está fora").

**Isolamento**: worktree removida; `git status --porcelain` da árvore real idêntico ao de antes do sensor.

---

## Interactive UAT Results

Não aplicável nesta volta (o usuário dorme; UAT visual feito pelo Verifier): painel renderizado a 360 px em Chrome headless e DOCX e PDF da Tabela sintética de 303 pontos convertidos em imagem e lidos (cinco colunas, faixa "I. Docência" com subtotal 92,00, 12 linhas `I.1` com período letivo, "Pontuação geral: 303,00", "Horas de PIT por semestre (Grupo I)", nenhum Status nem Comprovante).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | OK: `scoring_adoption.py` (56 linhas) e o predicado `is_group1_load_criterion` são os únicos acréscimos novos de estrutura; as classes de painel têm uso único cada, ligado a um GRES |
| Surgical changes | OK: o Relatório e o Comprovante não mudam (spec); o ramo antigo do Grupo I no motor sai em favor do `outside_total` |
| No scope creep | OK |
| Matches patterns | OK: porta e repositório seguem `set_scoring_table_version`; migração só de esquema como as anteriores |
| Spec-anchored outcome check (asserted values match spec) | OK, com G1 |
| Per-layer Coverage Expectation (domain 1:1 ACs; routes happy+edge+error) | OK: rotas com 422 `VERSAO_SUBSTITUIDA`, 422 `points_override`, 409 somente leitura |
| Every test maps to a spec requirement | OK: testes novos citam GI, GTAB, GRES ou caso de borda; `labels.test.ts:111,190` apoia GRES-04 e GRES-01 |
| Documented guidelines followed | `CLAUDE.md` (regras 1, 7 e 8 do motor; só dados sintéticos: o nome do teste declara a tabela sintética, `scoring_variants.py`); AD-001 (teste de arquitetura verde), AD-004 (PostgreSQL real), AD-012 (documentos gerados e processos fechados intactos), AD-023 |

Observação sem requisito: `scoring_admin.py:344` só bloqueia a edição de critério em versão que tem outra com `valid_from` maior; a versão substituída e a nova começam no mesmo dia, então um administrador pode editar critérios da versão substituída enquanto nenhum processo a usa. Sem efeito na pontuação (ninguém a escolhe). Anotado em G5.

---

## Edge Cases

- [x] Semestre só com ofertas fora do interstício: omitido no painel e na Tabela.
- [x] Horas com 3 ou mais casas: meio para cima, soma das linhas = subtotal.
- [x] Título de mais de 400 caracteres cortado na Tabela como nas outras linhas.
- [x] Oferta sem período letivo: "Sem período letivo", por último na Tabela, sem total próprio.
- [x] Seed duas vezes e com a versão antiga presente: sem duplicar, sem segunda troca.
- [ ] Fronteira do ano inteiro com o interstício começando em 31/12 ou terminando em 01/01: comportamento correto no código, sem teste (G1).

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`, rodado no HEAD `f0bbc08`.
- **Result backend**: `ruff` limpo (`All checks passed!`); `5455 passed, 3 deselected (maritalk_live), 1 warning in 690.93s`, uma única execução completa.
- **Result frontend**: `eslint` limpo (exit 0); `vite build` ok (exit 0); `Test Files 46 passed (46), Tests 634 passed (634)`.
- **Test count before feature**: 5322 (backend) e 584 (frontend), no HEAD `9bf9ad7` registrado em `.specs/features/correcoes-auditoria/validation.md`.
- **Test count after feature**: 5455 e 634.
- **Delta**: +133 de backend e +50 de frontend.
- **Skipped tests**: 3 `deselected` por `-m 'not maritalk_live'` (opt-in com `RUN_LIVE_MARITALK=1`, fora do gate).
- **Failures**: nenhuma.

---

## Fix Plans

### Fix 1 (G1): fronteiras 31/12 e 01/01 do ano inteiro (GI-09), prioridade Major

- **Root cause**: `scoring_periods.py:103` decide o ano inteiro fora com `date(year, 12, 31) < interstice.start` e `date(year, 1, 1) > interstice.end`; os testes de `test_scoring_periods.py:158-197` cobrem a fronteira com o interstício começando em 01/01 e terminando em 31/12 (os dias de fora do ano), mas não as duas fronteiras inversas: início em 31/12 (o último dia do ano anterior está dentro) e fim em 01/01. Os mutantes `<=` e `>=` passam.
- **Fix task FT1**: em `backend/tests/unit/domain/test_scoring_periods.py`, dois testes: (a) `Interstice(date(2022, 12, 31), date(2024, 12, 30))` com `_offer("2022.2")` é `PeriodState.SEM_DATA`; (b) `Interstice(date(2023, 1, 2), date(2025, 1, 1))` com `_offer("2025.1")` é `PeriodState.SEM_DATA`. Sem mudança de código. Verify: `cd backend && .venv/bin/pytest tests/unit/domain/test_scoring_periods.py -q`; reaplicar M03 e M04 e ver os dois testes falharem. Gate: quick. Commit: `test(domain): pin the year guard on the interstice start of December 31 and end of January 1`.
- **Priority**: Major (única falha do veredito).

---

## Requirement Traceability Update

A spec não foi alterada nesta volta. Depois da volta 2 passar: GI-01..GI-08 e GI-10..GI-12, GTAB-01..08 e GRES-01..09 passam de `Implemented` para `Verified`; GI-09 passa junto com a FT1.

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| GI-09 | Implemented | Needs Fix (FT1) |
| os outros 28 | Implemented | Verified na volta 2 |

---

## Gaps (ranqueadas)

| # | Gap | Requisito | Evidência | Severidade |
| - | --- | --------- | --------- | ---------- |
| G1 | Fronteiras 31/12 (início do interstício) e 01/01 (fim) do ano inteiro sem teste; M03 e M04 sobrevivem com efeito observável | GI-09 | `backend/app/domain/rules/scoring_periods.py:103`; testes `test_scoring_periods.py:158-197` | Major: bloqueia o PASS; corrigir com FT1 |
| G2 | A seção "Resumo" do GRES-08 ("sem rolagem horizontal a 360 px") continua sem teste versionado de navegador real; a medição desta volta usou uma página de escopo temporário e só vale para este commit | GRES-08 | `frontend/src/styles.test.ts:190` (regras estáticas) | Baixa: spec-precision; a lição L-021 já recomenda a verificação renderizada |
| G3 | A guarda `!(whole > 0)` de `widthOf` é inalcançável com dados consistentes da API; o teste "total 0" só zera as parcelas, então a guarda extra não é exercitada (F04 equivalente sob o invariante) | GRES-03 | `frontend/src/components/GroupBars.tsx:16`, `GroupBars.test.tsx:65` | Baixa |
| G4 | O tamanho de texto "comum" de GRES-02 é fixado só pela ausência de classe; o tamanho real é do CSS | GRES-02 | `PanelHeadline.test.tsx:42` | Baixa: spec-precision |
| G5 | A versão substituída segue editável por critério no administrador enquanto nenhum processo a usa (mesmo `valid_from` da nova) | GI-07 (fora do texto) | `backend/app/application/use_cases/scoring_admin.py:344` | Baixa: a spec não pede; decidir se bloqueia |

---

## Summary

**Overall**: Issues (volta 1 de 3)

**Spec-anchored check**: 28 de 29 requisitos com resultado da spec fixado por teste; GI-09 com lacuna de fronteira; 2 spec-precision (G2, G4) e 1 observação (G5)
**Sensor**: 45 de 49 mutantes mortos; 2 equivalentes (M38, F04); 2 sobreviventes reais (M03, M04)
**Gate**: backend 5455 passando, frontend 634 passando, `ruff`, `eslint` e `build` limpos

**What works**: Grupo I soma no total a 1 ponto por hora, com recusa de `points_override` nas duas versões; versão substituída nunca sugerida nem escolhível (422 `VERSAO_SUBSTITUIDA`); troca automática só de `RASCUNHO` e `EM_ANDAMENTO`, auditada, atômica e idempotente; VI.14 = 3 na versão nova e 6 na antiga intacta; Tabela de 5 colunas, seção I, 303 pontos no cenário derivado, sem Comprovante nem status no DOCX e no PDF; painel a 320 e 360 px sem rolagem; downgrade da `0009` testado em PostgreSQL real.

**Issues found**: G1 (dois testes de fronteira que faltam).

**Next steps**: executar a FT1 (dois testes, um commit), reverificar na volta 2 (reaplicar M03 e M04, rodar o gate), então marcar T34 e passar a rastreabilidade para `Verified`.

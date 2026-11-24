# Grupo I no total, Tabela sem Status nem Comprovante e resumo da Etapa 4 Validation

**Date**: 2026-11-20
**Spec**: `.specs/features/grupo-i-no-total/spec.md` (29 requisitos: GI-01..12, GTAB-01..08, GRES-01..09)
**Diff range**: `4845ba3..fdd393f` (T1 `ce32505` a T38 `fdd393f`; 38 commits desde `4845ba3`: 33 da feature, `f5381b4` com o relatório da volta 1 e as correções FT1..FT4 `1409220`, `e848e9c`, `bad286a`, `fdd393f`). Desde a volta 1 (`f0bbc08`): 5 arquivos de código e teste (`scoring_admin.py` +4, `test_admin_criteria.py` +39, `test_scoring_periods.py` +14, `GroupBars.test.tsx` +8, `styles.test.ts` +6); nenhum arquivo de produção do frontend mudou.
**Verifier**: sub-agente independente (autor diferente), volta 2 de 3. Não leu `Documentos/`, `Modelos/`, `requeriment.txt` nem `test/`; sem push, deploy nem VM; o `stash@{0}` antigo não foi tocado. Sensor em worktree temporária isolada (nunca `git stash`), removida no fim; `git status --porcelain` da árvore real igual ao de antes (só `requeriment.txt` e `test/`).

**Result**: PASS na volta 2. 29 de 29 requisitos têm evidência `arquivo:linha` e o gate está verde (backend 5459 passando, frontend 636 passando). As quatro lacunas da volta 1 (G1, G3, G4, G5) estão fechadas: M03 e M04 agora morrem (R1, R2), F04 morre (F04re), o CSS do mínimo não definido está fixado (G4re) e a versão substituída recusa a edição de critério (R3). O sensor da volta 2 rodou 45 mutantes (5 reaplicados da volta 1 e 40 novos): 40 mortos e 5 sobreviventes, todos sem efeito observável sobre um requisito (2 equivalentes por estado inalcançável, 1 fallback sem chamador, 2 fora do texto da spec); ver as lacunas de severidade baixa G6 a G10.

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
| T35..T38 (correções FT1..FT4 das lacunas G1, G3, G4, G5) | Done | `1409220`, `e848e9c`, `bad286a`, `fdd393f`; cada uma confirmada abaixo com o mutante reaplicado |
| T34 (Verifier) | Done | este relatório (volta 2 de 3) |

Testes removidos no intervalo: nenhum desde a volta 1 (só acréscimos: +2 em `test_scoring_periods.py`, +2 em `test_admin_criteria.py`, +1 em `GroupBars.test.tsx`, +1 em `styles.test.ts`). Os removidos até a volta 1 (22 funções de backend e 12 `it` de frontend) foram todos substituídos por teste da regra nova, como a volta 1 registrou.

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
| GI-07 versão nova única sugerida e escolhível; antiga substituída | só a nova é sugerida e escolhível; 422 `VERSAO_SUBSTITUIDA`; a antiga marcada | T: `backend/tests/integration/scoring/test_table_choice.py:208` (sugestão é a não substituída mesmo com o mesmo início), `:217` (inverter a marca inverte a sugestão), `:226` (só substituídas dá `suggested is None`), `:234` (`error.value.code == "VERSAO_SUBSTITUIDA"`, mensagem exata, nada gravado, auditoria igual); `backend/tests/integration/api/test_scoring_process_api.py:152` (HTTP 422, `(field, code) == ("version_id", "VERSAO_SUBSTITUIDA")`); `backend/tests/integration/scoring/test_admin_versions.py:157,185,195` (regras de versão aberta, sobreposição e base de importação); `backend/tests/integration/test_seed_scoring.py:150,204`; `backend/tests/integration/api/test_scoring_tables_api.py:157`; **`backend/tests/integration/scoring/test_admin_criteria.py:155` (versão marcada como substituída, sem processo que a use: `Conflict` com "substituída", critério segue `Decimal("5")`, nenhum evento `UPDATE`) e `:170` (a versão que a substitui aceita a edição, critério `Decimal("12")`)**; `scoring_admin.py:342-345`; R3 morto; `frontend/src/components/TablePicker.test.tsx:132,145,161`; C: `scoring.py:121-129,185-190`, `scoring_admin.py:135-138,417-420`, `entities/scoring.py:62-67`; M07..M11, M16, M18, M20, M39, F02 mortos | PASS |
| GI-08 percentual sem alerta | percentual do Grupo I sobre o total, sem alerta | T: `test_scoring_engine_group1_total.py:250` (`group1_percent == D("28.57")`), `:258` (`77.42`, `limit_adjustments == ()`, nenhuma linha com alerta); `test_scoring_golden.py:264-268` (`body["alerts"] == []`, `"30.36"` em `:252`); `frontend/src/components/PanelHeadline.test.tsx:54` (`30,36%`) | PASS |
| GI-09 ano inteiro fora | sem data e sem período de datas, ano inteiro do período fora do interstício vira `FORA_DO_INTERSTICIO`; sem inventar datas de semestre | T: `backend/tests/unit/domain/test_scoring_periods.py:158` (2019.1 contra 2022-2024 é FORA), `:162` (ano que cruza o início é SEM_DATA), `:167` (ano após o fim é FORA), `:171`, `:175-197` (fronteiras 01/01 do início e 31/12 do fim), **`:199` (início em 31/12/2022 e oferta 2022.2 dá `PeriodState.SEM_DATA`) e `:206` (fim em 01/01/2025 e oferta 2025.1 dá `SEM_DATA`)**, `:213-225` (data ou período de datas vencem o período letivo), `:233` e `:239` (outro grupo e período malformado seguem SEM_DATA); `test_activity_validity.py:329,339,348`; `test_scoring_engine_group1_total.py:275,289`; C: `scoring_periods.py:97-127`; M05, R1 (M03) e R2 (M04) mortos | PASS (G1 fechada) |
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
| GRES-02 "Mínimo não definido" em texto comum | sem destaque de valor | T: `PanelHeadline.test.tsx:42` (`className` vazio, sem `.panel-value` nem `.panel-minimum` no mínimo, só o total leva a classe de destaque) | PASS (G4 fechada: `frontend/src/styles.test.ts:270` fixa que `.panel-headline dd` não declara `font-size` nem `font-weight`; G4re morto) |
| GRES-03 uma linha por grupo com barra | nome, subtotal, barra proporcional ao total, 0,00 discreto | T: `frontend/src/components/GroupBars.test.tsx:22` (8 linhas), `:34` (subtotais em pt-BR, ordem I a VIII), `:48` (barra `aria-hidden`, largura `30,36%` e `52/303`), `:57` (`toHaveClass("muted")` e "0,00" em texto), `:65` (total 0: `"0%"` sem NaN nem Infinity); **`GroupBars.test.tsx:75`** (total `"0.00"` com parcela `"5.00"` dá `style.width === "0%"`, sem NaN nem Infinity); F04re morto (G3 fechada) | PASS |
| GRES-04 bloco Docência (PIT) | ofertas por período, disciplina, nível, horas, total do período, total geral; "Aguardando validação" fora das horas | T: `frontend/src/components/TeachingBlock.test.tsx:38,57,68,78,102`; `frontend/src/pages/ProcessScoring.test.tsx:448`; `frontend/src/components/ScoringPanel.test.tsx:54`; M27, F05, F06 mortos | PASS |
| GRES-05 sem ofertas | "Nenhuma disciplina lançada no Grupo I" | T: `TeachingBlock.test.tsx:89,96`; `ProcessScoring.test.tsx:494` | PASS |
| GRES-06 potencial em cartões | só com potencial maior que 0 | T: `frontend/src/components/PotentialCards.test.tsx:10,17`; `ScoringPanel.test.tsx:78` (a seção some); F07 morto | PASS |
| GRES-07 contadores em faixa única | atividades, com comprovante, pendentes, não pontuadas, com divergências | T: `ScoringPanel.test.tsx:66` (`["Atividades: 20", "Com comprovante: 15", "Pendentes: 3", "Não pontuadas: 4", "Com divergências: 6"]`), `:54` (ordem dos blocos) | PASS |
| GRES-08 sem depender de cor, sem rolagem a 360 px | texto em cada valor; sem rolagem horizontal da página | T: `ScoringPanel.test.tsx:97` (sem elemento focável), `GroupBars.test.tsx:48,57` (valor em texto), `frontend/src/styles.test.ts:190` (regras estáticas); **medição em Chrome**: página de medição de escopo temporário (não versionada) com o `ScoringPanel` e dados de estresse (total de 7 dígitos, títulos de 90 caracteres, pós-graduação, oferta aguardando) em iframes: 360 px `clientWidth 345 == scrollWidth 345`, 320 px `305 == 305`, sem rolagem horizontal; controle negativo (um `div` de 640 px na mesma página): `scrollWidth 656 > 345`, overflow detectado nas duas larguras Volta 2: nenhum arquivo de produção do frontend mudou desde `f0bbc08` (`git diff f0bbc08..HEAD -- frontend` só toca `GroupBars.test.tsx` e `styles.test.ts`), então a medição de Chrome da volta 1 vale para o HEAD | PASS |
| GRES-09 versão antiga | "Grupos II a VIII", Docência em horas, fora do total | T: `PanelHeadline.test.tsx:23`, `GroupBars.test.tsx:40` (7 linhas), `TeachingBlock.test.tsx:83`, `ScoringPanel.test.tsx:85`, `frontend/src/components/ScoringTable.test.tsx:184`; F03, F10 mortos | PASS |

**Status**: 29 de 29 requisitos com teste que fixa o resultado da spec e evidência `arquivo:linha`; as lacunas G1, G3, G4 e G5 da volta 1 estão fechadas. Nenhum requisito sem evidência.

**Edge cases**: semestre só fora omitido (`test_table_document_rows.py:328`, `TeachingBlock.test.tsx:102`); arredondamento meio para cima antes de somar (`test_scoring_engine_group1_total.py:78,123`); título de 400 caracteres cortado como nas outras linhas (`test_table_document_rows.py:296`, `test_table_docx.py:189`, `test_table_pdf.py:110`).

**Critérios de sucesso da spec**: 24, 24, 24 e 20 de Grupo I e 211 + 92 = 303 (`test_scenario_303.py:16`, `test_scoring_golden.py:252`); a Tabela gerada com seção I, total 303 e sem Status nem Comprovante, em DOCX e PDF (`test_generated_table_acceptance.py:60,90`); painel em blocos com Docência por período e disciplina (`ScoringPanel.test.tsx:54`).
---

## Discrimination Sensor

### Volta 2: reaplicação dos sobreviventes e mutantes novos

Worktree temporária (`git worktree add --detach`, removida no fim), um mutante por vez com restauração do arquivo logo após a rodada, rodando só os testes que cobrem o trecho (backend em PostgreSQL real com `pytest -x`; frontend em vitest). O pytest completo rodou uma vez e antes dos mutantes, nunca em paralelo com eles. 45 mutantes de comportamento: 5 reaplicados da volta 1 (R1, R2, R3, F04re, G4re) mais R4, N1..N13, P1..P8 de backend (21) e F11..F28 de frontend (18) novos, em áreas diferentes das da volta 1 (troca automática por status, justificativa e valores da auditoria, ordem e corte da Tabela, colunas e células do DOCX e do PDF, semente, percentual do Grupo I, tradução do 422, painel e blocos da Etapa 4).

| Mutation | Requisito | File:line | Description | Killed? | Killed by / nota |
| -------- | --------- | --------- | ----------- | ------- | ---------------- |
| R1 (M03) | GI-09 | `backend/app/domain/rules/scoring_periods.py:103` | `date(year, 12, 31) < start` virou `<=` | morto | `test_scoring_periods.py::test_offer_of_the_year_before_an_interstice_that_starts_on_december_31st_is_sem_data` (`:199`) |
| R2 (M04) | GI-09 | `backend/app/domain/rules/scoring_periods.py:103` | `date(year, 1, 1) > end` virou `>=` | morto | `test_scoring_periods.py::test_offer_of_the_year_after_an_interstice_that_ends_on_january_1st_is_sem_data` (`:206`) |
| R3 (G5) | GI-06/GI-07 | `backend/app/application/use_cases/scoring_admin.py:342` | recusa da edição de critério da versão substituída removida | morto | `test_admin_criteria.py::test_version_marked_as_superseded_is_read_only_when_no_process_uses_it` (`:155`) |
| F04re (G3) | GRES-03 | `frontend/src/components/GroupBars.tsx:16` | guarda `!(whole > 0)` removida | morto | `GroupBars.test.tsx > GRES-03: total 0 com uma parcela positiva também dá barra vazia` (`:75`) |
| G4re | GRES-02 | `frontend/src/styles.css:1122` | `.panel-headline dd` ganha `font-size` | morto | `styles.test.ts > GRES-02: o valor do mínimo herda o tamanho e o peso do texto comum` (`:270`) |
| R4 | GI-07 (downgrade) | `backend/alembic/versions/0009_version_superseded.py:34` | `downgrade` não derruba a coluna | morto | `test_migration_version_superseded.py::test_downgrade_one_revision_drops_the_column_and_keeps_the_versions` (`:45`) |
| N1 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:12` | `EDITABLE` só com `RASCUNHO` (processo `EM_ANDAMENTO` não troca) | morto | `test_adopt_superseding_version.py::test_draft_and_in_progress_processes_move_to_the_new_version_with_one_audit_event_each` (`:66`) |
| N2 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:51` | `before` e `after` da auditoria trocados | morto | o mesmo teste (`:66`, `changes == {...: {"before": legacy, "after": new}}`) |
| N3 | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:38` | `not in (None, new.id)` virou `is not None` (já marcada pela nova, não move mais) | sobreviveu | equivalente por estado inalcançável: a versão marcada nunca é escolhível (422 `VERSAO_SUBSTITUIDA`) e a marca e as trocas saem na mesma transação; ver G6 |
| N4 | GTAB-02 | `backend/app/domain/rules/table_document.py:139` | corte do título em 400 em vez de 399 mais reticências | morto | `test_table_document_rows.py::test_a_title_up_to_the_cap_is_shown_whole_and_a_longer_one_is_cut_with_an_ellipsis` |
| N5 | GTAB-02 | `backend/app/domain/rules/table_document.py:158` | ordem por título sem `casefold` | morto | `test_table_document_rows.py::test_the_offers_are_ordered_by_term_and_then_by_title_ignoring_case` (`:266`) |
| N6 | GTAB-02 | `backend/app/domain/rules/table_document.py:159` | ordem por título sem retirar a marca de acento | sobreviveu | fora do texto da spec e do design (D diz "sem diferenciar maiúscula"); o teste `:266` usa "álgebra" e "Banco", que ordenam igual com a marca; ver G7 |
| N7 | GTAB-08 | `backend/app/infrastructure/documents/table_text.py:48` | contadores do rodapé em ordem invertida | morto | `test_table_docx.py::test_no_cell_says_voucher_or_status_and_the_footer_has_no_voucher_nor_status_counters` |
| N8 | GTAB-06 | `backend/app/infrastructure/documents/table_text.py:10` | cabeçalho "Período letivo" virou "Período" | sobreviveu | a spec não nomeia os cabeçalhos da seção de horas (GTAB-06 pede só horas por período e total); ver G8 |
| N9 | GI-06 | `backend/app/domain/rules/activity_validity.py:99` | `GRUPO_NAO_CONTA` sem a exceção do critério de PIT | morto | `test_activity_validity.py::test_a_pit_offer_of_group_one_is_valid_although_the_group_is_outside_the_total` |
| N10 | GI-10 | `backend/app/infrastructure/database/seed.py:174` | a versão é inserida mesmo se já existe | morto | `test_seed_scoring.py::test_seed_twice_does_not_duplicate_anything` |
| N11 | GI-07 | `backend/app/presentation/errors.py:67` | `code` do 422 deixa de ir na resposta | morto | `test_scoring_process_api.py::test_choosing_a_superseded_version_is_422_with_the_code_versao_substituida` (`:152`) |
| N12 | GI-03 | `backend/app/domain/rules/scoring_engine.py:262` | `pit_hours` só em linha fora do total | morto | `test_scoring_engine_group1_total.py::test_points_equal_the_pit_hours_and_the_row_is_inside_the_total_in_every_weekly_load_row` |
| N13 | GTAB-07 | `backend/app/domain/rules/table_document.py:265` | faixa também para grupo fora do total | morto | `test_table_document_rows.py::test_the_211_scenario_has_seven_bands_with_the_group_subtotals` |
| P1 | GTAB-04 | `backend/app/infrastructure/documents/table_docx.py:105` | linha do total do DOCX mescla até a coluna 4 e não a 5 | morto | `test_table_docx.py::test_a_group_without_activity_has_its_band_with_zero_and_the_bands_are_merged_cells` |
| P2 | GTAB-02/04 | `backend/app/infrastructure/documents/table_docx.py:101` | colunas Pontuação unitária e Total trocadas no DOCX | morto | `test_generated_table_acceptance.py::test_section_i_has_one_row_per_offer_by_term_then_title_with_hours_one_point_and_total[docx]` |
| P3 | GTAB-02/04 | `backend/app/infrastructure/documents/table_pdf.py:99` | colunas Quantidade e Pontuação unitária trocadas no PDF | morto | o mesmo teste com `[pdf]` |
| P4 | GI-08 | `backend/app/domain/rules/scoring_engine.py:355` | percentual do Grupo I arredondado a 0 casas | morto | `test_scoring_engine_group1_total.py::test_group1_percent_is_the_group1_subtotal_over_the_total` (`:250`) |
| P5 | GI-07 | `backend/app/infrastructure/database/seed_data/ufpa.json:5` | `valid_from` da versão nova passa a 2026-01-01 (não vale para qualquer interstício) | morto | `test_seed_ufpa.py::test_table_and_version_metadata` |
| P6 | GI-01 | `backend/app/infrastructure/database/seed_data/ufpa.json:24` | Grupo I com `counts_in_total` falso na versão nova | morto | `test_seed_ufpa.py::test_group_one_is_pit_hours_counting_in_the_total` |
| P7 | GTAB-02 | `backend/app/domain/rules/table_document.py:149` | Quantidade da linha do Grupo I é a quantidade do critério e não as horas | morto | `test_table_document_rows.py::test_each_group_one_offer_is_a_row_with_item_title_period_hours_unit_and_total` (`:250`) |
| P8 | GTAB-02 | `backend/app/domain/rules/table_document.py:150` | Pontuação unitária da linha do Grupo I vem do critério e não 1,00 | morto | o mesmo teste (`:250`) |
| F11 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:30` | períodos em ordem decrescente | morto | `TeachingBlock.test.tsx > GRES-04: períodos em ordem, cada oferta com disciplina, nível e horas` |
| F12 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:30` | oferta sem período letivo vai para o início | morto | `TeachingBlock.test.tsx > GRES-04: oferta sem período letivo vai para 'Sem período letivo'` |
| F13 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:56` | total geral diz "horas" onde devia dizer "pontos" | morto | `TeachingBlock.test.tsx > GRES-04: o total geral vem da API e, na versão nova, diz '= pontos'` |
| F14 | GRES-06 | `frontend/src/components/PotentialCards.tsx:20` | cartão "com data" mostra o valor "sem data" | morto | `PotentialCards.test.tsx > GRES-06: com potencial maior que 0 mostra os três cartões` |
| F15 | GRES-06 | `frontend/src/components/ScoringPanel.tsx:67` | seção do potencial também com potencial 0 (`>=`) | morto | `ScoringPanel.test.tsx > GRES-06: sem potencial a seção do potencial não aparece` (`:78`) |
| F16 | GRES-07 | `frontend/src/components/ScoringPanel.tsx:80` | contador "Pendentes" mostra "Com comprovante" | morto | `ScoringPanel.test.tsx > GRES-07: os contadores são uma lista única` (`:66`) |
| F17 | GRES-03 | `frontend/src/components/GroupBars.tsx:27` | grupos em ordem decrescente | morto | `GroupBars.test.tsx > GRES-03: cada um dos oito grupos mostra o seu subtotal ... na ordem de I a VIII` (`:34`) |
| F18 | GRES-09 | `frontend/src/components/GroupBars.tsx:26` | filtro do Grupo I com `||` (some o Grupo I e todo outro grupo na versão antiga) | morto | `GroupBars.test.tsx > GRES-09: na versão antiga o grupo I não tem barra` (`:40`) |
| F19 | GRES-01 | `frontend/src/components/PanelHeadline.tsx:18` | valor do mínimo sumiu do texto curto | morto | `PanelHeadline.test.tsx > GRES-01: o mínimo atingido e o não atingido saem em texto curto com o valor` (`:30`) |
| F20 | GI-08 | `frontend/src/components/PanelHeadline.tsx:37` | percentual ausente mostra "0" em vez de "—" | morto | `PanelHeadline.test.tsx > GI-08` (`:54`) |
| F21 | GI-11 | `frontend/src/components/GeneratedBlock.tsx:75` | aviso da Etapa 5 sem a condição `kind === "TABELA"` | sobreviveu | equivalente: `ProcessGenerated.tsx:118` só passa `chosenTableVersionId` ao bloco da Tabela; nos outros blocos a prop é `undefined` e `Boolean(chosenTableVersionId)` já dá falso; ver G9 |
| F22 | GI-11 | `frontend/src/components/GeneratedBlock.tsx:74` | versão comparada é a da geração mais recente e não a da última pronta | morto | `ProcessGenerated.test.tsx > uma Tabela mais nova que falhou não esconde o aviso da última pronta` (`:265`) |
| F23 | GI-07 | `frontend/src/components/TablePicker.tsx:49` | processo em versão substituída volta a ter troca de tabela | morto | `TablePicker.test.tsx > GI-07: versão substituída > processo que ainda usa a versão antiga mostra o nome dela e nenhum botão` |
| F24 | GRES-09 | `frontend/src/components/ScoringPanel.tsx:35` | sem a prop, `outside` não é inferido das linhas (`?? false`) | sobreviveu | o único chamador (`ProcessScoring.tsx:154`) lê `table`, `scoring` e `version` juntos antes de renderizar, e sem versão não há linha `outside_total`: o fallback é inalcançável em produção; sonda no scratch: componente sem a prop com a versão antiga diz "Grupos II a VIII" (real) e "Grupos I a VIII" (mutante). Ver G10 |
| F25 | GI-01 | `frontend/src/components/ScoringTable.tsx:43` | linha fora do total passa a mostrar horas como pontos | morto | `ScoringTable.test.tsx > TELA-01: Grupo I em horas de PIT > mostra as horas com o rótulo 'horas (PIT)'` |
| F26 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:42` | nível da oferta some | morto | `TeachingBlock.test.tsx > GRES-04: períodos em ordem, cada oferta com disciplina, nível e horas` |
| F27 | GRES-04 | `frontend/src/components/TeachingBlock.tsx:49` | total do período mostra o total geral | morto | `TeachingBlock.test.tsx > GRES-04: períodos em ordem ...` e `a oferta aguardando validação ... o total do período é o da API` |
| F28 | GRES-08 | `frontend/src/components/ScoringPanel.tsx:43` | região viva não anuncia o total novo | morto | `ScoringPanel.test.tsx > região viva do total > anuncia o total novo depois de um recálculo que o muda` |

**Sensor depth**: P0-full, 45 mutantes manuais na volta 2 (49 na volta 1; 94 no total), caminho de integridade de dados: total da pontuação, troca de versão e migração.
**Resultado do sensor**: 40 de 45 mortos; 5 sobreviventes sem efeito observável sobre um requisito (N3 e F21 equivalentes, F24 sem chamador, N6 e N8 fora do texto da spec): PASS. As quatro lacunas da volta 1 estão fechadas pelos mutantes reaplicados R1, R2, R3, F04re e G4re (todos mortos).

**Isolamento**: worktree removida (`git worktree list` só com a árvore real); `git status --porcelain` da árvore real idêntico ao de antes do sensor (`?? requeriment.txt`, `?? test/`).

---

## Interactive UAT Results

Não aplicável nesta volta (o usuário dorme). O UAT visual da volta 1 (painel a 360 e 320 px em Chrome headless com controle negativo; DOCX e PDF da Tabela sintética de 303 pontos convertidos em imagem) continua válido: `git diff f0bbc08..HEAD` não toca arquivo de produção do frontend nem código de geração de documento, só `scoring_admin.py` (edição de critério) e testes.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | OK: a correção FT4 tem 4 linhas (`scoring_admin.py:342-345`); as outras três são só testes |
| Surgical changes | OK: o Relatório e o Comprovante não mudam (spec); nenhum arquivo fora do escopo das lacunas mudou desde a volta 1 |
| No scope creep | OK |
| Matches patterns | OK: a recusa usa `Conflict` como a recusa vizinha da mesma classe, com a mensagem em pt-BR |
| Spec-anchored outcome check (asserted values match spec) | OK: 29 de 29; as asserções fixam 8,00, 4,00, 12,00, 92, 303, 3 e 6 pontos, `VERSAO_SUBSTITUIDA` e as cinco colunas |
| Per-layer Coverage Expectation (domain 1:1 ACs; routes happy+edge+error) | OK: rotas com 422 `VERSAO_SUBSTITUIDA`, 422 `points_override`, 409 somente leitura |
| Every test maps to a spec requirement | OK: os seis testes novos citam GI-09, GRES-02, GRES-03 ou GI-06 e GI-07 |
| Documented guidelines followed | `CLAUDE.md` (regras 1, 7 e 8 do motor; só dados sintéticos); AD-001 (teste de arquitetura verde), AD-004 (PostgreSQL real), AD-012 (documentos gerados e processos fechados intactos), AD-023 |

---

## Edge Cases

- [x] Semestre só com ofertas fora do interstício: omitido no painel e na Tabela (`test_table_document_rows.py:328`, `TeachingBlock.test.tsx:102`).
- [x] Horas com 3 ou mais casas: meio para cima, soma das linhas = subtotal (`test_scoring_engine_group1_total.py:78,123`).
- [x] Título de mais de 400 caracteres cortado na Tabela como nas outras linhas (`test_table_document_rows.py:296`; N4 morto).
- [x] Oferta sem período letivo: "Sem período letivo", por último na Tabela, sem total próprio (`test_table_document_rows.py:283`).
- [x] Seed duas vezes e com a versão antiga presente: sem duplicar, sem segunda troca (`test_seed_scoring.py:252`; N10 morto).
- [x] Fronteira do ano inteiro com o interstício começando em 31/12 ou terminando em 01/01 (`test_scoring_periods.py:199,206`; R1 e R2 mortos).

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`, rodado no HEAD `fdd393f` (frontend em worktree com `node_modules` ligado, para não gravar `dist` na árvore real).
- **Resultado backend**: `ruff` limpo (`All checks passed!`); `5459 passed, 3 deselected (maritalk_live), 1 warning in 719.62s`, uma única execução completa e sem outro pytest em paralelo.
- **Resultado frontend**: `eslint` limpo (exit 0); `vite build` ok (exit 0); `Test Files 46 passed (46), Tests 636 passed (636)`.
- **Test count before feature**: 5322 (backend) e 584 (frontend), no HEAD `9bf9ad7` registrado em `.specs/features/correcoes-auditoria/validation.md`.
- **Test count after feature**: 5459 e 636.
- **Delta**: +137 de backend e +52 de frontend (+4 e +2 desde a volta 1: 5455 e 634).
- **Skipped tests**: 3 `deselected` por `-m 'not maritalk_live'` (opt-in com `RUN_LIVE_MARITALK=1`, fora do gate).
- **Failures**: nenhuma.

---

## Fix Plans

Nenhuma correção bloqueante. As lacunas G6 a G10 são de severidade baixa e opcionais (ver abaixo); nenhuma muda o veredito.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| GI-01..GI-12 | Implemented | Verified |
| GTAB-01..GTAB-08 | Implemented | Verified |
| GRES-01..GRES-09 | Implemented | Verified |

---

## Gaps (ranqueadas)

As lacunas G1 a G5 da volta 1 estão fechadas (G1 por `test_scoring_periods.py:199,206`; G3 por `GroupBars.test.tsx:75`; G4 por `styles.test.ts:270`; G5 por `scoring_admin.py:342` e `test_admin_criteria.py:155,170`; G2 segue como nota: nenhum teste de navegador é versionado, e a medição de Chrome da volta 1 vale para o HEAD porque nenhum arquivo de produção do frontend mudou).

| # | Gap | Requisito | Evidência | Severidade |
| - | --- | --------- | --------- | ---------- |
| G6 | N3: o teste de idempotência não cobre o estado "versão já marcada pela nova, mas com processo editável ainda nela"; com `is not None` no lugar de `not in (None, new.id)` essa tentativa não move mais o processo. Estado inalcançável pela API (a versão marcada é recusada com 422 e a marca e as trocas saem na mesma transação) | GI-10 | `backend/app/application/use_cases/scoring_adoption.py:38`; `test_adopt_superseding_version.py:127` | Baixa: opcional |
| G7 | N6: a ordem por título retira a marca de acento (`table_document.py:159`), regra que nem a spec nem o design dizem (o design diz "sem diferenciar maiúscula"), e o teste usa "álgebra" e "Banco", que ordenam igual com a marca. Lição L-030 | GTAB-02 | `backend/app/domain/rules/table_document.py:159`; `test_table_document_rows.py:266` | Baixa: spec-precision, decidir se a regra fica na spec ou sai do código |
| G8 | N8: o cabeçalho "Período letivo" da seção de horas não está na spec nem em teste. Lição L-029 | GTAB-06 | `backend/app/infrastructure/documents/table_text.py:10` | Baixa: spec-precision |
| G9 | F21: a condição `kind === "TABELA"` em `GeneratedBlock` é redundante com a prop só passada ao bloco da Tabela (`ProcessGenerated.tsx:118`); a defesa existe e o teste do Relatório e do Comprovante (`ProcessGenerated.test.tsx:296`) passa pela mesma via | GI-11 | `frontend/src/components/GeneratedBlock.tsx:75` | Baixa: equivalente |
| G10 | F24: o fallback de `ScoringPanel` quando `group1OutsideTotal` é omitido não tem teste nem chamador (o único chamador sempre tem a versão antes de renderizar). Lição L-028 | GRES-09 | `frontend/src/components/ScoringPanel.tsx:35`; `ProcessScoring.tsx:154` | Baixa: ou um teste sem a prop, ou remover o fallback |

---

## Summary

**Overall**: Ready (volta 2 de 3)

**Spec-anchored check**: 29 de 29 requisitos com o resultado da spec fixado por teste; as lacunas G2 e G4 da volta 1 são spec-precision que não bloqueiam; G7 e G8 são spec-precision novas, de severidade baixa
**Sensor**: 40 de 45 mutantes mortos na volta 2; 5 sobreviventes sem efeito observável (N3, N6, N8, F21, F24); os 4 sobreviventes reais da volta 1 (M03, M04, F04, G5) estão mortos
**Gate**: backend 5459 passando, frontend 636 passando, `ruff`, `eslint` e `build` limpos

**What works**: Grupo I soma no total a 1 ponto por hora, com recusa de `points_override` nas duas versões; versão substituída nunca sugerida nem escolhível (422 `VERSAO_SUBSTITUIDA`, e agora sem edição de critério); troca automática só de `RASCUNHO` e `EM_ANDAMENTO`, auditada com `before` e `after`, atômica e idempotente; VI.14 = 3 na versão nova e 6 na antiga intacta; Tabela de 5 colunas, seção I, 303 pontos no cenário derivado, sem Comprovante nem status no DOCX e no PDF; painel a 320 e 360 px sem rolagem; downgrade da `0009` testado em PostgreSQL real; fronteiras do ano inteiro (31/12 e 01/01) fixadas.

**Issues found**: só as lacunas de severidade baixa G6 a G10.

**Next steps**: marcar a feature como `Verified` e seguir para o deploy com a autorização do usuário (push e deploy não fazem parte da verificação).

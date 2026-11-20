# Revisão simplificada das atividades: Validation

## Validation: revisao-simplificada - FAIL ❌

**Date**: 2026-11-19
**Spec**: `.specs/features/revisao-simplificada/spec.md` (40 requisitos: VAL 6, SEC 12, DUP 7, SEG 5, EDT 7, QTD 3)
**Diff range**: `39bbfd2..e1b06a0` (56 commits, 114 arquivos de código e teste: 9658 inserções, 1416 remoções)
**Verifier**: sub-agente independente (T44, autor ≠ verificador); leu a spec, os testes e o código do zero e não reaproveitou as tabelas do autor.
**Result**: FAIL (nenhum requisito tem teste que contradiz a spec; 3 mutantes sobreviveram, 1 cláusula sem teste e 1 sem prova de renderização)

**Spec-anchored check**: 33 de 40 requisitos com asserção que bate com o resultado da spec; 7 com lacuna de cobertura (SEC-05, SEC-12, DUP-03, SEG-01, SEG-02, SEG-05, EDT-03); 10 lacunas de precisão da spec (SP1 a SP10).
**Gate**: backend `ruff` limpo e 5269 testes passando (3 `deselected`); frontend `tsc -b` e `eslint` limpos, 561 testes passando e 1 pulado.
**Sensor**: 66 mutantes injetados, 63 mortos, 3 sobreviventes (B27, B43, F3b).

Os mutantes e as lacunas viram as tarefas de correção FT1 a FT7 (abaixo). Este relatório não corrige nada; depois das correções, reverificar (volta 1 de no máximo 3).

---

## Task Completion

| Tarefa | Status | Notas |
| ------ | ------ | ----- |
| T1 a T42 | ✅ Done | commitadas (`e9125cd` a `c3b7189`), um commit por tarefa |
| T45 a T55 | ✅ Done | correções da revisão dos lotes 5 e 6 (`4837e2a` a `e1b06a0`) |
| T43 | ⚠️ Partial | AD-022 em `STATE.md`, regra 10 em `CLAUDE.md` e a rastreabilidade de `spec.md` e `design.md` estão na árvore sem commit (`git status`: M em 4 arquivos); as caixas de `tasks.md:1629-1632` seguem abertas |
| T44 | este relatório | |

---

## Spec-Anchored Acceptance Criteria

Convenção: `B/` = `backend/tests/`, `F/` = `frontend/src/`. "Mutantes" cita os mutantes da seção Sensor que guardam o requisito.

### P1: Validar pontua

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| VAL-01 validar com categoria e dentro do interstício pontua | II.5 validada = 8,00 na Etapa 4, sem outra ação | `B/integration/api/test_scoring_validity_api.py:89` `total == "0.00"` antes; `:100` `(row["status"], row["unit_points"], row["points"]) == ("PONTUADA","8.00","8.00")`; `:101` `body["total"] == "8.00"`. Também `B/unit/domain/test_scoring_engine_validity.py:146-150` (`row.points == D("8")`, `result.total == D("8")`), `B/integration/api/test_activities_validity_api.py:153,163,165` (previsto 8.00, total 0.00 → 8.00), `B/integration/api/test_activity_validate_rules_api.py:98-115` (200 e `VALIDADA`) | B4, B11, B23 | ✅ PASS |
| VAL-02 item por unidade sem quantidade | pontua com 1 e emite `QUANTIDADE_ASSUMIDA` | `B/unit/domain/test_scoring_engine_validity.py:223-230` `points == D("8")`, `effective_quantity == D("1")`, `ASSUMED in alert_codes(...)`; `:244-250` com quantidade informada não há alerta; `:253-260` só itens por unidade; `B/unit/domain/test_scoring_alerts.py:78`; `F/labels.test.ts:163-166` | B14, B35 | ✅ PASS (a gravidade `ALERTA`, a mensagem e a norma, afirmadas em `:233-241`, a spec não define: SP4) |
| VAL-03 validar sem categoria | 422 no campo `categoria`, "Escolha a categoria antes de validar", atividade como estava | `B/integration/api/test_activity_validate_rules_api.py:53-66` `detail == [{"field":"categoria","message":"Escolha a categoria antes de validar"}]` e `(after["status"], after["version"]) == ("AGUARDANDO_REVISAO", 1)`; `F/components/ActivityRow.test.tsx:148-158` | B11, B23 | ✅ PASS |
| VAL-04 lote | valida as com categoria, lista as sem | `B/integration/scoring/test_bulk_validate_skipped.py:40-54` `[a.id for a in result.activities] == [categorized...]`, `[(s.id, s.reason)...] == [(a.id,"SEM_CATEGORIA")...]`; `B/integration/api/test_bulk_validate_api.py:79-102`; `F/components/ValidActivitiesSection.test.tsx:165-184` ("3 validadas; 1 ficou sem categoria"), `:290-300` ("Validar as confiáveis") | B12, B12b | ✅ PASS (o lote também pula as não válidas, com `reason` própria: SP9) |
| VAL-05 auditoria do status, sem justificativa | 1 evento `STATUS`, `justification is None` | `B/integration/api/test_activity_validate_rules_api.py:98-115` `len(events) == 1`, `events[0].justification is None`; em lote `B/integration/api/test_bulk_validate_api.py:175-206` | B26 | ✅ PASS |
| VAL-06 "Validar" só para válida | nenhuma não válida oferece Validar | `F/components/ActivityRow.test.tsx:160-172` (`queryByRole("button",{name:/^Validar /})` ausente), `:174-184`; `F/components/InvalidActivitiesSection.test.tsx:98-109`; servidor recusa: `B/integration/api/test_activity_validate_rules_api.py:68-95` (`error["code"] == "ATIVIDADE_NAO_VALIDA"`) | B11b, F1b | ✅ PASS (a recusa no servidor não está na spec: SP4) |

### P1: Etapa 3 em duas seções

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| SEC-01 duas seções com o total | títulos "Atividades válidas (N)" e "Atividades não válidas (N)" | `F/components/ActivityWorkspace.test.tsx:70-75` `getByRole("heading",{level:2,name:"Atividades válidas (1)"})` e `name: /^Atividades não válidas \(2\)/` | F5 | ✅ PASS |
| SEC-02 seção de válidas | dentro do interstício, com ou sem categoria, carga suficiente, não rejeitadas; 25 por vez | `F/components/ValidActivitiesSection.test.tsx:80-87` `rowsShown() == 25`, depois 50, "Mostrando 50 de 120"; `:89-93`; classificação: `B/unit/domain/test_activity_validity.py:72-83,176-178,183-189`; `B/integration/api/test_activities_validity_api.py:60-87` (120 atividades) | B1, B3, F6, F16 | ✅ PASS |
| SEC-03 busca e filtros com contagem | chips todas/aguardando/validadas/precisa de categoria com a contagem, busca, grupo | `F/components/ValidActivitiesSection.test.tsx:103-119` ("Todas (120)", "Aguardando validação (80)", "Validadas (30)", "Precisa de categoria (10)"), `:121-135`, `:137-148`, `:405-414` (`["Todos os grupos","II · Orientação (1)","III · Bancas (2)"]`); `F/components/ActivityFilters.test.tsx:25-31` | F3a, F13, F17 | ✅ PASS |
| SEC-04 selo e seletor na linha | "Precisa de categoria" e seletor; aplica na hora, sem justificativa | `F/components/ActivityRow.test.tsx:100-107`, `:109-126` (`toMatchObject({group_number:3,item_number:2,expected_version:4})`, sem `justificativa`); `F/components/CategoryPicker.test.tsx:36-44`; `F/components/ActivityWorkspace.test.tsx:241-250` | F1 | ✅ PASS |
| SEC-05 bloqueio do avanço | avanço à Etapa 4 desabilitado e "N atividades precisam de categoria" | `F/pages/ProcessActivities.test.tsx:149-158` (`items[3]`/`items[4]` com `aria-disabled`, sem link), `:160-176` (libera ao escolher), `:187-196` (não válida sem categoria não bloqueia); `F/components/ValidActivitiesSection.test.tsx:153-156`; `F/labels.test.ts:150-153` | F2, F14, F15, F19 mortos; **F3b sobreviveu** | ⚠️ PASS com lacuna G3 (o aviso da seção com filtro ativo) e SP7 (sem tabela o avanço fica livre) |
| SEC-06 seção de não válidas | fora do interstício, carga abaixo do mínimo, rejeitadas, cada uma com o motivo | `F/components/InvalidActivitiesSection.test.tsx:98-109`; `B/integration/scoring/test_list_activities_validity.py:42-76` (`validity.params == {...}`); `B/unit/domain/test_activity_validity.py:100-134,240-246` | B1, B2 | ✅ PASS (a implementação lista também grupo que não conta e duplicidade residual: SP2) |
| SEC-07 texto do motivo | "Fora do interstício: data dd/mm/aaaa; interstício dd/mm/aaaa a dd/mm/aaaa"; "Carga horária insuficiente: N h; o item exige M h"; "Rejeitada por você" | `F/labels.test.ts:95-98` `toBe("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025")`, `:107-111`, `:119-121`; `F/components/ReasonText.test.tsx:15-39` | F11 | ✅ PASS (período de categoria por ano e precisão de mês não estão na spec: SP3) |
| SEC-08 corrigir leva às válidas, sem recarregar a página | a atividade passa para a seção de válidas | `F/components/ActivityWorkspace.test.tsx:91-112` `getByRole("heading",{name:"Atividades válidas (2)"})` e não válidas `(1)`; `B/integration/scoring/test_list_activities_validity.py:136-151` | | ✅ PASS |
| SEC-09 reabrir rejeitada | vai a "aguardando validação" e a seção de válidas a lista | `B/integration/scoring/test_list_activities_validity.py:154-167` `only.status is AGUARDANDO_REVISAO`; `B/integration/api/test_activity_validate_rules_api.py:117-128`; `F/components/ActivityWorkspace.test.tsx:135-148`; `F/components/InvalidActivitiesSection.test.tsx:121-127` | | ✅ PASS |
| SEC-10 não válidas fechada, com total e contagem por motivo | `aria-expanded=false`, "Atividades não válidas (4)" com "Fora do interstício: 2" etc. | `F/components/InvalidActivitiesSection.test.tsx:54-64`, `:86-94` | F5 | ✅ PASS |
| SEC-11 seção vazia | "Nenhuma atividade válida ainda" / "Nenhuma atividade não válida" | `F/components/ValidActivitiesSection.test.tsx:95-99`; `F/components/InvalidActivitiesSection.test.tsx:131-135` | | ✅ PASS |
| SEC-12 sem rolagem horizontal a 360 px, teclado, não só cor | | teclado: `F/components/ActivityWorkspace.test.tsx:164-171` (`toggle` recebe foco por Tab), `F/components/InvalidActivitiesSection.test.tsx:66-74`; não só cor: `F/components/ActivityRow.test.tsx:255-262`, `F/components/ReasonText.test.tsx:41-44`; largura: `F/components/ActivityWorkspace.test.tsx:173-179` (regex no CSS: nenhum `width`/`min-width` fixo, nenhum `overflow-x: scroll`) | | ⚠️ gap G5: a largura de 360 px só tem prova estática do CSS, não de renderização |

### P1: Duplicadas mescladas

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| DUP-01 mesclar; fica a validada, senão a primeira; provas somadas sem repetir o par | | `B/integration/doc_usecases/test_activity_merge.py:38-53` (`visible == {older.id}`, páginas `{(a,1),(b,2),(c,5)}`, origem da prova), `:73-80` (validada fica, mesmo mais nova), `:83-91` (ambas ou nenhuma: a primeira), `:94-102`; `B/integration/test_repositories_merge.py:208-225` (não repete documento e página) | B5, B5b, B6, B21 | ✅ PASS (mais de duas validadas: SP6) |
| DUP-02 a outra fica no banco, marcada, com auditoria dos dois ids | | `B/integration/doc_usecases/test_activity_merge.py:56-70` (`merged_into_id == older.id`, `is_merged`), `:132-144` (`changes["merged_activity_id"]["after"] == str(newer.id)`, `kept_activity_id`); `B/integration/test_repositories_merge.py:117-131` | B6, B22 | ✅ PASS |
| DUP-03 mesclada fora das listas, totais, Tabela, Relatório e Comprovante | | listas e totais: `B/integration/scoring/test_list_activities_validity.py:119-133`, `B/integration/api/test_activity_merge_api.py:73-89` (sem linha na pontuação), `B/integration/test_repositories_merge.py:79-92`; Tabela, Relatório, Comprovante: nenhum teste gera documento com atividade mesclada | B25, B46 | ⚠️ gap G4 (só as camadas de lista e pontuação têm teste; os três documentos herdam a lista, sem prova) |
| DUP-04 mescla ao criar, editar, reprocessar e na primeira abertura da Etapa 3 | | criar `B/integration/api/test_activity_merge_on_write_api.py:77-95`; editar `:109-120`; leitura do documento `B/integration/doc_usecases/test_document_merge.py:52-58`, reprocessar `:74-87`; rota `B/integration/api/test_activity_merge_api.py:48-58`; abertura `F/pages/ProcessActivities.test.tsx:99-105` (`count(calls, MERGE) == 1`, antes da lista), `:107-120` (recarga não mescla), `:122-132` (somente leitura não mescla) | B18, B19, B20, F4, F7, F18 | ✅ PASS |
| DUP-05 repetir não muda nada | | `B/integration/doc_usecases/test_activity_merge.py:147-157` (`again.count == 0`, snapshot igual, `len(merge_events) == 1`); `B/integration/api/test_activity_merge_api.py:60-71` | B7 | ✅ PASS |
| DUP-06 falha no meio não altera nada | | `B/integration/doc_usecases/test_activity_merge.py:160-183` (falha forçada no 2º `move`, tudo igual a antes), `:186-195`; `B/integration/api/test_activity_merge_on_write_api.py:141-158`; `B/integration/doc_usecases/test_document_merge.py:120-153` | | ✅ PASS |
| DUP-07 "N duplicadas mescladas" e "Não é duplicada" | restaura, devolve as provas, marca as duas como distintas | `F/components/MergedNote.test.tsx:13-25`, `:32-46` (`POST /api/activities/m2/separate`); `B/integration/doc_usecases/test_activity_separate.py:52-64` (provas de volta, `origin_activity_id is None`), `:83-96` (`distinct_justification == DISTINCT_DEFAULT_TEXT` nas duas e `report.count == 0`), `:125-134`; `B/integration/api/test_activity_merge_api.py:140-154` | B9, B10, B10b, B32, B33, F10 | ✅ PASS |

### P1: Só as válidas seguem

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| SEG-01 cálculo, Tabela, Relatório, Comprovante e prévia da conclusão só com válidas | nenhuma linha das não válidas, nem "Não pontuada" | `B/integration/api/test_generated_validity_acceptance.py:108-116` (`title not in text`, `not re.search(r"Não pontuada(?!s)")`), `:119-123` (`activity_count == 1`, `excluded == {}`), `:129-137`; `B/integration/doc_usecases/test_generation_inputs.py:33-48`; `B/unit/domain/test_activity_order.py:34-38`; `B/integration/api/test_scoring_validity_api.py:107-128` | B4, B17, B42, B45; **B27 sobreviveu** | ⚠️ gap G1 (contagem `excluded` com não válida aguardando) e SP10b (a "prévia da conclusão" não lê atividades: `conclusion.py:27-35`, sem resultado observável) |
| SEG-02 Comprovante sem página cuja única atividade é não válida ou mesclada | | `B/integration/api/test_generated_validity_acceptance.py:143-153` (`len(originals) == 1`, títulos fora do texto); mesclada: sem teste | | ⚠️ PASS para não válida; mesclada sem teste (G4) |
| SEG-03 corrigida entra no cálculo e nas gerações seguintes | | `B/integration/api/test_scoring_validity_api.py:131-149` (`total == "8.00"`, `counters.activities == 1`); `B/integration/api/test_generated_validity_acceptance.py:159-174` (`second["summary"]["activity_count"] == 2`), `:177-191` (a versão anterior não muda) | B4 | ✅ PASS |
| SEG-04 contadores só sobre as válidas | | `B/integration/api/test_scoring_validity_api.py:126-127` (`counters.activities == 1`, `not_scored == 0`), `:172-173`; `B/unit/domain/test_scoring_engine_validity.py:103-105` | B24, B45 | ✅ PASS (o frontend só exibe `counters` do servidor; sem teste próprio: SP10c) |
| SEG-05 geração recusada com 422 `ATIVIDADE_SEM_CATEGORIA` | | `B/integration/api/test_generated_validity_acceptance.py:199-208` (3 documentos × 2 status: `(detail["field"], detail["code"]) == ("geracao","ATIVIDADE_SEM_CATEGORIA")`), `:211-216` (não válida sem categoria não recusa); `B/integration/api/test_generation_error_mapping.py:63`; `B/integration/doc_usecases/test_generation_inputs.py:51` | B15 | ⚠️ PASS no pedido; gap G6: no worker o código cai em `ERRO_INTERNO` (`app/application/use_cases/generated_documents.py:307-318,462`), sem teste |

### P1: Editar atividade com poucos campos

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| EDT-01 campos | Título, Data, Categoria; Início/Fim por ano; Horas só com carga mínima | `F/components/ActivityForm.test.tsx:57-63` (`noField` para Descrição, Comprovante, Quantidade, Horas...), `:65-70`, `:72-76` (`getByLabelText("Horas")`), `:78-86` | F9 | ✅ PASS |
| EDT-02 data fora do interstício | 422 em `event_date`, "A data deve estar entre dd/mm/aaaa e dd/mm/aaaa", atividade como estava | `B/integration/api/test_activity_edit_rules_api.py:71-79` (`message == "A data deve estar entre 23/11/2022 e 23/11/2024"`), `:82-97` (primeiro e último dia aceitos, vizinhos recusados), `:161-176` (`(event_date, version) == ("2023-05-10", 1)`), `:179-198`; `F/components/ActivityForm.test.tsx:242-253` | B13, B13b, B13c | ✅ PASS (data inalterada não é rejulgada e precisão de mês: SP5) |
| EDT-03 categoria por ano | aceita o período que cruza, recusa o que não toca | `B/integration/api/test_activity_edit_rules_api.py:121-130` (201), `:133-155` (422 em `period_end`/`period_start`), `:201-217`; **sem teste** de período só com início na criação manual | B44 morto; **B43 sobreviveu** | ⚠️ gap G2 |
| EDT-04 nova manual pede Título, Data, Categoria, Quantidade | | `F/components/ActivityForm.test.tsx:184-200` (`toEqual({title, event_date:"2023-05", group_number:2, item_number:7, quantidade:4})`) | | ✅ PASS (Grupo I novo: SP10a) |
| EDT-05 oferta do Grupo I mostra só Título e Categoria | | `F/components/ActivityForm.test.tsx:88-94` | | ✅ PASS |
| EDT-06 aplica na hora, sem justificativa, com auditoria | | `B/integration/api/test_activity_edit_rules_api.py:262-284` (`update.justification is None`, `changes["quantity"] == {"before":"1","after":"3"}`); `B/integration/scoring/test_activity_update.py:65`; `F/components/ActivityForm.test.tsx:118-125` | | ✅ PASS |
| EDT-07 vínculo só pela ação "Vincular", sem campo de comprovante | | `F/components/ActivityForm.test.tsx:62` (`noField("Comprovante")`), `:118-125`; `F/components/ValidActivitiesSection.test.tsx:343-363` (`body == {document_id:"d2", page:3}`; o seletor não oferece documento fora do interstício) | | ✅ PASS |

### P1: Quantidade e valor manual na Etapa 4

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| QTD-01 "Editar pontuação" com Quantidade (ou Horas) e valor unitário | | `F/components/ScoreEditor.test.tsx:162-174` (Quantidade com valor 3 sem Horas; Horas sem Quantidade; `Valor unitário` presente) | | ✅ PASS |
| QTD-02 recalcula na hora, sem justificativa, com auditoria | | `B/integration/api/test_activity_edit_rules_api.py:278` `Decimal(after["total"]) == Decimal(before["total"]) * 3 > 0`, `:281-284`; `F/components/ScoreEditor.test.tsx:186-198` | | ✅ PASS |
| QTD-03 quantidade negativa ou não numérica | 422 no campo `quantidade` | `B/integration/api/test_activity_edit_rules_api.py:237-259` (`-1`, `-0.5`, `"abc"` na criação e na edição, 422 em `quantidade`, valor intacto `"1.00"`); `F/components/ScoreEditor.test.tsx:237-250` | | ✅ PASS (faixa 0 a 10000 e inteiro: SP8) |

**Status**: ❌ lacunas presentes (G1 a G6) e ⚠️ lacunas de precisão da spec (SP1 a SP10).

---

## Edge Cases (spec.md, "Edge Cases")

- [x] Deixar de ser duplicada por edição não desfaz a mesclagem: `B/integration/api/test_activity_merge_on_write_api.py:123-138` (`listed == [kept]` e a linha da mesclada segue existindo).
- [ ] Trocar a categoria de validada recalcula e mantém o status: sem teste que afirme o status `VALIDADA` nem os pontos novos depois da troca (`B/integration/scoring/test_activity_update.py:65-79` troca item sem checar o status); ⚠️ G7.
- [ ] Carga horária corrigida volta às válidas com o status que tinha: só a correção por data tem teste (`B/integration/scoring/test_list_activities_validity.py:136-151`, `F/components/ActivityWorkspace.test.tsx:91-112`); o caso por carga horária não tem; ⚠️ G7.
- [x] Prova em documento fora e outra em documento dentro: a atividade fica com a de dentro (AD-019), regra anterior à feature, fora do escopo do diff.

---

## Discrimination Sensor

**Método**: worktree git isolada (`git worktree add --detach` em diretório novo do scratchpad), um mutante por vez, restaurado a cada rodada, apenas testes direcionados (pytest do `backend/.venv` com PostgreSQL real, `vitest run <arquivo>` no frontend); nunca duas execuções de pytest ao mesmo tempo (o gate completo do orquestrador terminou antes do primeiro pytest do sensor). Worktree removida ao fim; `git status --porcelain` da árvore real igual ao do início (4 arquivos `M` de documentação e `requeriment.txt`, `test/` sem versionar; nada alterado pelo Verifier).
**Profundidade**: completa (caminho crítico: pontuação e dados do processo), 66 mutantes manuais.

### Backend (46 mutantes: 44 mortos, 2 sobreviventes)

| # | `file:line` | Mutação | Teste que matou | Resultado |
| - | ----------- | ------- | --------------- | --------- |
| B1 | `app/domain/rules/activity_validity.py:86` | inverte "fora do interstício" (`is not FORA`) | `test_activity_validity.py::test_a_dated_categorized_activity_inside_the_interstice_is_valid` | ✅ Killed |
| B2 | `activity_validity.py:102` | carga insuficiente com `<=` em vez de `<` | `::test_hours_equal_to_the_minimum_are_valid` | ✅ Killed |
| B3 | `activity_validity.py:95` | grupo que não conta ignorado | `::test_a_group_outside_the_total_that_is_not_pit_is_not_valid` | ✅ Killed |
| B38 | `activity_validity.py:97` | duplicidade residual ignorada | `::test_a_residual_duplicate_is_not_valid_with_reason_duplicidade` | ✅ Killed |
| B39 | `activity_validity.py:86` | categoria por ano julgada como período fechado | `::test_a_yearly_category_with_only_a_start_runs_to_the_end_of_the_interstice` | ✅ Killed |
| B40 | `activity_validity.py:95` | oferta PIT do Grupo I deixa de ser exceção | `::test_a_pit_offer_of_group_one_is_valid_although_the_group_is_outside_the_total` | ✅ Killed |
| B41 | `activity_validity.py:83` | item fora da tabela deixa de pedir categoria | `::test_an_activity_whose_item_is_not_in_the_table_is_valid_and_needs_a_category` | ✅ Killed |
| B4 | `app/domain/rules/scoring_engine.py:338` | o motor pontua atividade não válida (`valid = list(activities)`) | `test_scoring_engine_validity.py::test_not_valid_activities_produce_no_row` | ✅ Killed |
| B24 | `scoring_engine.py:353` | contador `activities` conta as não válidas | `::test_not_valid_activities_do_not_count_in_the_counters` | ✅ Killed |
| B14 | `scoring_engine.py:197` | `QUANTIDADE_ASSUMIDA` nunca emitido | `::test_a_per_unit_item_without_quantity_scores_one_unit_with_the_alert` | ✅ Killed |
| B35 | `scoring_engine.py:197` | alerta também para item por ano | `::test_the_alert_is_only_for_per_unit_items` | ✅ Killed |
| B5 | `app/application/services/activity_merge.py:44` | mantém a mais nova (`group[-1]`) | `test_activity_merge.py::test_two_duplicates_become_one_with_the_evidences_of_both` | ✅ Killed |
| B5b | `activity_merge.py:44` | ignora a validada (`group[0]`) | `::test_the_validated_activity_stays_even_when_the_other_is_older` | ✅ Killed |
| B6 | `activity_merge.py:77` | não move as evidências | `::test_two_duplicates_become_one_with_the_evidences_of_both` | ✅ Killed |
| B7 | `activity_merge.py:60` | mesclagem não idempotente (lista as já mescladas) | `::test_repeating_the_merge_changes_nothing` | ✅ Killed |
| B8 | `activity_merge.py:58` | mescla em processo somente leitura (CONCLUIDO/ARQUIVADO) | `::test_a_read_only_process_is_not_changed[CONCLUIDO]` | ✅ Killed |
| B22 | `activity_merge.py:84` | auditoria da mesclagem grava `SEPARATE` | `::test_merging_records_one_audit_event_with_both_ids` | ✅ Killed |
| B9 | `activity_merge.py:116` | separar não restaura as evidências | `test_activity_separate.py::test_the_activity_goes_back_to_the_lists_with_the_evidences_that_came_from_it` | ✅ Killed |
| B10 | `activity_merge.py:120` | separar não marca a restaurada como distinta | `::test_both_activities_are_marked_distinct_and_are_not_merged_again` | ✅ Killed |
| B10b | `activity_merge.py:142` | separar não marca a mantida como distinta | `::test_both_activities_are_marked_distinct_and_are_not_merged_again` | ✅ Killed |
| B32 | `activity_merge.py:113` | separar ignora a versão desatualizada | `::test_a_stale_version_is_refused_and_nothing_changes` | ✅ Killed |
| B33 | `activity_merge.py:111` | separar aceita atividade não mesclada | `::test_only_a_merged_activity_can_be_separated` | ✅ Killed |
| B21 | `app/infrastructure/database/repositories.py:1333` | `move` repete par documento e página | `test_repositories_merge.py::test_move_does_not_repeat_a_document_and_page_the_target_already_has` | ✅ Killed |
| B11 | `app/application/use_cases/scoring.py:556` | validar sem exigir categoria | `test_activity_validate_rules_api.py::test_validating_without_a_category_is_422_on_categoria_and_changes_nothing` | ✅ Killed |
| B11b | `scoring.py:554` | validar sem exigir atividade válida | `::test_validating_an_activity_outside_the_interstice_is_422_with_its_code` | ✅ Killed |
| B23 | `scoring.py:577` | validar sem nenhuma checagem | `::test_validating_without_a_category_is_422_on_categoria_and_changes_nothing` | ✅ Killed |
| B26 | `scoring.py:581` | sem evento de auditoria na validação | `::test_validating_a_categorized_activity_inside_the_interstice_is_200_and_audited_without_justification` | ✅ Killed |
| B12 | `scoring.py:646` | lote não lista as puladas | `test_bulk_validate_skipped.py::test_three_with_a_category_are_validated_and_two_without_are_skipped` | ✅ Killed |
| B12b | `scoring.py:644` | lote valida as sem categoria | `::test_three_with_a_category_are_validated_and_two_without_are_skipped` | ✅ Killed |
| B13 | `scoring.py:471` | data fora do interstício aceita na criação manual | `test_activity_edit_rules_api.py::test_a_manual_activity_with_a_date_outside_the_interstice_is_422_on_event_date` | ✅ Killed |
| B13b | `scoring.py:528` | data fora do interstício aceita na edição | `::test_editing_to_a_date_outside_the_interstice_is_422_and_keeps_the_activity` | ✅ Killed |
| B13c | `scoring.py:528` | data inalterada é rejulgada na edição | `::test_editing_a_title_keeps_a_date_that_was_already_outside_and_changing_it_is_refused` | ✅ Killed |
| B44 | `scoring.py:430` | campo do 422 do período sempre `period_start` | `::test_a_yearly_item_refuses_a_period_that_ends_before_the_interstice` | ✅ Killed |
| B43 | `scoring.py:422` | checagem manual trata categoria por ano como período fechado (`yearly = False`) | nenhum | ❌ Survived (18 passed) → FT2 |
| B19 | `scoring.py:484` | criação manual não mescla | `test_activity_merge_on_write_api.py::test_creating_an_activity_equal_to_another_merges_them_at_once_with_both_proofs` | ✅ Killed |
| B20 | `scoring.py:542` | edição não mescla | `::test_editing_the_title_to_equal_another_merges_them` | ✅ Killed |
| B18 | `app/application/use_cases/document_processing.py:161` | fim da leitura do documento não mescla | `test_document_merge.py::test_two_documents_that_lead_to_the_same_activity_become_one_with_both_proofs` | ✅ Killed |
| B16 | `scoring.py:736` | `predicted_points` sem filtrar o status (atividade sem categoria ganha previsão) | `test_list_activities_validity.py::test_an_activity_with_no_category_is_valid_and_needs_one` | ✅ Killed |
| B25 | `scoring.py:824` | o cálculo lista as mescladas | `test_activity_merge_api.py::test_merge_duplicates_merges_and_answers_how_many` | ✅ Killed |
| B45 | `scoring.py:787` | sem tabela, as não válidas entram nas linhas | `test_scoring_validity_api.py::test_without_a_table_only_the_valid_activities_count` | ✅ Killed |
| B46 | `scoring.py:730` | a descrição não busca as mescladas | `test_list_activities_validity.py::test_the_merged_activities_leave_the_list_and_the_kept_one_lists_them` | ✅ Killed |
| B47 | `scoring.py:876` | leitura de uma atividade não usa a descrição da lista | `test_activities_validity_api.py::test_the_read_of_one_activity_has_the_same_fields_as_the_list` | ✅ Killed |
| B15 | `app/application/services/generation_inputs.py:110` | geração não recusa `ATIVIDADE_SEM_CATEGORIA` | `test_generation_inputs.py::test_a_valid_activity_without_category_refuses_with_its_code` | ✅ Killed |
| B27 | `generation_inputs.py:89` | `excluded` conta como "pendentes" a não válida aguardando validação | nenhum (25 passed, incluindo `test_generated_validity_acceptance.py`) | ❌ Survived → FT1 |
| B17 | `app/domain/rules/activity_order.py:43` | `eligible_activities` deixa entrar a não válida | `test_activity_order.py::test_a_validated_activity_that_is_not_valid_does_not_enter` | ✅ Killed |
| B42 | `activity_order.py:43` | `eligible_activities` deixa entrar a sem categoria | `::test_an_activity_without_category_does_not_enter` | ✅ Killed |

### Frontend (20 mutantes: 19 mortos, 1 sobrevivente)

| # | `file:line` | Mutação | Teste que matou | Resultado |
| - | ----------- | ------- | --------------- | --------- |
| F1 | `components/ActivityRow.tsx:214` | "Validar" visível em atividade sem categoria | `ActivityRow.test.tsx` "sem categoria: selo ... e nenhum Validar" | ✅ Killed |
| F1b | `ActivityRow.tsx:214` | "Validar" visível em atividade não válida | `ActivityRow.test.tsx` "atividade não válida..."; `InvalidActivitiesSection.test.tsx` | ✅ Killed |
| F2 | `pages/ProcessActivities.tsx:102` | bloqueio de avanço removido | `ProcessActivities.test.tsx` "com 3 atividades sem categoria bloqueia as etapas 4 e 5..." (5 falhas) | ✅ Killed |
| F14 | `ProcessActivities.tsx:95` | o bloqueio conta também as não válidas sem categoria | "uma atividade sem categoria que não é válida não bloqueia o avanço" | ✅ Killed |
| F15 | `ProcessActivities.tsx:95` | o bloqueio vale sem tabela | "sem tabela, com atividade sem categoria, o avanço à Etapa 4 segue livre..." | ✅ Killed |
| F19 | `components/StepNav.tsx:51` | bloqueio fecha também a etapa que bloqueia (`>=`) | `StepNav.test.tsx` "as etapas até a que bloqueia seguem ativas..." | ✅ Killed |
| F3a | `activityList.ts:23` | chip "Precisa de categoria" some da contagem | `ValidActivitiesSection.test.tsx` "os chips contam sobre a lista inteira..." | ✅ Killed |
| F17 | `activityList.ts:30` | os chips não contam as validadas | mesmo teste | ✅ Killed |
| F13 | `activityList.ts:52` | filtro por grupo ignorado | `ValidActivitiesSection.test.tsx` "o filtro por grupo..." (3 falhas) | ✅ Killed |
| F6 | `activityList.ts:5` | `PAGE_SIZE` 20 em vez de 25 | `ValidActivitiesSection.test.tsx` e `InvalidActivitiesSection.test.tsx` (7 falhas) | ✅ Killed |
| F16 | `components/ValidActivitiesSection.tsx:72` | a página mostra uma linha a mais | "com 120 atividades mostra 25..." (4 falhas) | ✅ Killed |
| F12 | `ValidActivitiesSection.tsx:78` | o lote leva as sem categoria | "Validar as selecionadas depois de Selecionar todas envia só os ids..." | ✅ Killed |
| F3b | `ValidActivitiesSection.tsx:73` | o aviso "N atividades precisam de categoria" da seção conta só as filtradas | nenhum (testes só sem filtro ativo) | ❌ Survived → FT3 |
| F4 | `ProcessActivities.tsx:29` | a mesclagem roda a cada recarga (sem o cache `prepare`) | "validar recarrega a lista ... sem chamar a mesclagem de novo" | ✅ Killed |
| F7 | `ProcessActivities.tsx:32` | mescla processo somente leitura | "processo somente leitura não chama a mesclagem..." | ✅ Killed |
| F18 | `ProcessActivities.tsx:77` | lista carregada em paralelo à mesclagem | "abre a página chamando a mesclagem uma vez e só depois a lista" | ✅ Killed |
| F5 | `components/InvalidActivitiesSection.tsx:41` | seção de não válidas abre aberta | `InvalidActivitiesSection.test.tsx` (18 falhas) | ✅ Killed |
| F9 | `components/ActivityForm.tsx:82` | Horas sempre visíveis no formulário | `ActivityForm.test.tsx` (3 falhas) | ✅ Killed |
| F10 | `components/MergedNote.tsx:19` | "Não é duplicada" chama a rota errada | `MergedNote.test.tsx` (3 falhas) | ✅ Killed |
| F11 | `labels.ts:97` | motivo fora do interstício sem a faixa do interstício | `labels.test.ts`, `ReasonText.test.tsx` (4 falhas) | ✅ Killed |

**Resultado do sensor**: 63 de 66 mortos, 3 sobreviventes (B27, B43, F3b). Nenhum sobrevivente é equivalente: B27 muda a contagem `excluded` de uma atividade fora do interstício aguardando validação; B43 muda o julgamento de um período só com início numa categoria por ano; F3b muda o número mostrado quando há filtro. Veredito do sensor: FAIL ❌ (a spec do Verifier trata sobrevivente como lacuna).

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Mínimo de código, sem recursos além do pedido | ✅ (uma regra pura `classify_activity` serve motor, lista, geração e validação) |
| Mudanças cirúrgicas, padrões do projeto | ✅ (portes de `ActivityReviewList` para `ValidActivitiesSection`/`ActivityRow`; remoção do componente antigo com os testes portados) |
| Testes mapeiam requisitos e não espelham a implementação | ✅ (valores de pontos, textos e códigos vêm da spec; testes alterados de `test_scoring_engine.py` trocam `NAO_PONTUADA` por "sem linha", como SEG-01 pede, sem enfraquecer asserção) |
| Cobertura por camada | ⚠️ domínio 1:1; rotas com caminho feliz, borda e erro; documentos gerados sem caso de atividade mesclada (G4) |
| Teste sem requisito | ✅ nenhum órfão encontrado nas amostras (rótulos, foco e `aria-live` mapeiam SEC-12 e T45 a T55) |
| Diretrizes documentadas | CLAUDE.md: dados sintéticos nos testes (confirmado), sem justificativa nas Etapas 2, 3 e 4 (confirmado: nenhum campo de justificativa nos testes `ActivityRow`, `ActivityForm`, `ScoreEditor`) |

## Gate Check

- **Backend**: `cd backend && ruff check . && pytest -q` (execução do orquestrador sobre a árvore em `e1b06a0`, que difere do HEAD só por documentação): `ruff` limpo; `5269 passed, 3 deselected, 1 warning in 688.87s` (`/tmp/claude-1000/gate_pytest.txt`, `pytest exit 0`). Os 3 `deselected` são `maritalk_live` (`pyproject.toml`, `addopts`).
- **Frontend** (Verifier, worktree em `e1b06a0`): `npx vitest run` → 41 arquivos, `561 passed | 1 skipped`; o pulado é `tests/bundle.test.ts` (exige `dist` do `npm run build`, anterior à feature, justificado); `npx tsc -b` sem erro; `npx eslint .` sem aviso. `vite build` não foi executado pelo Verifier.
- **Contagem de testes**: backend, funções `def test_` 2764 → 2962 (+198) entre `39bbfd2` e `e1b06a0`, total de execuções 5048 (`969273e`, `STATE.md`) → 5269 (+221); frontend, `it(` 366 → 532, execuções 374 → 561 (+187). Testes removidos: só `ActivityReviewList.test.tsx` (394 linhas), com o componente (`e774550`); os casos de vínculo estão portados em `ValidActivitiesSection.test.tsx:342-376`.

---

## Lacunas ranqueadas

| # | Gravidade | Lacuna | Requisito | Evidência |
| - | --------- | ------ | --------- | --------- |
| G1 | Média | `_excluded` conta como "pendentes" uma atividade não válida aguardando validação e nenhum teste usa esse caso (B27); o resumo da geração mostraria um rastro da atividade fora, contra SEG-01 | SEG-01 | `app/application/services/generation_inputs.py:89`; `B/integration/doc_usecases/test_generation_inputs.py:33-48` só usa rejeitadas |
| G2 | Média | Período só com início (aberto) em categoria por ano, na criação e edição manuais, não tem teste; `yearly=False` em `_check_inside_interstice` passa (B43) | EDT-03 | `app/application/use_cases/scoring.py:422`; `B/integration/api/test_activity_edit_rules_api.py:121-155` |
| G3 | Baixa | O aviso "N atividades precisam de categoria" da seção usa a lista filtrada sem que teste algum o perceba (F3b); com busca ou filtro o número diverge do da navegação | SEC-05 | `F/components/ValidActivitiesSection.tsx:73`; `F/components/ValidActivitiesSection.test.tsx:153-161` |
| G4 | Média | Nenhum teste gera Tabela, Relatório ou Comprovante com uma atividade mesclada; a exclusão vale hoje por herança da lista | DUP-03, SEG-02 | `B/integration/api/test_generated_validity_acceptance.py:58-95` (o "duplicate" é residual, não mesclado) |
| G5 | Média | "Sem rolagem horizontal a 360 px" só tem prova estática do CSS (jsdom não renderiza layout) | SEC-12 | `F/components/ActivityWorkspace.test.tsx:173-179` |
| G6 | Baixa | `ATIVIDADE_SEM_CATEGORIA` no worker de geração vira `ERRO_INTERNO` (falta em `_FAILURE_MESSAGES`); a spec pede recusa com o código; conhecido na pergunta aberta 2 do AD-022 | SEG-05 | `app/application/use_cases/generated_documents.py:307-318,462` |
| G7 | Baixa | Bordas "trocar a categoria de validada recalcula e mantém o status" e "carga horária corrigida volta com o status que tinha" sem teste | Edge Cases | `B/integration/scoring/test_activity_update.py:65-79` (sem asserção de `VALIDADA` depois da troca); `B/integration/scoring/test_list_activities_validity.py:136-151` (só por data) |

### Lacunas de precisão da spec (⚠️)

| # | Ponto indefinido | Onde o teste fixa o valor |
| - | ---------------- | ------------------------- |
| SP1 | Ordem dos motivos quando vários se aplicam (rejeitada, data, categoria, grupo, duplicidade, carga) e a precedência "rejeitada antes de sem enquadramento" mudou o motor | `B/unit/domain/test_activity_validity.py:290-312`; `B/unit/domain/test_scoring_engine.py` ("precedence_rejected_over_missing_criterion...") |
| SP2 | SEC-06 e SEC-07 só nomeiam três motivos; a implementação acrescenta `GRUPO_NAO_CONTA` e `DUPLICIDADE` com textos "Grupo não conta no total" e "Duplicidade" | `F/labels.test.ts:129-130,133-141` |
| SP3 | SEC-07 não define o texto do período (categoria por ano) nem a precisão de mês; `validity.params` não carrega a precisão e o motivo mostraria o dia 01 de um mês | `F/labels.test.ts:100-105` |
| SP4 | Ordem das validações na rota de status (mesmo status, versão, não válida, categoria) e a recusa `ATIVIDADE_NAO_VALIDA` em `status`; gravidade, mensagem e norma do alerta `QUANTIDADE_ASSUMIDA` | `B/integration/api/test_activity_validate_rules_api.py:68-95`; `B/unit/domain/test_scoring_engine_validity.py:233-241` |
| SP5 | EDT-02 não diz que a data inalterada não é rejulgada ao salvar outro campo, nem como julgar a precisão de mês (mês inteiro) | `B/integration/api/test_activity_edit_rules_api.py:100-109,179-198` |
| SP6 | DUP-01 com mais de duas validadas ("a criada primeiro" entre as validadas) | `B/integration/doc_usecases/test_activity_merge.py:94-102` |
| SP7 | SEC-05 não cobre o processo sem tabela escolhida (o avanço fica livre, T47) | `F/pages/ProcessActivities.test.tsx:202-210` |
| SP8 | QTD-03 só recusa negativa e não numérica; o servidor exige inteiro de 0 a 10000 e aceita zero | `F/components/ScoreEditor.test.tsx:239` |
| SP9 | VAL-04 pula também as não válidas; o vocabulário de `skipped[].reason` não está na spec | `B/integration/scoring/test_bulk_validate_skipped.py:57-73` |
| SP10 | (a) EDT-04 não define o formulário de oferta nova do Grupo I; (b) a "prévia da conclusão" do SEG-01 não lê atividades, a cláusula não tem resultado observável; (c) o frontend da SEG-04 só exibe os contadores do servidor | `F/components/ActivityForm.test.tsx:208`; `app/application/use_cases/conclusion.py:27-35` |

## Fix Plans (tarefas de correção sugeridas, não executadas)

- **FT1 (G1, B27)**: em `test_generation_inputs.py`, uma atividade fora do interstício e uma com carga insuficiente em `AGUARDANDO_REVISAO`, esperar `inputs.excluded == {}`; e no teste de aceitação, o `summary["excluded"]` com essas atividades aguardando.
- **FT2 (G2, B43)**: teste de API da criação e da edição manual de item por ano com `period_start` dentro ou antes do interstício e sem `period_end` (aceito), e com início depois do fim do interstício (422); definir na spec o período aberto (SP3, SP5).
- **FT3 (G3, F3b)**: em `ValidActivitiesSection.test.tsx`, com 5 atividades e 3 sem categoria, aplicar a busca ou o filtro de grupo e afirmar "3 atividades precisam de categoria".
- **FT4 (G4)**: teste de aceitação com uma atividade mesclada (e a evidência que ficou nela), conferindo Tabela, Relatório e Comprovante sem o título e sem a página exclusiva dela.
- **FT5 (G5)**: verificação em navegador a 360 px da Etapa 3 (com 120 atividades) e registrar no `validation.md`; ou um teste de navegador se o projeto passar a ter um.
- **FT6 (G6)**: mapear `ATIVIDADE_SEM_CATEGORIA` em `_FAILURE_MESSAGES` com teste do worker, ou registrar na spec que a recusa vale só no pedido.
- **FT7 (SP1 a SP10, G7)**: ajustar `spec.md` com a ordem dos motivos, os textos de duplicidade e de grupo, o período e a precisão de mês, a data inalterada na edição, o caso sem tabela, a faixa da quantidade, o vocabulário de `skipped`, e a cláusula da prévia da conclusão; testes de status final para G7.

## Requirement Traceability Update

| Requisito | Status anterior | Novo status |
| --------- | --------------- | ----------- |
| VAL-01 a VAL-06, SEC-01 a SEC-04, SEC-06 a SEC-11, DUP-01, DUP-02, DUP-04 a DUP-07, SEG-03, SEG-04, EDT-01, EDT-02, EDT-04 a EDT-07, QTD-01 a QTD-03 | Implemented | ✅ Verified (com SP cadastrada) |
| SEC-05 | Implemented | ⚠️ Implemented (G3) |
| SEC-12 | Implemented | ⚠️ Implemented (G5) |
| DUP-03 | Implemented | ⚠️ Implemented (G4) |
| SEG-01 | Implemented | ❌ Needs Fix (G1) |
| SEG-02 | Implemented | ⚠️ Implemented (G4) |
| SEG-05 | Implemented | ⚠️ Implemented (G6) |
| EDT-03 | Implemented | ❌ Needs Fix (G2) |

O Verifier não altera `spec.md` (há alterações de rastreabilidade do orquestrador na árvore, sem commit); estes status valem quando o líder fechar FT1 a FT7.

## Summary

**Overall**: ❌ Not Ready (por regra do sensor: sobrevivente é lacuna)

**Spec-anchored check**: 33 de 40 requisitos com asserção alinhada à spec; 7 com lacuna; 10 lacunas de precisão
**Sensor**: 63 de 66 mutantes mortos
**Gate**: backend 5269 passando; frontend 561 passando, 1 pulado

**What works**: pontuar ao validar (8,00 de II.5), exclusão das não válidas do motor, da Tabela, do Relatório e do Comprovante, mesclagem atômica, idempotente, restaurável e auditada, bloqueio de avanço, filtros e contagens, formulário curto e editor de pontuação; 44 de 46 mutantes de backend e 19 de 20 de frontend morreram.

**Issues found**: G1 a G7 e SP1 a SP10 acima.

**Next steps**: executar FT1 a FT7 (cada uma é pequena e só de teste ou de texto, exceto FT6), reverificar (volta 1 de 3) e então rodar `validate_state.py`; T43 (documentação) ainda precisa do commit.

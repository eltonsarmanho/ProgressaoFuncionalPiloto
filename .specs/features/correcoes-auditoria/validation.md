# Correções da auditoria de requisitos Validation

**Date**: 2026-11-20
**Spec**: `.specs/features/correcoes-auditoria/spec.md` (39 requisitos: CAINI-01..14, CAREF-01..06, CATXT-01..04, CAEDI-01..04, CADOC-01..11)
**Diff range**: `35f6113..9bf9ad7` (T1 `b84de46` a T26 `9bf9ad7`; o commit `35f6113` aprova spec e tarefas e fica fora do alcance de código). 28 commits, 45 arquivos, +1202 −431.
**Verifier**: sub-agente independente (autor ≠ verifier), volta 1 de 3. Não leu `Documentos/`, `Modelos/`, `requeriment.txt` nem `test/`; sem push, deploy nem VM; o `stash@{0}` antigo não foi tocado.

**Verdict: PASS.** 39 de 39 requisitos com evidência `arquivo:linha`; gate verde; sensor com 39 mutantes: 38 mortos, 1 equivalente, 0 sobreviventes com efeito observável. Há 3 lacunas de severidade baixa (spec-precision), nenhuma bloqueia.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1..T5 (iniciar o processo) | Done | `b84de46`, `4e6eac7`, `1b20525`, `00a8efb`, `8580726` |
| T6..T11 (Grupo I, textos, edição) | Done | `c6ac141`, `0893cb0`, `e7d2b85`, `47afe82`, `0bdf1f4`, `c037a12` |
| T12, T13 (nomes de teste) | Done | `222b8d5`, `f61ed1d` |
| T14..T18 (sigla nos documentos) | Done | `bf9947c`, `dae9b40`, `69745cf`, `5ea9415`, `6082ce9` |
| T19..T26 (documentação de estado) | Done | `0c5924e`, `11f114c`, `ef2db8a`, `6a1bb92`, `d255ee6`, `2759608`, `68647fb`, `9bf9ad7` |
| T27 (Verifier) | Done | este relatório |

Testes removidos no intervalo: 10 funções, todas renomes (`real_case` para `derived_case`, miniatura sintética) ou a substituição do teste do item de valor informado do Grupo I por `test_informed_value_item_keeps_informed_points` (`test_activity_create.py:330`). Nenhum teste apagado sem substituto. Testes novos: 40 funções ou blocos `it` no intervalo.

---

## Spec-Anchored Acceptance Criteria

Notação: `T:` teste, `C:` código. Cada linha cita a asserção que fixa o valor que a spec define.

### P1: Iniciar o processo na Etapa 1 (CAINI-01..09)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CAINI-01 RASCUNHO mostra o botão | botão "Iniciar processo" ao lado da etiqueta | T: `frontend/src/pages/ProcessStep1.test.tsx:225` `findByRole("button", OPEN)` e `getByText("Rascunho")`; C: `ProcessStep1.tsx:189-196` | ⚠️ PASS com lacuna G1 (posição "fora do formulário de dados" sem asserção) |
| CAINI-02 outros status e processo novo sem botão | `queryByRole` ausente | T: `ProcessStep1.test.tsx:232` (it.each EM_ANDAMENTO, CONCLUIDO, ARQUIVADO), `:239` (processo novo); mutante F08 morto | ✅ PASS |
| CAINI-03 modal | título, texto exato, Iniciar e Cancelar, sem campo | T: `frontend/src/components/ProcessDialogs.test.tsx:24` `getByText(TEXT)`, `queryByRole("textbox")` ausente; `:72` Cancelar chama `onClose` sem requisição; C: `ProcessDialogs.tsx:96` | ✅ PASS |
| CAINI-04 pedido | `{"status":"EM_ANDAMENTO","expected_version":<versão exibida>}` sem `justificativa` | T: `ProcessDialogs.test.tsx:36` `toEqual({ status: "EM_ANDAMENTO", expected_version: 4 })` e `"justificativa" in body` falso; `ProcessStep1.test.tsx:246`, `Dashboard.test.tsx:192` repetem o corpo exato; C: `ProcessDialogs.tsx:85` | ✅ PASS |
| CAINI-05 200 | modal fecha, "Em andamento", botão some, versão devolvida no Salvar | T: `ProcessStep1.test.tsx:246` (`findByText("Em andamento")`, dialog ausente, campo "Observações" mantido, PUT com `expected_version: 2`); C: `ProcessStep1.tsx:101-104` | ✅ PASS |
| CAINI-06 409 | mensagem em `role="alert"` e recarga com GET | T: `ProcessDialogs.test.tsx:49` (alert com o texto, `onStale` 1 vez); `ProcessStep1.test.tsx:274` (GET repetido 2 vezes, etiqueta "Em andamento"); C: `ProcessStep1.tsx:89-99` | ✅ PASS |
| CAINI-07 404, 422 e outros | mensagem em alert, Iniciar habilitado, sem `onStale` | T: `ProcessDialogs.test.tsx:59` (it.each 404 e 422: `toHaveTextContent`, `onStale` não chamado, `toBeEnabled`); mutantes F03, F04, F05 mortos | ✅ PASS |
| CAINI-08 servidor 200 | `EM_ANDAMENTO`, `version` +1, evento `STATUS` com antes e depois e justificativa vazia | T: `backend/tests/integration/api/test_process_updates_api.py:149` (`(status, version) == ("EM_ANDAMENTO", 2)`, `last.changes == {"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}`, `last.justification is None`, `last.user_id == actor.id`), DOCENTE e ADMIN; C: `process.py:24`, `processes.py:213` | ✅ PASS |
| CAINI-09 sem leitura | 404 e processo intacto | T: `test_process_updates_api.py:171` (`status_code == 404`; depois `("RASCUNHO", 1)`), SECRETARIA de outra unidade e DOCENTE de outro docente; C: `access_policy.py:23` | ✅ PASS |

### P1: Etapa 5 (CAINI-10, CAINI-11)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CAINI-10 RASCUNHO | título, texto, link `/processos/{id}`, sem o botão | T: `frontend/src/pages/ProcessGenerated.test.tsx:212` (`getByText(DRAFT_TEXT)`, `getByRole("link", { name: "Ir para a Etapa 1" })` com `href "/processos/p1"`, botão ausente); C: `ProcessGenerated.tsx:134-143` | ✅ PASS |
| CAINI-11 EM_ANDAMENTO | botão de concluir, sem o texto de rascunho | T: `ProcessGenerated.test.tsx:221`; `:230` (CONCLUIDO e ARQUIVADO sem botão, sem texto, sem link); mutante F12 morto | ✅ PASS |

### P2: Painel (CAINI-12..14)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CAINI-12 | botão só em RASCUNHO, `aria-label` "Iniciar processo de {nome}" | T: `frontend/src/pages/Dashboard.test.tsx:175` (`getByRole("button", { name: "Iniciar processo de Docente Alfa" })`, `title` igual, ausente nos outros três status); C: `Dashboard.tsx:92-101`; mutantes F14, F17 mortos | ✅ PASS |
| CAINI-13 | mesmo modal e pedido; etiqueta e contagem mudam sem recarregar | T: `Dashboard.test.tsx:192` (corpo `toEqual({ status: "EM_ANDAMENTO", expected_version: 4 })`, `total("Rascunho")` 2 para 1, `total("Em andamento")` 0 para 1, `loadsOf(calls)` com 1 chamada); mutante F15 morto | ✅ PASS |
| CAINI-14 | 409 mostra a mensagem e recarrega a lista | T: `Dashboard.test.tsx:221` (alert com a mensagem do servidor, GET da lista 2 vezes, linha "Em andamento"); mutante F16 morto | ✅ PASS |

### P1: Grupo I (CAREF-01..06)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CAREF-01 | período, nível e horas obrigatórios no grupo 1 em qualquer tabela; item segue o nível | T: `backend/tests/integration/scoring/test_activity_create.py:380` (tabela com critério de valor informado no grupo 1: `field_of_failure(...) == field` para `academic_period`, `level`, `horas`), `:386` (`(group_number, item_number) == (1, 1)`), `:398` (edição para o item 3 exige os mesmos campos); `:92`, `:120` (tabela oficial); C: `scoring.py:271-281`; mutantes B01 a B05 mortos | ✅ PASS |
| CAREF-02 | `informed_points` gravado e limitado a `max_points`, com ajuste `ATIVIDADE` | T: `test_activity_create.py:330` (`informed_points == D("8")`, `group_number == 8`); `backend/tests/unit/domain/test_scoring_engine.py:294` (`points == D("10")`, `(before, after) == (D("14"), D("10"))`, `scope == "ATIVIDADE"`); `backend/tests/integration/scoring/test_process_score.py:202` (`group_subtotals[8] == D("10")`); C: `scoring_points.py:75-81`; mutantes B15, B16 mortos | ✅ PASS |
| CAREF-03 | 422 em `unit_points_override` no critério de valor informado | T: `test_activity_create.py:286` (`field_of_failure(world, **informed) == "unit_points_override"`); C: `scoring.py:306-314`; mutante B14 morto | ✅ PASS |
| CAREF-04 | nomes sintéticos e item "Item de valor informado (sintético)" no grupo 8 | `backend/tests/support/scoring_variants.py:15-18` (nomes e `INFORMED_GROUP = 8`, `INFORMED_ITEM = 38`), `:58-60` (`assert INFORMED_ITEM == max(...) + 1`); `grep` dos nomes antigos sem saída fora da spec e das tarefas | ⚠️ PASS com lacuna G2 (os nomes não têm asserção de teste) |
| CAREF-05 | os três `grep` sem saída | executado pelo Verifier em 2026-11-20 com as exclusões da spec: os três `grep` de CAREF-05 voltaram vazios | ✅ PASS |
| CAREF-06 | frase na regra 11 | `CLAUDE.md:23` contém "O Grupo I tem só os itens I.1 e I.2, em horas de PIT." | ✅ PASS |

### P1: Textos (CATXT-01..04)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CATXT-01 | nota exata, sem "lidos do documento" | T: `frontend/src/components/ScoreEditor.test.tsx:137` (`getByText("Neste item a pontuação é um valor informado na atividade, não calculado pela tabela: esta tela não o altera.")`), `:146` (`textContent` sem `/lidos\sdo\sdocumento/`); C: `ScoreEditor.tsx:16`; mutante F18 morto | ✅ PASS |
| CATXT-02 | 422 em `points_override` com a mensagem nova | T: `test_activity_create.py:428` (`message == "Esta tabela não aceita pontuação manual neste item; nos itens por unidade ou por bloco de horas, informe o valor unitário"`, com item e sem item); C: `scoring.py:313-321`; mutantes B06, B09 mortos | ✅ PASS |
| CATXT-03 | "Pontuação manual deve estar entre 0 e 10000" | T: `test_activity_create.py:439` (`message == ...`, campo `points_override`); C: `scoring.py:265`; mutante B07 morto | ✅ PASS |
| CATXT-04 | "Pontos informados deve estar entre 0 e 10000" | T: `test_activity_create.py:447`; C: `scoring.py:264`; mutante B08 morto | ✅ PASS |

### P1: Edição com pontuação manual gravada (CAEDI-01..04)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CAEDI-01 | 200, `points_override` limpo, demais campos gravados, valor anterior no evento `UPDATE` | T: `backend/tests/integration/scoring/test_activity_update.py:443` (por unidade, PIT e sem item: `(updated.title, updated.points_override) == ("Título novo", None)`, `event.action is AuditAction.UPDATE`, `event.changes["points_override"] == {"before": "24", "after": None}`); C: `scoring.py:507-522`, `:537`; mutantes B10, B13 mortos | ✅ PASS |
| CAEDI-02 | valor diferente: 422 e nada gravado | T: `test_activity_update.py:462` (`(error.value.field, error.value.message) == ("points_override", message)` com a mensagem de CATXT-02 e a de PIT; título, valor e versão iguais depois); mutante B11 morto | ✅ PASS |
| CAEDI-03 | onde o critério aceita, mantém o valor | T: `test_activity_update.py:487` (`points_override == D("24")` na tabela sintética, relido do banco); mutante B12 morto | ✅ PASS |
| CAEDI-04 | título editado com o corpo de `activityBody`: 200, título novo, `points_override` nulo | T: `backend/tests/integration/api/test_activities_api.py:517` (`status_code == 200`, `json()["title"] == "Título novo"`, `json()["points_override"] is None`; o corpo vem de `activity_body` em `:497`, espelho de `frontend/src/activityBody.ts:7-18`) | ✅ PASS |

### P2: Documentação (CADOC-01..11)

Conferidos por leitura do artefato e por `grep` no HEAD `9bf9ad7`.

| Criterion | Spec-defined outcome | Evidência | Result |
| --------- | -------------------- | --------- | ------ |
| CADOC-01 | Handoff com HEAD, branch, VM em `a136faf`, commits locais, feature corrente e seguinte, gate, sem arquivos "uncommitted" nem deploy pendente | `.specs/STATE.md:195` (HEAD e branch medidos), `:196` (34 commits locais, mais o commit do próprio Handoff, 35 em `git log origin/feat/inteligencia-documental..HEAD`, conforme o texto avisa), `:197` (VM `a136faf`, migração 0008), `:198-199` (corrente e seguinte), `:200` (gate); gate medido pelo Verifier no HEAD: 5322 e 584, igual ao registrado | ✅ PASS |
| CADOC-02 | nota em AD-017 e AD-019 | `.specs/STATE.md:139` (AD-017) e `:156` (AD-019): "substituída pela AD-022" | ✅ PASS |
| CADOC-03 | coluna Quantidade | `.specs/features/inteligencia-documental/design.md:173` ("1 por ação"), `:178` (V.1), `:183` (VI.10), `:184` (VI.12), todos "anos completos do período no interstício (`QUANTIDADE_ESTIMADA`)"; confere com `_PER_YEAR` em `backend/app/domain/rules/quantity_rules.py:26-41` | ✅ PASS |
| CADOC-04 | sem `real case`, `caso real`, `real_case` nos quatro arquivos | `grep -rniE "real case\|caso real\|real_case"` nos quatro arquivos: vazio | ✅ PASS |
| CADOC-05 | "cenário derivado" em toda citação de 211 ou 303 | `grep -rnE "\b(211\|303)\b"` em `spec.md`, `design.md`, `STATE.md` e `docs/`: restam `STATE.md:196` (assunto de commit que já diz "derived scenario") e `documentos-gerados/design.md:365` (exemplo JSON, introduzido na frase anterior como "cenário derivado") | ✅ PASS |
| CADOC-06 | dívida reescrita | `.specs/STATE.md:203` contém "Grupo I: os 303 pontos de `grupo-i-no-total` vêm de 92 horas de PIT de um cenário derivado; os documentos reais somam 76 h (auditoria de 2026-11-19, C10)..." | ✅ PASS |
| CADOC-07 | `Verified` com Verifier PASS; QUA, CER, e os sem passagem seguem `Implementing` | `.specs/features/inteligencia-documental/spec.md:654` (136 `Verified`, 35 `Implementing`: SEG-01, UIM-01..23, QUA-01..06, CER-01..05); SEG-01 é PARTIAL em `validation.md:10` (por isso segue `Implementing`); FORA-01..09 `Verified` em `spec.md:636-644` | ✅ PASS |
| CADOC-08 | 22 `Verified`, ACE-02 `Pending` | `.specs/features/tabela-oficial/spec.md:191` e contagem: 22 linhas `Verified`, 0 `Implemented`; ACE-02 `Pending` em `:183`; `tabela-oficial/validation.md:8,10` (PASS, 22 de 23, ACE-02 PARTIAL) | ✅ PASS |
| CADOC-09 | GP-DEL-07 com `PENDENTE` ou `PROCESSANDO` | `.specs/features/gestao-processos/spec.md:45`; confere com `_ACTIVE_JOB` em `backend/app/infrastructure/database/repositories.py:1121` | ✅ PASS |
| CADOC-10 | notas recíprocas | `.specs/features/tabela-oficial/spec.md:3` (PIT-01..03, TELA-01..02), `.specs/features/documentos-gerados/spec.md:3` (TAB-03, TAB-05), recíproca em `.specs/features/grupo-i-no-total/spec.md:3` | ✅ PASS |
| CADOC-11 | pergunta aberta (1) da AD-022 sem a sigla | `.specs/STATE.md:179`: "o item de valor informado de tabelas antigas, inexistente na tabela oficial, só existia na tabela antiga do IFCH ... e no rascunho da FASI" | ✅ PASS |

**Status**: ✅ 39 de 39 requisitos cobertos; 2 lacunas de spec-precision (G1, G2) assinaladas, ambas de severidade baixa.

**Goals e critérios de sucesso da spec**: Grupo I com período, nível e horas (CAREF-01); nenhum texto promete leitura do documento (CATXT-01, F18); editar com `points_override` gravado dá 200 (CAEDI-04); os `grep` de CAREF-05 e CADOC-04 vazios; gate verde. O fluxo "iniciar, gerar, concluir" não tem um único teste de ponta a ponta: o início pela API é exercido em `backend/tests/integration/api/test_conclusion_api.py:36` (`start_process` usa `POST /status` com `{"status": "EM_ANDAMENTO", "expected_version": ...}` e depois conclui) e por T1 (`test_process_updates_api.py:149`); a interface é coberta pelos testes de componente das Etapas 1 e 5 e do Painel (lacuna G3).

---

## Edge Cases

- [x] Início simultâneo: o segundo recebe 409, mensagem e recarga (`Dashboard.test.tsx:221`, `ProcessStep1.test.tsx:274`, `ProcessDialogs.test.tsx:49`).
- [x] Dados não salvos na Etapa 1 e início: campo "Observações" mantém o texto digitado (`ProcessStep1.test.tsx:262`), e o PUT seguinte leva `notes` e a versão 2 (`:271`).
- [x] Processo `EM_ANDAMENTO` salvo sem justificativa devolve 422 (`test_process_updates_api.py:69`, `test_em_andamento_update_without_justification_returns_422`; mutante B17 o derruba).
- [x] PUT com `points_override` nulo e valor gravado grava nulo (caminho comum de `normalize_activity`; sem teste novo, comportamento anterior preservado por `test_activity_update.py:111` e a suíte completa verde).
- [x] Edição só do valor unitário com `points_override` não aceito responde 200 e limpa (mesmo caminho de `_normalize_for_update`, CAEDI-01).

---

## Discrimination Sensor

Scratch: `git worktree add --detach <scratchpad>/wt HEAD`, mutação aplicada por substituição exata de um trecho único e restaurada por `git checkout` depois de cada rodada; worktree removido ao fim. Backend rodou `pytest -q -x` nos arquivos que cobrem a regra; frontend rodou `vitest --run` no arquivo de teste do componente. `git status --porcelain` da árvore real: antes `?? requeriment.txt`, `?? test/`; depois, igual. `git stash list` com 1 entrada, a antiga, intacta.

| # | File:line | Description | Killed? |
| - | --------- | ----------- | ------- |
| B01 | `scoring.py:273` | o item 3 volta a pular os campos do Grupo I (`or data.item_number == 3`) | ✅ Killed (`test_activity_create.py:380`) |
| B02 | `scoring.py:277` | nível deixa de ser exigido | ✅ Killed (`:120`, `changes2-level`) |
| B03 | `scoring.py:279` | horas deixam de ser exigidas | ✅ Killed (`:120`, `changes3-horas`) |
| B04 | `scoring.py:275` | formato `AAAA.N` deixa de ser conferido | ✅ Killed (`:120`, `changes1-academic_period`) |
| B05 | `scoring.py:281` | o item deixa de seguir o nível (troca 1 por 2) | ✅ Killed (`:92`) |
| B06 | `scoring.py:320` | mensagem de CATXT-02 perde o final "unitário" | ✅ Killed (`:428`) |
| B07 | `scoring.py:265` | rótulo de `points_override` volta a "Pontos informados" | ✅ Killed (`:439`) |
| B08 | `scoring.py:264` | rótulo de `informed_points` muda | ✅ Killed (`:447`) |
| B09 | `scoring.py:315` | atividade sem item deixa de ser recusada em `points_override` | ✅ Killed (`:306`) |
| B10 | `scoring.py:520` | valor igual recusado volta a dar 422 (nunca limpa) | ✅ Killed (`test_activity_update.py:443`) |
| B11 | `scoring.py:520` | valor diferente recusado é limpo em vez de 422 | ✅ Killed (`test_activity_update.py:443/462`) |
| B12 | `scoring.py:518` | o valor aceito é limpo em toda edição | ✅ Killed (`test_activity_update.py:111`) |
| B13 | `scoring.py:537` | `UpdateActivity` volta a `normalize_activity` | ✅ Killed (`test_activity_update.py:443`) |
| B14 | `scoring.py:308` | valor unitário aceito no critério de valor informado | ✅ Killed (`test_activity_create.py:286`) |
| B15 | `scoring_points.py:80` | valor informado deixa de ser limitado ao máximo | ✅ Killed (`test_scoring_engine.py:294`) |
| B16 | `scoring_points.py:80` | o ajuste de limite informa o teto como valor anterior | ✅ Killed (`test_scoring_engine.py:294`) |
| B17 | `process.py:24` | transição `RASCUNHO` para `EM_ANDAMENTO` removida | ✅ Killed (`test_process_updates_api.py`, 422 sem justificativa) |
| B18 | `processes.py:238` | auditoria grava o status de destino como "antes" | ✅ Killed (`test_process_updates_api.py:131`) |
| B19 | `processes.py:240` | justificativa vazia gravada como `""` em vez de `None` | ⚪ Equivalente: `AuditService.record` aplica `justification or None` (`audit_service.py:68`); sem efeito observável |
| B20 | `access_policy.py:26` | qualquer usuário lê o processo (staff) | ✅ Killed (`test_process_updates_api.py:171`) |
| B21 | `access_policy.py:25` | qualquer docente com `professor_id` lê o processo | ✅ Killed (`test_process_updates_api.py:171`) |
| F01 | `ProcessDialogs.tsx:85` | `expected_version: version + 1` | ✅ Killed (`ProcessDialogs.test.tsx:36`) |
| F02 | `ProcessDialogs.tsx:85` | envia `justificativa` no início | ✅ Killed (`ProcessDialogs.test.tsx:36`) |
| F03 | `ProcessDialogs.tsx:91` | `onStale` em todo erro | ✅ Killed (`:59`) |
| F04 | `ProcessDialogs.tsx:90` | botão fica ocupado depois do erro | ✅ Killed (`:59`, `toBeEnabled`) |
| F05 | `ProcessDialogs.tsx:89` | mensagem do servidor descartada | ✅ Killed (`:49`, `:59`) |
| F06 | `ProcessDialogs.tsx:110` | Cancelar não faz nada | ✅ Killed (`:72`) |
| F07 | `ProcessDialogs.tsx:98` | o texto diz que o processo volta a rascunho | ✅ Killed (`:24`) |
| F08 | `ProcessStep1.tsx:191` | botão também em `EM_ANDAMENTO` e `CONCLUIDO` | ✅ Killed (`ProcessStep1.test.tsx:232`) |
| F09 | `ProcessStep1.tsx:102` | versão antiga mantida depois de iniciar | ✅ Killed (`ProcessStep1.test.tsx:246`) |
| F10 | `ProcessStep1.tsx:93` | recarga ignora o status do servidor | ✅ Killed (`:274`) |
| F11 | `ProcessStep1.tsx:284` | sem recarga em 409 | ✅ Killed (`:274`) |
| F12 | `ProcessGenerated.tsx:134` | seção de rascunho aparece em `EM_ANDAMENTO` | ✅ Killed (`ProcessGenerated.test.tsx:221`, `:230`) |
| F13 | `ProcessGenerated.tsx:139` | link aponta para outra rota | ✅ Killed (`:212`) |
| F14 | `Dashboard.tsx:92` | botão também em `EM_ANDAMENTO` | ✅ Killed (`Dashboard.test.tsx:175`) |
| F15 | `Dashboard.tsx:33` | linha não muda de status depois de iniciar | ✅ Killed (`:192`) |
| F16 | `Dashboard.tsx:134` | sem recarga da lista em 409 | ✅ Killed (`:221`) |
| F17 | `Dashboard.tsx:96` | `aria-label` diferente do definido | ✅ Killed (`:175`) |
| F18 | `ScoreEditor.tsx:16` | nota volta a dizer "lidos do documento" | ✅ Killed (`ScoreEditor.test.tsx:137`, `:146`) |

**Sensor depth**: expandido (a feature mexe em fluxo de status, validação do Grupo I e gravação de edição, caminhos de integridade de dados). 39 mutantes: 38 mortos, 1 equivalente, 0 sobreviventes.
**Result**: 38/38 não equivalentes mortos, PASS ✅. Cobertura das regras centrais: botão fora de `RASCUNHO`, `justificativa` enviada, recarga em 409, Etapa 5 em `RASCUNHO`, ramo de valor informado em `_apply_group1`, limpeza com valor diferente, 422 com valor igual, limpeza do valor aceito, mensagem antiga de CATXT-02.

---

## Interactive UAT Results

Não realizado: o Verifier é não interativo. A verificação da interface é por teste de componente; a conferência no navegador fica para o deploy autorizado (smoke da VM).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (`StartProcessDialog` único, reutilizado por Etapa 1 e Painel; `_normalize_for_update` de 11 linhas) | ✅ |
| Surgical changes (45 arquivos, todos ligados a um requisito ou tarefa; nenhum arquivo proibido tocado) | ✅ |
| No scope creep (a rota de status e o domínio não mudaram, como a spec previa) | ✅ |
| Matches patterns (modal `Modal`, `request`, `errorMessage`, `isConflict`) | ✅ |
| Spec-anchored outcome check (valores afirmados batem com a spec) | ✅ |
| Per-layer Coverage Expectation (domínio 1:1 com ACs; rotas com feliz, 404 e 422; frontend com corpo exato e `role="alert"`) | ✅ |
| Every test maps to a spec requirement | ✅ |
| Documented guidelines followed: `CLAUDE.md` (dados sintéticos, regra 11, Conventional Commits com `Co-Authored-By`), AD-004 | ✅ |

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`, rodado no HEAD `9bf9ad7`.
- **Result backend**: `ruff` limpo; `5322 passed, 3 deselected (maritalk_live), 1 warning in 666.95s`, uma única execução completa.
- **Result frontend**: `eslint` limpo (exit 0); `vite build` ok (exit 0); `Test Files 42 passed, Tests 584 passed`.
- **Test count before feature** (`35f6113`, registro de `STATE.md` da revisão simplificada): backend 5281, frontend 563.
- **Test count after feature**: backend 5322, frontend 584.
- **Delta**: +41 backend, +21 frontend.
- **Skipped tests**: 3 `deselected` por `-m 'not maritalk_live'` (opt-in com `RUN_LIVE_MARITALK=1`, fora do gate).
- **Failures**: nenhuma.

---

## Fix Plans

Nenhum mutante sobrevivente e nenhum requisito sem evidência: nenhuma tarefa de correção obrigatória. Lacunas de baixa severidade, ranqueadas:

1. **G1 (baixa, CAINI-01)**: a spec diz "fora do formulário de dados, ao lado da etiqueta"; o botão está dentro do elemento `<form>` (em `.status-row`, `ProcessStep1.tsx:189-196`), com `type="button"`, fora dos `fieldset` de dados. Nenhum teste fixa a posição, e mover o botão não derruba nenhum teste. Sugestão: reescrever o critério para algo testável ("dentro de `.status-row`, ao lado da etiqueta, e não envia o formulário") ou aceitar a lacuna.
2. **G2 (baixa, CAREF-04)**: os nomes "Tabela Sintética ..." e "Item de valor informado (sintético)" são constantes de suporte sem asserção; a garantia é o `grep` registrado na tarefa e a asserção de numeração em `scoring_variants.py:58`. Renomear sem querer não derruba teste algum.
3. **G3 (baixa, critério de sucesso 1)**: não há um teste único de ponta a ponta "iniciar, gerar os três documentos, concluir"; as partes são cobertas separadamente (API: `test_conclusion_api.py:36`; telas: testes de componente).
4. **G4 (informativa, CAINI-06 na Etapa 1)**: depois de um 409, `reload()` refaz o formulário com os dados do servidor (`ProcessStep1.tsx:93-94`), descartando o que o usuário digitou; a spec manda manter os campos só para o início bem-sucedido e não diz o que fazer em 409. Comportamento aceitável, sem teste.

---

## Requirement Traceability Update

Todos os 39 requisitos de `spec.md` passam de `Implementing` para `Verified` (PASS com evidência acima). CAINI-01 e CAREF-04 ficam `Verified` com as lacunas G1 e G2 anotadas como spec-precision.

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 39/39 ACs com asserção que bate com o resultado da spec; 2 spec-precision gaps de baixa severidade (G1, G2).
**Sensor**: 39 mutantes, 38 mortos, 1 equivalente, 0 sobreviventes.
**Gate**: backend 5322 passando, frontend 584 passando, `ruff`, `eslint` e `build` limpos.

**What works**: iniciar o processo na Etapa 1 e no Painel, com confirmação, versão otimista e tratamento de 409, 404 e 422; Etapa 5 que explica o rascunho; Grupo I sempre com período, nível e horas; mensagens de pontuação manual corretas; edição que limpa só o `points_override` que o item recusa, com auditoria do valor anterior; documentação de estado conferida contra o código e o git.

**Issues found**: apenas as lacunas G1 a G4 acima, todas de baixa severidade.

**Next steps**: nenhuma correção obrigatória. Push e deploy só com autorização do usuário; a feature seguinte é `grupo-i-no-total`.

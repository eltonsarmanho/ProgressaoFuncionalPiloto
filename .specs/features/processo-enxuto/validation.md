# Processo enxuto: Etapa 1 sem os dados institucionais e as observações (processo-enxuto) Validation

**Date**: 2026-11-23
**Spec**: `.specs/features/processo-enxuto/spec.md` (ENX-01..ENX-07; AD-027 em `.specs/STATE.md`)
**Diff range**: `22fffaf^..18bf984` (3 commits: `22fffaf` spec, `8bd586f` backend, `18bf984` frontend), mais o commit `663e61d` (só teste, feito pelo Verifier, ver "Fix Plans")
**Verifier**: sub-agente independente (autor diferente). Não leu `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt`, `test/`, `AcessoVM.txt` nem arquivos `.env`; sem push, deploy, VM nem rede. Sensor numa worktree temporária (nunca `git stash`), removida no fim (`git worktree list` mostra só a árvore real).

**Result**: PASS, na segunda iteração. Na primeira o sensor deixou um sobrevivente real (a recusa das quatro chaves `resp_*` no corpo de `PUT` não era detectada); o Verifier acrescentou só um teste (`663e61d`, nenhuma linha de produção) e o mesmo sobrevivente passou a ser morto. Os sete requisitos têm evidência `arquivo:linha` e cada teste afirma o valor que a spec define. O sensor injetou 18 falhas de comportamento (11 no backend, 7 no frontend): 17 válidas, todas mortas ao fim (a M4e só depois do teste novo); a M4b morreu por motivo errado e foi descartada e substituída pela M4c.

---

## Task Completion

A feature não tem `tasks.md` (spec pequena, três commits): spec, backend, frontend.

| Item | Status | Notes |
| ---- | ------ | ----- |
| `22fffaf` spec + AD-027 | Done | `spec.md` Approved; `fundacao/spec.md` com a nota de emenda e PROC-01 `Amended` |
| `8bd586f` backend | Done | cinco campos fora de `ProcessFields`, `ProcessData`, `FunctionalProcess`, `ProcessSnapshot`, `_PROCESS_FIELDS`; regra e código `DADOS_INCOMPLETOS` removidos |
| `18bf984` frontend | Done | grupo "Dados institucionais e observações" e os cinco campos fora de `ProcessStep1.tsx` e de `types.ts` |

---

## Spec-Anchored Acceptance Criteria

### P1: Etapa 1 sem campos que nenhum documento usa

| Requisito | Resultado definido pela spec | `arquivo:linha` + asserção | Result |
| --------- | ---------------------------- | -------------------------- | ------ |
| ENX-01 | Etapa 1 sem o grupo e sem os cinco rótulos; campos de data seguem | `frontend/src/pages/ProcessStep1.test.tsx:230` `expect(screen.queryByLabelText(label)).not.toBeInTheDocument()` para os cinco rótulos literais da spec (`:224-228`); `:232` `queryByText("Dados institucionais e observações")` ausente; `:233` `getByLabelText("Data de abertura")` presente | PASS |
| ENX-01 (payload) | a tela não envia as chaves | `ProcessStep1.test.tsx:105` `expect(JSON.parse(post.init.body)).toEqual({...12 chaves, sem as cinco})` | PASS |
| ENX-02 | processo salvo e `alerts` sem `DADOS_INCOMPLETOS` | `backend/tests/integration/api/test_processes_api.py:145-146` `status_code == 201` e `response.json()["alerts"] == []` (criação sem os cinco campos); `:188` `response.json()["alerts"] == []` (alteração, depois do `PUT`); `:72` `codes(body) == set()` | PASS |
| ENX-02 (qualquer conteúdo antigo) | idem com as colunas preenchidas | `test_processes_api.py:217-219` o `PUT` sobre linha com valores antigos devolve 200; o código de alerta não consulta mais as colunas (a entidade e o `ProcessSnapshot` não têm os campos: `backend/tests/unit/domain/test_process_verification.py:337-341` `names.isdisjoint(removed)`) | PASS (ver nota 1) |
| ENX-03 | `POST`, `GET` e `PUT` sem as cinco chaves | `test_processes_api.py:148-149` `set(REMOVED_FIELDS).isdisjoint(body)` para a resposta do `POST` e do `GET`; `:187` e `:218` para o `PUT`. `GET /api/processes` (lista) usa `ProcessSummary`, que nunca teve os campos | PASS |
| ENX-04 (`POST`) | salva sem as chaves, sem gravar o valor, sem erro | `test_processes_api.py:161` `status_code == 201`; `:162` chaves ausentes na resposta; `:163` `legacy_row(...) == dict.fromkeys(REMOVED_FIELDS)` (as cinco colunas `None`) | PASS |
| ENX-04 (`PUT`) | idem no `PUT` | `test_processes_api.py:186-189` (novo, parametrizado nas cinco chaves, uma por vez) `status_code == 200`, chaves ausentes, `alerts == []`, colunas `None`. Antes de `663e61d` só `test_process_updates_api.py:163` mandava `notes` num `PUT`, sem asserção sobre o que se grava ou devolve (ver "Discrimination Sensor", M4e) | PASS (após `663e61d`) |
| ENX-05 | cinco colunas e valores ficam, sem leitura, exibição nem alteração; nenhuma migração | `test_processes_api.py:219` `legacy_row(engine, created["id"]) == LEGACY_VALUES` (valores gravados direto no banco sobrevivem a `PUT` com `target_level: 2`); `git diff --name-status 22fffaf^..18bf984` não lista nenhum arquivo em `backend/alembic/`; `backend/app/infrastructure/database/models.py:204-209` mantém as colunas | PASS |
| ENX-06 | código ausente em toda verificação e na lista de códigos | `test_process_verification.py:332` `verify_process(CLEAN_NEW, VERSIONS) == []`; `:333` e `:334` `"DADOS_INCOMPLETOS" not in {code.name ...}` e `{code.value ...}` | PASS |
| ENX-07 | auditoria da edição sem os cinco campos; eventos anteriores intactos | `test_processes_api.py:221-224` `events` não vazio e, para cada evento (criação e edição), `set(REMOVED_FIELDS).isdisjoint(event.changes)`. Eventos anteriores intactos: garantido pelo gatilho `audit_logs_immutable` (`backend/alembic/versions/0001_initial_schema.py:250-259`, `BEFORE UPDATE OR DELETE`) e pelo diff, que não toca o código de auditoria | PASS (ver nota 2) |

### Edge cases

| Caso | Evidência | Result |
| ---- | --------- | ------ |
| Cliente antigo envia as cinco chaves e recebe resposta como se não tivessem sido enviadas | `test_processes_api.py:153-163` (`POST`, as cinco juntas) e `:166-189` (`PUT`, uma por vez) | PASS |
| Processo antigo com valores nas colunas abre sem mostrá-los e salva sem alterá-los | `test_processes_api.py:218-219` (API); a tela só lê os campos de `FIELDS` (`frontend/src/pages/ProcessStep1.tsx:14-24`) | PASS |
| Processo com tudo correto devolve `alerts` vazio | `test_processes_api.py:146` e `:72` | PASS |

**Status**: todos os ENX cobertos com evidência; nenhum gap de precisão que impeça o PASS (duas notas abaixo).

**Notas de precisão da spec (não bloqueiam):**

1. ENX-02 diz "qualquer que seja o conteúdo antigo das cinco colunas". Nenhum teste prepara colunas preenchidas e lê o `alerts` do `PUT`; a garantia é estrutural (o alerta não tem mais acesso aos campos: a entidade e o `ProcessSnapshot` não os têm, e `:337-341` trava isso). Aceito porque o código que poderia reagir ao conteúdo antigo não existe mais.
2. ENX-07, segunda parte ("manter intactos os eventos anteriores") não tem asserção de que um evento antigo com as chaves continua legível; a imutabilidade vem do gatilho do banco, e o diff não altera `audit.py`.

---

## Discrimination Sensor

Worktree temporária em `HEAD` (`18bf984`); depois de cada falha o arquivo foi restaurado com `git checkout`. Backend: `test_processes_api.py`, `test_process_updates_api.py`, `test_process_alert_norms.py`, `test_process_verification.py`. Frontend: `ProcessStep1.test.tsx`.

| Mutação | Arquivo | Descrição | Killed? |
| ------- | ------- | --------- | ------- |
| M1a | `backend/app/presentation/schemas/processes.py` (`ProcessOut`) | volta a chave `resp_name` na saída | Killed (`test_a_process_without_the_removed_fields_saves_with_no_alert_and_no_such_keys`) |
| M2a | `backend/app/infrastructure/database/repositories.py` (`update`) | grava `NULL` em `resp_name` e `notes` ao salvar | Killed (`test_old_values_stay_in_the_columns_when_the_process_is_saved_again`) |
| M2b | idem (`add`) | grava `'x'` em `resp_name` ao criar | Killed (`test_the_removed_fields_sent_by_an_old_client_are_ignored_and_not_stored`) |
| M3a | `backend/app/domain/rules/process_verification.py` | volta o membro `DADOS_INCOMPLETOS` no enum | Killed (`test_a_clean_process_has_no_alerts_and_the_old_code_is_gone`) |
| M3b | idem | `verify_process` sempre acrescenta um alerta "Campos não preenchidos" | Killed (`test_proc10_fasi_case_has_24_months_and_no_alerts`) |
| M4a | `processes.py` (`ProcessCreate`) | `extra="forbid"` no `POST` | Killed (teste do cliente antigo no `POST`) |
| M4b | `processes.py` (`ProcessUpdate`) | `extra="forbid"` no `PUT` | Killed, mas por motivo errado (o teste manda `professor_id` e `unit_id`, que `ProcessUpdate` não declara); substituída pela M4c |
| M4c | `processes.py` (`ProcessUpdate`) | `PUT` responde 422 se vier qualquer das cinco chaves | Killed (antes: `test_process_with_career_jump_is_created_edited_and_started`, só por mandar `notes`; depois de `663e61d`: `...removed_field_sent_in_an_edition...[notes]`) |
| M4d | `processes.py` (`ProcessCreate`) | `POST` responde 422 se vier qualquer das cinco chaves | Killed |
| M4e | `processes.py` (`ProcessUpdate`) | `PUT` responde 422 só se vier uma das quatro chaves `resp_*` | **Survived antes de `663e61d`** (79 passed); Killed depois (`...[resp_name]`) |
| M5 | `backend/app/application/use_cases/processes.py` (`audit_view`) | acrescenta `resp_name` e `notes` à visão de auditoria | Killed (`test_old_values_stay_in_the_columns_when_the_process_is_saved_again`) |
| F1..F5 | `frontend/src/pages/ProcessStep1.tsx` | volta cada um dos cinco rótulos como campo | Killed, os cinco (`ENX-01`) |
| F6 | idem | volta o `fieldset` "Dados institucionais e observações" | Killed (`ENX-01`) |
| F7 | idem (`toPayload`) | acrescenta `resp_name: null` ao corpo enviado | Killed (`toEqual` em `ProcessStep1.test.tsx:105`) |

**Sensor depth**: lightweight ampliado (18 mutações em vez de 1 a 3, por tocar contrato de API e dados gravados).
**Result**: 17 de 17 mutações válidas mortas ao fim (M4b descartada por morrer por motivo errado); 1 sobrevivente na primeira passada (M4e), corrigido por `663e61d`. PASS.

**Isolamento**: `git status --porcelain` da árvore real antes do sensor: `?? backend/img/`, `?? requeriment.txt`, `?? test/`. Depois: as mesmas três linhas mais `?? .specs/features/gestao-tabelas/`, que apareceu durante a verificação e não foi criada pelo Verifier (nenhuma escrita fora de `.specs/features/processo-enxuto/`, `backend/tests/integration/api/test_processes_api.py` e a worktree temporária); nenhum arquivo rastreado ficou alterado pelo sensor.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | OK: o diff só remove campos e a regra; um teste novo por requisito |
| Surgical changes | OK: `fundacao/spec.md` ganha só a nota de emenda e PROC-01 `Amended` |
| No scope creep | OK: sem migração, sem documento novo |
| Matches patterns | OK: ENX-xx nos comentários dos testes, como o resto |
| Spec-anchored outcome check | OK (tabela acima; duas notas de precisão) |
| Per-layer coverage | OK: domínio (`test_process_verification.py`), API (`test_processes_api.py`), tela (`ProcessStep1.test.tsx`) |
| Every test maps to a requirement | OK; resíduo: `test_process_updates_api.py:163` ainda manda `"notes": "Salto informado"` num `PUT`, sem relação com o assunto do teste (carreira); inofensivo, passou a ser cobertura incidental de ENX-04, agora coberta de forma explícita |
| Guidelines followed | `CLAUDE.md` (dados sintéticos, Conventional Commits); gate do backend e do frontend |

Referências remanescentes aos cinco campos ou ao alerta (varredura em `backend/app`, `backend/tests`, `frontend/src`, `docs`, `scripts`, `deploy`): só as esperadas: `models.py:204-209` (colunas mantidas por ENX-05), `alembic/versions/0001_initial_schema.py` (histórico), os testes do ENX (`test_processes_api.py`, `test_process_verification.py`, `ProcessStep1.test.tsx`) e a menção a "Portaria de designação" no texto do tipo de documento `PORTARIA` (`infrastructure/ai/schemas.py:26`), que é outra coisa. Em `.specs`, só histórico de `fundacao`, `normativo/tasks.md`, `STATE.md` e a própria spec. O campo `notes` que sobra em `frontend/src/api/types.ts:112,279` e `NormForms.tsx` pertence a norma e a versão de tabela (Out of Scope da spec).

---

## Gate Check

- **Gate do autor** (rodado pelo autor, não repetido por inteiro): backend ruff limpo e 6505 passando; frontend eslint, tsc e build limpos e 765 passando.
- **Rodada do Verifier (só os alvos)**: backend `tests/unit/domain/test_process_verification.py`, `test_process_verification_citations.py`, `test_scoring_alerts.py`, `test_titration_verification.py`, `tests/integration/api/test_processes_api.py`, `test_process_updates_api.py`, `test_process_alert_norms.py` e `tests/integration/test_repositories.py`: 128 passed, 0 failed (123 do autor mais 5 do teste novo parametrizado); `ruff check .` limpo. Frontend `npx vitest run src/pages/ProcessStep1.test.tsx`: 12 passed.
- **Testes pulados**: nenhum.
- **Integridade dos testes**: nenhuma asserção enfraquecida; as asserções de `notes` foram trocadas por `current_denomination` (`ProcessStep1.test.tsx` CAINI-05) e por `target_level` (`test_process_updates_api.py`) com o mesmo valor discriminante; ENX-01..07 ganharam testes novos.

---

## Fix Plans

### Fix 1 (feito): ENX-04, ramo `PUT`, sem teste que o detecte

- **Root cause**: nenhum teste mandava, num `PUT`, as chaves `resp_name`, `resp_position`, `resp_appointment` ou `resp_admin_unit`; só `notes` ia, de passagem, sem asserção sobre o que se grava ou devolve. A mutação M4e sobreviveu.
- **Fix**: teste parametrizado nas cinco chaves (`test_processes_api.py:166-189`), commit `663e61d`, só teste. M4c e M4e passam a morrer.
- **Priority**: Major (requisito sem prova de comportamento), fechado.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| ENX-01 | Implementing | Verified |
| ENX-02 | Implementing | Verified |
| ENX-03 | Implementing | Verified |
| ENX-04 | Implementing | Verified |
| ENX-05 | Implementing | Verified |
| ENX-06 | Implementing | Verified |
| ENX-07 | Implementing | Verified |

---

## Summary

**Overall**: Ready (PASS)

**Spec-anchored check**: 7/7 requisitos com evidência e valor igual ao da spec; 2 notas de precisão registradas (ENX-02 estrutural, ENX-07 pelo gatilho do banco)
**Sensor**: 17/17 mutações válidas mortas (1 sobrevivente na primeira passada, corrigido por `663e61d`)
**Gate**: backend 128 passed nos alvos (autor: 6505 no total), frontend 12 passed no alvo (autor: 765 no total)

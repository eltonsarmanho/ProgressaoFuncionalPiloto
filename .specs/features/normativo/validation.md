# Base de normas e regras de elegibilidade (normativo) Validation

**Date**: 2026-11-22
**Spec**: `.specs/features/normativo/spec.md` (36 requisitos: NBASE-01..12, NLINK-01..06, NTIT-01..08, NLIST-01..03, NMIN-01..02, NMOV-01..05; o pedido dizia 37, mas a soma das famílias e a tabela de rastreabilidade dão 36)
**Diff range**: `c107b64..HEAD` (`7b06e61`). Volta 1 sobre `b52001b` (29 commits, T1 `e2eecbd` a T29 `b52001b`; 79 arquivos, +6412 −233); volta 2 acrescenta `e792068`, `99556ce`, `ff8d45f`, `3326845`, `7a18482` e `7b06e61` (5 arquivos, +90 −10: só testes e `spec.md`)
**Verifier**: sub-agente independente (autor diferente), volta 2 de 3 (a volta 1 está registrada abaixo, na seção "Volta 1" e nos planos FT1..FT6). Não leu `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt` nem `test/`; sem push, deploy, VM nem rede. Sensor em worktree temporária isolada (nunca `git stash`), removida no fim; `git status --porcelain` da árvore real igual ao de antes (só `backend/img/`, `requeriment.txt` e `test/`).

**Result**: PASS na volta 2 (a volta 1 terminou em reprovação, com os planos FT1..FT6 abaixo). Resumo da volta 1: 36 de 36 requisitos têm evidência `arquivo:linha` e o gate está verde (backend e frontend abaixo). O sensor rodou 78 mutantes: 73 mortos e 5 sobreviventes. Três sobreviventes não têm efeito observável sobre a spec (S04 e P07 equivalentes; U10 fora do texto, ver G4); dois são lacunas reais de teste (T03: citação do alerta `TABELA_FORA_DE_VIGENCIA`; P12: a titulação por classe some num `PUT` de corpo antigo) e viram tarefas de correção. Mais uma lacuna de evidência (NTIT-07: editar e iniciar processo com `TITULACAO_INSUFICIENTE`) e lacunas de precisão da spec. Nenhum defeito de comportamento do código de produção foi encontrado.

**Volta 2 (veredito)**: as seis lacunas FT1..FT6 foram conferidas no código, na spec e nos testes, cada teste novo afirma o valor da spec e não o espelho da implementação; os dois sobreviventes reais (T03 e P12) agora morrem; uma amostra nova de 19 mutantes sobre os testes novos e os testes que a volta 1 já cobria teve 18 mortos e 1 sobrevivente sem efeito na spec desta feature (X15, a ordem dos grupos de severidade, comportamento anterior à feature); o gate está verde (backend 5675 passando, frontend 668 passando). FT4 (extensão `.pdf`, mutante U10) ficou de propósito sem mudança: é uma nota de precisão da spec (NBASE-06), registrada abaixo, e não uma lacuna. Detalhes na seção "Volta 2".

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 (NMOV) | Done | `e2eecbd` |
| T2..T4 (entidade, validação, ordem das titulações) | Done | `02ce2c5`, `5e6dcb0`, `f938312` |
| T5..T9 (carreira, titulação, citações no domínio) | Done | `39b5eed`, `1fe06e5`, `569f603`, `41e9fe5`, `f4ea85f` |
| T10..T16 (migração, repositórios, storage, seed) | Done | `6ef80d8`, `32cedb0`, `655269b`, `1ab5ab0`, `afd3d22`, `10a73fd`, `c2a6d41` |
| T17..T22 (citações, casos de uso, API) | Done | `f679bec`, `b49e77e`, `c035797`, `6af68fb`, `631805e`, `cae7a8c` |
| T23..T28 (frontend) | Done | `e35cf28`, `71f3fba`, `8e1ec17`, `4066a7c`, `0d419f8`, `c5bfbeb` |
| T29 (AD-024, deploy) | Done | `b52001b`; `.specs/STATE.md:193` e `docs/deploy/vm.md:180` conferidos |
| T30 (Verifier) | Done | este relatório, volta 2 (a volta 1 reprovou; correções FT1..FT6 em `e792068`..`7b06e61`) |

Test Integrity: backend 5459 testes coletados em `c107b64` e 5675 em `HEAD` (+216: 210 até `b52001b` e 6 da volta 2); nenhum `def test_`, `it(` ou `describe(` foi removido no diff; os testes existentes que mudaram (`test_processes_api.py`, `test_scoring_*`, `test_seed.py`, `test_career_catalog.py`, `PanelHeadline.test.tsx`) mudaram por NMOV-02/03, NMIN-02 e NTIT-06 e não foram enfraquecidos.

---

## Spec-Anchored Acceptance Criteria

Legenda: ✅ o teste afirma o valor que a spec define; ⚠️ lacuna de precisão da spec; ❌ lacuna. Caminhos relativos a `backend/tests/` (b/) e `frontend/src/` (f/).

### P1: Base de normas

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| NBASE-01 | Gravar ativa e auditar | `b/integration/test_norm_usecases.py:111-128` (`stored.archived is False`, `version == 1`, evento `CREATE` com `user_id == admin.id`); `b/integration/api/test_norms_api.py:55-74` (201, `archived False`, `file None`) | ✅ |
| NBASE-02 | 422 com o campo (código repetido ou ausente; título, tipo, órgão, data) | `b/integration/api/test_norms_api.py:122-130` (422 e `detail[0]["field"] == field`, 9 casos); `:133-138` (cada campo ausente); `b/integration/test_norm_usecases.py:131-157`; `b/unit/domain/test_norm_rules.py:34,55` | ✅ |
| NBASE-03 | 422 no campo `valid_to` quando o fim é anterior ao início | `b/unit/domain/test_norm_rules.py:65-71` (igual passa, um dia antes recusa em `valid_to`); `b/integration/test_norm_usecases.py:160-168`; `b/integration/test_migration_norms.py:95` (CHECK no banco) | ✅ |
| NBASE-04 | 422 no campo da URL sem `http(s)://` | `b/unit/domain/test_norm_rules.py:79-90` (`ftp://` recusa; `http` e `https` passam); `b/integration/test_norm_usecases.py:172-177` | ✅ |
| NBASE-05 | Guardar PDF até 20 MB, substituir o anterior, auditar | `b/integration/test_norm_usecases.py:180-206` (`_stored_files == [second.file.internal_name]`, `file_original_name` before/after); `b/integration/api/test_norms_api.py:186-217`; `b/unit/infrastructure/test_norm_storage.py:33-96` (0700/0600, regex) | ✅ |
| NBASE-06 | 422 e mensagem do limite (não PDF ou > 20 MB) | `b/integration/test_norm_usecases.py:209-249` (um byte acima de 20 MB: `"20 MB" in error.value.message`; nada fica no disco); `b/integration/api/test_norms_api.py:228-244` | ✅ (nota de precisão da spec, volta 2: o texto diz só "não é PDF ou passa de 20 MB"; a checagem da extensão `.pdf` em `_check_pdf` vai além dele, mutante U10, sem efeito na spec) |
| NBASE-07 | Gravar sem mudar o código; valores anteriores na auditoria | `b/integration/test_norm_usecases.py:250-267` (`changes["title"] == {"before","after"}`, `"code" not in event.changes`); `b/integration/api/test_norms_api.py:142-165` (corpo com outro `code` é ignorado) | ✅ |
| NBASE-08 | Arquivar, manter as ligações, "(arquivada)" onde citada | `b/integration/test_norm_usecases.py:270-293` (`after.rules == before.rules`, `cite_norms(...).archived is True`, evento `ARCHIVE`); `f/components/NormLink.test.tsx:67-71`; `f/components/AlertList.test.tsx:51`; `f/pages/Norms.test.tsx:171` | ✅ |
| NBASE-09 | 403 para quem não é ADMIN | `b/integration/api/test_norms_api.py:248-261` (`[403, 403, 403, 403]` e a norma intacta); `b/integration/test_norm_usecases.py:296-319` (`Forbidden` em cadastrar, editar, arquivar e anexar) | ✅ |
| NBASE-10 | 409 à segunda edição da mesma versão | `b/integration/api/test_norms_api.py:265-281` (`(409, 409, 409)` e a primeira edição fica); `b/integration/test_norm_usecases.py:322-336`; `f/components/NormForms.test.tsx:121,184` | ✅ |
| NBASE-11 | Semear as sete normas com a URL de `FONTES.md` | `b/integration/test_seed_norms.py:95-113` (código, título, tipo, órgão, data e URL de cada uma); `:116-126` (URL em `FONTES.md`, a tabela oficial sem URL); `:129-137` (nota de data aproximada) | ✅ |
| NBASE-12 | Não alterar nem duplicar norma existente | `b/integration/test_seed_norms.py:150-158` (segunda partida: 7 normas, auditoria igual); `:161-184` (norma editada e arquivada fica como estava); `:187-206` (só os 6 códigos que faltam entram) | ✅ |

### P1: Regras e alertas ligados à norma

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| NLINK-01 | Estrutura, versão de tabela e titulação guardam o código, mantendo `norm_reference` | `b/unit/domain/test_career.py:87-100`; `b/integration/test_career_repository_norms.py:42-127`; `b/integration/test_scoring_version_norm_code.py:25-63`; `b/integration/api/test_career_api.py:318-397` (GET, PUT com os campos, PUT de corpo antigo mantém os códigos); `b/integration/test_migration_norms.py:72`; `b/integration/api/test_career_api.py:408-432` (volta 2: corpo sem `required_titration` em nenhuma classe e sem `norm_code`: `{A: None, B: None, C: "DOUTORADO", D: "DOUTORADO"}` na resposta do `PUT` e no `GET`, e `(norm_code, required_titration_norm_code) == ("LEI-12772-2012", "MANUAL-PROGEP-PROGRESSAO")`) | ✅ (G2 fechada) |
| NLINK-02 | Res. 4.644 -> `RES-4644-2015-CONSEPE`, Lei 15.141 -> `LEI-12772-2012`, tabela oficial -> `TABELA-OFICIAL-UFPA` | `b/unit/domain/test_career_catalog.py:71-75` (`norm_code ==` os dois literais); `b/integration/test_seed_links.py:71-86`, `:202-224` (`linked.norm_code == "TABELA-OFICIAL-UFPA"`); `b/integration/test_seed.py:55` | ✅ |
| NLINK-03 | Título, `norm_reference` e "Ver norma" no alerta, um código por origem (tabela do design) | `b/unit/domain/test_process_verification_citations.py:93-96` (8 alertas do processo, código esperado de cada um); `:107-110` (modalidade -> `LEI-12772-2012`); `b/unit/domain/test_scoring_citations.py:57-68` e `b/unit/domain/test_scoring_verification.py:137-169` (mínimo e extensão -> `RES-4644-2015-CONSEPE`, tabela não encontrada -> `TABELA-OFICIAL-UFPA`); `b/integration/api/test_process_alert_norms.py:103-133`; `b/integration/api/test_scoring_alert_norms.py:102`; `f/components/AlertList.test.tsx:35`; `b/unit/domain/test_scoring_citations.py:71-84` (volta 2: `TABELA_PENDENTE_VALIDACAO` e `TABELA_FORA_DE_VIGENCIA`, versão ligada e não ligada: `alert.code is ...` e `alert.norm_code == norm_code`, com o código sintético e com `None`) | ✅ (G1 fechada) |
| NLINK-04 | Link para o arquivo, senão a URL, senão só o título | `f/components/NormLink.test.tsx:43-63` (`href == FILE`, `href == URL`, sem link); `b/integration/api/test_process_alert_norms.py:137-163` (`norm_file_url == f"/api/norms/{lei.id}/file"`); `f/components/AlertList.test.tsx:46`; `f/pages/Norms.test.tsx:96` | ✅ |
| NLINK-05 | Sem norma ligada, só o texto de `norm_reference` | `b/integration/api/test_process_alert_norms.py:167-177` (código nulo e código inexistente: `norm_fields(alert) == NO_NORM`); `b/integration/test_norm_citations.py:54` (aviso no log com o código); `f/components/AlertList.test.tsx:57-76` | ✅ |
| NLINK-06 | Código e título da norma no alerta da API | `b/integration/api/test_process_alert_norms.py:111-117` (`norm_code`, `norm_title`, `norm_url`, `norm_file_url`, `norm_archived`); `b/integration/api/test_scoring_alert_norms.py:102-170`; `b/unit/domain/test_norm.py:40` | ✅ |

### P1: Titulação exigida pela classe pretendida

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| NTIT-01 | `TITULACAO_INSUFICIENTE` com severidade `ALERTA` na promoção, titulação menor que a exigida | `b/unit/domain/test_titration_verification.py:76-81` (`alert.severity is Severity.ALERTA`); `:84-88`; `:121-126` (salto A1 para C1); `b/unit/domain/test_titration_order.py:178-203` (ordem e `titration_at_least`); `b/integration/api/test_process_alert_norms.py:186-188` | ✅ |
| NTIT-02 | Texto "A classe <pretendida> (<denominação pretendida>) exige <titulação>; a titulação cadastrada do docente é <titulação>." com a norma da regra (texto da spec desde `3326845`) | `b/unit/domain/test_titration_verification.py:79-81` (`message == EXPECTED_MESSAGE`, `norm_reference`, `norm_code == RULE_CODE`); `:95-99` (graduação e especialização); `b/integration/api/test_process_alert_norms.py:189-198`; `f/components/AlertList.test.tsx:80` | ✅ (G5 fechada: a spec, em `.specs/features/normativo/spec.md:103`, agora escreve "A classe <classe pretendida> (<denominação pretendida>) exige <titulação exigida>; ...", igual a `process_verification.py:196-198` e ao teste) |
| NTIT-03 | Igual ou maior: sem alerta | `b/unit/domain/test_titration_verification.py:103-104` (`== []` para doutorado); `b/unit/domain/test_titration_order.py:203` | ✅ |
| NTIT-04 | Mesma classe: não confere | `b/unit/domain/test_titration_verification.py:108-117` (C1 para C2 com mestrado: `== []`) | ✅ |
| NTIT-05 | Sem regra para a classe: sem alerta | `b/unit/domain/test_titration_verification.py:130-145` (A para B e estrutura antiga: `== []`); `b/integration/api/test_career_api.py:64` | ✅ |
| NTIT-06 | Semear doutorado para C e D, ligado ao Manual da PROGEP | `b/unit/domain/test_career_catalog.py:77-85` (`{A: None, B: None, C: DOUTORADO, D: DOUTORADO}`, `required_titration_norm_code == "MANUAL-PROGEP-PROGRESSAO"`, estrutura antiga sem regra); `b/integration/test_seed_links.py:71-95` (base com versões antigas já usadas) e `:129` (valor do ADMIN não é sobrescrito) | ✅ |
| NTIT-07 | Nunca bloquear criação, edição nem andamento | `b/unit/domain/test_titration_verification.py:84-88` (a única saída é `ALERTA`); `b/integration/api/test_process_alert_norms.py:59-64` (criação 201 com o alerta presente, `:186`); `b/integration/api/test_process_alert_norms.py:222-257` (volta 2, docente de mestrado, alerta presente: `PUT` 200 com `notes` gravada e alerta `ALERTA`; `POST .../status` `EM_ANDAMENTO` 200 e `stored["status"] == "EM_ANDAMENTO"`; `PUT` em andamento com justificativa 200 e alerta `ALERTA`) | ✅ (G3 fechada) |
| NTIT-08 | Titulação corrigida: alerta some na leitura seguinte | `b/integration/api/test_process_alert_norms.py:200-219` (`PUT /api/professors` com `DOUTORADO`; `"TITULACAO_INSUFICIENTE" not in codes`; os outros alertas ficam) | ✅ |

### P1: Origem e destino informados pelo servidor

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| NMOV-01 | Usar classe, denominação e nível como informados, sem deduzir | `b/integration/api/test_process_updates_api.py:158-160` (`stored["current_class"], ... == ("A", 1)`, `("C", 1)` depois de criar, editar e iniciar); `b/integration/api/test_career_api.py:449-450` (denominação gravada fica); o código novo não calcula classe, denominação nem nível (`process_verification.py:142-165`, só avisa) | ⚠️ nota de precisão (sem lacuna de código): afirmação negativa; "telas e documentos gerados" só têm a cobertura que já existia (`b/integration/doc_usecases/test_generation_inputs.py:118`); o texto de NMOV-01 não foi alterado na volta 2 e ainda não diz onde as telas e os documentos leem os seis campos |
| NMOV-02 | Promoção fora da sequência: `ALERTA` e o texto exato | `b/unit/domain/test_process_verification.py:25-28` (texto), `:170-179` e `:180-195` (A1 para C1 e as variações: `severity is Severity.ALERTA`, `message == PROMOTION_JUMP`); `b/integration/api/test_process_updates_api.py:60-67`; `b/integration/api/test_processes_api.py:96` | ✅ |
| NMOV-03 | Progressão fora da sequência: `ALERTA` e o texto exato | `b/unit/domain/test_process_verification.py:29-32`, `:133-144`, `:201-214` (C1 para C3 e B4 para C1: `severity is Severity.ALERTA`, `message == PROGRESSION_JUMP`), `:217-231` (sequência usual sem alerta) | ✅ |
| NMOV-04 | Nunca bloquear nem alterar o processo por `MODALIDADE_INCOMPATIVEL` ou `DENOMINACAO_DIVERGENTE` | `b/unit/domain/test_process_verification.py:239-250` (nenhum `ERRO` por modalidade); `b/integration/api/test_process_updates_api.py:139-160` (criar 201, editar 200, iniciar `EM_ANDAMENTO`, valores gravados iguais) | ✅ |
| NMOV-05 | Novas denominações usadas na verificação seguinte, sem mudar processos nem documentos já gerados | `b/unit/domain/test_process_verification_citations.py:133-163` (o mesmo processo, antes e depois de renomear a classe C: `DENOMINACAO_DIVERGENTE` aparece com "Denominação Sintética", `process == before`); `b/integration/api/test_career_api.py:449-480` (ADMIN renomeia numa versão ainda não usada; `read["target_denomination"] == "Associado"`) | ✅ (G6 fechada: a spec, em `spec.md:127` e `:129`, agora diz "numa versão que nenhum processo usa, por CARR-08, ou numa versão nova" e que a verificação "lê as denominações da versão como estão gravadas quando roda", o que os dois testes citados exercitam) |

### P2: Lista de normas e mínimo não definido

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| NLIST-01 | Página "Normas" para todos, com título, tipo, órgão, data, vigência, link e regras ligadas | `f/pages/Norms.test.tsx:79-104` (DOCENTE vê as colunas e as regras, sem botões); `:218`; `b/integration/api/test_norms_api.py:78-96` (docente lista as 7 semeadas com `linked_rules`: `{"CARREIRA"}`, `{"TITULACAO"}`, `[]`); `b/integration/test_norm_usecases.py:339-366` | ✅ |
| NLIST-02 | Arquivadas escondidas, filtro "Mostrar arquivadas" | `f/pages/Norms.test.tsx:140-157` (`include_archived=false`, depois `true` e "(arquivada)"); `b/integration/api/test_norms_api.py:169-182` (`[]` e depois `[("RES-SINTETICA-2020", True)]`) | ✅ |
| NLIST-03 | Botões de gestão só para o ADMIN | `f/pages/Norms.test.tsx:107-137` (ADMIN vê Cadastrar, Editar, Anexar PDF e Arquivar; DOCENTE não, em `:79`) | ✅ |
| NMIN-01 | Estrutura da Lei 15.141 mantém `NAO_DEFINIDO`, sem número | `b/unit/domain/test_scoring_verification.py:148-169` (`minimum is None`, `status is NAO_DEFINIDO`); `b/integration/api/test_scoring_alert_norms.py:170-176` (`body["minimum"]["minimum"] is None`); `f/components/PanelHeadline.test.tsx:42` | ✅ |
| NMIN-02 | Texto "Mínimo não definido: a Res. 4.644/2015, art. 12, fixa mínimos só para as classes da estrutura antiga" e "Ver norma" para `RES-4644-2015-CONSEPE` | `f/components/PanelHeadline.test.tsx:62-88` (texto exato e `href` da URL), `:90-108` (arquivo anexado), `:110-117` (mínimo numérico sem texto nem link); `b/integration/api/test_scoring_alert_norms.py:170-189` (`body["minimum"]["norm"] == {code, title, source_url, file_url, archived}`) e `:200` (estrutura antiga: `norm is None`) | ✅ (ver (d) abaixo) |

**Status** (volta 2): 36 de 36 com evidência `arquivo:linha` e a asserção no valor da spec. 35 ✅; NMOV-01 ⚠️ só como nota de precisão (requisito negativo, sem lacuna de código); NBASE-06 ✅ com a nota de precisão sobre a extensão `.pdf` (U10). Na volta 1 eram 30 ✅, cinco ⚠️ e um ❌.

### Pontos que os autores pediram para decidir

- **(a) `ProcessStep1.test.tsx:16`** ainda usa `MODALIDADE_INCOMPATIVEL` com severidade `ERRO` como dado de exibição (e `:89` afirma o grupo "Erro (2)"). Lacuna real, mas só de fidelidade do dado: o teste verifica o agrupamento por severidade, não a regra. `AlertList.test.tsx:105` já cobre `MODALIDADE_INCOMPATIVEL` como `ALERTA`. Severidade baixa (G7). **Volta 2 (FT6 fechada em `7a18482`)**: `ProcessStep1.test.tsx:16` agora usa `INTERSTICIO_INSUFICIENTE` como `ERRO`, com a mensagem e a referência que o backend emite (`process_verification.py:173-177`: `Severity.ERRO`, "Interstício de {months} meses; o mínimo exigido é de {minimum} meses."), e `:89-95` mantém "Erro (2)"; o sensor X12..X14 confirma que o teste depende desses valores.
- **(b) Rastreabilidade**: `spec.md` linha de NTIT-01 diz "Implementing" apesar das tarefas feitas, e a linha "Coverage" diz "31 total, 0 mapped to tasks, 31 unmapped (Design pendente)", quando há 36 requisitos mapeados. Lacuna real de bookkeeping (G5). **Volta 2**: `3326845` corrigiu a linha de NTIT-01 para `Implemented` e a linha Coverage para "36 total, 36 mapped to tasks, 0 unmapped" (`spec.md:211`, `:230`); a passagem dos 36 requisitos para `Verified` fica com o orquestrador depois desta volta.
- **(c) NMOV-05 só numa versão sem uso**: o texto da spec está satisfeito no nível do domínio, onde está o comportamento: o teste `test_process_verification_citations.py:133` verifica o mesmo processo antes e depois da troca de denominação. No nível da API só dá para trocar denominação de uma versão sem processo (CARR-08 trava versão em uso, e uma versão é "em uso" exatamente quando algum processo a usa na verificação), então o teste independente da spec ("o processo que informou 'Associado' passa a mostrar `DENOMINACAO_DIVERGENTE`") não é alcançável por essa rota. É lacuna de precisão da spec, não de código nem de teste (G6; fechada na volta 2 por `3326845` e `7b06e61`, que reescreveram NMOV-05 e o teste independente conforme CARR-08); a ressalva "nem os documentos já gerados" não tem teste próprio (AD-012 já cobre).
- **(d) `MinimumOut.norm` só quando o mínimo é `NAO_DEFINIDO`**: coerente com NMIN-02 ("WHERE o mínimo é NAO_DEFINIDO ... com o link"); `schemas/scoring.py` põe `norm` só nesse estado e `test_scoring_alert_norms.py:200` afirma `None` para o mínimo numérico. Nenhuma lacuna. O sensor P08 (`norm` sempre preenchido) morreu; P07 (tirar `RES-4644` da consulta extra) sobreviveu por ser equivalente: `MINIMO_NAO_DEFINIDO` sempre entra na lista de códigos quando o estado é `NAO_DEFINIDO`.
- **(e) Todo alerta que o backend emite resolve a citação conforme a tabela do design**: conferido nos 11 pontos de criação de `Alert` do processo (`process_verification.py:113,133,156,172,193,215,225,235,248,262,278`), nos 4 de `scoring_table_choice.py`, em `scoring_engine.py:115` (todos os alertas de linha e de limite) e nos 2 de `scoring_verification.py`. `INTERSTICIO_DATAS_INVALIDAS` usa `RES-4644-2015-CONSEPE` e não está na tabela do design (testado em `test_process_verification_citations.py:76`, comentado como fora da tabela). Os três alertas de tabela têm teste de citação por alerta: `TABELA_DE_OUTRA_UNIDADE`, e, desde `e792068`, `TABELA_PENDENTE_VALIDACAO` e `TABELA_FORA_DE_VIGENCIA` (`test_scoring_citations.py:71-84`; a volta 1 tinha T03 sobrevivente, agora morto). Versões de tabela criadas pelo ADMIN com tabela nova ou importação CSV (`scoring_admin.py:169,573`) nascem sem `norm_code` (a cópia de versão mantém); a spec não pede e a feature `implantacao` trata a administração (nota N1).
- **(f) O seed nunca sobrescreve campo não nulo e audita com `actor=None`**: confirmado por `test_seed_links.py:129` (valor do ADMIN em estrutura), `:227` (código do ADMIN na tabela), `test_seed_norms.py:161` (norma editada e arquivada), `:147` (`{e.user_id} == {None}`), `test_seed_links.py:97` e `:202`. Mutantes S01, S02, S05, S07 e S03 mortos. S04 é equivalente (o `AuditService.record` já não grava quando nada mudou, `audit_service.py:46-49`).
- **(g) Regras de arquitetura**: `grep` de `fastapi|sqlalchemy|pydantic|app.infrastructure|app.presentation` em `backend/app/domain` e `backend/app/application` não acha nada; `tests/architecture/test_layers.py` passa no gate; `norm_rules.py`, `norm.py`, `norm_citations.py` e `norms.py` só importam portas e domínio.

---

## Discrimination Sensor

Worktree temporária `git worktree add --detach` em `/tmp/claude-1000/.../scratchpad/verifier-normativo/wt` (removida), `PYTHONDONTWRITEBYTECODE=1` e `__pycache__` limpo (uma primeira passada foi descartada porque um `.pyc` de mutante com o mesmo tamanho e o mesmo segundo de mtime contaminou a restauração; os resultados abaixo são da repetição limpa). Cada mutante rodou só os testes que cobrem o arquivo (backend) ou `vitest run` dos quatro arquivos de teste de componente e página (frontend). Script: `scratchpad/verifier-normativo/sensor.py`.

| # | Arquivo | Mutação | Resultado |
| - | ------- | ------- | --------- |
| M01 | `process_verification.py:195` | severidade de `TITULACAO_INSUFICIENTE` ALERTA -> ERRO | ✅ morto (`test_titration_verification.py:76`) |
| M02 | `process_verification.py:158` | severidade do salto de promoção ALERTA -> ERRO | ✅ morto (`test_process_verification.py::test_promotion_rules`) |
| M03 | `process_verification.py:268` | severidade do salto de progressão ALERTA -> ERRO | ✅ morto (`test_progression_must_keep_class_and_advance_one_level`) |
| M04 | `process_verification.py:191` | tirar a comparação de titulação (`titration_at_least`) | ✅ morto (`test_doutorado_gets_no_alert...`) |
| M05 | `professor.py:15-20` | ordem das titulações com mestrado antes de especialização | ✅ morto (`test_titration_order.py:178`) |
| M06 | `process_verification.py:187` | conferir também quando a classe pretendida é a atual | ✅ morto (`test_progression_c1_c2...`) |
| M07 | `process_verification.py:200` | código da titulação = `version.norm_code` | ✅ morto |
| M08 | `process_verification.py:163` | norma da modalidade `LEI-12772-2012` -> `RES-4644-2015-CONSEPE` | ✅ morto (`test_both_modality_alerts_cite_lei_12772...`) |
| M09 | `process_verification.py:245` | estrutura escolhida pela data inicial, não pela final | ✅ morto (`test_requerimento_2024_2026_case`) |
| M10 | `professor.py:25` | `>=` -> `>` em `titration_at_least` | ✅ morto |
| M11 | `process_verification.py:196` | mensagem com a classe atual no lugar da pretendida | ✅ morto |
| M12 | `process_verification.py:259` | calcular o alerta de titulação e não anexá-lo | ✅ morto |
| M13 | `process_verification.py:151` | último nível -> primeiro nível na condição da promoção | ✅ morto (`test_valid_promotion_has_no_alerts`) |
| M14 | `process_verification.py:263` | `level + 1` -> `level` menor (progressão) | ✅ morto |
| M15 | `process_verification.py:199` | `norm_reference` da titulação trocada | ✅ morto |
| N01 | `norm_rules.py:60` | `<` -> `<=` (vigência de um dia só) | ✅ morto (`test_end_equal_to_start_passes`) |
| N02 | `norm_rules.py:66` | aceitar só `https://` | ✅ morto |
| N03 | `norm_rules.py:10` | código aceita minúsculas | ✅ morto |
| N04 | `norm_rules.py:56` | tirar a exigência da data de publicação | ✅ morto |
| N05 | `norm_rules.py:60` | tirar a checagem da vigência | ✅ morto |
| N06 | `norm_rules.py:66` | tirar a checagem da URL | ✅ morto |
| N07 | `norm_rules.py:47` | tirar a exigência do tipo | ✅ morto |
| C01 | `norm.py:133` | `has_file` invertido | ✅ morto |
| C02 | `norm.py:134` | `archived=False` fixo na citação | ✅ morto |
| S01 | `seed.py` `link_career_norms` | ligação sobrescreve o código já gravado | ✅ morto (`test_a_value_already_set_by_the_admin_is_not_overwritten`) |
| S02 | `seed.py` `link_career_norms` | titulação da classe sobrescreve a já gravada | ✅ morto |
| S03 | `seed.py` `seed_norms` | não pular o código já existente | ✅ morto |
| S04 | `seed.py` `link_career_norms` | tirar o atalho "nada mudou" | ⚪ sobrevive, equivalente (`audit_service.py:46-49` não grava diferença vazia e `set_links` regrava os mesmos valores) |
| S05 | `seed.py` `link_table_norms` | tirar o pulo da versão já ligada | ✅ morto |
| S06 | `seed.py` `link_table_norms` | ligar as versões de todas as tabelas | ✅ morto (`test_archived_legacy_tables_stay_without_a_code`) |
| S07 | `seed.py` `link_career_norms` | código da titulação sobrescreve o gravado | ✅ morto |
| S08 | `seed_data/ufpa.json` | código da tabela trocado | ✅ morto |
| S09 | `seed_data/norms.json` | data do Manual 12/11 -> 13/11 | ✅ morto |
| S10 | `seed_data/norms.json` | URL na tabela oficial | ✅ morto |
| S11 | `seed.py` | não chamar `link_career_norms` na partida | ✅ morto |
| K01 | `career_catalog.py` | classe D exige mestrado | ✅ morto |
| K02 | `career_catalog.py` | norma da titulação = Lei | ✅ morto |
| K03 | `career_catalog.py` | estrutura antiga ligada à Lei | ✅ morto |
| K04 | `career_catalog.py` | classe B passa a exigir doutorado | ✅ morto |
| U01 | `norms.py` `ArchiveNorm` | sem `require_admin` | ✅ morto |
| U02 | `norms.py` `AttachNormFile` | não apagar o arquivo anterior | ✅ morto |
| U03 | `norms.py` `CreateNorm` | sem checagem de código repetido | ✅ morto |
| U04 | `norms.py` `UpdateNorm` | auditar o valor novo como o anterior | ✅ morto |
| U05 | `norms.py:37` | limite 20 -> 21 MB | ✅ morto |
| U06 | `norms.py` `ArchiveNorm` | não marcar arquivada | ✅ morto |
| U07 | `norms.py` `ArchiveNorm` | ignorar a versão esperada (409) | ✅ morto |
| U08 | `norms.py` | mensagem do limite sem os "20 MB" | ✅ morto |
| U09 | `norms.py` | regras de carreira sem a ligação em `linked_rules` | ✅ morto |
| U10 | `norms.py` `_check_pdf` | tirar a checagem da extensão `.pdf` | ⚪ sobrevive: o conteúdo (`inspect`) já recusa os não PDF e `validate_upload` recebe `.pdf` fixo; só um PDF de verdade com nome `.txt` mudaria (G4). Volta 2: nota de precisão da spec, ver "Volta 2" |
| U11 | `norms.py:37` | limite 20 MB menos 1 byte | ✅ morto |
| P01 | `schemas/processes.py` | `norm_archived` fixo em falso | ✅ morto |
| P02 | `schemas/processes.py` | `norm_url` fixo nulo | ✅ morto |
| P03 | `schemas/processes.py` | `norm_file_url` fixo nulo | ✅ morto |
| P04 | `use_cases/processes.py:86` | `verify_process` sem a titulação do docente | ✅ morto (NTIT-08) |
| P05 | `norm_citations.py` | sem o aviso de código ausente | ✅ morto |
| P06 | `norm_citations.py` | omitir a norma arquivada | ✅ morto |
| P07 | `use_cases/scoring.py:823` | tirar `NORM_RES_4644` da consulta | ⚪ sobrevive, equivalente (com `NAO_DEFINIDO` o alerta `MINIMO_NAO_DEFINIDO` já traz o código) |
| P08 | `schemas/scoring.py` | `norm` do mínimo sempre preenchido | ✅ morto |
| P09 | `repositories.py` `by_codes` | ignorar a norma arquivada | ✅ morto |
| P10 | `repositories.py` `list` | listar arquivadas por padrão | ✅ morto |
| P11 | `use_cases/career.py` | `PUT` sem `norm_code` apaga o código | ✅ morto |
| P12 | `use_cases/career.py` | `PUT` sem `required_titration` na classe apaga a regra gravada | ❌ **sobrevivia na volta 1**; ✅ morto na volta 2 (`test_career_api.py:408`) |
| T01 | `scoring_table_choice.py:40` | `TABELA_DE_OUTRA_UNIDADE` sem código | ✅ morto |
| T02 | `scoring_table_choice.py:51` | `TABELA_PENDENTE_VALIDACAO` sem código | ✅ morto |
| T03 | `scoring_table_choice.py:61` | `TABELA_FORA_DE_VIGENCIA` sem código | ❌ **sobrevivia na volta 1**; ✅ morto na volta 2 (`test_scoring_citations.py:80`) |
| T04 | `scoring_engine.py:115` | alertas de linha sem código | ✅ morto |
| F01 | `NormLink.tsx:25` | tirar "(arquivada)" | ✅ morto |
| F02 | `NormLink.tsx:17` | tirar o link "Ver norma" | ✅ morto |
| F03 | `NormLink.tsx:13` | URL antes do arquivo | ✅ morto |
| F04 | `NormLink.tsx:20` | `rel` sem `noopener` | ✅ morto |
| F05 | `AlertList.tsx` | não mostrar a norma do alerta | ✅ morto |
| F06 | `AlertList.tsx` | `archived` fixo em falso | ✅ morto |
| F07 | `PanelHeadline.tsx` | sem o `NormLink` do mínimo | ✅ morto |
| F08 | `PanelHeadline.tsx` | texto curto "Mínimo não definido" no lugar da explicação | ✅ morto |
| F09 | `Norms.tsx:85` | todo mundo é ADMIN | ✅ morto |
| F10 | `Norms.tsx:199` | botão Arquivar também em norma arquivada | ✅ morto |
| F11 | `AlertList.tsx` | `fileUrl` fixo nulo | ✅ morto |
| F12 | `Norms.tsx:87` | "Mostrar arquivadas" ligado por padrão | ✅ morto |

**Sensor depth (volta 1)**: P0 / dados e regras de elegibilidade (≥ 5 exigidos; 78 injetados em 8 arquivos de domínio, 8 de aplicação e persistência e 3 de frontend).
**Resultado da volta 1**: 73 de 78 mortos; 5 sobreviventes: 3 sem efeito observável (S04, P07 equivalentes; U10 fora do texto da spec) e 2 lacunas reais (P12, T03), que geraram as tarefas FT1 e FT2. Nota: nenhum teste afirma que um PDF de exatamente 20 MB é aceito (U11 morreu pela mensagem do limite, não pela fronteira); a fronteira é de `validate_upload`, código anterior à feature.

---

## Volta 2 (re-verificação das correções FT1..FT6)

Commits de correção (todos depois de `b52001b`): `e792068` (FT1), `99556ce` (FT2), `ff8d45f` (FT3), `3326845` e `7b06e61` (FT5), `7a18482` (FT6). FT4 foi pulada de propósito. Diff das correções: 5 arquivos, +90 −10, só testes e `spec.md`; **nenhum arquivo de código de produção mudou** (`git diff b52001b..HEAD --stat`).

### Verificação de cada correção

| Gap | Correção | Evidência (`arquivo:linha` + asserção) | Afirma o valor da spec? | Resultado |
| --- | -------- | -------------------------------------- | ----------------------- | --------- |
| FT1 (NLINK-03) | `e792068` | `backend/tests/unit/domain/test_scoring_citations.py:71-76` (`TABELA_PENDENTE_VALIDACAO`: `alert.code is ScoringAlertCode.TABELA_PENDENTE_VALIDACAO`, `alert.norm_code == norm_code`) e `:79-84` (`TABELA_FORA_DE_VIGENCIA`, versão vigente até o dia anterior ao fim: `alert.norm_code == norm_code`), cada um com `linked` (código sintético) e `unlinked` (`None`) | Sim: o código esperado é o da versão da tabela (NLINK-03, tabela do design) e vem do parâmetro, não de uma cópia da expressão `chosen.norm_code`; a versão é sintética e o nome do teste diz isso | ✅ |
| FT2 (NLINK-01, NTIT-05/06) | `99556ce` | `backend/tests/integration/api/test_career_api.py:408-432`: o corpo tira `required_titration` de cada classe (`:412`), `assert all("required_titration" not in c ...)` (`:415`), sem `norm_code` nem `required_titration_norm_code` (`:416`); depois do `PUT` 200 e do `GET`, `{A: None, B: None, C: "DOUTORADO", D: "DOUTORADO"}` e `("LEI-12772-2012", "MANUAL-PROGEP-PROGRESSAO")` | Sim: são os valores semeados por NTIT-06 e NLINK-02, escritos como literais; o `GET` confirma a gravação, não só a resposta do `PUT` | ✅ |
| FT3 (NTIT-07) | `ff8d45f` | `backend/tests/integration/api/test_process_alert_norms.py:222-257`: pré-condição `"TITULACAO_INSUFICIENTE" in codes` (`:225`); `PUT` 200 com `notes` nova gravada e `severity == "ALERTA"` (`:229-234`); `POST .../status` 200 e `stored["status"] == "EM_ANDAMENTO"` com o alerta ainda `ALERTA` (`:236-243`); `PUT` já em andamento, com justificativa (regra 5 do `CLAUDE.md` só dispensa a justificativa nas Etapas 2 a 4) 200 e alerta `ALERTA` (`:245-257`) | Sim: NTIT-07 diz "nunca bloquear a criação, a edição nem o andamento"; o teste cobre edição, início e edição em andamento com o alerta presente (docente de mestrado, promoção B para C) | ✅ |
| FT4 (NBASE-06) | pulada | `backend/app/application/use_cases/norms.py` `_check_pdf` mantém a checagem da extensão `.pdf`; `spec.md:63` diz só "não é PDF ou passa de 20 MB" | não se aplica | ⚠️ **nota de precisão da spec, não lacuna**: a extensão é uma checagem a mais que o conteúdo já cobre (`inspect` recusa os não PDF); nenhum comportamento definido pela spec muda (U10, mutante sem efeito na spec). Registrada aqui e em L-034, não escondida. Se o usuário quiser a extensão como regra, NBASE-06 deve dizê-lo e um teste "PDF de verdade com nome `norma.txt`" a fixa |
| FT5 (spec) | `3326845`, `7b06e61` | `.specs/features/normativo/spec.md:103` (NTIT-02 com "(<denominação pretendida>)", igual a `process_verification.py:196-198` e a `test_titration_verification.py:79`); `:127` e `:129` (NMOV-05 e o teste independente, "numa versão que nenhum processo usa, por CARR-08"; CARR-08 existe em `.specs/features/fundacao/spec.md:49`); `:211` (NTIT-01 `Implemented`); `:230` ("36 total, 36 mapped to tasks, 0 unmapped") | Conferido contra o `CLAUDE.md`: NMOV-05 mantém "sem mudar a denominação informada" e não introduz dedução de classe, denominação nem nível (a regra de NMOV-01 e a decisão de 2026-11-20 seguem em `spec.md:42`, `:123-127`); o salto continua `ALERTA` (`spec.md:124-125`, `:42`); nada contradiz as regras 1 a 11 do `CLAUDE.md` | ✅ (resta a nota sobre NMOV-01, acima) |
| FT6 (frontend) | `7a18482` | `frontend/src/pages/ProcessStep1.test.tsx:16` (`INTERSTICIO_INSUFICIENTE`, `ERRO`, mensagem e referência iguais às de `process_verification.py:173-177` e ao `norm_reference` "Res. 4.644/2015-CONSEPE, arts. 2º, 4º e 5º") e `:86-95` (`getByRole("region", { name: "Erro (2)" })`, dois itens, texto do código, da mensagem e "Referência normativa: ...") | Sim: o código usado como `ERRO` é um que o backend ainda emite como `ERRO`; o teste continua afirmando o agrupamento por severidade da UI-03 | ✅ |

### Sensor da volta 2

Worktree temporária `git worktree add --detach` em `/tmp/claude-1000/.../scratchpad/verifier2/wt` (com `frontend/node_modules` ligado por link simbólico), `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, nenhum `.pyc` gerado; restauração do arquivo original depois de cada mutante; worktree removida e podada no fim; `git worktree list` só com a árvore real. `git status --porcelain` da árvore real igual ao de antes (` M .specs/LESSONS.md`, ` M .specs/lessons.json`, `?? .specs/features/normativo/validation.md`, `?? backend/img/`, `?? requeriment.txt`, `?? test/`). Script: `scratchpad/verifier2/sensor2.py`. A base sem mutante passou na worktree (52 testes dos três arquivos alterados). Sufixo `n` = só os testes novos, para provar que o teste novo, sozinho, mata o mutante.

| # | Arquivo | Mutação | Resultado |
| - | ------- | ------- | --------- |
| T03 | `scoring_table_choice.py:61` | `TABELA_FORA_DE_VIGENCIA` sem código (sobrevivente da volta 1) | ✅ morto (`test_out_of_validity_alert_cites_the_synthetic_version_code[linked]`) |
| P12 | `use_cases/career.py` `_keep_stored_links` | `PUT` sem `required_titration` na classe apaga a regra (sobrevivente da volta 1) | ✅ morto (`test_put_without_required_titration_in_any_class_keeps_the_stored_rules`) |
| T03n | idem T03 | só o teste novo | ✅ morto |
| P12n | idem P12 | só o teste novo | ✅ morto |
| T02n | `scoring_table_choice.py` | `TABELA_PENDENTE_VALIDACAO` sem código, só o teste novo | ✅ morto (`test_pending_validation_alert_cites_...[linked]`) |
| X11 | `scoring_table_choice.py` | `TABELA_PENDENTE_VALIDACAO` com o código fixo `TABELA-OFICIAL-UFPA` no lugar do da versão | ✅ morto (o código sintético do teste difere do literal) |
| X01 | `use_cases/processes.py` `UpdateProcess` | recusar a edição (Conflict) quando há `TITULACAO_INSUFICIENTE` | ✅ morto (NTIT-07, teste novo) |
| X02 | `use_cases/processes.py` `ChangeProcessStatus` | recusar a mudança de status quando há `TITULACAO_INSUFICIENTE` | ✅ morto (NTIT-07, teste novo) |
| X03 | `use_cases/processes.py` `evaluate` | sem a titulação do docente quando o processo está `EM_ANDAMENTO` | ✅ morto (o alerta some depois do início) |
| X04 | `process_verification.py:195` | severidade de `TITULACAO_INSUFICIENTE` `ALERTA` para `ERRO`, só o teste novo | ✅ morto |
| X08 | `use_cases/processes.py` `evaluate` | tirar o alerta de titulação quando o processo tem observação (`notes`) | ✅ morto (a edição com `notes` perde o alerta) |
| X05 | `process_verification.py:196` | mensagem sem a denominação pretendida | ✅ morto (`test_mestrado_promoted_b_to_c_...`, NTIT-02 com a denominação) |
| X06 | `process_verification.py:196` | denominação atual no lugar da pretendida | ✅ morto |
| X07 | `process_verification.py:197` | titulação do docente no lugar da exigida | ✅ morto |
| X09 | `use_cases/career.py` | a regra da classe D não é preservada | ✅ morto (`test_put_without_required_titration_in_any_class_...`) |
| X10 | `use_cases/career.py` | a regra da classe C não é preservada | ✅ morto |
| X12 | `AlertList.tsx` | contador do grupo com `+ 1` | ✅ morto (`ProcessStep1.test.tsx`, "Erro (2)") |
| X13 | `AlertList.tsx` | referência normativa trocada pelo código da norma | ✅ morto |
| X14 | `AlertList.tsx` | mensagem do alerta não é exibida | ✅ morto |
| X15 | `labels.ts` | ordem dos grupos de severidade, ALERTA antes de ERRO | ⚪ sobrevive nos testes de `ProcessStep1` e nos 4 arquivos de componente e página: nenhum requisito desta feature define a ordem dos grupos (comportamento de `AlertList` anterior à feature, UI-03 da `fundacao`); fora do escopo, sem tarefa de correção |

**Sensor depth**: P0 / dados e regras de elegibilidade (≥ 5 exigidos): 20 mutantes (os 2 sobreviventes reais da volta 1, 3 variantes só com o teste novo, 15 amostras novas sobre os testes novos e a fixture do frontend).
**Resultado da volta 2**: 19 de 20 mortos; 1 sobrevivente (X15) sem requisito nesta feature. Os sobreviventes S04, P07 (equivalentes) e U10 (nota de precisão de NBASE-06) da volta 1 não foram repetidos: nada no código de produção que eles mutam mudou (`git diff b52001b..HEAD` não toca `app/`).

---

## Interactive UAT Results

Não aplicável: o Verifier rodou sem o usuário (sub-agente, sem VM nem navegador). A página "Normas", o `NormLink`, o `AlertList` e o `PanelHeadline` têm teste de componente com API simulada (ver NLIST-01..03, NLINK-04, NMIN-02); a fumaça visual fica para o deploy autorizado (`docs/deploy/vm.md:207-213`).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ (`link_*` e `cite_norms` pequenos e sem generalização) |
| Surgical changes | ✅ 79 arquivos, todos ligados a um requisito ou à AD-024 |
| No scope creep | ✅ |
| Matches patterns | ✅ versão otimista, `require_admin`, `AuditService`, `_stage` e download seguro reaproveitados |
| Spec-anchored outcome check | ✅ valores da spec batem nos testes (o texto de NTIT-02 foi alinhado à implementação em `3326845`, G5) |
| Per-layer Coverage Expectation (domínio 1:1; rotas feliz, 403, 409, 422, 404) | ✅ `test_norms_api.py:285-310` cobre 404 em todas as rotas, 401 em `:99` |
| Every test maps to a requirement | ✅ os testes citam NBASE/NLINK/NTIT/NMOV/NLIST/NMIN no nome, no comentário ou no docstring |
| Guidelines (`CLAUDE.md`, AD-001, AD-002, AD-004, AD-012) | ✅ domínio e aplicação puros; só dados sintéticos ("sintética" no nome onde a tabela ou estrutura é de teste) |

---

## Edge Cases

- [x] Código ligado inexistente: sem norma e aviso no log com o código (`test_norm_citations.py:54`, `test_process_alert_norms.py:167`)
- [x] Titulação do docente ausente: sem alerta (`test_titration_verification.py:149`)
- [x] Semeadura repetida: sem duplicata nem auditoria nova (`test_seed_norms.py:150`, `test_seed_links.py:115`)
- [x] Cruzamento de 01/01/2025: titulação pela estrutura do fim do interstício (`test_titration_verification.py:159-170`)

---

## Gate Check

- **Gate command**: `cd backend && ruff check . && pytest -q`; `cd frontend && npm run lint && npm run build && npm test -- --run`
- **Result backend (volta 2, `7b06e61`)**: `ruff check .` "All checks passed!" (exit 0); `pytest -q`: 5675 passed, 3 deselected, 1 warning in 806,02 s (0:13:26), exit 0; o teste intermitente `test_worker.py::test_a_database_error_while_claiming_does_not_kill_the_thread` passou nesta rodada (nada a reexecutar). Volta 1 (`b52001b`): 5669 passed em 826,61 s
- **Result frontend (volta 2)**: `npm run lint` exit 0; `npm run build` exit 0 (bundle 402,64 kB); `npm test -- --run` 668 passando (668), em 50 arquivos de teste
- **Test count before feature**: backend 5459 coletados em `c107b64`
- **Test count after feature**: backend 5675 coletados em `HEAD` (+216); frontend 668 (a volta 2 não acrescentou teste de frontend, só mudou uma fixture)
- **Skipped tests**: 3 desmarcados por `-m 'not maritalk_live'` (`pyproject.toml`), sem relação com a feature
- **Failures**: nenhuma

---

## Fix Plans

Planos da volta 1 e o que a volta 2 constatou (nenhum plano aberto):

| Plano | Prioridade | Situação na volta 2 |
| ----- | ---------- | ------------------- |
| FT1: citação do alerta `TABELA_FORA_DE_VIGENCIA` (e `TABELA_PENDENTE_VALIDACAO`) | Major | Feita em `e792068`; T03, T03n, T02n e X11 morrem |
| FT2: titulação por classe sobrevive a um `PUT` de corpo antigo | Major | Feita em `99556ce`; P12, P12n, X09 e X10 morrem |
| FT3: editar e iniciar processo com `TITULACAO_INSUFICIENTE` | Minor | Feita em `ff8d45f`; X01, X02, X03, X04 e X08 morrem |
| FT4: extensão do arquivo da norma | Minor | Pulada de propósito; nota de precisão da spec (NBASE-06 diz só "não é PDF ou passa de 20 MB"), mutante U10 sem efeito na spec; não é lacuna. Registrada na seção "Volta 2" |
| FT5: rastreabilidade e precisão da spec | Minor, docs | Feita em `3326845` e `7b06e61` (NTIT-01, Coverage, NTIT-02, NMOV-05 e seu teste independente). NMOV-01 (dizer onde as telas e os documentos leem os seis campos) não foi alterado: nota de precisão, sem efeito no comportamento |
| FT6: fixture de `ProcessStep1.test.tsx` | Minor | Feita em `7a18482`; X12, X13 e X14 morrem |

---

## Requirement Traceability Update

Verificação concluída (PASS na volta 2). Todos os 36 requisitos de `Implemented` para `Verified`; NTIT-01 já está `Implemented` desde `3326845`. A mudança das linhas de `spec.md` para `Verified` não foi feita por este Verifier (o escopo da volta 2 não inclui `spec.md`); fica para o orquestrador, junto do fechamento da feature.

---

## Summary

**Overall**: ✅ Ready (volta 2 de 3)

**Spec-anchored check**: 36/36 requisitos com evidência `arquivo:linha` e a asserção no valor da spec; 2 notas de precisão que não são lacunas (NBASE-06: a extensão `.pdf` vai além do texto, mutante U10; NMOV-01: requisito negativo sem indicar onde os campos são lidos)
**Sensor**: volta 1: 73/78 mortos; volta 2: 19/20 mortos, os 2 sobreviventes reais da volta 1 (T03, P12) agora mortos; 1 sobrevivente (X15, ordem dos grupos de severidade) sem requisito nesta feature; sobreviventes da volta 1 que ficam: S04 e P07 (equivalentes) e U10 (nota de precisão)
**Gate**: backend 5675 passando, 0 falhas, `ruff` limpo; frontend 668 passando, lint e build verdes

**What works**: toda a regra nova está certa (severidade e texto do salto, titulação, validação de norma, arquivo, versão otimista, 403, seed idempotente e auditado, citação em cada alerta e no mínimo, frontend), e as seis correções da volta 1 fecharam as lacunas sem tocar código de produção.

**Issues found**: nenhum aberto. Notas: NBASE-06 (extensão `.pdf`, U10) e NMOV-01 (precisão do texto).

**Next steps**: orquestrador marca os requisitos como `Verified` em `spec.md`; push e deploy só com a autorização do usuário.

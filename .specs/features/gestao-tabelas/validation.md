# Gestão das tabelas de pontuação (gestao-tabelas) Validation

**Date**: 2026-11-23
**Spec**: `.specs/features/gestao-tabelas/spec.md` (45 requisitos GTAB-01..45), com as Assumptions, os Edge Cases, `design.md` (emendas A1 a A13), AD-028 e `CLAUDE.md`
**Diff range (rodada 1)**: `fa052e0..723e43c` (HEAD da implementação), branch `feat/inteligencia-documental`: 37 commits (T1 a T37, um por tarefa), 70 arquivos, +10366 −562 (código de produção e testes em 30 arquivos de `backend/app` e `frontend/src`: +3297 −277). Mais, depois da implementação, o commit de testes `8538269` desta verificação (só um arquivo novo de teste).
**Verifier**: três agentes independentes (autor diferente; lentes backend, frontend com renderização e transversal com ensaio de deploy), consolidados por um quarto agente que refez as verificações que importam (abaixo, "Reverificação"). Nenhum leu `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt`, `test/`, `backend/img/`, `AcessoVM.txt` nem `.env`; sem push, deploy, VM nem banco de produção; só dados sintéticos. Sensores em worktree isolado e em cópia sob o scratchpad (nunca `git stash`, nunca a árvore real). `git status --porcelain` da árvore real antes e depois da lente transversal: igual (`?? .claude/`, `?? backend/img/`, `?? requeriment.txt`, `?? test/`). As lentes backend e frontend não puderam rodar `git` na árvore real (o sandbox recusa); o frontend registrou um instantâneo de 833 arquivos (nome, mtime, tamanho) idêntico antes e depois, e o backend não escreveu na árvore real. O consolidador só escreveu este relatório e o arquivo de teste de `8538269`.

**Result**: PASS

**Round 1 verdict**: FAIL (rodada 2 no fim deste arquivo: PASS, seção "Round 2"; o registro da rodada 1 fica abaixo)

**Diff range (rodada 2)**: `fa052e0..HEAD` (`HEAD` = o commit de testes `175de9b`, mais o de comentários `6e147b4` e o commit desta verificação), branch `feat/inteligencia-documental`: 74 arquivos, +11576 −579 até `6e147b4`.

---

_Registro da rodada 1 (FAIL), mantido sem alteração de conteúdo:_

Os 45 requisitos têm teste com `arquivo:linha`, e o comportamento do código confere com a spec em 43 deles, **com duas exceções confirmadas**: o GTAB-26 (a reabertura da versão anterior é deduzida das datas, e não do fechamento que a spec manda desfazer) e o GTAB-38 (três botões da tela têm 32 px, abaixo dos 44 px exigidos). O roteiro de deploy tem ainda um passo de volta que não funciona (`docs/deploy/vm.md`). O sensor deixou 5 mutantes válidos vivos depois dos três que o consolidador fechou com testes novos. Por isso o veredito é FAIL, com 3 tarefas de correção de produção e documentação (F1 a F3), tarefas de teste (F6, F7, F9) e as menores (F8, F10 a F14); F4 já está feito. A rodada de re-verificação vem depois delas.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 a T37 (Fase 1 a 6: banco e domínio, casos de uso, API, semente, frontend, documentação) | Done | 37 commits `0b63e33..723e43c`, um por tarefa, todos com `Co-Authored-By: Claude Sonnet 5.5`; a mensagem de cada um confere com a linha `Commit:` de `tasks.md`; nenhum adiciona `backend/img`, `requeriment.txt`, `test/`, `.env` nem arquivo de `Documentos/` ou `Modelos/`; a varredura das linhas novas não achou credencial |
| T38 (Verifier) | Done (rodada 2) | rodada 1: FAIL; rodada 2: PASS (seção "Round 2") |

**Test integrity**: nenhum arquivo de teste apagado (`git diff --diff-filter=D` vazio). Dois testes do frontend saíram de `ScoringAdmin.test.tsx` por decisão da spec (GTAB-15, a tela deixou de ser só do ADMIN: "SECRETARIA e DOCENTE são redirecionados" virou "veem o link e a lista" e o teste do ADMIN foi ampliado). Nenhum teste de backend removido. Asserções não foram enfraquecidas nas áreas tocadas (conferido pela lente transversal no diff).

---

## Spec-Anchored Acceptance Criteria

Caminhos relativos a `backend/tests/` (b/) e `frontend/src/` (f/). Os mutantes citados (M) estão na tabela do sensor. As lentes numeraram os mutantes por conta própria: `Mb` é da lente backend e `Mf` da lente frontend. "Duas metades" quer dizer que o requisito tem parte no backend e parte no frontend, e as duas foram conferidas.

### P1: Tabela em uso por unidade (GTAB-01 a GTAB-10)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-01 | uma só marcação por unidade | `b/integration/scoring/test_unit_defaults.py:81` (trocar a marcação deixa uma linha), `:244` (duas marcações concorrentes: `SELECT count(*) = 1`); `b/integration/test_scoring_repositories.py:434`; `b/integration/test_migration_unit_defaults.py:57` (a chave do banco recusa a 2ª) | PASS |
| GTAB-02 | só o ADMIN marca; evento `CREATE`/`UPDATE` com usuário e `{version_id:{before,after}}`; marcar a mesma de novo não grava evento | `b/integration/scoring/test_unit_defaults.py:67`, `:81`, `:96`, `:137`, `:149`; API `b/integration/api/test_scoring_admin_api.py:546` (resposta `{unit_id, version_id}`), `:150`; frontend `f/pages/ScoringAdmin.test.tsx:684` (uma unidade: `PUT /api/scoring-units/u1/default-version` com `{version_id}` na hora), `:729` (duas unidades: diálogo); Mb05, Mb08, Mb11, Mb16, Mf14, Mf15 mortos | PASS |
| GTAB-03 | 422 em `unit_id` (tabela não associada, unidade inexistente ou arquivada); 409 versão substituída; 409 tabela arquivada | `b/integration/scoring/test_unit_defaults.py:183`, `:164`, `:171`, `:192`, `:205`; API `:581`, `:590`, `:602`, `:613`; Mb05, Mb07, Mb64 mortos | PASS; o código tem uma precedência que a spec não diz (⚠️ spec-precision, abaixo) |
| GTAB-04 | desmarcar com auditoria `DELETE` e `before`; a sugestão volta à vigência | `b/integration/scoring/test_unit_defaults.py:112`, `:130`; API `:559` (204 duas vezes); aceitação `b/integration/api/test_gestao_tabelas_acceptance.py:77`; frontend `f/pages/ScoringAdmin.test.tsx:708` (`DELETE`, selo some); Mb12b, Mb14, Mb15 mortos | PASS; o bloqueio da unidade (`lock_unit`) no desmarcar só fica preso depois de `8538269` (Mb13, ver F4) |
| GTAB-05 | a marcação vence uma versão válida mais nova; a sugestão não é aplicada ao processo | `b/integration/scoring/test_table_choice.py:284`, `:296`; aceitação `:77`; Mb01 morto | PASS |
| GTAB-06 | marcação inválida (substituída, arquivada, unidade fora) cai para a vigência; sem marcação, vigência | `b/integration/scoring/test_table_choice.py:320`, `:329`, `:352`; unitários `b/unit/domain/test_scoring_table_choice.py:108`, `:113`, `:117`; Mb02, Mb03, Mb04, Mb62 mortos | PASS |
| GTAB-07 | marcação fora de vigência é sugerida sem alerta; `TABELA_FORA_DE_VIGENCIA` só ao confirmar | `b/integration/scoring/test_table_choice.py:306`; `b/unit/domain/test_scoring_table_choice.py:99`; Mb55 morto | PASS |
| GTAB-08 | processo com tabela escolhida não muda; documento gerado não muda | `b/integration/scoring/test_table_choice.py:384`, `:398`; aceitação `b/integration/api/test_gestao_tabelas_acceptance.py:77` (JSON da pontuação, lista de geração e sha256 do PDF iguais) | PASS |
| GTAB-09 | a semente marca FASI e IFCH uma vez, com evento do sistema; não refaz, não remarca unidade desmarcada nem sem a tabela oficial | `b/integration/test_seed_scoring.py:448`, `:452`, `:467`, `:481`, `:498`, `:513`, `:546`, `:559`, `:393`; Mb39, Mb60, Mb67 mortos; ensaio de deploy (abaixo) | PASS; a perna "nenhuma versão em uso" não tem teste próprio (Mb66 vivo, F7) |
| GTAB-10 | a lista traz `default_for_unit_ids`, `process_count` e `in_use` com o sentido antigo | `b/integration/api/test_scoring_tables_api.py:199`, `:221`, `:263`; frontend `f/pages/ScoringAdmin.test.tsx:146`, `:159`; Mb45, Mb56, Mb57, Mf08, Mf29 mortos | PASS |

### P1: Gestão pela tela (GTAB-11 a GTAB-17)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-11 | criar tabela: `POST` com nome, unidades, situação, início e norma; 422 ao lado do campo | `f/components/ScoringTableDialogs.test.tsx:90`, `:117`, `:146`, `:167`; `f/pages/ScoringAdmin.test.tsx:481`; Mf51 morto | PASS |
| GTAB-12 | nova versão: `POST /versions` com `source_version_id`; 409 como mensagem da API | `f/pages/ScoringAdmin.test.tsx:567`, `:596`, `:550`; `f/components/ScoringAdminForms.test.tsx:57`, `:92` | PASS |
| GTAB-13 | importar CSV: erros do arquivo listados, só o `POST` de importação | `f/pages/ScoringAdmin.test.tsx:622`; `f/components/ScoringAdminForms.test.tsx:125`, `:147`, `:171` | PASS |
| GTAB-14 | unidades da tabela: `PUT /units`, diálogo fecha e lista recarrega | `f/pages/ScoringAdmin.test.tsx:519`; `f/components/ScoringTableDialogs.test.tsx:222`, `:234` | PASS; o ramo das unidades "desconhecidas" não tem teste (Mf52 vivo, F7) |
| GTAB-15 | leitura para qualquer perfil; escrita só do ADMIN (403) | backend `b/integration/api/test_scoring_admin_api.py:150`, `:163`; frontend `f/pages/ScoringAdmin.test.tsx:241` (SECRETARIA e DOCENTE veem a lista), guardas reais `:475`, `:513`, `:660`, `:817`, `:909`, `:1005`, `:1071`, `:1106`, `f/components/VersionRow.test.tsx` e `ScoringTableCard.test.tsx`; Mf01, Mf02c, Mf03, Mf24, Mf25 mortos; renderização como SECRETARIA a 360 e 1280 px: só "Ver critérios" | PASS; as três asserções negativas de `ScoringAdmin.test.tsx:251` usam nomes de botão que não existem (vazias, F9) |
| GTAB-16 | cada diálogo termina com texto de estado e recarrega a lista sem recarregar a página | `f/pages/ScoringAdmin.test.tsx:456`, `:481`, `:519`, `:567`, `:684`, `:951`; Mf35, Mf48 mortos | PASS |
| GTAB-17 | histórico por tabela com data, autor, ação e mudança, sem UUID | `f/components/ScoringTableDialogs.test.tsx:427`, `:437`, `:456`; `f/pages/ScoringAdmin.test.tsx:1082`, `:1106`; Mf20, Mf20b mortos | PASS |

### P1: Editar critérios (GTAB-18 a GTAB-22)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-18 | `PUT` só com os campos mudados mais `change_reference` | `f/components/CriterionEditDialog.test.tsx:65`, `:112`, `:126`; `f/pages/ScoringAdmin.test.tsx:1024`; Mf12, Mf13, Mf55 mortos | PASS |
| GTAB-19 | versão usada por processo é somente leitura, com a quantidade | `f/pages/ScoringAdmin.test.tsx:1051`; backend `b/integration/api/test_scoring_tables_api.py:311`, `b/unit/domain/test_scoring_table_guards.py:224`, `b/integration/scoring/test_admin_criteria.py:190`, `:244`; Mf26 morto | PASS |
| GTAB-20 | versão substituída ou não mais recente: somente leitura, com o motivo; ordem substituída, não mais recente, usada | `f/pages/ScoringAdmin.test.tsx:1051-1068`; `b/integration/scoring/test_admin_criteria.py:202`, `:221`, `:232`, `:244`; `b/integration/api/test_scoring_tables_api.py:350`, `:366`, `:382`; `b/unit/domain/test_scoring_table_guards.py:208`, `:215`, `:234`; Mb46, Mb74, Mb75 mortos | PASS; ⚠️ spec-precision: "a versão que a substitui" não diz se a tela nomeia a versão (a tela diz "foi substituída por outra") |
| GTAB-21 | erro 422 ao lado do campo, valor digitado mantido; 409 como texto | `f/components/CriterionEditDialog.test.tsx:165`, `:185`; `f/components/formKit.test.tsx:75` | PASS |
| GTAB-22 | depois de salvar, a linha mostra o valor novo sem recarregar a página | `f/pages/ScoringAdmin.test.tsx:1024-1049` (`12,00`, uma só leitura de tabelas e de versão) | PASS |

### P1: Arquivar e excluir (GTAB-23 a GTAB-32)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-23 | arquivar e desarquivar com auditoria `ARCHIVE`/`UPDATE`, sem justificativa | `b/integration/scoring/test_admin_archive.py:45`, `:59`, `:72`; API `:671`; frontend `f/pages/ScoringAdmin.test.tsx:829`, `:852`; Mb20, Mb61, Mf19, Mf47 mortos | PASS |
| GTAB-24 | arquivada: fora da sugestão, da escolha da Etapa 4 e da marcação; leitura e cálculo dos processos que a usam seguem | `b/integration/scoring/test_table_choice.py:370`, `:434`, `:446`, `:458`, `:469`; `b/integration/test_scoring_repositories.py:542`; `b/integration/scoring/test_unit_defaults.py:205`; frontend `f/pages/ProcessScoring.test.tsx:570`; Mb22, Mb23, Mb62, Mf50 mortos | PASS |
| GTAB-25 | arquivar com versão em uso: 409 com as siglas, nada gravado | `b/integration/scoring/test_admin_archive.py:89`, `:105`; API `b/integration/api/test_scoring_admin_api.py:692`; frontend `f/pages/ScoringAdmin.test.tsx:829` (texto de estado, sem campo de justificativa); Mb17, Mb65 mortos | PASS |
| GTAB-26 | excluir versão apaga a versão, os grupos e os critérios, mantém a auditoria; **só** se a versão apagada é a mais recente **e tinha fechado** a anterior (ADM-05), devolve à anterior o fim de vigência da apagada | `b/integration/scoring/test_admin_delete_version.py:92`, `:107`, `:129`, `:140`, `:153`, `:166`, `:185`; Mb29, Mb72, Mb73, Mb75, Mb76 mortos; `b/integration/scoring/test_admin_lock_and_boundary_gaps.py` (nesta verificação): meio da fila não reabre (Mb71 morto), e o teste xfail do defeito | ❌ GAP confirmado (F1): a reabertura vem de `valid_to == dia anterior`, sem conferir que a versão apagada fechou a anterior; ver "Reverificação" |
| GTAB-27 | versão usada por processo, em uso de unidade, que substitui outra ou única: 409 com o motivo, a contagem e nada apagado | `b/integration/scoring/test_admin_delete_version.py:201`, `:215`, `:227`, `:241`, `:252`, `:271`; `b/unit/domain/test_scoring_table_guards.py:78-136`; API `:763`; frontend `f/pages/ScoringAdmin.test.tsx:921`, `f/components/DeleteScoringDialog.test.tsx:78`; Mb25, Mb26, Mb27, Mb28, Mb30 mortos | PASS; o bloqueio da tabela (`lock_table`) da exclusão da versão só fica preso depois de `8538269` (Mb47, F4) |
| GTAB-28 | excluir tabela apaga tabela, versões, grupos, critérios e associações numa transação | `b/integration/scoring/test_admin_delete_table.py:108`, `:179`, `:191`, `:292`; `b/integration/test_scoring_repositories.py:566`, `:657`, `:673`; Mb34, Mb54 mortos | PASS |
| GTAB-29 | tabela com versão usada, em uso ou oficial: 409 (`TABELA_OFICIAL_PROTEGIDA`), nada apagado | `b/integration/scoring/test_admin_delete_table.py:212`, `:230`, `:201`, `:363`; API `:745`, `:787`; frontend `f/pages/ScoringAdmin.test.tsx:921-949`, `f/components/DeleteScoringDialog.test.tsx:203`; Mb31, Mb32, Mb33 mortos | PASS |
| GTAB-30 | prévia antes de excluir (nome, versões, critérios, unidades, bloqueios); botão habilitado só depois dela | `b/integration/scoring/test_admin_delete_table.py:255`, `:269`, `:282`; `b/integration/scoring/test_admin_delete_version.py:291`, `:301`, `:320`; API `:813`, `:835`; frontend `f/components/DeleteScoringDialog.test.tsx:37`, `:168`, `:190`, `:113`, `:152`; Mb69, Mb70, Mf16, Mf17, Mf18, Mf53, Mf54 mortos | PASS |
| GTAB-31 | toda escrita é só do ADMIN (403), nada muda | `b/integration/api/test_scoring_admin_api.py:150` (as 15 escritas), `:163` (401); casos de uso `b/integration/scoring/test_admin_archive.py:127`, `test_admin_delete_version.py:280`, `test_admin_delete_table.py:244`, `test_unit_defaults.py:137`; CSRF global `presentation/csrf.py`; Mb15, Mb16, Mb21, Mb51, Mb52 mortos | PASS |
| GTAB-32 | auditoria de excluir com usuário e `before` com nome, versões, critérios e unidades | `b/integration/scoring/test_admin_delete_table.py:132`, `:166`; `b/integration/scoring/test_admin_delete_version.py:107`; aceitação `b/integration/api/test_gestao_tabelas_acceptance.py:77`; Mb35, Mb36 mortos | PASS |

### P1: Lista legível e com ações visíveis (GTAB-33 a GTAB-40)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-33 | um cartão por tabela, versões em sub-cartões, siglas (nunca ids), sem `<table>` | `f/pages/ScoringAdmin.test.tsx:128`, `:202`, `:211`; Mf10 morto; renderização: 3 cartões, 0 `<table>` nos cartões a 360 e 1280 px | PASS; ⚠️ spec-precision: "destacar a versão em uso" é só um selo verde |
| GTAB-34 | vigência `dd/mm/aaaa a dd/mm/aaaa`, selos "Em uso (sigla)", "Usada por processo", "Substituída", "Arquivada", "Pendente de validação", "Encerrada" | `f/pages/ScoringAdmin.test.tsx:128`, `:146`, `:159`, `:184`; Mf08, Mf09, Mf29, Mf30, Mf38, Mf45 mortos | PASS; "Encerrada" aparece em versão que não está em uso? Ninguém testa (Mf37 vivo, F7) |
| GTAB-35 | botões com texto, um por operação, o objeto da operação no `aria-label` | `f/pages/ScoringAdmin.test.tsx:261`, `:474-1010`; `f/components/ScoringTableCard.test.tsx`; renderização: os 14 rótulos com texto a 360 e 1280 px | PASS |
| GTAB-36 | ação bloqueada fica desabilitada com o motivo em texto visível ou descrição acessível; a API traz os motivos | `f/components/VersionRow.test.tsx` (`aria-disabled`, `aria-describedby`, clique não chama a ação); `b/integration/api/test_scoring_tables_api.py:311`, `:330`, `:350`, `:366`, `:382`, `:401`, `:414`, `:425`; Mb46, Mb56, Mf04, Mf05 mortos | PASS; a spec diz "desabilitado" e a tela usa `aria-disabled` (⚠️ spec-precision) |
| GTAB-37 | filtro por unidade; arquivadas escondidas por padrão | `f/pages/ScoringAdmin.test.tsx:317`, `:330`; Mf06, Mf07, Mf19, Mf32 mortos | PASS |
| GTAB-38 | 360 px sem rolagem horizontal, sem palavra em letras isoladas, versões empilhadas, botões por teclado, alvo de toque de **pelo menos 44 px** | estático `f/styles.test.ts:296-386` (quebra de palavra, `flex-wrap`, `min-height >= 2.75rem` só em `.tbl-actions .btn`, `.modal .btn`, `.tbl-edit`, `.tbl-filter-archived`); Mf21, Mf22, Mf23, Mf27, Mf28, Mf33, Mf42 mortos; renderização: sem rolagem e sem quebra em letras a 360 e 1280 px, **mas "Nova tabela", "Limpar filtros" e "Tentar de novo" medem 32 px** | ❌ GAP confirmado (F2): `styles.css:526-531` dá `min-height: 2rem` ao `.btn` e os três botões não têm a classe que sobe para 44 px; nenhum teste os cobre |
| GTAB-39 | carregando, erro com "Tentar de novo" e recarga | `f/pages/ScoringAdmin.test.tsx:365`, `:373`; renderização do erro a 360 e 1280 px | PASS (o botão tem os 32 px do F2) |
| GTAB-40 | vazio: mensagem e "Limpar filtros" que restaura os filtros | `f/pages/ScoringAdmin.test.tsx:348`; Mf31 morto; renderização do vazio a 360 px | PASS (o botão tem os 32 px do F2) |

### P1: Coerência com a semente e com as outras regras (GTAB-41 a GTAB-45)

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| GTAB-41 | a semente não re-arquiva nem desassocia tabela antiga que uma pessoa já mexeu | `b/integration/test_seed_scoring.py:589`, `:606`, `:620`, `:634`, `:651`; aceitação `:77`; Mb40, Mb41 mortos | PASS; ⚠️ spec-precision: "alterou" vale só para eventos da entidade tabela com usuário (a spec fala de qualquer alteração) |
| GTAB-42 | a tabela oficial e a versão atual dela são protegidas de exclusão (mas arquivar e marcar valem); desde 2026-11-23 (A14) as versões substituídas da oficial podem ser excluídas | `b/integration/scoring/test_admin_delete_table.py:201`; `b/integration/scoring/test_admin_delete_version.py:252`, `:271`; API `:745`; `b/integration/api/test_scoring_tables_api.py:401`; Mb30, Mb33 mortos | PASS |
| GTAB-43 | tirar a unidade que tem a versão em uso: 409 `UNIDADE_COM_VERSAO_EM_USO` com as siglas, unidades inalteradas | `b/integration/scoring/test_admin_units.py:38`, `:52`, `:67`, `:78`, `:117`, `:145`; frontend `f/components/ScoringTableDialogs.test.tsx:246`, `:272`; Mb06, Mb37, Mb38, Mb68, Mb77, Mf34 mortos | PASS |
| GTAB-44 | escolher versão de tabela arquivada: 409 `TABELA_ARQUIVADA`, com a exceção da versão que o processo já tem | `b/integration/scoring/test_table_choice.py:434`, `:446`, `:458`, `:479`; API `b/integration/api/test_scoring_process_api.py:168`; Mb22, Mb23, Mb24 mortos | PASS |
| GTAB-45 | a norma (`norm_code`) oficial não é copiada ao duplicar nem ao criar versão em outra tabela | `b/integration/scoring/test_admin_create.py:224`, `:235`; `b/integration/scoring/test_admin_versions.py:220`, `:227`; Mb43, Mb44 mortos | PASS |

### Casos de borda (spec e design)

| Caso | Evidência | Resultado |
| ---- | --------- | --------- |
| Versão em uso que um versão nova encerra | `b/integration/scoring/test_table_choice.py:398` (a marcação fica na antiga, sugerida, `FORA_DE_VIGENCIA` só ao confirmar) | PASS |
| Substituição desfaz a marcação | `b/integration/scoring/test_adopt_superseding_version.py:234`, `:250`, `:260`, `:271`, `:278`; Mb42, Mb63 mortos | PASS |
| Marcação concorrente | `b/integration/scoring/test_unit_defaults.py:244`, `:280` (duas transações reais, espera em `pg_stat_activity`) | PASS |
| Exclusão de tabela atômica | `b/integration/scoring/test_admin_delete_table.py:292`, `:363`; Mb54 morto | PASS |
| Desarquivar não remarca | `b/integration/scoring/test_admin_archive.py:118`; aceitação `:77`; Mb18 morto | PASS |
| Nome repetido (sem diferenciar caixa nem espaços) | `b/integration/scoring/test_admin_create.py:82`, `:186`; API `b/integration/api/test_scoring_admin_api.py:127`, `:209`; Mb58, Mb59 mortos | PASS |

### Histórias (teste de aceitação independente)

`b/integration/api/test_gestao_tabelas_acceptance.py:77` percorre marcar, sugerir sem aplicar, trocar a marcação, recusar arquivar, arquivar/desarquivar, prévia e exclusão de versão e de tabela com 409 nos bloqueados, reinício da semente (a unidade desmarcada continua desmarcada, a tabela antiga continua como está) e conferência de que o processo existente, o JSON da pontuação e o PDF (sha256) não mudaram. PASS. Papéis: `:275`.

**Status**: ❌ Gaps presentes (GTAB-26, GTAB-38) e ⚠️ spec-precision gaps (abaixo).

---

## Reverificação das afirmações dos três relatórios

O consolidador abriu o código e o teste de cada afirmação de gravidade alta e dos sobreviventes antes de registrá-los.

| Afirmação | Origem | Resultado da reverificação |
| --------- | ------ | -------------------------- |
| A reabertura da versão anterior é deduzida das datas (GTAB-26) | transversal, "major" | **Confirmada.** `backend/app/application/use_cases/scoring_admin.py:950-983` (`_reopen_previous`): reabre a anterior sempre que `valid_to == valid_from - 1 dia` e não há versão posterior; não confere que a versão apagada fechou a anterior no `close_open_version` (`:567-593`, que só fecha uma versão **aberta**). Reproduzi o caso em teste (`b/integration/scoring/test_admin_lock_and_boundary_gaps.py`, `test_deleting_the_latest_does_not_reopen_a_previous_version_the_admin_ended_himself`): V1 de 2020-01-01 a 2023-12-31, V2 de 2024-01-01 criada sem fechar nada, V2 apagada; sem o `xfail`, `assert None == datetime.date(2023, 12, 31)` falha. O teste fica como `xfail(strict=True)` até a correção F1. Gravidade major: muda a vigência de uma versão que processos podem usar, com evento de auditoria que descreve um fechamento que não houve |
| Três botões de 32 px (GTAB-38) | frontend, "major" | **Confirmada por leitura do CSS e do JSX.** `styles.css:526-531`: `.btn { min-height: 2rem }` (32 px); só `.tbl-actions .btn` (`:1404`), `.modal .btn` (`:1427`), `.tbl-edit` (`:1431`), `.tbl-filter-archived` (`:1296`) e `.tbl-check` (`:1313`) sobem para `2.75rem`. "Nova tabela" (`ScoringAdmin.tsx:161-177`, `btn btn-primary` em `.tbl-page-head`), "Limpar filtros" (`:218-221`, em `.tbl-empty`) e "Tentar de novo" (`:134-139` e `:185-189`) usam só `.btn`. A medida de 32 px em Chrome 146 vem da lente frontend (não repeti a renderização) e `styles.test.ts:296-386` não cobre esses seletores |
| O passo de volta "só a imagem" do deploy falha | transversal, "major" | **Confirmada por leitura e pela repetição da lente transversal.** `docs/deploy/vm.md:362` diz que voltar só a imagem funciona; `git ls-tree fa052e0 backend/alembic/versions` termina em `0011_board_opinion.py`, e a lente transversal registrou `alembic upgrade head` da árvore antiga contra o banco em `0012`: "Can't locate revision identified by '0012'", saída 255, que com `set -eu` do `docker-entrypoint.sh` derruba o contêiner em laço |
| `lock_table` da exclusão de versão sem teste de corrida (Mb47) | backend, "major" | **Confirmada como lacuna de teste, não de produção.** O código está certo (`scoring_admin.py:929`); a sonda da lente backend passa no código e falha sem a trava. Fechada em `8538269` (`test_two_deletions_of_the_two_versions_of_a_table_never_leave_it_without_a_version`, passa; a morte do mutante foi medida pela lente backend com o mesmo texto de teste) |
| `lock_unit` do desmarcar sem teste (Mb13) | backend, minor | Confirmada como lacuna; fechada em `8538269` (`test_clearing_while_another_mark_is_being_written_records_the_version_it_really_removed`) |
| Excluir uma versão do meio não está fixado (Mb71) | backend, minor | Confirmada como lacuna; fechada em `8538269` (`test_deleting_a_middle_version_does_not_reopen_the_first_one`) |
| Mutantes vivos Mb66, Mb10, Mb49, Mf37, Mf52 | backend e frontend | Mf37 e Mf52 conferidos no código: `VersionRow.tsx:73` (`ended = marked.length > 0 && ...`) e `ScoringTableDialogs.tsx:178-179` (ramo das unidades desconhecidas). Os cinco continuam vivos; Mb10 e Mb49 são prováveis travas redundantes (as outras travas e o bloqueio de linha do `DELETE` serializam as mesmas corridas), sem prova de equivalência |
| Possível impasse entre criar versão e excluir a mais recente | transversal, minor | **Plausível por leitura, não reproduzido.** `close_open_version` atualiza a linha da versão aberta (a que a exclusão vai apagar) e depois insere a nova, cuja chave estrangeira pede `FOR KEY SHARE` na linha da tabela; `DeleteScoringVersion` tem `FOR UPDATE` na tabela e quer a versão. Dois ADMIN ao mesmo tempo podem cruzar as travas e receber `40P01` (500, sem mapeamento para 409) |

Afirmações descartadas: nenhuma. O mutante Mb12 (limpar sem marcação gravando evento) e os mutantes Mf02 e Mf02b são equivalentes e foram substituídos por Mb12b e Mf02c pelos próprios autores da verificação.

---

## Discrimination Sensor

Sensor em worktree isolado (backend e frontend) e em cópia sob o scratchpad (transversal); profundidade completa (caminho crítico: auditoria, autorização e integridade dos dados). Cada linha é uma falha de comportamento; `Mb` e `Mf` como acima. As falhas pedidas em T38 (marcação ignorada na sugestão, guarda de arquivada, guarda de substituída, exclusão sem bloqueio, exclusão que apaga versão usada, semente que remarca a desmarcada, semente que re-arquiva tabela tocada, filtro de arquivadas, botão sem motivo, `<table>` de volta) estão todas na lista e todas morreram.

**Backend**: 78 mutantes (Mb01 a Mb77 e Mb12b), 77 válidos (Mb12 equivalente, porque `AuditService.record` descarta o evento sem diferença). A lente somou 70 mortos e 7 vivos, mas só nomeou 6 vivos (Mb10, Mb13, Mb47, Mb49, Mb66, Mb71); a lista nominal é a que vale, então 71 mortos e 6 vivos (a diferença de um na soma da lente é registrada aqui, não resolvida).

**Frontend**: 49 executados, 47 válidos (Mf02 e Mf02b equivalentes), 45 mortos, 2 vivos: Mf37, Mf52.

| Mutante | Falha injetada (arquivo) | Resultado |
| ------- | ------------------------ | --------- |
| Mb01 | `suggest_version` ignora a marcação da unidade | ✅ Morto (`test_table_choice.py::test_the_version_in_use_is_suggested_even_when_a_newer_valid_version_exists`) |
| Mb02, Mb03, Mb04 | `pick_unit_default` sem a guarda de arquivada, de substituída, de unidade fora da tabela | ✅ Mortos (`test_scoring_table_choice.py`) |
| Mb05 | `SetUnitDefaultVersion` sem o 422 de associação | ✅ Morto |
| Mb06 | sem a nova checagem do 422 depois das travas | ✅ Morto (`test_admin_units.py`) |
| Mb07 | ordem dos 409 trocada | ✅ Morto |
| Mb08, Mb09 | sem `lock_unit`, sem `lock_table` ao marcar | ✅ Mortos |
| **Mb10** | sem `lock_version` ao marcar | ❌ **Sobreviveu** (92 testes passam; provável trava redundante) → F6 |
| Mb11, Mb14 | marcar e desmarcar sem auditoria | ✅ Mortos |
| Mb12b | desmarcar sem marca grava evento | ✅ Morto |
| **Mb13** | sem `lock_unit` ao desmarcar | ❌ Sobreviveu nos testes dos autores → ✅ morto por `8538269` (sonda da lente backend) |
| Mb15, Mb16, Mb21, Mb51, Mb52 | sem `require_admin` em desmarcar, marcar, arquivar, excluir versão, excluir tabela | ✅ Mortos |
| Mb17, Mb18, Mb19, Mb20 | arquivar com versão em uso; desarquivar remarca; sem trava; sem auditoria | ✅ Mortos |
| Mb22, Mb23, Mb24 | escolha aceita tabela arquivada; exceção invertida; sem `lock_version` | ✅ Mortos |
| Mb25 a Mb28 | exclusão de versão sem o bloqueio de processo, de unidade, de substituição, de última versão | ✅ Mortos |
| Mb29, Mb72, Mb73, Mb75, Mb76 | reabertura: não devolve o fim, reabre a que não fechou (a de anos de distância), sem auditoria, versão com mesmo início conta como posterior, sem reabrir | ✅ Mortos |
| Mb30 | só a versão corrente da oficial é protegida | ✅ Morto |
| Mb31 a Mb33 | exclusão de tabela sem bloqueio de processo, de unidade, da oficial | ✅ Mortos |
| Mb34, Mb35, Mb36 | exclusão uma a uma (chave própria), auditoria sem `before` | ✅ Mortos |
| Mb37, Mb38, Mb68, Mb77 | `SetTableUnits`: tira a unidade com versão em uso, sem trava, bloqueia por marca de outra tabela, texto sem as siglas | ✅ Mortos |
| Mb39, Mb40, Mb41, Mb60, Mb67 | semente: remarca desmarcada, re-arquiva a tocada, conta evento do sistema, marca unidade sem a oficial, não chama a marcação | ✅ Mortos |
| Mb42, Mb63 | substituição não desmarca, desmarca a nova | ✅ Mortos |
| Mb43, Mb44 | copia `norm_code` ao duplicar e para outra tabela | ✅ Mortos |
| Mb45, Mb46, Mb56, Mb57 | `process_count` só 0/1; ordem dos motivos; `default_for_unit_ids` vazio; `in_use` redefinido | ✅ Mortos |
| Mb47 | sem `lock_table` na exclusão de versão | ❌ Sobreviveu nos testes dos autores → ✅ morto por `8538269` (sonda da lente backend) |
| Mb48, Mb50, Mb53, Mb54 | exclusões sem `lock_version`, sem os travas por versão, com `commit` antes da auditoria | ✅ Mortos |
| **Mb49** | `DeleteScoringTable` sem `lock_table` (as travas por versão ficam) | ❌ **Sobreviveu** (provável trava redundante) → F6 |
| Mb55, Mb58, Mb59, Mb61, Mb62, Mb64, Mb65, Mb69, Mb70, Mb74 | vigência exigida, nome repetido (sem e com caixa), ação `ARCHIVE`, lista de versões sem filtrar arquivada, unidade arquivada aceita, siglas, prévia, versão posterior substituída | ✅ Mortos |
| **Mb66** | a semente sobrescreve unidade com versão em uso, sem evento | ❌ **Sobreviveu** (subsumida pela perna "sem evento anterior"; só alcançável com marca inserida à mão) → F7 |
| Mb71 | reabre a anterior também quando a apagada não é a mais recente | ❌ Sobreviveu nos testes dos autores → ✅ morto por `8538269` (sonda da lente backend) |
| Mf01, Mf02c, Mf03, Mf24, Mf25 | não ADMIN vê botões de versão, barra da tabela, "Nova tabela"; rota só do ADMIN; menu só do ADMIN | ✅ Mortos |
| Mf04, Mf05 | ação desabilitada clicável; motivo sem `aria-describedby` | ✅ Mortos |
| Mf06 a Mf10, Mf19, Mf29, Mf30, Mf31, Mf32, Mf38, Mf45 | filtro, padrão das arquivadas, selos, `<table>` na lista, limpar filtros, contagem | ✅ Mortos |
| Mf12 a Mf18, Mf20, Mf20b, Mf34, Mf35, Mf43, Mf46 a Mf51, Mf53 a Mf55 | `PUT` completo, sem referência, diálogos, exclusão, histórico, unidades, recarga, foco, Etapa 4, validação local | ✅ Mortos |
| Mf21, Mf22, Mf23, Mf27, Mf28, Mf33, Mf42 | CSS: quebra de palavra, `flex-wrap`, largura fixa, alvo de toque dos botões dos cartões e dos diálogos | ✅ Mortos |
| **Mf37** | selo "Encerrada" em qualquer versão com fim passado, não só a em uso | ❌ **Sobreviveu** (os 13 arquivos passam) → F7 |
| **Mf52** | `UnitsDialog` descarta as unidades da tabela que não vêm na lista carregada | ❌ **Sobreviveu** → F7 |

**Sensor depth**: completo (caminho crítico).
**Sensor, rodada 1**: FAIL ❌. Os dois lados somam 124 mutantes válidos (77 + 47). Com os testes dos autores, 8 sobreviveram (Mb10, Mb13, Mb47, Mb49, Mb66, Mb71, Mf37, Mf52) e 116 morreram. Os três testes de `8538269` matam Mb13, Mb47 e Mb71 (medido pela lente backend com o mesmo texto de teste), o que deixa 5 vivos (Mb10, Mb49, Mb66, Mf37, Mf52) e 119 mortos. O sensor não gera F1 e F2, porque são defeitos do comportamento e não de teste: os acharam a sonda de teste e a renderização.

---

## Visual Check

Navegador disponível: Chrome 146 headless (`/usr/bin/google-chrome`) com playwright-core instalado no scratchpad (não no repositório), sobre o build real, servidor estático e JSON sintético (4 tabelas com nomes longos, arquivada, versão em uso, usada por processo, substituída, encerrada e uma referência de 90 caracteres sem espaço). Medido a 360 e a 1280 px como ADMIN e como SECRETARIA, nos estados lista, lista com arquivadas e critérios abertos, diálogo de exclusão, vazio e erro. Capturas em `/tmp/claude-1000/-home-nees-Documents-VSCodigo-ProgressaoFuncionalPiloto/118aba81-5621-4e3f-847f-fa68c56fc9d9/scratchpad/gtab-render/` (`gtab-360.png`, `gtab-1280.png`, `gtab-360-secretaria.png`, `gtab-1280-secretaria.png`, `gtab-360-archived-criteria.png`, `gtab-360-error.png` e as demais).

| Verificação | 360 px | 1280 px |
| ----------- | ------ | ------- |
| `scrollWidth == innerWidth` (ADMIN e SECRETARIA, também com critérios e diálogo abertos) | 360 = 360, ✅ | 1280 = 1280, ✅ |
| Elementos além da janela ou cortados | 0 ✅ | 0 ✅ |
| `<table>` dentro dos cartões | 0 ✅ | 0 ✅ |
| Palavra quebrada letra por letra | nenhuma ✅ (só a referência sintética de 90 caracteres, quebrada por `break-word` em 4 linhas, 2 a 1280 px) | nenhuma ✅ |
| Botões dos cartões e dos diálogos | 44 px ✅ | 44 px ✅ |
| "Nova tabela", "Limpar filtros", "Tentar de novo" | **32 px ❌** | **32 px ❌** |
| Seletor de unidade | 42 px (⚠️ spec-precision: a spec não diz se o `select` conta) | 42 px |
| SECRETARIA | só "Ver critérios" (5 botões), sem "Nova tabela" nem barra de ações, sem rolagem ✅ | igual ✅ |

Defeitos cosméticos sem sobreposição nem texto cortado (F10): o botão bloqueado se alarga até a largura do motivo, o que deixa as linhas irregulares a 1280 px; a 1280 px o `h1` e "Nova tabela" encostam no cartão do filtro; a coluna "Modo" dos critérios mostra o enum cru `POR_UNIDADE` (já existia).

Limite da prova (L-021): `styles.test.ts` é estático e não mede altura de botão; só a renderização achou os três botões de 32 px.

---

## Ensaio de deploy (lente transversal)

Estado de produção reproduzido num Postgres descartável com a árvore `fa052e0` em `0011` (FASI, IFCH, a tabela oficial com a versão substituída e a do Grupo I, duas tabelas antigas arquivadas, um processo em rascunho e um concluído). A árvore nova rodou `alembic upgrade head` e o `seed` três vezes, e o `docker-entrypoint.sh` real uma vez. Resultado: `0012`; a semente gravou exatamente 2 eventos (`unit_scoring_default`, `CREATE`, sem usuário, `before` nulo, `after` a versão do Grupo I) e marcou FASI e IFCH; tabelas, versões e `norm_code` não mudaram; os dois processos mantiveram versão e situação; as tabelas antigas continuaram arquivadas e sem unidades; reinícios deixaram o instantâneo idêntico (diff vazio). O contêiner chegou a "Application startup complete" (o bind do uvicorn falhou só porque a porta 8000 estava ocupada na máquina). A volta só da imagem antiga contra o banco em `0012` falha (F3).

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Mínimo de código, sem funcionalidade além da pedida | ✅ |
| Mudanças cirúrgicas | ✅ (`TablePicker` e `ProcessScoring` não leem `in_use`; os campos novos são aditivos; `PUT .../scoring/table` ganhou o 409 `TABELA_ARQUIVADA`, coberto) |
| Segue os padrões existentes | ⚠️ `presentation/dependencies.py:146` importa a função privada `_official_table_data` de `seed.py` (F11) |
| Asserções iguais ao resultado definido pela spec | ✅ nos 43 PASS; ⚠️ nos pontos da seção "Spec-precision" |
| Cobertura por camada (domínio 1:1, rotas feliz, borda e erro) | ✅ as 15 escritas têm 403 e 401; cada guarda tem teste unitário e de integração |
| Todo teste mapeia um requisito, borda ou "Done when" | ✅ |
| Diretrizes documentadas | `CLAUDE.md` regras 1, 5, 9, 11 e 12 seguidas (sem justificativa nas escritas, sem IA, só a tabela oficial); o nome dos testes com outra tabela declara "Sintética" nos dados e nos docstrings, não no nome da função (não verificável por máquina) |

Outros achados de qualidade (menores, F11 a F14): `TableOut` é usado nas respostas de escrita sem os motivos de bloqueio (sempre nulos nelas, a tela recarrega a lista e não é afetada); `today` do selo "Encerrada" vem de `toISOString()` em UTC (em Belém, das 21h às 24h o selo aparece cerca de 3 horas antes); `ScoringAdminForms.tsx` exporta só três diálogos e o nome ficou largo; `AD-028` ainda diz GTAB-01 a GTAB-40.

---

## Gate Check

- **Comando (tasks.md, nível Build)**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run`
- **Execuções dos autores (T37, não repetidas por este Verifier em suíte inteira)**: backend **6728 passed**; frontend **916 passed**.
- **Execuções dos verificadores (direcionadas, nunca a suíte inteira)**: backend, 19 arquivos de escolha, administração, API, semente e migração: 396 passed em 159 s; transversal: 110 + 126 passed e 23 passed nas sondas; frontend: 245 passed (13 arquivos) e 242 passed (11 arquivos), `eslint` e `tsc --noEmit` limpos, `npm run build` ok no worktree.
- **Execução do consolidador depois de `8538269`**: `ruff check` do arquivo novo sem erro; `pytest -q tests/integration/scoring/test_admin_lock_and_boundary_gaps.py`: 3 passed, 1 xfailed (estrito). O total de backend passa a 6731 passed e 1 xfailed.
- **Contagem antes da feature**: não medida (nenhum teste foi apagado; ver "Test integrity"). Depois: backend 6728 (autores) mais 3 e 1 xfailed; frontend 916.
- **Pulos**: nenhum novo.
- **Falhas**: nenhuma nos gates dos autores; o `xfail` estrito é o defeito F1 confirmado.

---

## Fix Plans

Ordem de prioridade (as gravidades são a do consolidador depois da reverificação). Máximo de 3 voltas de correção e verificação.

### F1 (major, confirmado): a reabertura da versão anterior é deduzida das datas (GTAB-26)

- **Causa**: `DeleteScoringVersion._reopen_previous` (`backend/app/application/use_cases/scoring_admin.py:950-983`) reabre a anterior sempre que seu `valid_to` é o dia anterior ao início da apagada; a spec manda reabrir só quando a apagada "tinha fechado" a anterior (ADM-05, `close_open_version` `:567-593`). Um ADMIN que encerrou a V1 em 31/12/2023 e criou a V2 em 01/01/2024 vê a V1 virar aberta (ou tomar o fim da V2) ao apagar a V2, com evento de auditoria de um fechamento que não houve.
- **Tarefa**: registrar no evento `CREATE` da versão nova qual versão ela fechou (por exemplo `closed_previous_id` em `changes`) ou ler o evento `UPDATE valid_to None -> dia anterior` gravado na mesma criação, e reabrir só então; remover o `xfail` de `test_deleting_the_latest_does_not_reopen_a_previous_version_the_admin_ended_himself`; manter os testes de `test_admin_delete_version.py:140`, `:153`, `:166`, `:185`. Precisar o GTAB-26 na spec ("como se detecta que fechou").
- **Verify**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest tests/integration/scoring/test_admin_delete_version.py tests/integration/scoring/test_admin_lock_and_boundary_gaps.py tests/integration/scoring/test_admin_versions.py -q`.
- **Done when**: o teste xfail passa sem marca; os cinco testes de reabertura existentes passam; mutante "reabre sem conferir o fechamento" morre.

### F2 (major, confirmado): três botões de 32 px (GTAB-38)

- **Causa**: `frontend/src/styles.css:526-531` (`.btn` com `min-height: 2rem`) e `:1404`, `:1427`, `:1431` sobem para `2.75rem` só em quatro seletores; "Nova tabela" (`ScoringAdmin.tsx:161-177`), "Limpar filtros" (`:218-221`) e os dois "Tentar de novo" (`:134-139`, `:185-189`) ficam fora.
- **Tarefa**: `min-height: 2.75rem` em `.tbl-page-head .btn`, `.tbl-empty .btn` e no botão de erro (uma regra para os três, ou subir o `.btn` global só nesta tela); estender `styles.test.ts` (GTAB-38) para os três seletores e, de preferência, uma conferência por renderização dos botões nos três estados (lista, vazio, erro).
- **Verify**: `cd frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run src/styles.test.ts src/pages/ScoringAdmin.test.tsx`, mais medida a 360 e 1280 px num navegador sem cabeça.
- **Done when**: os três botões medem 44 px nos dois tamanhos; o teste falha com `min-height` de 2rem em cada um dos três seletores.

### F3 (major, confirmado): o passo "voltar só a imagem" do deploy não funciona

- **Causa**: `docs/deploy/vm.md:362`: com `alembic_version` em `0012`, a imagem anterior (sem a revisão `0012`) falha em `alembic upgrade head` e o contêiner entra em laço de reinício (`set -eu`).
- **Tarefa**: reescrever a seção: voltar exige antes `alembic downgrade 0011` com a imagem nova (remove `scoring_unit_defaults` e as marcações) e só então trocar as etiquetas das imagens, ou restaurar o dump; dizer que a imagem anterior se recusa a subir com `0012`. Ajustar também a lista de comandos de checagem do roteiro.
- **Done when**: o roteiro de volta cobre as duas rotas e está de acordo com o ensaio (`downgrade`, `alembic current` = `0011`, imagem antiga sobe).

### F4 (feito em `8538269`): travas sem teste de corrida (Mb47, Mb13) e meio da fila (Mb71)

Fechados pelos três testes novos de `test_admin_lock_and_boundary_gaps.py`. Fica a rodada 2 para repetir o sensor desses três mutantes sobre o HEAD.

### F6 (minor): travas possivelmente redundantes (Mb10, Mb49)

- **Tarefa**: ou documentar em `scoring_defaults.py` e `scoring_admin.py` que `lock_version` no marcar e `lock_table` na exclusão de tabela são defesa em profundidade (e por que o resto já serializa), ou escrever o entrelaçamento que cada uma cobre (a exclusão da tabela contra `SetTableUnits` e `ArchiveScoringTable`, que só travam a tabela) e provar que o teste falha sem a trava.
- **Done when**: Mb10 e Mb49 mortos ou registrados como equivalentes com argumento.

### F7 (minor): mutantes vivos de comportamento (Mb66, Mf37, Mf52)

- Mb66: um teste de semente com marca inserida direto por `repo.set_unit_default` (sem evento) que a semente deixa como está, ou escrever na spec que a regra do evento é a única.
- Mf37: `ScoringAdmin.test.tsx`, versão não marcada com `valid_to` no passado: `not.toHaveTextContent("Encerrada")` (a versão `FASI_V1` do `MOVED` já serve).
- Mf52: teste do `UnitsDialog` com uma unidade da tabela ausente da lista carregada que continua no corpo do `PUT`, ou apagar o ramo se for inalcançável.

### F8 (minor): possível impasse entre criar versão e excluir a mais recente

- **Tarefa**: `lock_table` no começo de `CreateVersionFrom`, `ImportCriteriaCsv` e do caminho de versão de `CreateScoringTable` (a ordem "unidade, tabela, versão" dita em `scoring_defaults.py` e `ports.py`), ou mapear `DeadlockDetected` para 409 repetível; teste de corrida entre criar versão e excluir a mais recente (copiar `tests/support/races.py`).

### F9 (minor): asserções vazias de GTAB-15

`ScoringAdmin.test.tsx:241-260`: trocar os nomes "Duplicar tabela", "Criar nova versão", "Importar CSV" pelos reais ("Duplicar a tabela …", "Nova versão a partir de …", "Importar CSV para a tabela …") ou por expressão regular, e afirmar que os únicos botões do cartão são "Ver critérios".

### F10 (minor, cosmético): linhas irregulares, `h1` encostado, `POR_UNIDADE` cru

`max-width` na coluna do botão bloqueado, `margin-bottom` em `.tbl-page-head`, `SCORING_MODE_LABELS` na coluna "Modo".

### F11 (minor): o contêiner de dependências importa uma função privada

`presentation/dependencies.py:146`: expor `official_table_name()` em `seed.py` (ou em um módulo de configuração) e importar essa.

### F12 (minor): respostas de escrita sem motivos de bloqueio

`TableOut` nas respostas de `units`, `archive`, `unarchive`, `create` e `duplicate` traz `read_only_reason`, `delete_blocked_reason` e `archive_blocked_reason` sempre nulos: preencher (reaproveitar `_table_view`) ou documentar no OpenAPI que só o GET é confiável.

### F13 (minor): "hoje" em UTC no selo "Encerrada"

`ScoringAdmin.tsx:74`: montar a data pelos componentes locais, ou receber do servidor.

### F14 (minor): documentação

`STATE.md` AD-028 diz "GTAB-01 a GTAB-40" (são 45); GTAB-41 diz "alguma pessoa já alterou" e o código só conta eventos da entidade tabela com usuário (restringir o texto a "desarquivou ou reassociou" ou contar eventos de versão); as linhas de rastreabilidade do GTAB-26/27 não citam A11 e A12, que só estão em `design.md`.

---

## Spec-precision gaps

| Requisito | O que a spec não diz | Como o código ou o teste decidiu |
| --------- | -------------------- | ------------------------------- |
| GTAB-03 | quando a versão está fora da unidade e também arquivada ou substituída, qual erro vence; unidade inexistente ou arquivada no `PUT`; unidade inexistente no `DELETE` | 422 em `unit_id`, depois 409 `VERSAO_SUBSTITUIDA`, depois 409 `TABELA_ARQUIVADA` (`b/integration/scoring/test_unit_defaults.py:217`, `:231`); `PUT` com unidade inexistente ou arquivada dá 422 (`:164`, `:171`); `DELETE` de unidade inexistente dá 204 |
| GTAB-26/27/29 | ordem entre vários bloqueios da mesma exclusão | oficial, processo, unidade, substitui, última (`b/unit/domain/test_scoring_table_guards.py:118`, `:187`) |
| GTAB-10/27 | `process_count` conta processos de todas as situações | `b/integration/test_scoring_repositories.py:481` |
| GTAB-42 | como se identifica a tabela oficial | pelo nome (casefold) lido de `ufpa.json` |
| GTAB-20 | se a tela nomeia a versão que substitui | a tela diz "foi substituída por outra" e o teste confirma esse texto (`f/pages/ScoringAdmin.test.tsx:1051-1068`) |
| GTAB-33 | o que é "destacar" a versão em uso | um selo verde dentro da versão, sem realce do cartão |
| GTAB-36 | "desabilitado" ou `aria-disabled` | `aria-disabled` com `aria-describedby`, focável (`f/components/VersionRow.test.tsx`) |
| GTAB-19 | se quem não é ADMIN vê a orientação de criar nova versão | só o ADMIN vê (`ScoringAdmin.tsx`: `isAdmin && openVersion.read_only_reason`) |
| GTAB-38 | quais controles contam para os 44 px (o `select` mede 42 px) | os botões e as caixas de marcar |
| GTAB-41 | "alguma pessoa já alterou" | evento da entidade tabela com usuário (`backend/app/infrastructure/database/seed.py`) |
| GTAB-26 | como se sabe que a versão apagada fechou a anterior | o código deduz das datas (F1) |

---

## Requirement Traceability Update

A tabela de `spec.md` **não muda** (veredito FAIL): as 45 linhas seguem em `Implemented / Implementing`. Depois das correções F1 a F3 e da rodada 2, passam a `Verified`. Resultado desta rodada por requisito:

| Requisito | Estado anterior | Resultado desta rodada |
| --------- | --------------- | ---------------------- |
| GTAB-01 a GTAB-25 | Implementing | ✅ evidência completa (GTAB-20, 33, 36 e 38 com notas de spec-precision) |
| GTAB-26 | Implementing | ❌ Needs Fix (F1) |
| GTAB-27 a GTAB-37 | Implementing | ✅ evidência completa |
| GTAB-38 | Implementing | ❌ Needs Fix (F2) |
| GTAB-39, GTAB-40 | Implementing | ✅ (botões de 32 px dependem de F2) |
| GTAB-41 a GTAB-45 | Implementing | ✅ evidência completa |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 43 de 45 requisitos com a asserção no resultado que a spec define; 2 gaps (GTAB-26 e GTAB-38); 11 linhas de spec-precision.
**Sensor**: 124 mutantes válidos injetados no backend e no frontend; 119 mortos depois de `8538269` e 5 vivos (Mb10, Mb49, Mb66, Mf37, Mf52): FAIL.
**Gate**: backend 6728 passed e frontend 916 passed (execuções dos autores, não repetidas aqui em suíte inteira); `8538269` acrescenta 3 passed e 1 xfailed.
**Render**: 360 e 1280 px sem rolagem horizontal e sem quebra em letras; 3 botões de 32 px.

**What works**: marcação por unidade com travas e corridas reais, sugestão com recuo para a vigência, arquivar e excluir com prévia, bloqueios com código e auditoria, semente idempotente e fiel ao estado de produção (ensaio de deploy), leitura aberta a todos os perfis e escrita só do ADMIN, e nenhum processo nem documento gerado alterado (AD-012).

**Issues found**: F1 reabertura deduzida das datas; F2 três botões de 32 px; F3 volta de deploy que não funciona; F6 e F7 mutantes vivos; F8 a F14 menores (F4 já fechado em `8538269`).

**Next steps**: executar F1 a F3 (e F6 a F9 se o usuário quiser fechar tudo antes do deploy), repetir o sensor de Mb10, Mb13, Mb47, Mb49, Mb66, Mb71, Mf37, Mf52 e a medida a 360 e 1280 px, e então a rodada 2. Sem push nem deploy sem a autorização do usuário.


---

# Round 2

**Date**: 2026-11-23
**Diff range**: `fa052e0..HEAD`. A rodada 2 verificou `cac86b0` (fim das correções F1 a F14); o consolidador acrescentou dois commits antes deste relatório: `175de9b` (só testes) e `6e147b4` (só dois comentários).
**Verifier**: dois verificadores independentes (lentes backend e frontend com navegador; autor diferente) e um consolidador que reabriu o código e os testes de cada afirmação que decide o veredito. Nenhum leu `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt`, `test/`, `backend/img/`, `AcessoVM.txt` nem `.env`; sem push, deploy nem VM; só dados sintéticos. Sensores em worktrees isolados (detached em `cac86b0`), nunca na árvore real e nunca com `git stash`; o worktree do consolidador foi removido. As lentes não puderam rodar `git status` na árvore real (o sandbox recusa) e usaram uma busca de arquivos mais novos que um marcador, sem achados; o consolidador rodou `git status --short` antes e depois do sensor: só os arquivos de teste e de comentário que ele mesmo comitou, mais `?? .claude/`, `?? backend/img/`, `?? requeriment.txt`, `?? test/`.

## Correções verificadas

Relido pelo consolidador no código (`backend/app/application/use_cases/scoring_admin.py`) e nos testes citados.

| Correção | Estado | Evidência (`arquivo:linha`) |
| -------- | ------ | --------------------------- |
| F1 reabertura (GTAB-26) | Corrigido | `scoring_admin.py:628-636` grava `closed_version_id` no evento `CREATE` só quando a criação fechou de fato a versão aberta; `:976-1022` (`_reopen_previous`) reabre apenas a versão que `_closed_by` nomeia, que não está substituída e termina no dia anterior; o guarda `has_later_version` continua. `backend/tests/integration/scoring/test_admin_lock_and_boundary_gaps.py:128` (admin que encerrou a V1 não vê a V1 reaberta), `:146` (versão vizinha que a apagada nunca fechou), `:109` (meio da fila); `test_admin_delete_version.py` (fim de vigência devolvido, inclusive o `valid_to` explícito). O `xfail` saiu. Uma versão criada antes do registro não reabre nada, o que o GTAB-26 reescrito diz |
| F2 alvos de toque (GTAB-38) | Corrigido | `frontend/src/styles.css`: `min-height: 2.75rem` em `.tbl-page-head .btn`, `.tbl-empty .btn` e `.tbl-retry`; `frontend/src/styles.test.ts` (alvo de toque dos três botões); renderização abaixo: 44 px |
| F3 volta do deploy | Corrigido | `docs/deploy/vm.md:360-376` conferido pela lente backend num banco descartável: `alembic upgrade head` da árvore antiga com o banco em `0012` falha com "Can't locate revision identified by '0012'"; a rota A (`downgrade 0011` com a árvore nova, depois a imagem antiga) deixa o banco em `0011`; a rota B (restaurar o dump) e a troca das etiquetas Docker não foram reproduzidas (precisam da VM real) |
| F6 travas (Mb10, Mb49) | Corrigido, com teste novo do consolidador | Mb49 morto por `test_admin_lock_and_boundary_gaps.py:204`. Mb10 **não é equivalente**: `AdoptSupersedingVersion` (`scoring_adoption.py:31-60`) supersede a versão e limpa as marcas sem trava de tabela. O comentário dos autores (a trava seria só defesa em profundidade) estava incompleto e foi corrigido em `6e147b4`; o teste novo mata o mutante (abaixo) |
| F7 Mf37, Mf52, Mb66 | Corrigido | Mf37: `frontend/src/pages/ScoringAdmin.test.tsx:184`; Mf52: `frontend/src/components/ScoringTableDialogs.test.tsx` ("uma unidade da tabela que não está na lista carregada continua no corpo do PUT"); Mb66: `backend/tests/integration/test_seed_scoring.py` ("a unit that already has a mark keeps it even without any audit event") |
| F8 impasse | Corrigido, com teste novo do consolidador | `CreateVersionFrom` (`scoring_admin.py:675`) e `ImportCriteriaCsv` (`:735`) pegam `lock_table` primeiro (ordem unidade, tabela, versão). O teste de corrida existia só para `CreateVersionFrom` (`test_admin_lock_and_boundary_gaps.py:170`); o da importação é novo (abaixo) |
| F9 asserções de GTAB-15 | Corrigido | `ScoringAdmin.test.tsx`: todo botão do cartão da SECRETARIA e do DOCENTE é "Ver critérios de …" e "Nova tabela" não existe; Mn13a e Mn18 morrem |
| F10 aparência | Corrigido | coluna de ação com `max-width: 16rem`, `margin-bottom` em `.tbl-page-head`, `SCORING_MODE_LABELS` na coluna "Modo"; Mn07, Mn08, Mn11 mortos; renderização sem enum cru |
| F11 função privada | Corrigido | `seed.official_table_name()` pública, importada por `presentation/dependencies.py`; `test_the_public_official_table_name_is_the_name_in_the_seed_file` passa; N18 morto por 7 testes |
| F12 motivos nas respostas | Corrigido para `TableOut` | `GetScoringTable` e `table_out()` nas cinco rotas de escrita da tabela; `test_the_answers_of_the_table_writes_carry_the_same_block_reasons_as_the_list`; N5a a N5e e N12 mortos. As respostas das duas rotas de versão ficam como estão (item "Achados menores" 4) |
| F13 data local | Corrigido, reforçado | `localIsoDate` em `ScoringAdmin.tsx:18-21`; testes de Belém no fim do ano e, novos, no meio do ano (abaixo) |
| F14 documentação | Corrigido | `STATE.md` AD-028 diz GTAB-01 a GTAB-45; GTAB-26 e GTAB-41 do `spec.md` reescritos e conferidos com o código; A11 e A12 nas linhas de rastreabilidade de GTAB-26 e GTAB-27 em `tasks.md` |

## Sensor da rodada 2

Profundidade completa (caminho crítico), em worktrees isolados. Lente backend: 6 mutantes da rodada 1 repetidos (Mb10, Mb13, Mb47, Mb49, Mb66, Mb71) e 20 novos (N1, N2, N2b, N3, N4, N5a a N5e, N7, N8, N11, N12, N17, N18), dos quais 18 válidos. Lente frontend: 18 execuções (2 da rodada 1 e 16 novas), 17 válidas (Mn13b equivalente).

| Mutante | Falha injetada | Resultado |
| ------- | -------------- | --------- |
| Mb13, Mb47, Mb49, Mb66, Mb71 (rodada 1) | `ClearUnitDefaultVersion` sem `lock_unit`; `DeleteScoringVersion` sem `lock_table`; `DeleteScoringTable` sem `lock_table`; a semente sobrescreve a marca; reabre a anterior quando a apagada não é a última | ✅ Mortos (`test_admin_lock_and_boundary_gaps.py` e `test_seed_scoring.py`) |
| N1, N2, N2b, N7 | reabertura por datas de novo; dia errado; `valid_to` sempre aberto; o `CREATE` nunca registra `closed_version_id` | ✅ Mortos (`test_deleting_the_latest_*`, `test_the_previous_version_takes_the_end_of_validity_of_the_deleted_one`) |
| N3, N17 | `CreateVersionFrom` sem `lock_table`; exclusão de versão trava a versão antes da tabela | ✅ Mortos (`:170`, `:204`, `:42`) |
| N5a a N5e, N12 | respostas de criar, duplicar, unidades, arquivar e desarquivar com motivos nulos; catálogo protegido vazio | ✅ Mortos (teste das respostas de escrita) |
| N18 | `official_table_name()` devolve vazio | ✅ Morto (7 testes) |
| N8 | grava a versão aberta como "fechada" mesmo quando a criação não fechou nada | Equivalente: uma versão que não fechou nada ou sobrepõe a aberta (409) ou começa antes e então `has_later_version` é verdadeiro e a exclusão não reabre; não conta |
| N11 | `CreateVersionFrom` ignora o `False` do `lock_table` | Equivalente: `add_version` do repositório levanta o mesmo `NotFound` para tabela inexistente; não conta |
| **Mb10** | `SetUnitDefaultVersion` sem `lock_version` | ❌ Sobreviveu aos 184 testes dos autores; **não equivalente** (a sonda da lente backend e o teste novo falham sem a trava) → morto pelo teste novo `test_admin_lock_and_boundary_gaps.py::test_marking_waits_for_a_concurrent_supersession_of_the_version_and_loses_to_it` (commit `175de9b`): sem a trava o `wait_until_blocked` estoura em 30 s e o teste falha (`tests/support/races.py:66`); com a trava passa |
| **N4** | `ImportCriteriaCsv` sem `lock_table` | ❌ Sobreviveu aos 93 testes dos autores → morto por `test_importing_a_version_while_the_latest_one_is_being_deleted_is_not_a_deadlock` (`175de9b`): sem a trava a exclusão falha (a lente viu `DeadlockDetected`, `40P01`), com ela passa |
| Mf37, Mf52 (rodada 1) | selo "Encerrada" sem exigir unidade marcada; `UnitsDialog` descarta unidades desconhecidas | ✅ Mortos (`ScoringAdmin.test.tsx:184`; `ScoringTableDialogs.test.tsx`) |
| Mn01, Mn12 | `toISOString` de volta; `<=` na comparação do selo | ✅ Mortos (testes de Belém, 23h de 31/12) |
| **Mn02** | mês sem `+1` em `localIsoDate` | ❌ Sobreviveu aos 141 testes → morto por "no meio do ano, a versão marcada que terminou ontem (04/08) está encerrada" (`ScoringAdmin.test.tsx`, `175de9b`) |
| **Mn03** | dia UTC (`getUTCDate`) com mês local | ❌ Sobreviveu → morto por "no meio do ano, às 22h de 05/08 em Belém (já é 06/08 em UTC), o dia e o mês locais decidem o selo" (`175de9b`) |
| **Mn09, Mn10** | tirar a classe `tbl-retry` de um dos dois "Tentar de novo" | ❌ Sobreviveram (a renderização do mutante mediu 32 px) → mortos por `expect(retry).toHaveClass("tbl-retry")` no teste GTAB-39 e pelo teste novo do erro com a lista carregada (`175de9b`) |
| Mn04, Mn05, Mn06, Mn07, Mn08, Mn11, Mn13a, Mn18 | `min-height` de 2rem em cada seletor, coluna sem largura máxima, "Modo" sem rótulo, sem `margin-bottom`, barra e "Nova tabela" para todos os perfis | ✅ Mortos |
| Mn13b | `barActions` sem o `isAdmin` | Equivalente: o `isAdmin &&` do JSX continua escondendo a barra; substituído por Mn18 |

**Medida do consolidador, depois de `175de9b`** (worktree em `cac86b0` mais o arquivo de teste novo, mutante aplicado e desfeito, árvore real intacta): linha de base 9 passed no arquivo de corrida (antes eram 7) e 62 passed em `ScoringAdmin.test.tsx` (antes 59); N4: 1 failed, 8 passed; Mb10: 1 failed (o teste novo, `races.py:66`); Mn02, Mn03, Mn09 e Mn10: 1 failed cada, e o teste que falha é o novo esperado.

**Sensor depth**: completo (caminho crítico).
**Sensor, rodada 2**: PASS ✅. Dos mutantes válidos desta rodada, os 6 que sobreviveram (Mb10, N4, Mn02, Mn03, Mn09, Mn10) foram mortos por testes puros novos; os equivalentes (N8, N11, Mn13b) têm argumento; nenhum sobrevivente válido resta. O acumulado da rodada 1 (Mb10, Mb49, Mb66, Mf37, Mf52 vivos) também está morto.

## Visual Check (rodada 2)

Navegador: Chrome 146 headless com playwright-core (no scratchpad, não no repositório), sobre o build real da árvore `cac86b0` (que só difere do HEAD final em dois comentários), servidor estático e JSON sintético (3 tabelas visíveis e 1 arquivada: em uso, usada por processo, substituída, encerrada e em uso, referência de 90 caracteres, nome longo; erro 500 simulado por rota). ADMIN e SECRETARIA, 360 e 1280 px, nos estados lista, vazio, erro, erro com a lista, critérios, diálogo "Nova tabela".

| Verificação | 360 px | 1280 px |
| ----------- | ------ | ------- |
| `scrollWidth == innerWidth`, em todos os estados | 360 = 360 ✅ | 1280 = 1280 ✅ |
| Elementos cortados ou fora da janela | 0 ✅ | 0 ✅ |
| Palavra quebrada letra por letra | nenhuma ✅ (só a referência sintética de 90 caracteres, `break-word`, 4 linhas) | nenhuma ✅ (2 linhas) |
| Altura de "Nova tabela" | 44 px ✅ (era 32) | 44 px ✅ |
| Altura de "Limpar filtros" (estado vazio) | 44 px ✅ (era 32) | 44 px ✅ |
| Altura de "Tentar de novo" (erro inicial e erro com a lista) | 44 px ✅ (era 32) | 44 px ✅ |
| Botões dos cartões e dos diálogos | 44 px ✅ | 44 px ✅ |
| Coluna do botão bloqueado, folga do `h1`, coluna "Modo" | `h1` com 8 px até "Nova tabela" ✅; "Modo" mostra "Por unidade" | coluna limitada a 256 px, 16 px antes do cartão do filtro ✅; sem enum cru |
| SECRETARIA | 5 botões "Ver critérios", sem "Nova tabela" nem barra ✅ | igual ✅ |

Capturas em `/tmp/claude-1000/-home-nees-Documents-VSCodigo-ProgressaoFuncionalPiloto/118aba81-5621-4e3f-847f-fa68c56fc9d9/scratchpad/gtab-render2/`: `gtab-360.png`, `gtab-1280.png`, `gtab-empty-360.png`, `gtab-empty-1280.png`, `gtab-error-360.png`, `gtab-error-1280.png`, `gtab-error-inline-360.png`, `gtab-error-inline-1280.png`, `gtab-360-secretaria.png`, `gtab-1280-secretaria.png`, `gtab-360-criteria-archived.png`, `gtab-1280-criteria-archived.png`, `gtab-360-dialog-nova.png`, `gtab-1280-dialog-nova.png` e `result.json` com as medidas. O consolidador não repetiu a renderização; conferiu no código os seletores e as classes que a medida exercita e rodou os testes estáticos e de comportamento. O único controle abaixo de 44 px é o link "Sair" do cabeçalho global do aplicativo (22 px), anterior à feature e fora dos controles da página; fica fora do GTAB-38 e anotado como achado menor.

Limite da prova (L-021): `styles.test.ts` continua estático e não mede altura; a prova dos 44 px é a renderização acima, e as asserções de classe (`tbl-retry`) e de seletor são o que impede a regressão silenciosa.

## Regressões

Nenhuma. Backend, 185 passed na execução de cobertura da lente (corrida e limites, exclusão de versão e de tabela, versões, importação, criação, API de administração, aceitação, semente, migração `0012`, marcações) e `ruff check` limpo; frontend, 141 passed nos 6 arquivos tocados, `eslint` e `npm run build` limpos. A ordem das travas (unidade, tabela, versão) segue sem ciclo (N17 morto). Uma observação sem ação: as respostas de escrita da tabela agora fazem uma segunda leitura depois do `commit`; se outro ADMIN apagar a tabela entre as duas, a escrita que deu certo responderia 404 (muito improvável).

## Achados menores que ficam (nenhum bloqueia)

Reverificados pelo consolidador; nenhum é blocker nem major, e nenhum quebra um requisito GTAB.

1. **Rótulo do histórico (GTAB-17)**: `frontend/src/labels.ts:280-296` não tem rótulo para `closed_version_id`, que todo evento `CREATE` que fechou uma versão traz agora; a tela do histórico mostra a chave crua em inglês (o valor sai como nome da versão, porque `UUID_PATTERN` o captura, então o requisito "sem UUID" vale). Tarefa de correção opcional F15: `"Encerrou a versão"` em `HISTORY_CHANGE_LABELS` e a chave em `HISTORY_ID_KEYS`, com teste no diálogo de histórico.
2. **Garantia de A11 limitada**: apagar a versão do meio e depois a última deixa a mais antiga fechada e a tabela sem versão corrente, porque o `closed_version_id` da última aponta para a versão já apagada; uma versão criada antes do registro não reabre nada. As duas limitações estão no texto do GTAB-26 ("a versão criada antes do registro nao reabre nenhuma"); a meta de A11 vale só para o par criado e apagado em sequência. Aceito como decisão da spec; o aviso na prévia de exclusão fica como melhoria futura.
3. **Documentação das travas**: `tasks.md` (item 3) e `ports.py` não citam as duas travas novas; só documentação.
4. **Respostas de versão**: `POST /scoring-tables/{id}/versions` e `.../versions/import` devolvem `VersionOut` com `read_only_reason`, `delete_blocked_reason` e `process_count` nos valores padrão (documentado no comentário de `VersionView`, `scoring_admin.py:53-57`); a tela recarrega a lista depois da escrita, então não há efeito visível. O F12 pedia só o `TableOut`.
5. **Rota B do deploy** (restaurar o dump) e a troca das etiquetas Docker não foram reproduzidas; o ensaio cobriu a rota A.
6. **Link "Sair"** de 22 px no cabeçalho global, fora da feature.
7. **Seletor de unidade** com 42 px (spec-precision de GTAB-38, da rodada 1, sem mudança).

## Gate (rodada 2)

- **Comando**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run`
- **Execuções finais dos autores (não repetidas pelo Verifier em suíte inteira)**: backend **6738 passed**; frontend **923 passed**.
- **Execuções do consolidador, depois dos commits `175de9b` e `6e147b4`**: `ruff check .` do backend limpo; `pytest -q tests/integration/scoring tests/integration/test_seed_scoring.py tests/integration/api/test_gestao_tabelas_acceptance.py`: **424 passed** em 209 s; frontend inteiro, `REQUIRE_DIST=1 npx vitest run`: **926 passed** (61 arquivos; os 923 dos autores mais os 3 testes novos de `175de9b`); `eslint` dos dois arquivos tocados limpo. O backend inteiro não foi repetido: o commit `175de9b` soma 2 testes ao total dos autores (esperado 6740, não medido) e `6e147b4` só muda comentários.
- **Pulos**: nenhum novo. **Falhas**: nenhuma. O `xfail` estrito da rodada 1 saiu (F1).
- **Integridade dos testes**: nenhum teste apagado ou enfraquecido nas correções (`git diff --diff-filter=D` sem arquivos de teste).

## Requirement Traceability Update (rodada 2)

Todos os GTAB-01 a GTAB-45 têm teste com `arquivo:linha` (tabelas da rodada 1) e passam. A rodada 2 fechou os dois gaps: GTAB-26 em `test_admin_lock_and_boundary_gaps.py:128`, `:146`, `:109` e `scoring_admin.py:628-636`, `:976-1022`; GTAB-38 pela renderização (44 px nos três botões) e `styles.test.ts`. O `spec.md` passa as 45 linhas para `Implemented / Verified`.

| Requisito | Estado anterior | Estado novo |
| --------- | --------------- | ----------- |
| GTAB-01 a GTAB-45 | Implementing (GTAB-26 e GTAB-38 em Needs Fix) | ✅ Verified |

## Lições

Lições destiladas dos sinais fundamentados desta rodada (sobreviventes válidos e a falha de render): L-052 (uma prova de corrida por ponto de entrada que pega trava, e reconferir contra todo escritor da linha a trava dada como equivalente), L-053 (data montada pelos componentes locais, testada no meio do ano com mês e dia diferentes do UTC) e L-054 (garantia de layout dada por classe CSS, afirmada em teste de comportamento em cada elemento), registradas por `scripts/lessons.py` como candidatas (primeira ocorrência).

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 45 de 45 requisitos com a asserção no resultado que a spec define; os gaps da rodada 1 (GTAB-26, GTAB-38) estão fechados.
**Sensor**: rodada 2 sem sobrevivente válido; 6 sobreviventes válidos mortos por testes puros novos (`175de9b`); N8, N11 e Mn13b equivalentes, com argumento.
**Gate**: backend 6738 passed e frontend 923 passed (execuções finais dos autores); consolidador: 424 passed no backend tocado e 926 passed no frontend inteiro.
**Render**: 360 e 1280 px sem rolagem horizontal, sem quebra em letras e os três botões em 44 px.

**What works**: tudo o que a rodada 1 registrou, mais a reabertura pela marca de fechamento, as travas em ordem fixa com corrida real em cada ponto de entrada, as respostas de escrita com os motivos, a data local no selo "Encerrada", os alvos de toque de 44 px e o roteiro de volta do deploy.

**Issues found**: só achados menores (lista acima); F15 opcional (rótulo de `closed_version_id`).

**Next steps**: push e deploy só com a autorização do usuário; seguir o roteiro de `docs/deploy/vm.md`, que traz as duas rotas de volta.

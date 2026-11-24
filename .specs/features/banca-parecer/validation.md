# Banca, Parecer, Requerimento e checklist do dossiê (banca-parecer) Validation

**Date**: 2026-11-22
**Spec**: `.specs/features/banca-parecer/spec.md` (44 requisitos: PORT-01..12, PAR-01..14, REQ-01..08, DOS-01..07, BNAV-01..03), com `design.md`, `tasks.md` (bloco de regras e Notas confirmadas) e `CLAUDE.md`
**Diff range**: `e9fd0eb..HEAD` (`2e89f84`), branch `feat/inteligencia-documental`: 52 commits (T1 a T50, mais a correção `2050ba2` do despacho por tipo e a correção `02846e9` do teste de versões do Parecer), 137 arquivos, +15932 −762
**Verifier**: sub-agente independente (autor diferente). Não leu `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt` nem `test/`; sem push, deploy, VM nem rede. Leu só o modelo público da PROGEP (`docs/referencias/normas/PROGEP-Modelo-Requerimento-Progressao-Promocao.docx`) para conferir os textos literais do Requerimento. Sensor em duas worktrees temporárias (nunca `git stash`), removidas no fim; `git status --porcelain` da árvore real igual ao de antes (só `backend/img/`, `requeriment.txt` e `test/`); `git worktree list` mostra só a árvore real.

**Result**: PASS. Os 44 requisitos têm evidência `arquivo:linha` e cada teste afirma o valor que a spec define (frase da conclusão, linha do mínimo, literais do Requerimento, códigos de recusa e a ordem `CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE`, `TABELA_DESATUALIZADA`, limites 5 000/15/200/100/50/20 MB, 404, 409, rótulos e os nove itens do dossiê). O gate está verde (backend 6312 passando, frontend 765 passando, ruff, lint e build limpos; a rodada completa é posterior à correção `02846e9`). O sensor injetou 133 falhas de comportamento: 127 mortas, 5 sobreviventes equivalentes (explicadas) e 1 sonda sem efeito fora da contagem; nenhum sobrevivente real. Nenhuma lacuna de código nem de teste que bloqueie; três notas de precisão da spec e quatro observações menores abaixo (nenhuma vira tarefa de correção).

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1..T7 (Fase 1: entidades, regras da banca, tipos de documento, conclusão) | Done | `ac76648`, `0b57bc0`, `005b10a`, `0c0486f`, `54a7e4b`, `55a4ad2`, `024821b` |
| T8..T11 (Fase 2: textos do Parecer e do Requerimento, checklist) | Done | `907b892`, `668823f`, `c6448c2`, `2f805e4` |
| T12..T16 (Fase 3: migração `0011`, repositórios, exclusão) | Done | `5881fec`, `f91b41a`, `f56e01f`, `1c4f5b0`, `820066c` |
| T17..T23 (Fase 4: extrator da IA, casos de uso da portaria, leitura, conclusão) | Done | `1ea7c7a`, `1fc2b1c`, `8da391a`, `8e2d2ab`, `9da9823`, `0d1b541`, `849a65e` |
| T24..T32 (Fase 5: escritores DOCX e PDF, geração por tipo) | Done | `ed592e2`, `c16aba3`, `0278f4e`, `c06f51c`, `87cf6c9`, `00c2a02`, `2050ba2`, `e2b73ca`, `9be8c4d` |
| T33..T39 (Fase 6: dossiê, ligação, API) | Done | `f30f07d`, `85239a8`, `8b35192`, `0d9d2e7`, `3a857de`, `e6c2fe9`, `d20b03e` (mais a correção `02846e9`) |
| T40..T45 (Fase 7: frontend, navegação, Etapa 6) | Done | `966cf95`, `5b81b89`, `250c768`, `0de75e1`, `081e4ba`, `f911ed1` |
| T46..T49 (Fase 8: frontend, Etapa 7, conclusão) | Done | `a70f8db`, `3f0b271`, `564993e`, `4afcc89` |
| T50 (Fase 9: AD-025, deploy) | Done | `2e89f84`; `.specs/STATE.md:202` e `docs/deploy/vm.md:220` conferidos |
| T51 (Verifier) | Done | este relatório |

**Test integrity**: 502 `def test_` acrescentados e 5 removidos no backend (diff de `backend/tests`); 109 `it(` acrescentados e 17 removidos no frontend. Os 5 removidos do backend foram renomeados e fortalecidos por requisito novo: `test_the_six_names_...` virou `test_the_ten_names_...` (`b/unit/domain/test_download_names.py`, com os 4 nomes novos), `test_the_three_kinds_...` virou `test_the_five_kinds_...` (`b/unit/domain/test_generated_entities.py`), `test_the_kind_of_a_request_must_be_one_of_the_three_documents` virou `..._of_the_five_documents` (`b/unit/presentation/test_generated_schemas.py`, agora também aceita `PARECER` e `REQUERIMENTO` e recusa `PORTARIA`), `test_the_list_follows_the_file_...` (`test_dossier_order_api.py`) e `test_only_the_report_the_table_and_the_proof_...` (`test_dossier_order_file.py`) foram substituídos por `test_dossier_api.py:241` e `test_dossier_order_file.py:8-75` (nove itens, chaves e fontes). Os 17 removidos do frontend, ponto (h) abaixo, têm todos equivalente de mesma força ou maior. O gate completo passou em `HEAD` depois da correção `02846e9`, que só troca `[2, 1]` por o conjunto `[1, 2]` em `test_asking_for_the_parecer_again_gives_version_2_and_keeps_version_1` (`b/integration/api/test_generated_documents_api.py:353-363`); a versão 1 continua baixável (`assert client.get(file_url(first, "pdf")).status_code == 200`) e os números 1 e 2 continuam afirmados.

---

## Spec-Anchored Acceptance Criteria

Legenda: PASS = o teste afirma o valor que a spec define; NOTA = lacuna de precisão da spec, sem lacuna de código. Caminhos relativos a `backend/tests/` (b/) e `frontend/src/` (f/). Os mutantes citados (B, G, C, R, U, O, K, D, W, F, L, P) estão na tabela do sensor.

### P1: Registrar a portaria da banca

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| PORT-01 | Guardar o arquivo como portaria do processo e pôr a leitura na fila | `b/integration/doc_usecases/test_ordinance_upload.py:52` (`stored.reading_state is ReadingState.PENDENTE`, `file.mime`, `size_bytes`, `sha256 == hashlib.sha256(content).hexdigest()`, arquivo igual no disco); `:75` (auditoria `UPLOAD`, `justification is None`); `b/integration/api/test_board_file_api.py:83` (200, leitura na fila); `f/components/OrdinanceForm.test.tsx:46` (`FormData` com o arquivo, `expected_version` 0, sem substituição) | PASS |
| PORT-02 | Número, data e membros (nome e função `PRESIDENTE`/`MEMBRO`/`SUPLENTE`), cada valor com a página | `b/integration/doc_usecases/test_ordinance_reading.py:76` (`("123/2025", 1, EXTRAIDO)`, data com página 1, três membros `(nome, função, página, origem)`); `b/integration/api/test_board_file_api.py:95`; `b/integration/api/test_banca_parecer_acceptance.py:181`; `f/components/OrdinanceForm.test.tsx:96` ("página 2") | PASS |
| PORT-03 | Valor que não está no texto da página citada fica vazio com `VALOR_SEM_ORIGEM` no campo | `b/integration/doc_usecases/test_ordinance_reading.py:134` (número e data só na outra página: `(None, None, None)` e `OrdinanceWarning(VALOR_SEM_ORIGEM, "number")`), `:149` (a conferência usa o texto original, não o mascarado), `:160` (membro inventado cai com aviso em `members`); `b/unit/domain/test_ordinance_grounding.py:64,79,112,125`; `f/components/OrdinanceForm.test.tsx:111,129`; mutantes G10, G11, G12, G17, F15 mortos | PASS |
| PORT-04 | Só o texto mascarado vai à IA, nunca o arquivo nem o texto sem máscara | `b/integration/doc_usecases/test_ordinance_reading.py:116` (`isinstance(sent, str)`, `[CPF]`, `[EMAIL]`, `[TELEFONE]`, os valores reais ausentes, nomes mantidos); `b/unit/infrastructure/test_ordinance_extractor.py:123` (a mensagem do usuário é exatamente o texto recebido), `:201` (a chave só no cabeçalho, nunca em `repr`, erro nem log); `f/` não contém `maritalk`, `api_key` nem `apikey` (grep em `frontend/src`); mutante O01 (texto sem máscara) morto | PASS |
| PORT-05 | Gravar o informado, marcar cada valor editado como "informado pela pessoa", auditar, sem justificativa | `b/integration/doc_usecases/test_ordinance_save.py:63` (só o membro corrigido vira `(nome, MEMBRO, None, INFORMADO)`, os outros mantêm página e origem), `:107` (só o número), `:204` (`justification is None`, `fields_changed == ["number"]`, nenhum nome na auditoria); `f/components/OrdinanceForm.test.tsx:152`; mutante U06 morto | PASS |
| PORT-06 | Registro sem arquivo, com origem "informado pela pessoa" | `b/integration/doc_usecases/test_ordinance_save.py:171`; `b/integration/api/test_board_api.py:100`; `f/components/OrdinanceForm.test.tsx:62` | PASS |
| PORT-07 | `FALHOU` com o motivo, campos editáveis, "Ler de novo" | `b/integration/doc_usecases/test_ordinance_reading.py:240` (erro do extrator vira `FALHOU` com o código e o digitado fica), `:278` (`TEXTO_ILEGIVEL` e a IA não é chamada), `:288` (`ERRO_INTERNO`, o log só traz o tipo); `b/integration/doc_usecases/test_ordinance_upload.py:335` (ler de novo põe na fila); `b/integration/api/test_board_file_api.py:123,147`; `f/components/OrdinanceForm.test.tsx:204`; `f/pages/ProcessBoard.test.tsx:111`; mutantes O02, O06, O07, O08 mortos | PASS |
| PORT-08 | Confirmar a substituição apaga o arquivo anterior do disco, lê o novo e audita | `b/integration/doc_usecases/test_ordinance_upload.py:154` (sem `replace`: 409 e o primeiro fica), `:221` (`assert not old_path.exists()`, só o novo no disco, `PENDENTE`), `:240` (auditoria `operation == "REPLACE"`), `:257` (falha antes do commit mantém o antigo e remove o novo); `f/components/OrdinanceForm.test.tsx:225,239`; mutantes U01, U02, U03, F08, F09 mortos | PASS |
| PORT-09 | A portaria não entra na Etapa 2, nas atividades, na pontuação nem no Comprovante | `b/integration/doc_usecases/test_ordinance_upload.py:305` (`snapshot() == before` com os documentos, as entradas de geração e a pontuação, `before[0] == []`); `b/integration/api/test_banca_parecer_acceptance.py:181` (`documents() == []`, atividades e pontuação iguais); `b/integration/documents/test_board_repository.py:434` (a portaria não está entre os documentos do processo); ver nota N5 | PASS |
| PORT-10 | PDF, PNG, JPEG até 20 MB; senão 422 e a mensagem do limite | `b/integration/doc_usecases/test_ordinance_upload.py:105` (20 MB + 1: `field == "arquivo"`, `code == "ARQUIVO_GRANDE"`, `"tamanho máximo" in message`, nada no disco), `:130` (tipo inválido), `:144` (exatamente 20 MB aceito); `b/integration/api/test_board_file_api.py:185,199,210`; `f/components/OrdinanceForm.test.tsx:271` | PASS com NOTA N1 (a mensagem é a existente, "O arquivo passa do tamanho máximo.", sem "20 MB"; a tela mostra "PDF, PNG ou JPEG de até 20 MB.", `OrdinanceForm.tsx:160`) |
| PORT-11 | Mais de 15 membros, nome vazio ou acima de 200, número acima de 50: 422 indicando o campo | `b/unit/domain/test_board_rules.py:24` (15 passam), `:28` (16 erram em `members`), `:36,42` (nome vazio), `:46` (200 passa, 201 erra), `:54` (50 passa, 51 erra); `b/integration/api/test_board_api.py:139,150,160`; `b/integration/doc_usecases/test_ordinance_save.py:250,260`; `f/components/OrdinanceForm.test.tsx:251,264`; mutantes G01, G02, G03, G09 mortos | PASS |
| PORT-12 | Duas gravações da mesma versão: a primeira vale, a segunda 409 | `b/integration/doc_usecases/test_ordinance_save.py:287` (`StaleVersion`, `code == "VERSAO_DESATUALIZADA"`, `stored_board == first`), `:300,310`; `b/integration/api/test_board_api.py:178` (200 e 409 com o código), `:188`; `b/integration/documents/test_board_repository.py:142,164`; `f/components/OrdinanceForm.test.tsx:280`; mutante P01 morto (U04 e U11 equivalentes, ver sensor) | PASS |

### P1: Gerar a minuta do Parecer

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| PAR-01 | Campos conclusão (sem valor inicial), data, local, observações | `b/integration/api/test_board_api.py:198` (a minuta salva sem conclusão a mantém vazia); `b/integration/doc_usecases/test_opinion_save.py:48,57,66,79`; `b/integration/test_migration_board.py:116`; `f/components/OpinionForm.test.tsx:35` (nenhum rádio marcado), `:56` (envia conclusão, data, local, observações e versão) | PASS |
| PAR-02 | Versão do Parecer em DOCX e PDF, imutável e numerada | `b/integration/doc_usecases/test_run_generation_opinion.py:82` (versão 1 `PRONTO` com DOCX e PDF), `:243` (versão 2 e as duas ficam no histórico e no disco); `b/integration/api/test_generated_documents_api.py:318,353`; `b/integration/api/test_banca_parecer_acceptance.py:211` | PASS |
| PAR-03 | Seções na ordem: cabeçalho, título, identificação, portaria, interstício, documentos analisados, pontos por grupo e Total, mínimo, conclusão, observações, local e data, uma assinatura por membro | `b/unit/domain/test_opinion_document.py:87` (`[s.key] == ["identificacao","portaria","intersticio","documentos","pontos","minimo","conclusao","observacoes","local_data"]`), `:103` (cabeçalho com a unidade e título "PARECER"), `:136` (os seis campos como digitados), `:173` (versão usada); `b/unit/infrastructure/test_opinion_docx.py:45` e `test_opinion_pdf.py:57` (a mesma ordem no arquivo), `:102`/`:90` (uma linha de assinatura por membro); `b/integration/api/test_banca_parecer_acceptance.py:211` (`text.count(SIGNATURE_LINE) == 3` em DOCX e PDF); mutantes B02, B09, B10, B12, B16, W01, W02, W07, W08 mortos | PASS com NOTA N2 |
| PAR-04 | Pontos por grupo, Total e mínimo copiados do instantâneo da última Tabela `PRONTO` | `b/unit/domain/test_opinion_document.py:189` (oito grupos `("I - Atividades de ensino", "100,00")`...), `:204` (`("Total geral", "211,00")` mesmo com subtotais que não somam); `b/integration/doc_usecases/test_run_generation_opinion.py:95,155,167,183`; `b/integration/api/test_banca_parecer_acceptance.py:211` (`total_geral(text) == pt(total)`); mutantes B07, L10, L11, R11, R12 mortos | PASS |
| PAR-05 | "A banca manifesta-se FAVORÁVEL à <progressão\|promoção> de <docente>, do nível <n> da classe <X> (<atual>) para o nível <m> da classe <Y> (<pretendida>), referente ao interstício de <dd/mm/aaaa> a <dd/mm/aaaa>." e a mesma com DESFAVORÁVEL | `b/unit/domain/test_opinion_document.py:228` (igualdade exata da frase: "...à promoção de Maria Docente da Silva, do nível 4 da classe B (Adjunto) para o nível 1 da classe C (Associado), referente ao interstício de 23/11/2022 a 23/11/2024."), `:238` (DESFAVORÁVEL e "progressão"); `b/integration/doc_usecases/test_run_generation_opinion.py:109,120`; mutantes B01, B03, B06 mortos | PASS |
| PAR-06 | Mínimo "não definido": "Mínimo de referência: não definido pela norma aplicável", sem número | `b/unit/domain/test_opinion_document.py:213` (`lines == ("Mínimo de referência: não definido pela norma aplicável",)`), `:219` (numérico: "Mínimo de referência: 200,00 pontos"); `b/integration/doc_usecases/test_run_generation_opinion.py:155,167,183`; mutante B08 morto | PASS |
| PAR-07 | Sem conclusão: 422 `CONCLUSAO_AUSENTE` | `b/integration/doc_usecases/test_request_opinion.py:62,69` (`error.code == GenerationCode.CONCLUSAO_AUSENTE`, nenhuma linha criada); `b/integration/api/test_generated_documents_api.py:292`; `b/integration/api/test_banca_parecer_acceptance.py:211` (`status_code == 422`, `detail[0]["code"] == "CONCLUSAO_AUSENTE"`); `f/pages/ProcessBoard.test.tsx:131` | PASS |
| PAR-08 | Sem membro: 422 `BANCA_SEM_MEMBROS` | `b/integration/doc_usecases/test_request_opinion.py:75,84` (conclusão e nenhum membro; portaria sem membro é o mesmo que sem portaria); `b/integration/api/test_generated_documents_api.py:292` | PASS |
| PAR-09 | Sem Tabela `PRONTO`: 422 `TABELA_AUSENTE` | `b/integration/doc_usecases/test_request_opinion.py:91` (membros e nenhuma Tabela), `:101` (Tabela só `GERANDO` não conta); `b/integration/api/test_generated_documents_api.py:292`; mutante R10 morto | PASS |
| PAR-10 | Total atual diferente do da Tabela: 422 `TABELA_DESATUALIZADA` e "A pontuação mudou depois da última Tabela; gere a Tabela de novo" | `b/integration/doc_usecases/test_request_opinion.py:110` (`error.code == TABELA_DESATUALIZADA`, `OUTDATED_MESSAGE in error.message`, só a Tabela na lista), `:121` (mesmo total com outra versão da tabela: também desatualizada); `b/integration/api/test_generated_documents_api.py:292-315` (a ordem completa `CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE`, aceita, `TABELA_DESATUALIZADA` com a mensagem exata, nova Tabela, aceita); `b/integration/doc_usecases/test_run_generation_opinion.py:199` (a atividade mudada entre o pedido e a execução reprova a linha), `:219` (a conclusão apagada no meio também); `b/integration/api/test_banca_parecer_acceptance.py:239`; `f/pages/ProcessBoard.test.tsx:142`; mutantes R01, R03, R04, R06, L06 mortos | PASS |
| PAR-11 | Gerar o texto sem chamar a IA | `b/integration/doc_usecases/test_run_generation_opinion.py:261` (`assert no_ai == []` e `parecer.state is PRONTO`); `b/integration/doc_usecases/opinion_support.py:88` (a fixture troca `MariTalkClient.chat`, `httpx.Client.send` e `httpx.AsyncClient.send` por funções que registram e levantam `AssertionError`); `b/integration/api/test_banca_parecer_acceptance.py:264` (`flow.real_ai_calls == []`, a leitura da portaria é a única chamada); `b/unit/domain/test_opinion_document.py:313`; mutante R13 (uma chamada HTTP dentro de `_opinion`) morto: a fixture falha mesmo | PASS |
| PAR-12 | Nunca preencher nem sugerir a conclusão | `b/integration/doc_usecases/test_board_read.py:71` (a leitura não preenche a conclusão com a Tabela pronta e os pontos acima do mínimo); `b/integration/api/test_banca_parecer_acceptance.py:211` (`flow.board()["opinion"]["conclusion"] is None` antes e depois da Tabela); `f/components/OpinionForm.test.tsx:35,44` (nenhum rádio marcado, mesmo com data, local e observações), `:78` (salvar sem escolher envia `conclusion` nulo); mutantes U07, F01, F16 mortos | PASS |
| PAR-13 | Observações acima de 5 000 ou local acima de 100: 422 no campo | `b/integration/doc_usecases/test_opinion_save.py:104,113`; `b/unit/domain/test_board_rules.py:85,90`; `b/integration/api/test_board_api.py:229,237`; `b/integration/test_migration_board.py:128` (CHECK no banco); `f/components/OpinionForm.test.tsx:95,103,113`; mutantes G04, G05, F10, F12 mortos | PASS |
| PAR-14 | Pedir de novo gera a versão seguinte e mantém as anteriores no histórico e no disco | `b/integration/doc_usecases/test_run_generation_opinion.py:243`; `b/integration/api/test_generated_documents_api.py:353` (`(first["version_number"], second["version_number"]) == (1, 2)`, `sorted(...) == [1, 2]`, a versão 1 baixa com 200); `f/pages/ProcessBoard.test.tsx:157` | PASS |

### P1: Gerar o Requerimento pelo modelo da PROGEP

Os literais foram conferidos contra o modelo público (cabeçalho, título, "Prezado Sr. Presidente da CPPD,", "Nestes termos, pede deferimento.", "Assinatura do (a) requerente", "Observação" e o texto da LGPD, e o início do parágrafo "Eu, ..., Matrícula SIAPE ..., docente do (  ) Magistério Superior/ (  ) Ensino Básico e Tecnológico, atualmente lotado no (a) ..., solicito (progressão/promoção) funcional, do nível ... da classe ...").

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| REQ-01 | Versão do Requerimento em DOCX e PDF, imutável e numerada | `b/integration/doc_usecases/test_run_generation_request.py:62` (versão 1 com os dois arquivos, sem atividade nem Tabela), `:162` (a versão 2 e a 1 intocada); `b/integration/api/test_generated_documents_api.py:277,342`; `b/integration/api/test_banca_parecer_acceptance.py:264` (`(1, 2)`); `f/pages/ProcessDossier.test.tsx:159` | PASS |
| REQ-02 | Cabeçalho MEC/UFPA/PROGEP, título, saudação e a opção "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO" | `b/unit/domain/test_request_document.py:50` (`header_lines == MODEL_HEADER`, `title == MODEL_TITLE`, `greeting == MODEL_GREETING`, `option == MODEL_OPTION`, cada literal igual ao do modelo); `b/unit/infrastructure/test_request_docx.py:40` e `test_request_pdf.py:48` (a ordem nos arquivos); mutantes L09, W05 mortos | PASS |
| REQ-03 | Parágrafo com nome, SIAPE, carreira marcada, unidade, progressão ou promoção, nível, classe e denominação atuais e pretendidos como informados, e o interstício | `b/unit/domain/test_request_document.py:66` (igualdade exata do parágrafo da promoção do nível 4 da classe B (Adjunto) para o nível 1 da classe C (Associado), "(X) Magistério Superior/ (  ) Ensino Básico e Tecnológico", "23/11/2022 a 23/11/2024"), `:76` (progressão), `:83` (classe D para E com denominações fora do padrão copiadas como digitadas), `:97` (carreira desconhecida não marca nenhuma); mutantes B05, B13, B14 mortos | PASS |
| REQ-04 | Com Parecer `PRONTO`, a data do último Parecer; sem Parecer, "___/___/___" | `b/unit/domain/test_request_document.py:107` ("...realizada na data de 02/04/2025."), `:113` ("...de ___/___/___."); `b/integration/doc_usecases/test_run_generation_request.py:95,111,125` (Parecer só `GERANDO` não dá data); `b/integration/api/test_banca_parecer_acceptance.py:264` (antes e depois do Parecer); mutantes B11, R09 mortos | PASS |
| REQ-05 | Termina com "<cidade>, <data de abertura por extenso>.", "Nestes termos, pede deferimento.", a linha, "Assinatura do (a) requerente", "Matrícula SIAPE: <siape>" e a LGPD | `b/unit/domain/test_request_document.py:122` (`place_date_line == "Belém, 10 de março de 2025."`), `:137` (fechamento, linha, legenda, `"Matrícula SIAPE: 1234567"`, LGPD literal), `:148` (a ordem do modelo); `b/unit/domain/test_pt_format.py` (`format_long_date`); `b/integration/doc_usecases/test_opinion_save.py:125`; mutantes B04, L04, L05 mortos | PASS |
| REQ-06 | Sem cidade: "__________" | `b/unit/domain/test_request_document.py:126` (`"__________, 10 de março de 2025."`), `:130` (cidade só com espaços); `b/integration/doc_usecases/test_run_generation_request.py:85`; `f/pages/ProcessDossier.test.tsx:126`; mutantes B14, L12 mortos | PASS |
| REQ-07 | Sem a parte "REVISÃO" nem as instruções | `b/unit/domain/test_request_document.py:170` (nenhum texto com "REVISÃO" fora do título, nem "SIPAC" nem "Processo 23073"); `b/unit/infrastructure/test_request_docx.py:104` | PASS |
| REQ-08 | Gerar o texto sem chamar a IA | `b/integration/doc_usecases/test_run_generation_request.py:181` (`no_ai == []`); `b/unit/domain/test_request_document.py:184`; `b/integration/api/test_banca_parecer_acceptance.py:264` | PASS |

### P2: Checklist do dossiê

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| DOS-01 | Nove itens na ordem do arquivo: Requerimento, Portaria da última progressão, Declaração, Relatório, Tabela, Comprovante, Currículo Lattes, Portaria da banca, Parecer da banca | `b/unit/infrastructure/test_dossier_order_file.py:8` (ordem 1 a 9 e os títulos), `:24` (chaves `REQUERIMENTO`, `PORTARIA_ULTIMA_PROGRESSAO`, `DECLARACAO_EXERCICIOS_ANTERIORES`, `RELATORIO`, `TABELA`, `COMPROVANTE`, `CURRICULO_LATTES`, `PORTARIA_BANCA`, `PARECER`); `b/unit/domain/test_dossier_checklist.py:45`; `b/integration/api/test_dossier_api.py:241`; `f/components/DossierChecklist.test.tsx:42` (`["1",...,"9"]`, primeiro "Requerimento", último "Parecer da banca"), `:50` (não reordena); mutante F04 morto | PASS com NOTA N3 |
| DOS-02 | Documento gerado com versão `PRONTO`: "Gerado", número da última versão e link | `b/unit/domain/test_dossier_checklist.py:82,92` (a falha mais nova não esconde a última pronta); `b/integration/doc_usecases/test_dossier.py:101`; `b/integration/api/test_dossier_api.py:97,113`; `f/components/DossierChecklist.test.tsx:69` (versão e links de PDF e DOCX); mutantes C04, C06, F13 mortos (C08 equivalente) | PASS |
| DOS-03 | Portaria com ao menos um membro: "Registrada" | `b/unit/domain/test_dossier_checklist.py:114,120`; `b/integration/doc_usecases/test_dossier.py:133,139`; `b/integration/api/test_dossier_api.py:124`; `f/components/DossierChecklist.test.tsx:96`; mutantes C01, C03, F05 mortos | PASS |
| DOS-04 | Marcar e desmarcar "Entregue" no que o sistema não produz, gravado e auditado, sem justificativa | `b/integration/doc_usecases/test_dossier.py:174` (recarrega e vê a marca; auditoria sem justificativa), `:189,198,212` (repetir não grava evento), `:231` (chave que não é manual: 422 e nada gravado); `b/integration/api/test_dossier_api.py:153,161,173`; `b/integration/documents/test_dossier_delivery_repository.py:26-97`; `f/components/DossierChecklist.test.tsx:107,117,130`; mutantes C05, D02, D03, F06 mortos | PASS |
| DOS-05 | Sem versão, registro nem marca: "Pendente" | `b/unit/domain/test_dossier_checklist.py:57` (três Gerado e seis Pendente), `:153`; `b/integration/doc_usecases/test_dossier.py:84,113`; `b/integration/api/test_dossier_api.py:64` | PASS |
| DOS-06 | Tabela gerada com outra versão da tabela: "Gerada com outra versão da tabela de pontuação; gere de novo" | `b/unit/domain/test_dossier_checklist.py:168,176,182,191`; `b/integration/doc_usecases/test_dossier.py:148,162`; `b/integration/api/test_dossier_api.py:136`; `f/components/DossierChecklist.test.tsx:156,163`; mutantes C02, C07, D04, F07 mortos | PASS |
| DOS-07 | A confirmação de concluir lista como aviso o Requerimento, a Portaria da banca e o Parecer pendentes, sem impedir | `b/unit/domain/test_conclusion_purge.py:94,103,110,117,121,128` (`pending_board` em ordem, a Tabela, o Relatório e o Comprovante não limpam os itens da banca); `b/integration/doc_usecases/test_conclusion_preview.py:163,178,188`; `b/integration/doc_usecases/test_conclude_process.py:368`; `b/integration/api/test_banca_parecer_acceptance.py:290`; `f/components/ConcludeDialog.test.tsx:92` (lista "Requerimento, Portaria da banca, Parecer" e deixa concluir), `:116`; `f/pages/ProcessDossier.test.tsx:219`; mutantes K04, K05, K06, F03 mortos | PASS |

### P1: Etapas 6 e 7 na navegação

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| BNAV-01 | Sete etapas, a 6 "Banca e Parecer", a 7 "Requerimento e dossiê", nenhuma "em breve" | `f/components/StepNav.test.tsx:16` (sete habilitadas, títulos, nenhuma "em breve"), `:28` (rotas `/banca` e `/dossie`), `:41`, `:104`; `f/pages/ProcessStep1.test.tsx:131` (`toHaveLength(7)`); `f/pages/ProcessBoard.test.tsx:53,68`; `f/pages/ProcessDossier.test.tsx:67,80`; mutantes F02, F14, F19 mortos | PASS |
| BNAV-02 | `ARQUIVADO` ou `CONCLUIDO`: leitura só, e envio, gravação e geração recusados com 409 | `b/integration/api/test_banca_parecer_acceptance.py:376` e `:290` (`refuse_every_write`: oito escritas, cada uma `409` com `code == "PROCESSO_SOMENTE_LEITURA"`); `b/integration/api/test_board_api.py:312`; `b/integration/doc_usecases/test_ordinance_upload.py:193`; `test_ordinance_save.py:322`; `test_opinion_save.py:199`; `test_request_opinion.py:215` (os dois tipos novos recusados e os outros três ainda gerados, DEL-13); `b/integration/api/test_generated_documents_api.py:393,410`; `b/integration/doc_usecases/test_dossier.py:251`; `f/pages/ProcessBoard.test.tsx:167`, `f/components/OrdinanceForm.test.tsx:291`, `OpinionForm.test.tsx:142`, `DossierChecklist.test.tsx:170`, `ProcessDossier.test.tsx:265`; mutantes R05, U09, U10, D01, F11, F17 mortos | PASS |
| BNAV-03 | Sem acesso: 404 em toda rota da portaria, do Parecer, do Requerimento e do checklist | `b/integration/api/test_board_api.py:337` (as quatro rotas, dois forasteiros, e o dono vê a banca vazia); `b/integration/api/test_board_file_api.py:303`; `b/integration/api/test_dossier_api.py:211`; `b/integration/doc_usecases/test_request_opinion.py:256`; `test_board_read.py:119,183`; `test_dossier.py:269`; mutantes U08, U13, D05 mortos | PASS |

**Status**: 44 de 44 com evidência `arquivo:linha` e a asserção no valor da spec. Três notas de precisão da spec (N1, N2, N3), sem lacuna de código.

---

## Pontos que os autores pediram para decidir

- **(a) PORT-10, mensagem do limite**: não é lacuna de código. O envio da portaria passa por `validate_upload`, a mesma regra do upload da Etapa 2 (`backend/app/domain/rules/upload_validation.py:129-130`: `ARQUIVO_GRANDE`, "O arquivo passa do tamanho máximo."), e o design reusa essa regra ("PDF, PNG, JPEG até 20 MB" em `design.md`, linha "Validação de envio"). Os testes afirmam o 422 no campo `arquivo`, o código e o trecho "tamanho máximo" nos dois lados do limite (20 MB + 1 recusado, exatamente 20 MB aceito: `b/integration/doc_usecases/test_ordinance_upload.py:105,144`; `b/integration/api/test_board_file_api.py:185,199`), e a tela mostra o limite fixo "PDF, PNG ou JPEG de até 20 MB." (`frontend/src/components/OrdinanceForm.tsx:160`). A spec diz só "a mensagem do limite", sem texto; ver N1.
- **(b) Classe, denominação e nível só dos seis campos do processo (NMOV-01)**: confirmado. `opinion_document.py:84-97,136-149` e `request_document.py:267-279` leem `process.current_*` e `process.target_*`; nenhum dos dois, nem `ordinance_grounding.py` nem `dossier_checklist.py`, cita `next_class` nem a estrutura de carreira (grep); o único dado de carreira é o código `MAGISTERIO_SUPERIOR` que marca "(X) Magistério Superior" (`generated_documents.py:824`). Os testes copiam o digitado: `b/unit/domain/test_opinion_document.py:161` ("Titular-Livre", "Denominação Nova"), `b/unit/domain/test_request_document.py:83` (classe D para E, "Denominação Antiga" para "Titular-Livre"), e a promoção do nível 4 da classe B para o nível 1 da classe C (salto) nos dois textos exatos; o mutante B03 (trocar atual e pretendido) morreu.
- **(c) PAR-11 e REQ-08, sem IA na geração**: confirmado, e a fixture `no_ai` falha de verdade (`opinion_support.py:88-101`: substitui `MariTalkClient.chat`, `httpx.Client.send` e `httpx.AsyncClient.send` por um guarda que registra e levanta `AssertionError`). O mutante R13 acrescentou uma chamada `httpx.Client().send(...)` dentro de `_opinion` e `test_run_generation_opinion.py` falhou. Os testes de texto-fonte (`inspect.getsource`, `test_opinion_document.py:313`, `test_request_document.py:184`) só complementam.
- **(d) PAR-12, a conclusão nunca é preenchida nem sugerida, também na tela**: confirmado no servidor (`SaveOpinion` grava o que veio, `None` incluído; `GetBoard` não escreve nada; U07 morto) e na tela (`OpinionForm.tsx:42` `useState(opinion.conclusion)` sem valor padrão, dois rádios sem seleção inicial; F01 e F16 mortos; `OpinionForm.test.tsx:35,44,78`).
- **(e) PORT-04, só texto mascarado à IA e a chave só no backend**: `ordinance_reading.py:61-65,120` envia `_masked_text(pages)` (texto por página com `mask_identifiers`, só `str`, nunca o arquivo); `test_ordinance_reading.py:116` afirma que o CPF, o e-mail e o telefone saem e os nomes ficam; O01 (texto sem máscara) morreu. A chave existe só em `infrastructure/ai` e `core/config.py` (grep de `maritalk_api_key` em `backend/app`), `test_ordinance_extractor.py:201` afirma que ela só vai no cabeçalho `Authorization` e nunca no erro, no `repr` nem no log, e `frontend/src` não tem nenhuma ocorrência de `maritalk`, `api_key` ou `apikey`. A leitura registra no log só o tipo do erro (`ordinance_reading.py:110`; O07 morto).
- **(f) PORT-09, a portaria fora da Etapa 2, das atividades, da pontuação e do Comprovante**: a portaria é uma entidade própria (`board_ordinances`), não um `Document`; os testes de `test_ordinance_upload.py:305` e `test_banca_parecer_acceptance.py:181` comparam documentos, entradas de geração e pontuação antes e depois do envio, e `test_board_repository.py:434` afirma que ela não aparece entre os documentos. Ver N5.
- **(g) PAR-10 também na execução**: `check_opinion_inputs` é chamado no pedido (`generated_documents.py:331-332`) e de novo em `_opinion` (`:765`); a recusa é por total diferente **ou** versão da tabela diferente (`:210-212`); `test_run_generation_opinion.py:199` (atividade mudada entre o pedido e a execução reprova a linha) e `test_request_opinion.py:121` (mesmo total, outra versão); R03 (só total), R04 (só versão) e R06 (a execução não confere) mortos.
- **(h) Testes removidos do frontend**: 17 `it(` saíram e todos têm substituto de mesma força ou maior. `ProcessGenerated.test.tsx` perdeu "UIG-09" (3 testes, 4 execuções) e "CAINI-10, CAINI-11" (3 testes, 4 execuções): os 8 casos foram recriados com as mesmas asserções em `ProcessDossier.test.tsx:184-263` (botão só em `EM_ANDAMENTO`, `RASCUNHO` e `ARQUIVADO` sem botão, recarrega o processo depois de concluir, título e texto de rascunho, link "Ir para a Etapa 1" com `href="/processos/p1"`, nada em `CONCLUIDO` e `ARQUIVADO`), agora contra o bloco "Requerimento" em vez da Tabela, e `ProcessGenerated.test.tsx` ganhou o teste inverso (a Etapa 5 não oferece mais o botão nem o título "Concluir o processo"). `DossierOrder.test.tsx` (4 testes) foi substituído em `DossierChecklist.test.tsx:42,50,61` (ordem recebida, não reordena, erro de leitura) e `:69` (três Gerado e seis Pendente, o que cobre o "só eles" do antigo). Os 5 testes de `StepNav.test.tsx` e o "UI-04 / TELA-01" de `ProcessStep1.test.tsx` passaram de nove etapas para sete (`StepNav.test.tsx:16,28,41,66,104,162`; `ProcessStep1.test.tsx:131`).
- **(i) Arquitetura, AD-012 e auditoria sem nome de membro**: `grep` de `fastapi|sqlalchemy|pydantic|starlette|httpx|app.infrastructure|app.presentation` em `backend/app/domain` e `backend/app/application` não acha nada e `tests/architecture/test_layers.py` passa no gate; os novos módulos de domínio só importam portas e domínio. AD-012: versões do Parecer e do Requerimento são linhas imutáveis numeradas só em `PRONTO` (`test_run_generation_opinion.py:243`, `test_run_generation_request.py:162`, `test_generated_documents_api.py:353`; `test_generated_schemas`). Nenhum nome de membro na auditoria: `test_ordinance_save.py:204` e `:223`, `test_ordinance_reading.py:102`, `test_opinion_save.py:93`; U05 e O05 (nomes na auditoria da gravação e da leitura) mortos. Os nomes ficam só em `board_ordinances.members`, no JSON bruto da leitura e no instantâneo do Parecer, por decisão do design.
- **(j) Conclusão e exclusão**: a conclusão remove o arquivo da portaria e guarda número, data e membros (`test_conclude_process.py:378`, `test_purge_inputs.py:209`, `test_banca_parecer_acceptance.py:290-373`: `after["file"]["deleted"] is True`, `(number, date, members)` iguais, download 410 com `ARQUIVO_EXCLUIDO`); a exclusão apaga o arquivo e as quatro tabelas (`test_delete_process.py:332,343`, `test_process_purge_repository.py`) e é recusada com leitura em andamento (`test_delete_process.py:352,366`, motivo `LEITURA_PORTARIA`). K01, K02, K03, K07, K08, K09, K10 mortos.

---

## Discrimination Sensor

Duas worktrees temporárias `git worktree add --detach` em `/tmp/claude-1000/.../scratchpad/verifier-banca/` (`wt` e `wt2`), cada uma com um PostgreSQL próprio (`TEST_DATABASE_URL`), `PYTHONDONTWRITEBYTECODE=1` e `__pycache__` limpo a cada mutante; um mutante por vez, arquivo restaurado depois de cada rodada. Cada mutante rodou só os testes que cobrem o arquivo (backend) ou o `vitest run` dos oito arquivos de tela e rótulos (frontend). **Antes** de contar um morto, os 23 conjuntos de teste usados foram rodados sem mutação em `wt2` e todos passam (saída 0), então cada morto é uma falha causada pela mutação. Scripts em `scratchpad/verifier-banca/` (`engine.py`, `batch1..6.py`, `baseline.py`).

**Profundidade**: ampla (133 mutantes de comportamento, distribuídos pelos arquivos pedidos). Um sobrevivente real viraria tarefa de correção; não houve.

| # | Arquivo | Falha injetada | Resultado |
| - | ------- | -------------- | --------- |
| B01 | `domain/rules/opinion_document.py` | swap FAVORÁVEL/DESFAVORÁVEL | morto |
| B02 | `domain/rules/opinion_document.py` | drop the minimum line | morto |
| B03 | `domain/rules/opinion_document.py` | Parecer sentence: current/target swapped | morto |
| B04 | `domain/rules/request_document.py` | Requerimento uses the end of the interstice instead of the opening date | morto |
| B05 | `domain/rules/request_document.py` | Requerimento swaps promoção/progressão | morto |
| B06 | `domain/rules/opinion_document.py` | Parecer swaps promoção/progressão | morto |
| B07 | `domain/rules/opinion_document.py` | Total summed from subtotals instead of copied | morto |
| B08 | `domain/rules/opinion_document.py` | minimum line inverted | morto |
| B09 | `domain/rules/opinion_document.py` | empty notes create a section | morto |
| B10 | `domain/rules/opinion_document.py` | signature role always Membro | morto |
| B11 | `domain/rules/request_document.py` | Requerimento never writes the Parecer date | morto |
| B12 | `domain/rules/opinion_document.py` | groups in reverse order | morto |
| B13 | `domain/rules/request_document.py` | career option always marked | morto |
| B14 | `domain/rules/request_document.py` | no blank when the city is empty | morto |
| B15 | `domain/rules/opinion_document.py` | ordinance date blank dropped | morto |
| B16 | `domain/rules/opinion_document.py` | unit missing from the header | morto |
| G01 | `domain/rules/board_rules.py` | limit members 15->16 | morto |
| G02 | `domain/rules/board_rules.py` | limit member name 200->201 | morto |
| G03 | `domain/rules/board_rules.py` | limit number 50->51 | morto |
| G04 | `domain/rules/board_rules.py` | limit place 100->101 | morto |
| G05 | `domain/rules/board_rules.py` | limit notes 5000->5001 | morto |
| G06 | `domain/rules/board_rules.py` | limit city 100->101 | morto |
| G07 | `domain/rules/board_rules.py` | skip MEMBRO_REPETIDO | morto |
| G08 | `domain/rules/board_rules.py` | repeat check without normalising case/accents | morto |
| G09 | `domain/rules/board_rules.py` | off-by-one members | morto |
| G10 | `domain/rules/ordinance_grounding.py` | accept a number that is not in the page | morto |
| G11 | `domain/rules/ordinance_grounding.py` | accept a member not in the page | morto |
| G12 | `domain/rules/ordinance_grounding.py` | accept a date that is not in the page | morto |
| G13 | `domain/rules/ordinance_grounding.py` | no MEMBROS_NAO_ENCONTRADOS | morto |
| G14 | `domain/rules/ordinance_grounding.py` | re-reading overwrites the typed number | morto |
| G15 | `domain/rules/ordinance_grounding.py` | re-reading overwrites the typed members | morto |
| G16 | `domain/rules/ordinance_grounding.py` | accept a role outside the three | morto |
| G17 | `domain/rules/ordinance_grounding.py` | no VALOR_SEM_ORIGEM on the number | morto |
| G18 | `domain/rules/ordinance_grounding.py` | re-reading overwrites the typed date | morto |
| C01 | `domain/rules/dossier_checklist.py` | ordinance state label ENTREGUE instead of REGISTRADA | morto |
| C02 | `domain/rules/dossier_checklist.py` | ignore the other-version warning | morto |
| C03 | `domain/rules/dossier_checklist.py` | ordinance without members counts as registered | morto |
| C04 | `domain/rules/dossier_checklist.py` | first ready version wins instead of the last | morto |
| C05 | `domain/rules/dossier_checklist.py` | a mark counts on a non-manual key | morto |
| C06 | `domain/rules/dossier_checklist.py` | missing generated item reads GERADO | morto |
| C07 | `domain/rules/dossier_checklist.py` | unknown table version counts as outdated | morto |
| C08 | `domain/rules/dossier_checklist.py` | a non-ready version counts as ready | sobrevive, equivalente: `version_number is None` já exclui a linha não pronta (AD-012 só numera em PRONTO) |
| R01 | `application/use_cases/generated_documents.py` | order: BANCA_SEM_MEMBROS before CONCLUSAO_AUSENTE | morto |
| R02 | `application/use_cases/generated_documents.py` | table checked after (equivalent order probe) | sonda sem efeito (reordenação sem mudança de comportamento), fora da contagem |
| R03 | `application/use_cases/generated_documents.py` | TABELA_DESATUALIZADA only on total | morto |
| R04 | `application/use_cases/generated_documents.py` | TABELA_DESATUALIZADA only on version | morto |
| R05 | `application/use_cases/generated_documents.py` | Parecer/Requerimento generated in a read-only process | morto |
| R06 | `application/use_cases/generated_documents.py` | the run does not re-check TABELA_DESATUALIZADA | morto |
| R07 | `application/use_cases/generated_documents.py` | request does not check the Parecer inputs | morto |
| R08 | `application/use_cases/generated_documents.py` | dispatch: Requerimento produced as Parecer | morto |
| R09 | `application/use_cases/generated_documents.py` | Requerimento never gets the Parecer date | morto |
| R10 | `application/use_cases/generated_documents.py` | TABELA_AUSENTE not raised (AttributeError instead) | morto |
| R11 | `application/use_cases/generated_documents.py` | snapshot stores a fixed conclusion | morto |
| R12 | `application/use_cases/generated_documents.py` | Parecer minimum from the current score even when the Tabela saved one | morto |
| U01 | `application/use_cases/board.py` | replace without confirmation | morto |
| U02 | `application/use_cases/board.py` | old ordinance file stays on the disk | morto |
| U03 | `application/use_cases/board.py` | a failed upload leaves the new file | morto |
| U04 | `application/use_cases/board.py` | upload ignores the version | sobrevive, equivalente: a versão é conferida de novo no repositório (`_locked_at`/`create`) dentro de `_versioned()`, com o mesmo 409 |
| U05 | `application/use_cases/board.py` | member names in the audit | morto |
| U06 | `application/use_cases/board.py` | every save marks the number as typed | morto |
| U07 | `application/use_cases/board.py` | the system fills the conclusion | morto |
| U08 | `application/use_cases/board.py` | GetBoard without the access check | morto |
| U09 | `application/use_cases/board.py` | SaveOpinion allowed in a read-only process | morto |
| U10 | `application/use_cases/board.py` | SaveRequestSettings allowed in a read-only process | morto |
| U11 | `application/use_cases/board.py` | re-read ignores the version | sobrevive, equivalente: `request_reading` confere a versão no repositório (`_locked_at`) e o 409 sai igual; só muda qual dos dois 409 vence quando ambos valem, e a spec não ordena |
| U12 | `application/use_cases/board.py` | download of a purged ordinance file not Gone | morto |
| O01 | `application/use_cases/ordinance_reading.py` | unmasked text sent to the AI | morto |
| O02 | `application/use_cases/ordinance_reading.py` | audit code of interrupted reading | morto |
| O03 | `application/use_cases/ordinance_reading.py` | grounding on the masked text | morto |
| O04 | `application/use_cases/ordinance_reading.py` | merge against the claimed copy, not the locked row | morto |
| O05 | `application/use_cases/ordinance_reading.py` | member names in the reading audit | morto |
| O06 | `application/use_cases/ordinance_reading.py` | illegible text code | morto |
| O07 | `application/use_cases/ordinance_reading.py` | log carries the error message | morto |
| K01 | `application/services/purge_inputs.py` | conclusion leaves the ordinance file | morto |
| K02 | `application/services/purge_inputs.py` | ordinance file not marked deleted | morto |
| K03 | `application/use_cases/conclusion.py` | ordinance file not counted as left | morto |
| K04 | `domain/rules/conclusion_rules.py` | pending_board omits the Parecer | morto |
| K05 | `domain/rules/conclusion_rules.py` | artifacts with all kinds | morto |
| K06 | `domain/rules/conclusion_rules.py` | pending ordinance inverted | morto |
| K07 | `infrastructure/database/repositories.py` | delete leaves board_opinions | morto |
| K08 | `infrastructure/database/repositories.py` | delete leaves dossier_deliveries | morto |
| K09 | `infrastructure/database/repositories.py` | delete allowed while the ordinance is being read | morto |
| K10 | `infrastructure/database/repositories.py` | delete does not remove the ordinance file | morto |
| D01 | `application/use_cases/dossier.py` | mark Entregue in a read-only process | morto |
| D02 | `application/use_cases/dossier.py` | mark a non-manual item | morto |
| D03 | `application/use_cases/dossier.py` | mark is not audited | morto |
| D04 | `application/use_cases/dossier.py` | checklist never compares the table version | morto |
| D05 | `application/use_cases/dossier.py` | GetDossier without the access check | morto |
| F01 | `f/components/OpinionForm.tsx` | OpinionForm pre-selects a conclusion | morto |
| F02 | `f/components/StepNav.tsx` | StepNav shows 6 steps | morto |
| F03 | `f/components/ConcludeDialog.tsx` | ConcludeDialog blocks on the pending board | morto |
| F04 | `f/components/DossierChecklist.tsx` | checklist order reversed | morto |
| F05 | `f/labels.ts` | state label Registrada changed | morto |
| F06 | `f/components/DossierChecklist.tsx` | Entregue box on every item | morto |
| F07 | `f/components/DossierChecklist.tsx` | other-version warning dropped | morto |
| F08 | `f/components/OrdinanceForm.tsx` | replace without the confirmation step | morto |
| F09 | `f/components/OrdinanceForm.tsx` | confirmed replacement sent without replace | morto |
| F10 | `f/components/OpinionForm.tsx` | notes limit 5001 | morto |
| F11 | `f/components/DossierChecklist.tsx` | Entregue boxes enabled in a read-only process | morto |
| F12 | `f/components/OpinionForm.tsx` | save allowed with notes over the limit | morto |
| F13 | `f/labels.ts` | state label Gerado changed | morto |
| F14 | `f/components/StepNav.tsx` | step 6 title | morto |
| F15 | `f/components/OrdinanceForm.tsx` | VALOR_SEM_ORIGEM not shown on the number | morto |
| F16 | `f/components/OpinionForm.tsx` | save sends a default conclusion | morto |
| F17 | `f/pages/ProcessBoard.tsx` | Etapa 6 editable when concluded | morto |
| F18 | `f/components/DossierChecklist.tsx` | Entregue box checked for generated state | sobrevive, equivalente: item MANUAL só tem os estados ENTREGUE e PENDENTE |
| F19 | `f/components/StepNav.tsx` | step 7 title | morto |
| W01 | `infrastructure/documents/opinion_docx.py` | DOCX Parecer without signature lines | morto |
| W02 | `infrastructure/documents/opinion_pdf.py` | PDF Parecer without signature lines | morto |
| W03 | `infrastructure/documents/request_docx.py` | DOCX Requerimento without the evaluation line | morto |
| W04 | `infrastructure/documents/request_pdf.py` | PDF Requerimento without the place and date line | morto |
| W05 | `infrastructure/documents/request_docx.py` | DOCX Requerimento without the option | morto |
| W06 | `infrastructure/documents/request_pdf.py` | PDF Requerimento without the LGPD text | morto |
| W07 | `infrastructure/documents/opinion_pdf.py` | PDF Parecer sections in reverse | morto |
| W08 | `infrastructure/documents/opinion_docx.py` | DOCX Parecer sections in reverse | morto |
| R13 | `application/use_cases/generated_documents.py` | the Parecer run makes an HTTP call (AI) | morto |
| U13 | `application/use_cases/board.py` | download of the ordinance file without the access check | morto |
| U14 | `application/use_cases/board.py` | re-read accepted while reading | sobrevive, equivalente: `request_reading` do repositório recusa a leitura já na fila com o mesmo `OPERACAO_EM_ANDAMENTO` |
| O08 | `application/use_cases/ordinance_reading.py` | weak OCR is trusted | morto |
| P01 | `infrastructure/database/repositories.py` | ordinance version check removed in the repository | morto |
| P02 | `infrastructure/database/repositories.py` | queue not oldest-first | morto |
| P03 | `infrastructure/database/repositories.py` | claim without SKIP LOCKED | morto (travamento): morto por travamento: sem `SKIP LOCKED` o segundo `claim` espera o lock da mesma thread e o teste não termina |
| L01 | `f/labels.ts` | TABELA_DESATUALIZADA label text changed | morto |
| L02 | `f/labels.ts` | conclusion labels swapped | morto |
| L03 | `f/labels.ts` | CONCLUSAO_AUSENTE label text changed | morto |
| L04 | `domain/rules/pt_format.py` | month name without the accent | morto |
| L05 | `domain/rules/pt_format.py` | month index off by one | morto |
| L06 | `application/use_cases/generated_documents.py` | TABELA_DESATUALIZADA message truncated | morto |
| L08 | `domain/rules/opinion_document.py` | blank text length | morto |
| L09 | `domain/rules/request_document.py` | greeting changed | morto |
| L10 | `domain/rules/opinion_document.py` | numeric minimum without two places | morto |
| L11 | `domain/rules/opinion_document.py` | missing subtotal defaults to 1 | morto |
| L12 | `domain/rules/request_document.py` | whitespace city not treated as empty | morto |

**Resumo do sensor**: 133 mutantes (132 contados mais a sonda R02, que reordenou duas verificações sem mudar o comportamento e fica fora da conta). 127 mortos (um deles, P03, por travamento do teste), 5 sobreviventes equivalentes (C08, U04, U11, U14, F18) e nenhum sobrevivente real. Os equivalentes têm a razão na própria linha: um guarda redundante que o repositório repete com o mesmo 409 (U04, U11, U14), uma verificação que a invariante AD-012 já garante (C08) e um estado que o item MANUAL nunca tem (F18). P03 (sem `SKIP LOCKED`) foi derrubado porque `test_two_concurrent_claims_never_take_the_same_ordinance` (`b/integration/documents/test_board_repository.py:305`) espera o lock da mesma thread e não termina; é uma detecção real, mas por travamento e não por asserção, ver O3.
**Sensor depth**: ampla
**Sensor**: 127 de 127 mutantes reais mortos, 5 equivalentes, 0 sobreviventes: PASS

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Sem recurso além do pedido | OK: a portaria é entidade própria (design, AD-025), o Parecer e o Requerimento são dois tipos de documento no mesmo fluxo; nada de IA no texto |
| Sem abstração de uso único | OK: `_BoardUseCase`, `check_opinion_inputs` e `latest_ready` têm mais de um uso (pedido e execução, checklist e conclusão) |
| Mudanças cirúrgicas | OK: os arquivos existentes mudaram só nos pontos que a spec exige (despacho por tipo em `generated_documents.py`, `conclusion_rules.py`, `purge_inputs.py`, `dossier_order.json`, `StepNav`, `ConcludeDialog`, `ProcessGenerated`) |
| Segue os padrões existentes | OK: rascunho com versão otimista, `FieldError`, `AuditService`, `GeneratedBlock`, `usePolling`, escritores no molde do Relatório |
| Domínio e aplicação puros (AD-001) | OK: `tests/architecture/test_layers.py` verde e `grep` sem importação proibida |
| Teste afirma o valor da spec | OK nos 44 requisitos; ver NOTAs para o que a spec não fixa |
| Cobertura por camada (domínio 1:1, rotas feliz, borda e erro) | OK: domínio com a tabela PAR-03 a PAR-06, REQ-02 a REQ-07 e DOS-01 a DOS-06 em `b/unit/domain`; todas as rotas novas com 200, 401, 404, 409 de versão e de somente leitura e 422 por campo (`test_board_api.py`, `test_board_file_api.py`, `test_dossier_api.py`) |
| Todo teste mapeia a um requisito | OK: nenhum teste sem requisito, caso de borda ou "Done when" |
| Diretrizes documentadas seguidas | `CLAUDE.md` (regras 1, 2, 5, 8, 9; dados sintéticos; chave só no backend), AD-001, AD-009, AD-011, AD-012, AD-015, AD-018, `backend/pyproject.toml` (`ruff` E,F,I,B,UP, linha 100) |

---

## Edge Cases

- [x] Portaria sem nenhum membro: lista vazia, `MEMBROS_NAO_ENCONTRADOS`, dá para digitar (`test_ordinance_reading.py:170`; `test_ordinance_grounding.py:146,153`; `OrdinanceForm.test.tsx:143`)
- [x] Mesmo nome duas vezes, ignorando maiúsculas e acentos: 422 `MEMBRO_REPETIDO` em `members[1].name` (`test_ordinance_save.py:270`; `test_board_rules.py:59,67`; `test_board_api.py:168`; G07 e G08 mortos)
- [x] Conclusão apaga o arquivo da portaria e mantém número, data e membros (`test_conclude_process.py:378`; `test_banca_parecer_acceptance.py:290`)
- [x] Exclusão do processo apaga a portaria, os dados, as marcas, os Pareceres e os Requerimentos (`test_delete_process.py:332,343`; `test_process_purge_repository.py`; K07 a K10 mortos)
- [x] Pedido do mesmo tipo com outro `GERANDO`: 409 `GERACAO_EM_ANDAMENTO` (`test_request_opinion.py:232`; `test_migration_board.py:204`)
- [x] Reinício durante a geração: `FALHOU` com `INTERROMPIDA` (`test_run_generation_opinion.py:271`) e durante a leitura da portaria (`test_ordinance_reading.py:333,356`; `test_generation_wiring.py:214`; O02 morto)

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run` (rodado uma vez na árvore real, em `HEAD` `2e89f84`, depois da correção `02846e9`)
- **Backend**: `ruff check .` sem achados ("All checks passed!"); `pytest -q -p no:cacheprovider`: **6312 passed, 3 deselected, 1 warning** em 1396,95 s (23 min 16 s; o aviso é `StarletteDeprecationWarning` de `httpx` no `TestClient`, anterior à feature). Nenhum dos dois testes intermitentes conhecidos (`test_a_database_error_while_claiming_does_not_kill_the_thread`, `test_an_output_above_the_limit_fails_and_leaves_no_file`) falhou nesta rodada, então não houve o que reexecutar; `test_asking_for_the_parecer_again_gives_version_2_and_keeps_version_1` passou na rodada completa
- **Frontend**: `npm run lint` saída 0; `npm run build` saída 0 (`dist/assets/index-B-iuMnrM.js` 419,86 kB); `npm test -- --run`: **55 arquivos e 765 testes passando**, saída 0
- **Test count before feature**: cerca de 673 no frontend (765 − (109 − 17), contando definições); no backend, 502 `def test_` novos e 5 removidos (os parametrizados fazem a contagem coletada ser maior que a de definições)
- **Delta**: +92 testes de frontend; backend +497 definições
- **Skipped/deselected**: 3 deselected no backend (`-m 'not maritalk_live'`, os testes que chamam a MariTalk de verdade e só rodam com `RUN_LIVE_MARITALK=1`); nenhum skip
- **Failures**: nenhuma
- **Árvore real**: `git status --porcelain` depois do sensor igual ao de antes (`?? backend/img/`, `?? requeriment.txt`, `?? test/`); `git worktree list` só com a árvore real; os contêineres PostgreSQL do sensor foram removidos

---

## Lacunas, em ordem

Nenhuma lacuna bloqueia. Nada virou tarefa de correção; as notas abaixo ficam para o autor decidir.

**Lacunas de precisão da spec (sem lacuna de código nem de teste)**

- **N1, PORT-10**: "a mensagem do limite" não diz o texto. O código devolve "O arquivo passa do tamanho máximo." (código `ARQUIVO_GRANDE`), a mesma do upload da Etapa 2, sem "20 MB"; a tela mostra o limite num texto fixo. Escolher entre fixar o texto na spec ou acrescentar "20 MB" à mensagem.
- **N2, PAR-03**: a spec fixa a ordem das seções e a frase da conclusão, mas não o texto das linhas de identificação, portaria, interstício e documentos analisados nem os rótulos dos grupos. Os testes fixam o texto que a Nota 5 do `tasks.md` decidiu ("Situação atual: nível 4 da classe B (Adjunto)", "Portaria da banca: nº 123/2025, de 10/03/2025.", "versão 3", "não gerado", "I - Atividades de ensino"). `test_opinion_document.py:136` confere a identificação por trechos e não por linha inteira.
- **N3, DOS-01**: a spec nomeia os itens por nome curto ("Relatório", "Comprovante", "Requerimento") e o arquivo tem os títulos longos de antes ("Relatório de progressão funcional", "Documentação comprobatória, em ordem e numerada", "Requerimento à CPPD, conforme o modelo"). `test_dossier_order_file.py:8` confere vários por `startswith`; as chaves, que identificam o item, são afirmadas por igualdade (`:24`).

**Observações menores (sem tarefa)**

- **O1**: `02846e9` trocou `[2, 1]` por o conjunto `[1, 2]` na lista de versões do Parecer. É coerente com a PAR-14 (que fala de manter as versões, não da ordem), mas a ordem de dois pedidos no mesmo instante fica indefinida na API.
- **O2**: a guarda de versão e a de "já na fila" aparecem no caso de uso e de novo no repositório (U04, U11, U14). Com as duas condições juntas, não há teste de qual 409 vence, e a spec também não ordena.
- **O3**: P03 só morreu por travamento: `test_board_repository.py:305` usa uma só thread e, sem `SKIP LOCKED`, o segundo `claim` espera o lock do primeiro. Um `lock_timeout` na segunda sessão faria o teste falhar rápido em vez de travar. A fila é de uma thread só (AD-008), então o risco real é baixo.
- **O4**: PORT-09 prova a ausência do Comprovante pela igualdade das entradas de geração e dos documentos, não por um Comprovante gerado com portaria; a separação estrutural (tabela própria) e `test_board_repository.py:434` sustentam.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| PORT-01..PORT-12 | Implemented | Verified |
| PAR-01..PAR-14 | Implemented | Verified |
| REQ-01..REQ-08 | Implemented | Verified |
| DOS-01..DOS-07 | Implemented | Verified |
| BNAV-01..BNAV-03 | Implemented | Verified |

---

## Summary

**Overall**: Ready (PASS)

**Spec-anchored check**: 44 de 44 requisitos com o valor da spec afirmado; 3 notas de precisão da spec (N1 PORT-10, N2 PAR-03, N3 DOS-01), nenhuma lacuna de código
**Sensor**: 127 de 127 mutantes reais mortos (5 equivalentes explicados)
**Gate**: backend 6312 passando, frontend 765 passando, ruff, lint e build limpos

**What works**: a portaria é lida pela IA só com texto mascarado e cada valor é conferido no texto original da página; o que a pessoa digitou nunca é sobrescrito; o Parecer e o Requerimento saem por regras puras, sem IA, com a classe e o nível como digitados e o Total copiado da Tabela; `TABELA_DESATUALIZADA` é conferida no pedido e na execução, por total e por versão da tabela; a conclusão não é preenchida nem sugerida em lugar nenhum; o checklist segue a ordem do arquivo; a conclusão remove só o arquivo da portaria e a exclusão apaga tudo.

**Issues found**: nenhum que bloqueie.

**Next steps**: marcar T51 como Done, passar os 44 requisitos para `Verified` e fechar a feature. Push e deploy só com a autorização do usuário.

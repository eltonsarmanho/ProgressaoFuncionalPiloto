# Layout oficial: Parecer pelo modelo e brasão da UFPA (layout-oficial) Validation

**Date**: 2026-11-23
**Spec**: `.specs/features/layout-oficial/spec.md` (40 requisitos: PMOD-01..29, BRAS-01..11), com as Assumptions, os Edge Cases, as decisões da seção Notas de `tasks.md` (confirmadas pelo usuário em 2026-11-23) e `CLAUDE.md`
**Diff range**: `a658128..HEAD` (`e0e4b91`), branch `feat/inteligencia-documental`: 28 commits, 68 arquivos, +2873 −1069 (T1 a T24 mais as correções FT1 a FT4 `c58cb43`, `d7c018a`, `2987f4f`, `e0e4b91`); as correções mexem em quatro arquivos (`1016e91..HEAD`: +98 −2), e o único código de produção é `opinion_pdf.py` (cor da linha)
**Verifier**: agente independente (autor diferente), duas rodadas (a rodada 1 deu FAIL e a rodada 2, de re-verificação, deu PASS; o corpo abaixo traz as duas, e as marcas "rodada 1" dizem o que mudou). Não leu nem listou `Documentos/`, `Modelos/`, `corpus-reports/`, `requeriment.txt` nem `test/`; não procurou o modelo `Parecer.pdf`; sem push, deploy, VM nem rede. Sensor em cópia isolada sob o scratchpad (nunca `git stash`, nunca a árvore real); `git status --porcelain` da árvore real igual ao de antes (só `?? backend/img/`, `?? requeriment.txt`, `?? test/`, mais este relatório e os arquivos de lições); `git worktree list` mostra só a árvore real.

**Result**: PASS

Os 40 requisitos têm teste com `arquivo:linha` e cada asserção usa o valor que a spec define. A rodada 1 deu FAIL por sobreviventes reais do sensor (escritor do Parecer em PDF sem teste de centralização, justificação, entrelinha 1,5 e corpo de 12 pt; espaço de 3 mm dos PDF só com limite inferior; `keepNext` só com a presença afirmada) e por um defeito visual cosmético (linha cinza). As quatro correções (FT1 `c58cb43`, FT2 `d7c018a`, FT3 `2987f4f`, FT4 `e0e4b91`) fecham todos: na rodada 2 os oito sobreviventes (M43, M76, M82, M84, M85, M88, M89, M90) e a falha da linha cinza morrem na cópia isolada, uma amostra nova de 20 falhas de comportamento também morre (29 de 29), o gate está verde e a amostra regenerada mostra a linha preta. Não há defeito de código; ficam duas notas de precisão da spec (cor da linha e quebra da linha de local e data em branco), que não são lacuna.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1, T2 (Fase 1: `spell_number`, `to_roman`, `format_place_date`) | Done | `8f56da8`, `ba63edd` |
| T3..T8 (Fase 2: texto do Parecer, Liberation Sans, DOCX, PDF, geração, sem Observações) | Done | `5d6c3c0`, `3e5a47e`, `3f5a49e`, `b14700f`, `c622368`, `33c42ec` |
| T9 (Fase 3: formulário sem Observações) | Done | `2ce4256` |
| T10..T16 (Fase 4: brasão, ajudantes, Tabela, Relatório) | Done | `9cc3a36`, `bbab919`, `cf4dce0`, `d6d6418`, `ee00e4b`, `2ce5925`, `87dd255` |
| T17..T22 (Fase 5: Comprovante, Requerimento, Parecer, aceitação) | Done | `688bf77`, `1c498a0`, `02b1f2b`, `44884ec`, `39ff62d`, `b3185a0` |
| T23, T24 (Fase 6: documentação) | Done | `4aeb4e8`, `1016e91` |
| T25 (Verifier) | Done (rodada 2) | este relatório, PASS depois de FT1..FT4 |

**Test integrity**: nenhum teste removido sem substituto nas áreas tocadas; os testes do Parecer antigo (seções, Total geral, assinaturas, observações) foram reescritos para o modelo (`test_opinion_document.py`, `test_opinion_pdf.py`, `test_opinion_docx.py`, `test_run_generation_opinion.py`, `test_banca_parecer_acceptance.py`, `test_document_writer.py`, `test_opinion_save.py`, `test_board_api.py`, `OpinionForm.test.tsx`). As correções só acrescentaram testes (+5 no backend) e reforçaram duas asserções. Contagem: backend 6508 (6503 mais os 5 testes das correções) e frontend 764; ver Gate Check.

---

## Spec-Anchored Acceptance Criteria

Caminhos relativos a `backend/tests/` (b/) e `frontend/src/` (f/). Os mutantes citados (M, J, F) estão na tabela do sensor.

### P1: Texto do Parecer pelo modelo oficial

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| PMOD-01 | A4 retrato; só brasão, cabeçalho, título, linha de local e data, parágrafo e linhas dos membros, nesta ordem | `b/unit/domain/test_opinion_document.py:416` (`vars(document)` é exatamente `page, header_lines, title, place_date_line, paragraph, member_lines`); `b/unit/infrastructure/test_opinion_docx.py:69` (`texts == ["", cabeçalho x3, "PARECER", linha, PARAGRAPH, "PRESIDENTE: ...", "MEMBRO 1: ..."]`) e `:95` (210 x 297 mm); `b/unit/infrastructure/test_opinion_pdf.py:52` (595 x 842 pt), `:61` (ordem dos marcadores) | PASS |
| PMOD-02 | Cabeçalho em três linhas centralizadas, serifa, "Universidade Federal do Pará", campus, "<unidade> – <sigla>", e linha horizontal na largura do texto | `b/unit/domain/test_opinion_document.py:340` (`header_lines == (..., "Campus Universitário Sintético", "Faculdade de Testes Sintéticos – FATS")`); `b/unit/infrastructure/test_opinion_docx.py:117` (centralizado, `pBdr/bottom` só na última linha); `b/unit/infrastructure/test_opinion_pdf.py:146` (serifa), `:170` (um traço de `LEFT` a `PAGE_WIDTH - RIGHT`); `b/integration/doc_usecases/test_run_generation_opinion.py:148` (campus no texto dos dois arquivos) | PASS (rodada 2): `b/unit/infrastructure/test_opinion_pdf.py:253` (`(box.x0 + box.x1) / 2 == approx((LEFT + PAGE_WIDTH - RIGHT) / 2, abs=1.5)` para as três linhas do cabeçalho), `:198` (`rules[0]["color"] == (0.0, 0.0, 0.0)`, uma só linha horizontal); M84, M85 e a linha cinza mortos. Antes: GAP (M84) |
| PMOD-03 | Sem unidade-mãe `CAMPUS`: só "Universidade Federal do Pará" e "<unidade> – <sigla>" | `b/unit/domain/test_opinion_document.py:350` (`parent` `None` e `INSTITUTE`: duas linhas); `b/unit/infrastructure/test_opinion_docx.py:85`; `b/integration/doc_usecases/test_run_generation_opinion.py:158` (`"Campus Universitário" not in text`); mutante M18 morto | PASS |
| PMOD-04 | "PARECER" centralizado, negrito, sem serifa | `b/unit/domain/test_opinion_document.py:360` (`title == "PARECER"`); `b/unit/infrastructure/test_opinion_docx.py:127` (`[("Arial", True)]`, `CENTER`); `b/unit/infrastructure/test_opinion_pdf.py:139` (`("LiberationSans-Bold", "PARECER") in found`) | PASS (rodada 2): `b/unit/infrastructure/test_opinion_pdf.py:253` (`"PARECER"` com centro igual ao da área de texto, ±1,5 pt); M88 morto. Antes: GAP (M88) |
| PMOD-05 | "<Cidade>, <dd> de <Mês> de <aaaa>." sem zero à esquerda, mês com maiúscula, em Sans, a partir da metade da largura | `b/unit/domain/test_opinion_document.py:172` (os doze meses, `"Belém, 27 de {capital} de 2025."`), `:181` (`"Belém, 7 de Maio de 2025."`); `b/unit/domain/test_pt_format.py:169` (`"2 de Abril de 2025"`); `b/unit/infrastructure/test_opinion_docx.py:135` (Arial, `left_indent.mm == 80.0`); `b/unit/infrastructure/test_opinion_pdf.py:163` (`x0 == LEFT + (PAGE_WIDTH - LEFT - RIGHT) / 2`), `:144` (só a linha na face Sans); mutantes M08, M09, M67, M68, M95 mortos | PASS |
| PMOD-06 | Parágrafo único justificado, recuo de primeira linha, entrelinha 1,5, com o texto do modelo | `b/unit/domain/test_opinion_document.py:74` (igualdade exata: "Aos vinte e sete dias do mês de maio de dois mil e vinte e cinco, reuniram-se os membros da Banca de Análise, nomeados pela Portaria nº 123/2025, Ana Presidente Souza (presidente), Bruno Membro Lima, Carla Membro Reis, responsáveis por analisar o Relatório de Atividades do Professor Adjunto Nível IV Maria Docente da Silva, para fins de progressão funcional do docente, referente ao interstício de 23/11/2022 a 23/11/2024, para Classe C (Associado) Nível I. Após a análise, os membros APROVARAM o referido relatório."); `b/unit/infrastructure/test_opinion_docx.py:145` (`JUSTIFY`, recuo 1,25 cm, `line_spacing == 1.5`); `b/unit/infrastructure/test_opinion_pdf.py:188` (recuo só na primeira linha) | PASS (rodada 2): `b/unit/infrastructure/test_opinion_pdf.py:262` (`box.x1 == approx(PAGE_WIDTH - RIGHT, abs=1.5)` em toda linha do parágrafo menos a última, e `:263` a última termina 20 pt antes), `:272` (`{size} == {12.0}`) e `:274` (`pitches == [approx(18.0, abs=0.5)] * n`, 18 = 1,5 x 12 pt da spec e do DOCX, `test_opinion_docx.py:145`); M82, M89 e M90 mortos. Antes: GAP |
| PMOD-07 | Negrito só nas palavras da data (sem "Aos") e em "<denominação> Nível <n> <nome>" | `b/unit/domain/test_opinion_document.py:86` (`bold_runs == ["vinte e sete dias do mês de maio de dois mil e vinte e cinco", "Adjunto Nível IV Maria Docente da Silva"]`, "Aos " e "Professor " fora); `b/unit/infrastructure/test_opinion_docx.py:153`; `b/unit/infrastructure/test_opinion_pdf.py:128`; mutantes M22, M69 mortos | PASS |
| PMOD-08 | Dia de 2 a 31: "Aos <cardinal> dias do mês de <mês> de <ano por extenso>" | `b/unit/domain/test_opinion_document.py:111` (2, 21, 31: "Aos dois dias", "Aos vinte e um dias", "Aos trinta e um dias"), `:74` (27 e 2025); `b/unit/domain/test_spelled_numbers.py:40` (tabela: 27 "vinte e sete", 2025 "dois mil e vinte e cinco", 1999 "mil novecentos e noventa e nove", 2020 e 2026 pela mesma regra de "dois mil e dez", 2100 "dois mil e cem", 2101 "dois mil cento e um", 100 "cem", 101 "cento e um"), `:51` (volta pelo leitor do projeto para 1 a 2999); mutantes M01 a M07, M19, M21, M27 mortos | PASS |
| PMOD-09 | Dia 1: "Ao primeiro dia do mês de <mês> de <ano por extenso>" | `b/unit/domain/test_opinion_document.py:123` (`startswith("Ao primeiro dia do mês de janeiro de dois mil e vinte e seis, reuniram-se")`; negrito começa em "primeiro dia"); mutante M19 morto; teste fixo `b/integration/api/test_banca_parecer_acceptance.py:203` (dia 1 de abril de 2025 nos dois arquivos) | PASS |
| PMOD-10 | `FAVORAVEL`: "os membros APROVARAM o referido relatório" | `b/unit/domain/test_opinion_document.py:188`; `b/integration/doc_usecases/test_run_generation_opinion.py:116` (nos dois arquivos); mutante M12 morto | PASS |
| PMOD-11 | `DESFAVORAVEL`: "os membros NÃO APROVARAM o referido relatório" | `b/unit/domain/test_opinion_document.py:192`; `b/unit/infrastructure/test_opinion_docx.py:164`; `b/integration/doc_usecases/test_run_generation_opinion.py:133` (`"os membros APROVARAM" not in text`); mutantes M12, M23 mortos | PASS |
| PMOD-12 | Níveis em romanos; classe e denominações como digitadas | `b/unit/domain/test_opinion_document.py:208` ("Adjunto Nível I", "Classe C (Associado) Nível IV."), `:215` (0 e 4000 saem como digitados), `:223` (salto de A para C, "Titular-Livre"); `b/unit/domain/test_pt_format.py:156` (I, II, III, IV, V, IX, X, XIV, XL, XC, CD, MCMXCIV, MMMCMXCIX), `:164` (0, -1, 4000 levantam `ValueError`); mutantes M10, M11, M16, M17 mortos | PASS |
| PMOD-13 | Só `PRESIDENTE` e `MEMBRO`, presidente primeiro, linhas centralizadas "PRESIDENTE: <nome>", "MEMBRO <n>: <nome>", sem assinatura | `b/unit/domain/test_opinion_document.py:240` (linhas exatas, suplente ausente), `:251` (presidente que não é o primeiro); `b/unit/infrastructure/test_opinion_docx.py:172` (`CENTER`, sem `___`, sem sublinhado, sem suplente); `b/unit/infrastructure/test_opinion_pdf.py:61` (termina em "MEMBRO 1: Bruno Membro Lima", sem suplente); mutantes M13, M14, M24, M86 mortos | PASS (rodada 2): `b/unit/infrastructure/test_opinion_pdf.py:253` (`"PRESIDENTE: Ana Presidente Souza"` e `"MEMBRO 1: Bruno Membro Lima"` centralizadas, ±1,5 pt); M85 e N01 (alinhadas à direita) mortos. Antes: GAP (M85) |
| PMOD-14 | Sem `PRESIDENTE`: sem "(presidente)" e só "MEMBRO <n>" | `b/unit/domain/test_opinion_document.py:271` (`"(presidente)" not in paragraph`, linhas `("MEMBRO 1: ...", "MEMBRO 2: ...")`); `b/unit/infrastructure/test_opinion_pdf.py:88` (PDF = DOCX sem presidente e sem campus); mutante M15 morto | PASS |
| PMOD-15 | Nomes, docente e número da portaria como registrados, sem título | `b/unit/domain/test_opinion_document.py:324` ("Prof. Dr." digitado sai como está, "89/2025 - CCAME", sem "Prof. Prof." nem "Dr. Bruno"), `:311` (15 membros e nome de 200 caracteres inteiros) | PASS |
| PMOD-16 | Sem data: "Aos ______ dias do mês de ________ de ________" e "<Cidade>, ____ de ________ de ________." | `b/unit/domain/test_opinion_document.py:370` (os dois textos exatos, sem erro); mutantes M31, M33 mortos | PASS |
| PMOD-17 | Sem local: "__________" no lugar da cidade | `b/unit/domain/test_opinion_document.py:379`, `:385` (só espaços) (`"__________, 27 de Maio de 2025."`); mutante M26 morto | PASS |
| PMOD-18 | Sem número da portaria: "__________" depois de "Portaria nº" | `b/unit/domain/test_opinion_document.py:391` (`"nomeados pela Portaria nº __________, Ana Presidente Souza"`); mutante M29 morto | PASS |
| PMOD-19 | Sem "Total geral", "Mínimo de referência", "Documentos analisados", "Pontuação por grupo", "Observações", "Identificação", "Portaria da banca:", "Conclusão", sem tabela e sem rodapé | `b/unit/domain/test_opinion_document.py:400` (os oito textos ausentes); `b/unit/infrastructure/test_opinion_docx.py:194` (`tables == []`, rodapé sem `PAGE`/`NUMPAGES`); `b/unit/infrastructure/test_opinion_pdf.py:203` (`"Página" not in`, `find_tables().tables` vazio); `b/integration/doc_usecases/test_layout_oficial_generation.py:117` e `b/integration/doc_usecases/test_run_generation_opinion.py:101` (nos arquivos gerados); mutantes M72, M87 mortos | PASS |

### P1: Gerar o Parecer pelo modelo

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| PMOD-20 | Versão imutável em DOCX e PDF com o mesmo texto na mesma ordem | `b/unit/infrastructure/test_opinion_pdf.py:82` (`pdf_text == docx_text`), `:88`, `:125` (15 membros), `:268`; `b/integration/doc_usecases/test_run_generation_opinion.py:88` (versão 1 `PRONTO`, DOCX e PDF), `:116` (o parágrafo do modelo nos dois), `:297` (versão 2 e as duas no histórico); `b/integration/api/test_banca_parecer_acceptance.py:203` | PASS |
| PMOD-21 | Até três titulares: PDF de uma página A4 | `b/unit/infrastructure/test_opinion_pdf.py:95` (`len(pdf) == 1` com `THREE_TITULARS`), `:102` (com um suplente), `:247` (com brasão e campus); amostra real: 1 página | PASS |
| PMOD-22 | Recusa 422 com o código na ordem `CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE`, `TABELA_DESATUALIZADA` | `b/integration/doc_usecases/test_request_opinion.py:63` (sem conclusão mesmo sem membros e sem tabela), `:76` (só membros), `:142`, `:161`, `:172`; `b/integration/api/test_banca_parecer_acceptance.py:203` (422 com `detail[0].code == "CONCLUSAO_AUSENTE"`), `:237`; mutante J03 morto | PASS |
| PMOD-23 | Só suplentes: 422 `BANCA_SEM_MEMBROS` | `b/integration/doc_usecases/test_request_opinion.py:100` (só suplentes recusa, nenhuma linha criada), `:111` (sem conclusão vence), `:118` (sem tabela: `BANCA_SEM_MEMBROS` antes de `TABELA_AUSENTE`), `:125` (suplente e membro aceitos), `:133` (só presidente aceito); mutantes J01, J02 mortos | PASS |
| PMOD-24 | Instantâneo com os mesmos campos de antes, mesmo sem imprimi-los | `b/integration/doc_usecases/test_run_generation_opinion.py:101` (`snapshot["total"] == table.snapshot["total"]`, subtotais), `:179` (tabela, versões, campos e portaria), `:215`, `:225`, `:239` (mínimo); `b/integration/doc_usecases/test_layout_oficial_generation.py:129`; `b/integration/api/test_banca_parecer_acceptance.py:203` (`summary.total`) | PASS |
| PMOD-25 | Texto sem chamar a IA | `b/integration/doc_usecases/test_run_generation_opinion.py:317` (`no_ai`); `b/unit/domain/test_opinion_document.py:440` (sem relógio, sem `maritalk`, sem `app.infrastructure`) | PASS |

### P1: Etapa 6 sem o campo Observações

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| PMOD-26 | Minuta só com conclusão (sem valor inicial), data e local, sem "Observações da banca" nem contador | `f/components/OpinionForm.test.tsx:34` (dois rádios, `Data do Parecer`, `Local`, `queryByLabelText("Observações da banca")` e `/Observações/` ausentes, sem `/\d+ \/ 5 000/`), `:47` (nenhum rádio marcado); mutantes F01, F04, F05 mortos | PASS |
| PMOD-27 | `notes` no corpo: 422 | `b/integration/api/test_board_api.py:227` (`status_code == 422`, `field_of(response) == "notes"`, nada gravado), `:196` (a resposta é exatamente `{conclusion, opinion_date, place, version}`); mutantes J06, J07, F02 mortos | PASS |
| PMOD-28 | Coluna e texto de `notes` ficam, sem leitura, impressão nem alteração | `b/integration/documents/test_board_opinion_repository.py:134` (`UPDATE ... notes = 'Texto antigo'`, depois `update` de conclusão, data e local: `stored_notes == "Texto antigo"`, `not hasattr(read, "notes")`); `b/integration/doc_usecases/test_opinion_save.py:94` (auditoria só com `conclusion`, `opinion_date`, `place_length`); `grep notes backend/app` sem ocorrência ligada ao Parecer fora de `models.py:674,686`; nenhum arquivo em `backend/alembic` no diff | PASS |
| PMOD-29 | Local acima de 100 caracteres: 422 em `place` | `b/unit/domain/test_board_rules.py:85` (100 passa, 101 erra), `:90`; `b/integration/doc_usecases/test_opinion_save.py:106` (`ValidationFailed.field == "place"`, nada gravado); `b/integration/api/test_board_api.py:237,243` (200 e 422 em `place`); `f/components/OpinionForm.test.tsx:104` (a mensagem junto do campo, `toBeInvalid`); mutantes J08, F03 mortos | PASS |

### P1: Brasão da UFPA nos documentos oficiais

| Req | Resultado definido pela spec | `arquivo:linha` + asserção | Resultado |
| --- | ---------------------------- | -------------------------- | --------- |
| BRAS-01 | Brasão como primeiro elemento da primeira página da Tabela, DOCX e PDF | `b/unit/infrastructure/test_table_docx.py:302` (`body[0]` é `w:p` centralizado, `cx == 720_000`, segundo é "TABELA DE PONTUAÇÃO"); `b/unit/infrastructure/test_table_pdf.py:262` (largura 20 mm, centro da página paisagem, `rect.y1 + 3 * mm <= title.y0`); `b/integration/doc_usecases/test_layout_oficial_generation.py:79,96`; mutantes M54, M55, M65 mortos | PASS |
| BRAS-02 | Idem no Relatório | `b/unit/infrastructure/test_report_docx.py:197` (brasão e depois as três linhas); `b/unit/infrastructure/test_report_pdf.py:174` (acima do cabeçalho, centrado na área de texto); `b/integration/doc_usecases/test_layout_oficial_generation.py:79,96`; mutantes M56, M57, M66 mortos | PASS |
| BRAS-03 | Capa do Comprovante, nenhuma outra página | `b/unit/infrastructure/test_front_matter.py:199` (capa com imagem de 20 mm, centro 297,6 pt, `rect.y1 + 3 * mm <= title.y0`), `:212` (sumário e separadores sem imagem), `:223` (`TOC_CAPACITY == 44` e mesmo número de páginas); `b/unit/infrastructure/test_comprovante_assembler.py:361` (`with_emblem == [0]` no PDF montado), `:349`; `b/integration/doc_usecases/test_layout_oficial_generation.py:96,110`; mutantes M62, M63, M64, M80 mortos | PASS |
| BRAS-04 | Parecer: primeiro elemento, acima das três linhas do cabeçalho | `b/unit/infrastructure/test_opinion_docx.py:220` (`body[0]` centralizado, `cx == 720_000`, depois as três linhas), `:238` (sem campus); `b/unit/infrastructure/test_opinion_pdf.py:235` (imagem acima de "Universidade Federal do Pará"); mutantes M60, M61, M83 mortos | PASS |
| BRAS-05 | Requerimento: primeiro elemento, acima de "MINISTÉRIO DA EDUCAÇÃO" | `b/unit/infrastructure/test_request_docx.py:137` (primeiro é o brasão, segundo "MINISTÉRIO DA EDUCAÇÃO"); `b/unit/infrastructure/test_request_pdf.py:109`; mutantes M58, M59 mortos | PASS |
| BRAS-06 | Centralizado, 2,0 cm de largura, altura proporcional a 279 x 351, 3 mm abaixo, igual em todos | `b/unit/infrastructure/test_emblem.py:37` (`width == 20.0`, `height ≈ 25.16`), `:44` (`EMBLEM_WIDTH_MM == 20.0`, `EMBLEM_GAP_MM == 3.0`); `b/unit/infrastructure/test_emblem_docx.py:52` (`cx == 720_000`, `cy == cx * 351 / 279 ± 1`), `:61` (`after == 170` twips ± 1, `keepNext` existe); `b/unit/infrastructure/test_emblem_pdf.py:44,53,86` e os testes de cada PDF (`rect.width ≈ 20 * mm ± 0.5`, `rect.height ≈ 20 * mm * 351 / 279`, centro ± 0,5); `b/integration/doc_usecases/test_layout_oficial_generation.py:79,96` | PASS (rodada 2): `b/unit/infrastructure/test_emblem_pdf.py:65` (`spacer.height == approx(3 * mm)`) e `:69` (`3 * mm <= gap <= 3 * mm + leading`, teto de uma entrelinha), M76 morto; `b/unit/infrastructure/test_emblem_docx.py:69` (`keepNext` sem `w:val` ou com `1`/`true`/`on`), M43 morto. Antes: GAP (M76, M43) |
| BRAS-07 | Documento com mais de uma página: brasão só na primeira | `b/unit/infrastructure/test_emblem_pdf.py:70`; `b/unit/infrastructure/test_table_pdf.py:275` (300 linhas), `test_report_pdf.py:191`, `test_opinion_pdf.py:256` (15 membros), `test_front_matter.py:212`; `b/integration/doc_usecases/test_layout_oficial_generation.py:109` (`all(page.get_images() == [] for page in list(pdf)[1:])`); DOCX: uma imagem no pacote (`test_table_docx.py:316`, `test_report_docx.py:214`, `test_opinion_docx.py:249`); mutante M52 morto | PASS |
| BRAS-08 | Texto de cada documento, do cabeçalho em diante, igual ao de antes | `b/unit/infrastructure/test_table_pdf.py:284` (`startswith("TABELA DE PONTUAÇÃO Docente: ...")`, 2 páginas, "Página 1 de 2"), `test_table_docx.py:327`; `test_report_pdf.py` (`test_the_pdf_has_the_same_text_in_the_same_order_as_the_docx_of_the_model` sem mudança); `test_request_docx.py:157`, `test_request_pdf.py:124`; `test_front_matter.py:236` (a capa: "COMPROVANTE DE DOCUMENTOS" e "Docente: ..."); os testes de texto existentes seguem passando só com o parágrafo do brasão pulado | PASS |
| BRAS-09 | PNG versionado em `app/infrastructure/documents/assets/ufpa.png`, levado pelo `COPY app ./app` | `b/unit/infrastructure/test_emblem.py:20` (arquivo filho de `app`, `"COPY app ./app" in Dockerfile`), `:28` (PNG de 279 x 351), `:82` (nenhum módulo cita `img/ufpa.png`, nenhum `COPY img`); verificado: `cmp backend/img/ufpa.png backend/app/infrastructure/documents/assets/ufpa.png` idêntico (SHA-256 `61e2b240...ff84e`), `git ls-files` lista o arquivo, `.dockerignore` não o exclui, `backend/img/` fora do git | PASS |
| BRAS-10 | Brasão ausente ou não PNG: `EmblemUnavailable` com o nome do arquivo, versão `FALHOU` com `ERRO_INTERNO`, sem arquivo | `b/unit/infrastructure/test_emblem.py:49` (a mensagem tem `ufpa.png` e não o caminho), `:60` (vazio), `:69` (texto); cada escritor: "sem o arquivo levanta e não escreve" (`test_opinion_docx.py:260`, `test_opinion_pdf.py:284`, `test_table_*`, `test_report_*`, `test_request_*`, `test_front_matter.py:245`, `test_comprovante_assembler.py:349`); `b/integration/doc_usecases/test_layout_oficial_generation.py:139` (cinco tipos: `state is FALHOU`, `error_code is ERRO_INTERNO`, mensagem fixa, `files == ()`, `stored_files == before`, log `error_type=EmblemUnavailable`, sem `private-dir`); mutantes M37, M39, M40, M44, M50, M51, J10, J11 mortos | PASS |
| BRAS-11 | Gerar de novo leva o brasão à versão nova e mantém as anteriores com os mesmos bytes | `b/integration/doc_usecases/test_layout_oficial_generation.py:174` (SHA-256 da Tabela e do Parecer v1 iguais depois da v2, v2 com arquivos próprios), `:187` (a v2 tem o brasão), `:196` (tentativa sem brasão não toca a v1) | PASS |

**Status**: 40 de 40 requisitos com asserção igual ao valor da spec (na rodada 1, 35; os cinco com lacuna de teste no PDF, PMOD-02, 04, 06, 13 e BRAS-06, fechados na rodada 2). Nenhuma lacuna de código. Duas observações de precisão da spec (ver Spec-precision notes), que não são lacuna.

### Pontos específicos pedidos

- **(a) PDF do Parecer de uma página com até três titulares e sem estouro**: `test_opinion_pdf.py:95,102,247` e a amostra real (1 página, brasão e cabeçalho completos). Com 15 membros de 200 caracteres o PDF passa para 3 páginas, o brasão só na primeira e todos os nomes aparecem (`test_opinion_pdf.py:111,125,256`); a amostra `parecer_15membros_nomes200.pdf` confirma. PASS.
- **(b) DOCX e PDF com o mesmo texto**: `test_opinion_pdf.py:82,88,125,268` comparam o texto normalizado do PDF com o do DOCX do mesmo modelo (inclusive 15 membros, sem campus, sem presidente e em branco). PASS.
- **(c) Brasão do pacote = `backend/img/ufpa.png`**: `cmp` idêntico, mesmo SHA-256, dentro de `app` (`Dockerfile:31 COPY app ./app`), `backend/img/` fora do `.dockerignore` e fora do git, nunca tocado. PASS.
- **(d) `notes` fora do caso de uso, da API, do repositório e do frontend, com a coluna no banco**: `grep "notes"` em `backend/app` só acha `processes`, `norms`, `scoring`, `seed.py`, e, do Parecer, só `models.py:674,686` (coluna e `CHECK`) e o docstring de `repositories.py:2527`; `notes_length` e `MAX_NOTES` do Parecer não existem mais; `frontend/src` só tem o "Observações" do processo (Etapa 1) e das normas; nenhum arquivo de `alembic` no diff. PASS.
- **(e) Nenhum nome real**: os testes novos usam "Ana Presidente Souza", "Bruno Membro Lima", "Carla Membro Reis", "Davi Suplente Rocha", "Eva Presidente Dias", "Maria Docente da Silva", "Faculdade de Testes Sintéticos" e "Campus Universitário Sintético"; "Campus Universitário do Tocantins/Cametá" e "Ana Beatriz Lima" são fixtures anteriores à feature; "89/2025 - CCAME" é um código de órgão da própria spec, não uma pessoa. PASS.
- **(f) Arquitetura e AD-012**: `opinion_document.py` só importa módulos de `app.domain` (o teste `test_opinion_document.py:440` e `tests/architecture/test_layers.py` passam); o brasão e as fontes ficam em `infrastructure/documents`; AD-012 coberto por `test_layout_oficial_generation.py:174`. PASS.

---

## Visual Check

Amostras geradas pelos escritores reais com dados sintéticos (nomes fictícios), em `/tmp/claude-1000/-home-nees-Documents-VSCodigo-ProgressaoFuncionalPiloto/118aba81-5621-4e3f-847f-fa68c56fc9d9/scratchpad/layout-oficial-samples/`, primeira página em PNG a 110 dpi (PDF) e a 80 dpi (DOCX convertido pelo LibreOffice):

| Documento | Arquivo | Resultado |
| --------- | ------- | --------- |
| Tabela PDF (paisagem) | `tabela.pdf`, `tabela.png` | brasão no topo, centralizado, proporção correta, acima do título, sem sobreposição; a Tabela fica com 2 páginas como antes |
| Relatório PDF | `relatorio.pdf`, `relatorio.png` | brasão centralizado acima de "Serviço Público Federal"; nada sobreposto |
| Comprovante (frente) | `comprovante_front.pdf`, `comprovante_front.png` | brasão só na capa, acima do título, sem encostar; o sumário e os separadores sem brasão (4 páginas geradas) |
| Requerimento PDF | `requerimento.pdf`, `requerimento.png` | brasão acima de "MINISTÉRIO DA EDUCAÇÃO"; uma página |
| Parecer PDF | `parecer.pdf`, `parecer.png` | estrutura do modelo: brasão, três linhas do cabeçalho, linha horizontal, "PARECER" em Sans negrito, linha de local e data a partir da metade, parágrafo justificado com a data e o docente em negrito, linhas centralizadas, uma página |
| Parecer PDF, outras | `parecer_desfavoravel_3titulares.pdf`, `parecer_sem_campus_sem_data.pdf`, `parecer_15membros_nomes200.pdf` | três titulares em uma página e "NÃO APROVARAM"; sem campus e sem data com os traços em branco; 15 membros de 200 caracteres em 3 páginas, brasão só na primeira |
| Parecer PDF, rodada 2 | `round2/parecer_round2.pdf`, `round2/parecer_round2.png` | gerado pelo escritor real depois das correções, dados sintéticos: a linha horizontal do cabeçalho está preta; brasão, três linhas centralizadas, "PARECER" em Sans negrito, linha de local e data a partir da metade, parágrafo justificado com negrito na data e no docente, duas linhas de membros centralizadas, uma página |
| DOCX convertidos (LibreOffice) | `docx_pdf/parecer.pdf`, `parecer_docx.png`, `tabela_docx.png`, `relatorio.pdf`, `requerimento.pdf` | os quatro DOCX abrem e mostram o brasão no topo, centralizado; o Parecer DOCX tem uma página com a linha horizontal preta |

Defeitos visuais, todos cosméticos e sem requisito que os proíba:

- **V1 (corrigido por FT3, `2987f4f`; rodada 2: preta na amostra `round2/parecer_round2.png`)**: antes, a linha horizontal do cabeçalho do Parecer em PDF saía cinza claro (`HRFlowable` com a cor padrão `lightgrey`, `(0.827, 0.827, 0.827)`), enquanto no DOCX sai preta (`w:color auto`). A spec só diz "linha horizontal" (precisão da spec); agora o teste também confere a cor preta (`test_opinion_pdf.py:198`).
- **V2**: com data e local em branco, a linha "__________, ____ de ________ de ________." não cabe na metade da largura e quebra em duas linhas (o recuo de metade da largura deixa 80 mm para a linha). O texto está certo; só a quebra é feia. Com cidade e data normais cabe.

---

## Discrimination Sensor

Cópia isolada em `<scratchpad>/mut/backend` (e `<scratchpad>/mutfe` para o frontend, com `node_modules` ligado por link simbólico), cada mutante aplicado, testado e revertido; nunca `git stash`; `PYTHONDONTWRITEBYTECODE=1` e `__pycache__` apagado a cada mutante. Linha-base na cópia: 333 testes unitários alvo passando. 110 falhas reais injetadas (mais um controle de identidade, J05, que sobreviveu por construção e fica fora da conta).

| # | Arquivo | Falha injetada | Resultado |
| - | ------- | -------------- | --------- |
| M01 | `domain/rules/spelled_numbers.py` | "e" sempre depois de "mil" | morto |
| M02 | idem | nunca "e" depois de "mil" | morto |
| M03 | idem | 100 vira "cento" | morto |
| M04 | idem | dezenas sem "e" ("vinte sete") | morto |
| M05 | idem | 1000 vira "um mil" | morto |
| M06 | idem | limite superior 3000 aceito | morto |
| M07 | idem | sem "e" entre centena e resto | morto |
| M08 | `domain/rules/pt_format.py` | mês minúsculo na linha de local e data | morto |
| M09 | idem | dia com zero à esquerda | morto |
| M10 | idem | romanos sem `CM` | morto |
| M11 | idem | limite 4000 aceito em `to_roman` | morto |
| M12 | `domain/rules/opinion_document.py` | APROVARAM e NÃO APROVARAM trocados | morto |
| M13 | idem | suplentes entram como membros | morto |
| M14 | idem | "MEMBRO n" desde 0 | morto |
| M15 | idem | sem "(presidente)" | morto |
| M16 | idem | níveis em algarismos arábicos | morto |
| M17 | idem | classe pretendida lida da classe atual | morto |
| M18 | idem | linha do campus para qualquer unidade-mãe | morto |
| M19 | idem | dia 1 no plural | morto |
| M20 | idem | mês com maiúscula no parágrafo | morto |
| M21 | idem | anos por extenso só até 2099 | morto |
| M22 | idem | palavras da data sem negrito | morto |
| M23 | idem | sem `ValueError` sem conclusão | morto |
| M24 | idem | membros antes dos presidentes | morto |
| M25 | idem | hífen no lugar do travessão | morto |
| M26 | idem | local de só espaços não vira traço | morto |
| M27 | idem | dia em algarismos | morto |
| M28 | idem | título "Parecer" | morto |
| M29 | idem | sem traço quando o número da portaria falta | morto |
| M30 | idem | "promoção funcional" no lugar de "progressão funcional" | morto |
| M31 | idem | traços da data em branco da linha alterados | morto |
| M32 | idem | interstício com início e fim trocados | morto |
| M33 | idem | linha de local e data em branco usa o mês por extenso | morto |
| M34 | `infrastructure/documents/emblem.py` | largura de 25 mm | morto |
| M35 | idem | espaço de 0 mm | morto |
| M36 | idem | espaço de 1 mm | morto |
| M37 | idem | assinatura de PNG não conferida | morto |
| M38 | idem | altura invertida (largura por altura) | morto |
| M39 | idem | `emblem_path` sem validar | morto |
| M40 | idem | mensagem com o caminho completo do servidor | morto |
| M41 | `documents/docx_support.py` | brasão alinhado à esquerda | morto |
| M42 | idem | sem espaço abaixo | morto |
| M43 | idem | `keep_with_next = False` | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M44 | idem | brasão ausente é ignorado em silêncio | morto |
| M45 | idem | altura esticada | morto |
| M46 | idem | sem texto alternativo | morto |
| M47 | `documents/pdf_styles.py` | brasão à esquerda | morto |
| M48 | idem | `Spacer` de 0 | morto |
| M49 | idem | `draw_emblem` sem centralizar | morto |
| M50 | idem | `emblem_flowables` ignora a falta do arquivo | morto |
| M51 | idem | `draw_emblem` ignora a falta do arquivo | morto |
| M52 | idem | brasão repetido em toda página (`NumberedCanvas`) | morto |
| M53 | idem | largura de meio brasão | morto |
| M54 | `table_docx.py` | sem a chamada de `add_emblem` | morto |
| M55 | `table_pdf.py` | sem `emblem_flowables` | morto |
| M56 | `report_docx.py` | sem `add_emblem` | morto |
| M57 | `report_pdf.py` | sem `emblem_flowables` | morto |
| M58 | `request_docx.py` | sem `add_emblem` | morto |
| M59 | `request_pdf.py` | sem `emblem_flowables` | morto |
| M60 | `opinion_docx.py` | sem `add_emblem` | morto |
| M61 | `opinion_pdf.py` | sem `emblem_flowables` | morto |
| M62 | `front_matter.py` | capa sem brasão | morto |
| M63 | idem | brasão também no sumário | morto |
| M64 | idem | brasão encosta no título da capa | morto |
| M65 | `table_docx.py` | brasão depois do título (não é o primeiro) | morto |
| M66 | `report_pdf.py` | brasão depois do cabeçalho (não é o primeiro) | morto |
| M67 | `opinion_pdf.py` | linha de local e data com recuo de um terço | morto |
| M68 | `opinion_docx.py` | idem, no DOCX | morto |
| M69 | `opinion_pdf.py` | negrito do parágrafo removido | morto |
| M70 | `opinion_docx.py` | parágrafo sem justificar | morto |
| M71 | idem | linha horizontal em todas as linhas do cabeçalho | morto |
| M72 | `opinion_pdf.py` | rodapé "Página N de M" | morto |
| M73 | idem | sem recuo de primeira linha | morto |
| M74 | idem | título em serifa | morto |
| M75 | idem | texto sem `xml_safe` | morto |
| M76 | `pdf_styles.py` | espaço abaixo do brasão de 12 mm nos PDF | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M77 | `docx_support.py` | espaço abaixo de 12 mm no DOCX | morto |
| M78 | `opinion_docx.py` | título sem negrito | morto |
| M79 | idem | recuo de primeira linha de 2,5 cm | morto |
| M80 | `front_matter.py` | brasão da capa fora do centro | morto |
| M81 | `opinion_docx.py` | entrelinha 1,0 | morto |
| M82 | `opinion_pdf.py` | entrelinha 1,0 | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M83 | idem | brasão depois do cabeçalho | morto |
| M84 | idem | cabeçalho alinhado à esquerda | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M85 | idem | linhas dos membros à esquerda | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M86 | `opinion_docx.py` | linhas dos membros à esquerda | morto |
| M87 | idem | rodapé com `PAGE` | morto |
| M88 | `opinion_pdf.py` | título à esquerda | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M89 | idem | parágrafo sem justificar | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M90 | idem | corpo de 10 pt | **sobreviveu** na rodada 1; **morto** na rodada 2 |
| M91 | idem | sem a linha horizontal | morto |
| M92 | `opinion_docx.py` | corpo de 10 pt | morto |
| M93 | idem | cabeçalho à esquerda | morto |
| M94 | idem | título à esquerda | morto |
| M95 | `opinion_pdf.py` | linha de local e data em serifa | morto |
| J01 | `application/use_cases/generated_documents.py` | só suplentes aceitos | morto |
| J02 | idem | suplente conta como titular | morto |
| J03 | idem | `BANCA_SEM_MEMBROS` antes de `CONCLUSAO_AUSENTE` | morto |
| J04 | idem | unidade-mãe nunca lida (campus some) | morto |
| J06 | `presentation/schemas/board.py` | `notes` aceito de novo no corpo | morto |
| J07 | idem | `notes` devolvido na resposta | morto |
| J08 | `domain/rules/board_rules.py` | limite de 100 do local removido | morto |
| J10 | `generated_documents.py` | log com a mensagem do erro (vaza o caminho) | morto |
| J11 | idem | falha do brasão fechada com outro código | morto |
| J12 | idem | instantâneo do Parecer sem as versões usadas | morto |
| F01 | `f/components/OpinionForm.tsx` | campo "Observações da banca" de volta | morto |
| F02 | idem | corpo do `PUT` com `notes: null` | morto |
| F03 | idem | erro de `place` não mostrado | morto |
| F04 | idem | conclusão pré-marcada | morto |
| F05 | idem | contador "0 / 5 000" de volta | morto |

**Sobreviventes da rodada 1** (8 de 110; nenhum é equivalente, exceto M43 que é quase equivalente; todos mortos na rodada 2, abaixo):

| Mutante | Por que sobrevive | Requisito | Veredito |
| ------- | ----------------- | --------- | -------- |
| M84 cabeçalho do Parecer PDF à esquerda | `test_opinion_pdf.py` não afirma o alinhamento de nenhum parágrafo | PMOD-02 | real: tarefa F1 |
| M88 título do Parecer PDF à esquerda | idem | PMOD-04 | real: tarefa F1 |
| M85 linhas dos membros do Parecer PDF à esquerda | idem | PMOD-13 | real: tarefa F1 |
| M89 parágrafo do Parecer PDF sem justificar | idem | PMOD-06 | real: tarefa F1 |
| M82 entrelinha 1,0 no Parecer PDF | só o DOCX afirma `line_spacing == 1.5` | PMOD-06 | real: tarefa F1 |
| M90 corpo de 10 pt no Parecer PDF | só o DOCX afirma 12 pt (`test_opinion_docx.py:106`); 12 pt é a suposição "Fontes do Parecer" da spec | Assumptions, PMOD-21 | real: tarefa F1 |
| M76 espaço de 12 mm abaixo do brasão nos PDF | `rect.y1 + 3 * mm <= texto.y0` é limite inferior; o teste de constante `EMBLEM_GAP_MM == 3.0` não vê o `Spacer` | BRAS-06 | real: tarefa F2 |
| M43 `keepNext` com `val=0` | o teste só confere que o elemento `w:keepNext` existe | BRAS-06 (detalhe de desenho da T11) | quase equivalente: o parágrafo do brasão é sempre o primeiro do corpo, então manter com o próximo não muda o resultado; tarefa F3, opcional |

**Sensor depth**: ampla (110 falhas reais; matriz de risco: números por extenso, romanos, texto do Parecer, recusas, brasão em cada escritor e `notes`)
**Result (rodada 1)**: 102 de 110 mortos, 8 sobreviventes (7 reais e 1 quase equivalente) → FAIL

### Rodada 2 (re-verificação, `HEAD` `e0e4b91`)

Cópia isolada nova (`git archive HEAD backend` em `<scratchpad>/v2/backend`, interpretador do `.venv` real, `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` apagado a cada mutante, arquivo restaurado depois de cada um e a árvore `app` da cópia conferida com `diff -r` contra o `HEAD`); nunca `git stash`, nunca a árvore real; nenhum `git worktree` criado. Linha-base: 197 testes dos 13 arquivos de documentos (`test_opinion_pdf/docx`, `test_emblem*`, `test_table_*`, `test_report_*`, `test_request_*`, `test_front_matter`, `test_pdf_styles`) passando. Cada mutante roda esse conjunto com `-x`; o teste que falhou aparece na coluna de resultado.

| # | Arquivo | Falha injetada | Resultado (teste que falhou) |
| - | ------- | -------------- | ---------------------------- |
| M43 | `docx_support.py` | `keep_with_next = False` | morto (`test_emblem_docx.py::test_the_space_after_the_paragraph_is_3_mm_and_it_stays_with_the_next`) |
| M76 | `pdf_styles.py` | `Spacer` de 12 mm no lugar de 3 mm | morto (`test_emblem_pdf.py::test_the_space_below_the_emblem_is_exactly_3_mm`) |
| M82 | `opinion_pdf.py` | entrelinha 1,0 | morto (`test_opinion_pdf.py::test_the_paragraph_is_set_in_12_pt_with_one_and_a_half_line_spacing`) |
| M84 | idem | cabeçalho à esquerda | morto (`...::test_the_header_the_title_and_the_member_lines_are_centered_on_the_text_area`) |
| M85 | idem | linhas dos membros à esquerda | morto (mesmo teste de centralização) |
| M88 | idem | título à esquerda | morto (mesmo teste de centralização) |
| M89 | idem | parágrafo sem justificar | morto (`...::test_the_paragraph_is_justified_up_to_its_last_line`) |
| M90 | idem | corpo de 10 pt | morto (`...::test_the_paragraph_is_set_in_12_pt_with_one_and_a_half_line_spacing`) |
| GREY | idem | sem `color=colors.black` (linha cinza de volta) | morto (`...::test_the_horizontal_rule_under_the_header_is_black_as_in_the_docx`) |
| N01 | idem | linhas dos membros à direita (`alignment=2`) | morto (teste de centralização) |
| N02 | idem | cabeçalho à direita | morto (teste de centralização) |
| N03 | idem | sem recuo de primeira linha | morto (`...::test_the_paragraph_is_indented_on_its_first_line_only`) |
| N04 | idem | recuo de 2,5 cm | morto (mesmo teste de recuo) |
| N05 | idem | negrito em todas as partes | morto (`...::test_the_date_words_and_the_current_situation_with_the_name_are_bold_and_aos_is_not`) |
| N06 | idem | título em Sans sem negrito | morto (`...::test_the_title_and_the_place_and_date_line_are_sans_and_the_rest_is_serif`) |
| N07 | `emblem.py` | largura do brasão de 20,5 mm | morto (`...::test_the_first_page_has_the_emblem_centered_on_the_text_above_the_university`) |
| N08 | idem | largura de 19 mm | morto (mesmo teste) |
| N09 | `front_matter.py` | brasão também no sumário | morto (`test_front_matter.py::test_only_the_cover_has_the_emblem_not_the_table_of_contents_nor_the_separators`) |
| N10 | idem | brasão também nos separadores | morto (mesmo teste) |
| N11 | `docx_support.py` | brasão alinhado à direita | morto (`test_opinion_docx.py::test_the_first_element_is_the_centered_emblem_followed_by_the_header`) |
| N12 | `opinion_docx.py` | entrelinha 2,0 | morto (`...::test_the_paragraph_is_justified_with_a_first_line_indent_and_one_and_a_half_spacing`) |
| N13 | idem | sem recuo de primeira linha | morto (mesmo teste) |
| N14 | idem | negrito em todas as partes | morto (`...::test_only_the_date_words_and_the_current_situation_with_the_name_are_bold`) |
| N15 | `opinion_pdf.py` | linhas dos membros em ordem inversa | morto (`...::test_the_text_comes_in_the_order_of_the_model`) |
| N16 | idem | linha horizontal com 60% da largura | morto (`...::test_a_horizontal_rule_crosses_the_text_width_under_the_header`) |
| N17 | `front_matter.py` | brasão da capa encostado no título (55 mm do topo) | morto (`test_front_matter.py::test_the_cover_has_the_emblem_centered_above_the_title_without_touching_it`) |
| N18 | `pdf_styles.py` | brasão dos PDF à direita | morto (`test_opinion_pdf.py::test_the_first_page_has_the_emblem_centered_on_the_text_above_the_university`) |
| N19 | `opinion_docx.py` | linha de local e data com recuo de um quarto | morto (`...::test_the_place_and_date_line_is_arial_and_starts_at_half_the_text_width`) |
| N20 | `opinion_pdf.py` | linha de local e data com recuo de um quarto | morto (`...::test_the_place_and_date_line_starts_at_half_the_text_width`) |

Uma primeira versão de N01 e N02 usava `TA_RIGHT`, que `opinion_pdf.py` não importa: morreram por `NameError` e não contaram; foram refeitas com `alignment=2` (o valor de `TA_RIGHT`) e morreram pelo teste de centralização.

**Sensor depth (rodada 2)**: ampla, 9 reaplicações da rodada 1 (8 sobreviventes e a linha cinza) e 20 falhas novas (centralização de cabeçalho e membros por outro valor, recuo, negrito, largura do brasão, brasão só na primeira página do Comprovante, alinhamento e entrelinha no DOCX, ordem, largura da linha horizontal, recuo da linha de local e data)
**Result (rodada 2)**: 29 de 29 mortos, nenhum sobrevivente → PASS. Juntando as duas rodadas: 110 falhas da rodada 1 (102 mortas e 8 reais que a rodada 2 matou) e 20 novas, nenhuma sobrevivente no `HEAD`.

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Sem recurso além do pedido | OK: só o Parecer, o brasão e o corte de `notes` |
| Sem abstração de uso único | OK: `add_emblem`, `emblem_flowables` e `draw_emblem` têm nove usos; `spell_number`, `to_roman` e `format_place_date` têm um uso cada mas são funções puras de domínio com testes próprios |
| Mudanças cirúrgicas | OK: cada escritor só ganhou a chamada do brasão; o texto de cada documento ficou igual (BRAS-08) |
| Segue os padrões existentes | OK: `FONTS_DIR` e `register_fonts` para as fontes, `xml_safe` em todo texto, `PdfCanvas`/`NumberedCanvas` |
| Domínio e aplicação puros (AD-001) | OK: `tests/architecture/test_layers.py` verde; `opinion_document.py` sem importação de infraestrutura |
| Teste afirma o valor da spec | OK no texto, no brasão e (rodada 2) no layout do Parecer em PDF e no espaço de 3 mm dos PDF: 18 pt = 1,5 x 12 pt (spec e DOCX), 12 pt e centro da área de texto vêm da spec, nenhum valor copiado da implementação; o teto do espaço usa `build_styles(11).body.leading` só como limite superior |
| Cobertura por camada | OK: domínio 1:1 com PMOD-01..19 e todos os casos de borda; escritores com DOCX e PDF; casos de uso com todas as recusas e a ordem; API com 200, 422 de `notes` e de `place`; frontend |
| Todo teste mapeia a um requisito | OK; `test_the_error_is_a_runtime_error_so_the_generation_closes_as_failed` mapeia a BRAS-10 |
| Diretrizes documentadas seguidas | `CLAUDE.md` (regras 1, 2, 5, 8; dados sintéticos; sem `Documentos/`), AD-001, AD-011, AD-012, AD-025, `backend/pyproject.toml` (`ruff` E,F,I,B,UP) |

---

## Edge Cases

- [x] 15 membros ou nomes de 200 caracteres: todos escritos, segunda página, sem cortar (`test_opinion_document.py:311`; `test_opinion_pdf.py:111,125`; amostra de 3 páginas)
- [x] Os doze meses em minúsculas no parágrafo e com inicial maiúscula na linha (`test_opinion_document.py:155`)
- [x] Dia 1, 2, 21 e 31 (`test_opinion_document.py:111,123`)
- [x] Anos 2000, 2025, 2100 e 2101 por extenso (`test_opinion_document.py:132`; `test_spelled_numbers.py:29-36`)
- [x] Ano fora de 1000 a 2999 em algarismos (`test_opinion_document.py:147`: 999 e 3000)
- [x] Nível fora de 1 a 3999 como digitado (`test_opinion_document.py:215`)
- [x] Unidade-mãe que não é `CAMPUS`: sem a linha (`test_opinion_document.py:350`, `INSTITUTE`)
- [x] Um único `PRESIDENTE` (`:284`), dois `PRESIDENTE` (`:291`)
- [x] Caractere de controle ou marcação num nome, escrito limpo e como texto (`test_opinion_pdf.py:210`; `test_opinion_docx.py:205`)
- [x] Tabela paisagem longa, Relatório longo e Comprovante com sumário cheio: mesmo número de páginas, brasão só na primeira (`test_table_pdf.py:275,284`; `test_report_pdf.py:191`; `test_front_matter.py:223`)
- [x] Arquivo do brasão ausente, vazio ou sem assinatura de PNG falha (`test_emblem.py:49,60,69`)
- [x] Falha por causa do brasão: mensagem fixa e log só com o tipo e o identificador (`test_layout_oficial_generation.py:139`)
- [x] Versões anteriores do Parecer mantêm os bytes (`test_layout_oficial_generation.py:174`)

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`, rodado uma vez na árvore real em cada rodada (rodada 1 em `1016e91`, rodada 2 em `e0e4b91`)
- **Backend, rodada 2**: `ruff check .` sem achados ("All checks passed!"); `pytest -q -p no:cacheprovider`: **6508 passed, 3 deselected, 1 warning** em 1107,58 s (18 min 27 s; o aviso é o `httpx` do `TestClient`, anterior à feature), saída 0. Nenhum dos dois testes intermitentes conhecidos falhou. Rodada 1: 6503 passed.
- **Frontend, rodada 2**: `npm run lint` saída 0; `npm run build` saída 0 (`dist/assets/index-34Iv_AYQ.js` 419,41 kB); `npm test -- --run`: 55 arquivos, **764 testes passando**, saída 0 (igual à rodada 1)
- **Skipped/deselected**: 3 deselected no backend (`-m 'not maritalk_live'`, testes que chamam a MariTalk de verdade); nenhum skip
- **Test integrity**: contagem do backend subiu de 6503 para 6508, +5 testes novos (`test_opinion_pdf.py` 3 de layout e 1 de cor da linha, `test_emblem_pdf.py` 1 do espaço de 3 mm) e 2 asserções reforçadas (`test_emblem_docx.py:66-69` e o teto do espaço); nenhum teste removido nem asserção enfraquecida
- **Árvore real**: `git status --porcelain` depois do sensor e dos gates igual ao de antes (` M .specs/LESSONS.md`, ` M .specs/lessons.json`, `?? .specs/features/layout-oficial/validation.md`, `?? backend/img/`, `?? requeriment.txt`, `?? test/`); `git worktree list` mostra só a árvore real

---

## Fix Plans

Máximo de 3 voltas de correção e nova verificação; esta foi a segunda (rodada 2) e fechou tudo.

| Fix | Prioridade | Commit | Verificação na rodada 2 |
| --- | ---------- | ------ | ----------------------- |
| FT1: layout do Parecer em PDF (centro do cabeçalho, do título e dos membros; justificação; 12 pt; entrelinha de 18 pt) | Major | `c58cb43` | `test_opinion_pdf.py:237,256,266`; M82, M84, M85, M88, M89, M90 mortos |
| FT2: espaço de 3 mm abaixo do brasão com teto | Minor | `d7c018a` | `test_emblem_pdf.py:61`; M76 morto |
| FT3: linha do cabeçalho do Parecer em PDF preta (V1) | Cosmetic | `2987f4f` (código: `opinion_pdf.py:107`) | `test_opinion_pdf.py:188`; linha cinza morta; amostra `round2/parecer_round2.png` com a linha preta |
| FT4: valor de `keepNext` afirmado no DOCX | Cosmetic | `e0e4b91` | `test_emblem_docx.py:66-69`; M43 morto |

Detalhes conferidos contra a spec e não contra a implementação:

- **FT1**: o centro esperado é `(LEFT + PAGE_WIDTH - RIGHT) / 2` (as margens do modelo, 30 mm e 20 mm, com tolerância de 1,5 pt); a justificação é afirmada pela borda direita de toda linha do parágrafo menos a última em `PAGE_WIDTH - RIGHT` e pela última linha mais curta que isso por 20 pt (um alinhamento à esquerda falha); o passo entre linhas é 18 pt = 1,5 x 12 pt, o valor que a spec (PMOD-06 e a suposição "Fontes do Parecer") e o DOCX (`test_opinion_docx.py:145`, `line_spacing == 1.5`; `opinion_docx.py:23,26`) definem, com tolerância de 0,5 pt. A asserção de 12 pt vale para todas as linhas de texto da página (`test_opinion_pdf.py:275`), inclusive o título e a linha de local e data, para os quais a spec não fixa o tamanho (ver notas).
- **FT2**: a altura do `Spacer` é 3 mm (spec BRAS-06) e a distância da base da imagem à tinta da primeira linha fica entre 3 mm e 3 mm mais uma entrelinha; um espaço de 12 mm passa de longe do teto.
- **FT3**: a spec (PMOD-02) só diz "linha horizontal"; o modelo e o DOCX são pretos, e o teste exige exatamente `(0.0, 0.0, 0.0)` numa só linha horizontal. Ver nota de precisão.
- **FT4**: um `<w:keepNext/>` sem `w:val` liga a propriedade, um `w:val="0"` ou `false` a desliga; o teste aceita só `None`, `1`, `true` e `on`.

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| PMOD-01..29 | Implemented | Verified |
| BRAS-01..11 | Implemented | Verified |

`spec.md` e `tasks.md` foram atualizados no commit desta verificação (T25 Done, 40 requisitos Verified), porque o veredito da rodada 2 é PASS e o `validate_state.py` passa.

---

## Spec-precision notes

Nenhuma é lacuna de teste ou de código; são pontos em que a spec não fixa um valor (⚠️ Spec-precision gap, sem tarefa de correção):

- **PMOD-02, V1**: "linha horizontal na largura do texto" não diz a cor nem a espessura; o PDF e o DOCX usam preto de 0,75 pt desde FT3. Fixar na spec ("linha preta").
- **PMOD-05, V2**: a linha de local e data "a partir da metade da largura" não diz o que fazer quando não cabe; com data e local em branco ("__________, ____ de ________ de ________.") o texto quebra em duas linhas (80 mm de largura). Nota documentada: a spec não define o comportamento; o texto está certo e a quebra é só visual.
- **PMOD-06**: "espaçamento entre linhas de cerca de 1,5" não define a tolerância; o DOCX usa exatamente 1,5 e o PDF 18 pt para 12 pt (tolerância de 0,5 pt no teste).
- **Tamanho do título e da linha de local e data**: a suposição "Fontes do Parecer" fixa 12 pt para corpo e cabeçalho e silencia sobre o título e a linha de local e data; o escritor usa 12 pt em tudo e `test_opinion_pdf.py:275` exige 12 pt em todas as linhas, então muda-se esse teste se a spec passar a permitir outro tamanho para o título.
- **BRAS-06**: "3 mm de espaço abaixo" é a distância entre a base da imagem e o começo do bloco seguinte; no PDF o texto tem ainda a folga da entrelinha, então a distância medida até a tinta do texto é maior que 3 mm. A spec não diz se a medida é até a caixa do parágrafo ou até a tinta; o teste de FT2 aceita de 3 mm a 3 mm mais uma entrelinha.
- **Spec × amostra**: o nome do campus no cabeçalho é o cadastrado ("Campus Universitário do Tocantins/Cametá" no seed), não o do modelo (Notas de `tasks.md`).

---

## Summary

**Overall**: Ready (PASS na rodada 2, depois do FAIL da rodada 1 por teste que não discriminava)

**Spec-anchored check**: 40 de 40 requisitos com o valor da spec afirmado; 5 notas de precisão da spec (cor da linha, quebra da linha de local e data em branco, tolerância de 1,5, tamanho do título, medida dos 3 mm), nenhuma lacuna
**Sensor**: rodada 2, 29 de 29 mortos (os 8 sobreviventes e a linha cinza da rodada 1, mais 20 falhas novas); no total 130 falhas de comportamento e nenhuma sobrevivente no `HEAD`
**Gate**: backend 6508 passando, frontend 764 passando, ruff, lint e build limpos

**What works**: o texto do Parecer segue o modelo palavra por palavra (extensos, romanos, "Ao primeiro dia", APROVARAM/NÃO APROVARAM, suplentes de fora, traços em branco); o layout do Parecer em PDF agora é protegido (centralização, justificação, 12 pt, 18 pt de passo, linha preta); as quatro recusas e a ordem delas; `notes` fora da API, do caso de uso, do repositório e da tela, com a coluna e o texto antigo no banco; o brasão do pacote idêntico ao do usuário, primeiro elemento, centralizado, de 20 mm com 3 mm de espaço limitado dos dois lados, só na primeira página dos cinco documentos, com falha clara e sem arquivo quando falta; versões antigas com os mesmos bytes.

**Issues found**: nenhuma aberta. As cinco da rodada 1 (FT1 a FT4) estão corrigidas e verificadas.

**Next steps**: commit da verificação; push e deploy só com a autorização do usuário.

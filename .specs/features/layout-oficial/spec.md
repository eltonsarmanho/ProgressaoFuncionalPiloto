# Layout oficial: Parecer pelo modelo e brasão da UFPA nos documentos gerados (layout-oficial) Specification

**Status**: Approved (usuário, 2026-11-23)
**Origem**: pedidos do usuário em 2026-11-23, depois de testar o Parecer gerado pela feature `banca-parecer`.

## Problem Statement

O Parecer que o sistema gera hoje tem uma estrutura própria (identificação, portaria, documentos analisados, pontos por grupo, Total geral, mínimo, conclusão, observações e linhas de assinatura), e o modelo oficial da banca (`Parecer.pdf`, uma página A4) é outro: cabeçalho institucional, título, local e data, um parágrafo único com a data por extenso, os membros da banca e a decisão, e as linhas dos membros. Além disso, os documentos oficiais que o sistema gera (Tabela de Pontuação, Relatório de Atividades, Comprovante, Parecer e Requerimento) saem sem o brasão da UFPA, que o documento oficial leva no topo. A feature faz o Parecer seguir o modelo, sem outra estrutura textual, e põe o brasão, centralizado, no alto da primeira página de cada um dos cinco documentos.

## Goals

- [ ] O Parecer gerado (DOCX e PDF) tem só os elementos do modelo oficial, com o texto do modelo preenchido com os dados do processo, e nenhum dos textos "Total geral", "Mínimo de referência" e "Observações".
- [ ] O brasão da UFPA é o primeiro elemento da primeira página de cada documento oficial gerado (Tabela, Relatório, Comprovante, Parecer e Requerimento, em DOCX e em PDF onde existem os dois), centralizado e do mesmo tamanho em todos.
- [ ] A imagem do brasão viaja com o código (pacote do backend e imagem Docker), e a falta dela faz a geração falhar com erro claro, nunca sai um documento sem o brasão.
- [ ] A Etapa 6 deixa de pedir "Observações da banca", sem apagar o que já foi gravado no banco.

## Out of Scope

Explicitamente excluído. Documentado para evitar crescimento do escopo.

| Feature | Reason |
| ------- | ------ |
| Mudar documentos já gerados | AD-012: a versão gerada é imutável; só as versões novas levam o brasão e o novo texto do Parecer |
| Apagar a coluna `board_opinions.notes` ou migrar dados | Decisão do usuário em 2026-11-23: a coluna e as linhas antigas ficam sem uso; nenhuma migração nova |
| Brasão nas telas do sistema e nos demais arquivos (portaria da banca, documentos de entrada) | O pedido é só para os cinco documentos oficiais gerados |
| Brasão nas páginas de sumário, separadores e originais do Comprovante | Decisão do usuário em 2026-11-23: só no topo do documento (a capa do Comprovante) |
| Mudar o texto de cabeçalho, de título ou de corpo da Tabela, do Relatório, do Comprovante e do Requerimento | O brasão só entra acima do que já existe |
| Linha de assinatura, "Prof." ou "Dr." no Parecer | O modelo não tem linha de assinatura; o sistema escreve os nomes como registrados na portaria |
| Conclusão do Parecer sugerida ou decidida pelo sistema | Regra 1 e AD-025: a conclusão é sempre da pessoa |
| Tela para escolher a unidade-mãe (campus) da unidade | A API de unidades já aceita `parent_id`; esta feature só lê o que está cadastrado |
| Brasão vetorial (SVG/EMF) ou PDF/A | O arquivo fornecido é PNG; PDF/A não é requisito do projeto |

---

## Assumptions & Open Questions

Toda ambiguidade é resolvida ou registrada aqui. "Confirmed? y" é decisão do usuário (2026-11-23); "n" é padrão do agente que o usuário confirma ao aprovar a spec.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Estrutura do Parecer | A do modelo oficial `Parecer.pdf` (uma página A4 retrato): cabeçalho de três linhas e linha horizontal, "PARECER", local e data, parágrafo único, linhas dos membros. Nenhuma outra estrutura textual | Pedido do usuário em 2026-11-23: "o modelo de parecer deve seguir o modelo oficial (Parecer.pdf). Não use outra estrutura textual." | y |
| Conclusão no texto | `FAVORAVEL` escreve "os membros APROVARAM o referido relatório"; `DESFAVORAVEL` escreve "os membros NÃO APROVARAM o referido relatório" | Decisão do usuário em 2026-11-23 | y |
| O que sai do Parecer | Nenhum total, nenhum mínimo de referência, nenhum documento analisado, nenhuma observação e nenhuma seção do formato antigo (PAR-03 a PAR-06 ficam substituídos) | Decisão do usuário em 2026-11-23: o modelo não os tem | y |
| Campo "Observações" | Sai da Etapa 6, da API e do documento; a coluna `board_opinions.notes` e as linhas antigas ficam no banco sem uso, e o limite de 5 000 caracteres (PAR-13) deixa de existir; o limite de 100 caracteres do local fica | Decisão do usuário em 2026-11-23 | y |
| Recusas do Parecer | `CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE` e `TABELA_DESATUALIZADA`, nesta ordem, exatamente como em PAR-07 a PAR-10, mesmo que o total não seja mais impresso | Decisão do usuário em 2026-11-23: o Parecer continua exigindo Tabela em dia | y |
| Membros no Parecer | Só `PRESIDENTE` e `MEMBRO`; os suplentes não aparecem (continuam registrados na portaria); ordem da portaria com o `PRESIDENTE` primeiro; linhas "PRESIDENTE: <nome>" e "MEMBRO 1: <nome>", "MEMBRO 2: <nome>" ...; sem `PRESIDENTE`, o parágrafo não diz "(presidente)" e as linhas são só "MEMBRO n" | Decisão do usuário em 2026-11-23 | y |
| Nomes e número da portaria | Escritos como estão registrados; o sistema nunca acrescenta "Prof. Dr." (a pessoa pode digitá-lo); o número sai como registrado depois de "Portaria nº" (a pessoa pode digitar "89/2025 - CCAME") | Decisão de 2026-11-23, segue o modelo | y |
| Linha do campus | Nome da unidade-mãe da unidade do processo quando ela é do tipo `CAMPUS` (o seed tem "Campus Universitário do Tocantins/Cametá"); sem unidade-mãe `CAMPUS`, a linha não sai | Decisão de 2026-11-23, segue o modelo | y |
| Linha da unidade | "<nome da unidade> – <sigla>" com travessão (U+2013) e um espaço de cada lado | Decisão de 2026-11-23, segue o modelo | y |
| Linha de local e data | Local e data do Parecer; mês com inicial maiúscula nesta linha e minúscula no parágrafo | Decisão de 2026-11-23, segue o modelo | y |
| Níveis em romanos | O nível atual e o pretendido saem em algarismos romanos (o processo guarda o número digitado na Etapa 1); a letra da classe e as denominações ficam como digitadas (NMOV-01: nunca deduzidas) | Decisão de 2026-11-23, segue o modelo | y |
| "para fins de progressão funcional do docente" | Texto literal para progressão e para promoção | Decisão de 2026-11-23, segue o modelo | y |
| Data e local em branco | Data em branco: "Aos ______ dias do mês de ________ de ________" no parágrafo; local em branco: "__________" na linha de local e data; nenhuma recusa nova | Decisão de 2026-11-23 | y |
| Data da reunião | A data do Parecer é a data usada no parágrafo | Decisão de 2026-11-23 | y |
| Números por extenso | Código puro do domínio, dias de 1 a 31 e anos de 1000 a 2999 com a forma certa ("vinte e sete", "dois mil e vinte e cinco"); dia 1 usa o singular: "Ao primeiro dia do mês de ..."; os outros dias: "Aos <cardinal> dias do mês de ..." | Decisão do usuário em 2026-11-23 (o modelo diz "dias"; "um dias" seria errado) | y |
| Brasão: arquivo | O PNG fornecido pelo usuário (`backend/img/ufpa.png`, 279 por 351 px, fora do git) é copiado, com o mesmo conteúdo, para `backend/app/infrastructure/documents/assets/ufpa.png`, versionado; o `Dockerfile` copia `app`, então a imagem o leva; o original em `backend/img/` não entra no commit | Pedido do usuário em 2026-11-23 e o `backend/Dockerfile`, que copia só `app` e `alembic` | y |
| Brasão: tamanho e lugar | Primeiro elemento da primeira página, centralizado na largura do texto, com cerca de 2,0 cm de largura e altura proporcional (cerca de 2,52 cm), e um espaço pequeno abaixo; igual em todos os documentos; o texto de cabeçalho que já existe vem logo abaixo | Pedido do usuário em 2026-11-23 | y |
| Quais documentos | Tabela de Pontuação (DOCX e PDF; o PDF é paisagem), Relatório de Atividades (DOCX e PDF), Comprovante (PDF, só a capa), Parecer (DOCX e PDF) e Requerimento (DOCX e PDF) | Pedido do usuário em 2026-11-23 | y |
| Brasão ausente | A geração falha com erro claro; o documento nunca sai sem o brasão | Pedido do usuário em 2026-11-23 | y |
| Versões já geradas | Não mudam (AD-012); só as versões novas levam o brasão e o novo texto do Parecer | Pedido do usuário em 2026-11-23 | y |
| Dia na linha de local e data | Sem zero à esquerda ("7 de Maio de 2025"), como no Requerimento ("10 de março de 2025", mês em minúscula) | Decisão do usuário em 2026-11-23: o modelo não deixa claro; sem zero é o português corrente | y |
| Espaço abaixo do brasão | 3 mm | O pedido diz "um espaço pequeno"; valor do agente | n |
| Fontes do Parecer | Corpo e cabeçalho em Times New Roman (Liberation Serif no PDF) a 12 pt, com as margens do modelo do Relatório; título e linha de local e data em Arial (Liberation Sans no PDF, versionada com a licença OFL, como a Serif). O tamanho do Relatório (9 pt) é pequeno demais para um parecer de uma página | O modelo pede fonte com serifa no cabeçalho e sem serifa no título; o corpo e o tamanho não foram descritos | n |
| Rodapé "Página N de M" no Parecer | Sai: o modelo é uma página e não tem rodapé | "Não use outra estrutura textual" | n |
| Portaria só com suplentes | `BANCA_SEM_MEMBROS` também quando nenhum membro é `PRESIDENTE` nem `MEMBRO`, para não sair um Parecer sem nome (amplia a condição de PAR-08, que conta qualquer membro) | O Parecer sem nenhum nome não serve; a recusa existente é a mais próxima | n |
| Dois `PRESIDENTE` na portaria | Os dois saem como "(presidente)" no parágrafo e como "PRESIDENTE: <nome>" nas linhas, antes dos membros; os membros são numerados a partir de 1 | A validação da portaria não proíbe dois presidentes; o sistema não escolhe | n |
| Nível fora de 1 a 3999 e ano fora de 1000 a 2999 | O nível sai como digitado (algarismos arábicos) e o ano sai em algarismos, sem recusar | O motor de extenso e de romanos cobre só essas faixas; falhar na geração por isso seria pior | n |
| Data em branco na linha de local e data | "<Cidade>, ____ de ________ de ________." | Mesmos traços do parágrafo, para o usuário preencher à mão | n |
| Número da portaria em branco | "__________" depois de "Portaria nº" | Mesmo traço de local em branco e do `BLANK_TEXT` já usado | n |
| Instantâneo da versão do Parecer | Continua gravando versão da tabela, total, subtotais, mínimo, versões usadas, conclusão, data, local, número e data da portaria e membros, mesmo sem imprimi-los | O resumo da versão e a conferência `TABELA_DESATUALIZADA` leem o instantâneo; AD-012 | n |
| Corpo de `PUT /board/opinion` com `notes` | 422, como qualquer campo desconhecido dos corpos do módulo (`extra="forbid"`); a resposta deixa de trazer `notes` | O frontend e o backend sobem juntos; um campo ignorado em silêncio esconderia erro | n |
| Código de erro do brasão ausente | `ERRO_INTERNO` (já existe) com o tipo `EmblemUnavailable` no log do backend; nenhum valor novo no enum do banco | Um valor novo exigiria `ALTER TYPE ... ADD VALUE`, que não se desfaz (AD-025) | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Texto do Parecer pelo modelo oficial ⭐ MVP

**User Story**: Como docente ou secretaria, quero que o Parecer saia exatamente no formato do modelo oficial da banca, para entregá-lo sem reescrever nem remontar o texto.

**Why P1**: É o pedido principal; o formato atual não é aceito pela banca.

**Acceptance Criteria** (a ordem é a dos IDs `PMOD-01` a `PMOD-19`):

1. The system SHALL montar o Parecer em uma página A4 retrato com estes elementos, nesta ordem e nenhum outro: o brasão (BRAS-04), o cabeçalho, o título, a linha de local e data, o parágrafo único e as linhas dos membros.  <!-- ubiquitous -->
2. The system SHALL escrever o cabeçalho em três linhas centralizadas e em fonte com serifa, "Universidade Federal do Pará", o nome da unidade-mãe do tipo `CAMPUS` da unidade do processo e "<nome da unidade> – <sigla>", seguidas de uma linha horizontal na largura do texto.  <!-- ubiquitous -->
3. WHERE a unidade do processo não tem unidade-mãe do tipo `CAMPUS` the system SHALL escrever o cabeçalho só com as linhas "Universidade Federal do Pará" e "<nome da unidade> – <sigla>".  <!-- optional-feature -->
4. The system SHALL escrever o título "PARECER" centralizado, em negrito e em fonte sem serifa.  <!-- ubiquitous -->
5. The system SHALL escrever, em fonte sem serifa e a partir da metade da largura do texto, a linha "<Cidade>, <dd> de <Mês> de <aaaa>." com o local e a data do Parecer, o dia sem zero à esquerda e o mês com inicial maiúscula.  <!-- ubiquitous -->
6. The system SHALL escrever o parágrafo único, justificado, com recuo na primeira linha e espaçamento entre linhas de cerca de 1,5, com o texto "<data>, reuniram-se os membros da Banca de Análise, nomeados pela Portaria nº <número da portaria>, <presidente> (presidente), <membro>, <membro>, responsáveis por analisar o Relatório de Atividades do Professor <denominação atual> Nível <nível atual> <nome do docente>, para fins de progressão funcional do docente, referente ao interstício de <dd/mm/aaaa> a <dd/mm/aaaa>, para Classe <letra pretendida> (<denominação pretendida>) Nível <nível pretendido>. Após a análise, os membros <decisão> o referido relatório."  <!-- ubiquitous -->
7. The system SHALL escrever em negrito, no parágrafo, só as palavras da data ("<dia> dias do mês de <mês> de <ano>", sem "Aos") e o trecho "<denominação atual> Nível <nível atual> <nome do docente>".  <!-- ubiquitous -->
8. WHEN o dia da data do Parecer é de 2 a 31 THEN the system SHALL escrever a data do parágrafo como "Aos <dia em cardinal> dias do mês de <mês em minúsculas> de <ano por extenso>", por exemplo "Aos vinte e sete dias do mês de maio de dois mil e vinte e cinco".  <!-- event-driven -->
9. WHEN o dia da data do Parecer é 1 THEN the system SHALL escrever a data do parágrafo como "Ao primeiro dia do mês de <mês em minúsculas> de <ano por extenso>".  <!-- event-driven -->
10. WHEN a conclusão é `FAVORAVEL` THEN the system SHALL escrever "os membros APROVARAM o referido relatório" no fim do parágrafo.  <!-- event-driven -->
11. WHEN a conclusão é `DESFAVORAVEL` THEN the system SHALL escrever "os membros NÃO APROVARAM o referido relatório" no fim do parágrafo.  <!-- event-driven -->
12. The system SHALL escrever o nível atual e o nível pretendido em algarismos romanos e a letra da classe e as denominações exatamente como o servidor as digitou na Etapa 1.  <!-- ubiquitous -->
13. The system SHALL escrever, no parágrafo e nas linhas dos membros, só os membros de função `PRESIDENTE` ou `MEMBRO`, na ordem da portaria com o `PRESIDENTE` primeiro, cada linha centralizada e sem linha de assinatura, como "PRESIDENTE: <nome>" ou "MEMBRO <n>: <nome>" com n de 1 em diante.  <!-- ubiquitous -->
14. WHERE a portaria não tem membro `PRESIDENTE` the system SHALL omitir "(presidente)" no parágrafo e escrever as linhas só como "MEMBRO <n>: <nome>".  <!-- optional-feature -->
15. The system SHALL escrever os nomes dos membros, o nome do docente e o número da portaria exatamente como estão registrados, sem acrescentar título.  <!-- ubiquitous -->
16. IF o Parecer não tem data THEN the system SHALL escrever "Aos ______ dias do mês de ________ de ________" no parágrafo e "<Cidade>, ____ de ________ de ________." na linha de local e data, sem recusar a geração.  <!-- unwanted-behavior -->
17. IF o Parecer não tem local THEN the system SHALL escrever "__________" no lugar da cidade da linha de local e data, sem recusar a geração.  <!-- unwanted-behavior -->
18. IF a portaria não tem número THEN the system SHALL escrever "__________" depois de "Portaria nº", sem recusar a geração.  <!-- unwanted-behavior -->
19. The system SHALL escrever o Parecer sem os textos "Total geral", "Mínimo de referência", "Documentos analisados", "Pontuação por grupo", "Observações", "Identificação", "Portaria da banca:" e "Conclusão", e sem tabela e sem rodapé de página.  <!-- ubiquitous -->

**Independent Test**: Num processo sintético de promoção do nível 4 da classe B (Adjunto) para o nível 1 da classe C (Associado), com portaria de um presidente, dois membros e um suplente e conclusão `FAVORAVEL`, montar o texto do Parecer e conferir, palavra por palavra, o parágrafo com a data por extenso, os algarismos romanos, o interstício, a decisão "APROVARAM" e as três linhas de membros sem o suplente; repetir com `DESFAVORAVEL`, sem `PRESIDENTE`, com o dia 1 e com data, local e número em branco.

---

### P1: Gerar o Parecer pelo modelo ⭐ MVP

**User Story**: Como docente ou secretaria, quero gerar o Parecer em DOCX e PDF no formato do modelo, com as mesmas condições de antes, para entregá-lo à banca.

**Why P1**: O texto só vale quando os dois arquivos saem iguais e as condições de geração continuam protegendo a pontuação.

**Acceptance Criteria** (IDs `PMOD-20` a `PMOD-25`):

1. WHEN a pessoa pede "Gerar Parecer" e as condições de geração estão cumpridas THEN the system SHALL gerar uma versão imutável do Parecer em DOCX e em PDF com o mesmo texto na mesma ordem.  <!-- event-driven -->
2. WHILE o Parecer tem até três membros titulares the system SHALL gerar o PDF com uma única página A4.  <!-- state-driven -->
3. IF falta a conclusão, não há membro registrado, não há Tabela `PRONTO` ou o Total geral calculado agora difere do da última Tabela `PRONTO` THEN the system SHALL recusar a geração com 422 e o código `CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE` ou `TABELA_DESATUALIZADA`, nesta ordem, como em PAR-07 a PAR-10.  <!-- unwanted-behavior -->
4. IF nenhum membro registrado tem função `PRESIDENTE` ou `MEMBRO` THEN the system SHALL recusar a geração com 422 `BANCA_SEM_MEMBROS`.  <!-- unwanted-behavior -->
5. The system SHALL gravar no instantâneo de cada versão do Parecer os mesmos campos de antes (versão da tabela, total, subtotais, mínimo, versões usadas, conclusão, data, local, número e data da portaria e membros), mesmo sem imprimi-los.  <!-- ubiquitous -->
6. The system SHALL gerar o texto do Parecer sem chamar a IA.  <!-- ubiquitous -->

**Independent Test**: Num processo sintético com Tabela `PRONTO`, gerar o Parecer e conferir que o DOCX e o PDF têm o mesmo texto e que o PDF tem uma página; mudar uma atividade validada e ver `TABELA_DESATUALIZADA`; registrar só um suplente e ver `BANCA_SEM_MEMBROS`; conferir que o instantâneo traz o total da Tabela.

---

### P1: Etapa 6 sem o campo Observações ⭐ MVP

**User Story**: Como docente ou secretaria, quero preencher na Etapa 6 só o que o Parecer usa, para não digitar um texto que o documento não imprime.

**Why P1**: O campo "Observações" não aparece no modelo; deixá-lo na tela induz a erro.

**Acceptance Criteria** (IDs `PMOD-26` a `PMOD-29`):

1. The system SHALL mostrar na minuta do Parecer da Etapa 6 só os campos conclusão (`FAVORAVEL` ou `DESFAVORAVEL`, sem valor inicial), data e local, sem o campo "Observações da banca" nem o contador de caracteres.  <!-- ubiquitous -->
2. IF o corpo de `PUT /api/processes/{id}/board/opinion` traz o campo `notes` THEN the system SHALL recusar o pedido com 422.  <!-- unwanted-behavior -->
3. The system SHALL manter a coluna `board_opinions.notes` e o texto já gravado nela, sem lê-los, mostrá-los nem imprimi-los, e sem alterá-los quando a pessoa salva a conclusão, a data ou o local.  <!-- ubiquitous -->
4. IF o local passa de 100 caracteres THEN the system SHALL recusar a gravação com 422 indicando o campo `place`.  <!-- unwanted-behavior -->

**Independent Test**: Abrir a Etapa 6 de um processo sintético e ver só conclusão, data e local; salvar e ver a resposta da API sem `notes`; num processo com `notes` gravado antes, salvar de novo e ver, no banco, o mesmo texto em `notes`.

---

### P1: Brasão da UFPA nos documentos oficiais ⭐ MVP

**User Story**: Como docente, quero que cada documento oficial gerado leve o brasão da UFPA no topo, centralizado, para entregá-lo no formato institucional.

**Why P1**: É o segundo pedido do usuário e vale para os cinco documentos.

**Acceptance Criteria** (IDs `BRAS-01` a `BRAS-11`):

1. The system SHALL colocar o brasão da UFPA como o primeiro elemento da primeira página da Tabela de Pontuação, no DOCX e no PDF.  <!-- ubiquitous -->
2. The system SHALL colocar o brasão da UFPA como o primeiro elemento da primeira página do Relatório de Atividades, no DOCX e no PDF.  <!-- ubiquitous -->
3. The system SHALL colocar o brasão da UFPA no topo da capa do Comprovante, e em nenhuma outra página dele.  <!-- ubiquitous -->
4. The system SHALL colocar o brasão da UFPA como o primeiro elemento da primeira página do Parecer, no DOCX e no PDF, acima das três linhas do cabeçalho.  <!-- ubiquitous -->
5. The system SHALL colocar o brasão da UFPA como o primeiro elemento da primeira página do Requerimento, no DOCX e no PDF, acima de "MINISTÉRIO DA EDUCAÇÃO".  <!-- ubiquitous -->
6. The system SHALL centralizar o brasão na largura do texto da página, com 2,0 cm de largura, altura proporcional à imagem (279 por 351 px) e 3 mm de espaço abaixo, igual em todos os documentos.  <!-- ubiquitous -->
7. WHILE um documento tem mais de uma página the system SHALL mostrar o brasão só na primeira.  <!-- state-driven -->
8. The system SHALL manter o texto de cada documento, do cabeçalho existente em diante, igual ao de antes do brasão.  <!-- ubiquitous -->
9. The system SHALL ler o brasão de um arquivo PNG versionado dentro do pacote do backend (`app/infrastructure/documents/assets/ufpa.png`), copiado para a imagem Docker pelo `COPY app ./app`.  <!-- ubiquitous -->
10. IF o arquivo do brasão não existe ou não é um PNG THEN the system SHALL falhar a geração com `EmblemUnavailable` que nomeia o arquivo, fechar a versão como `FALHOU` com `ERRO_INTERNO` e não deixar arquivo gerado.  <!-- unwanted-behavior -->
11. WHEN a pessoa gera de novo um documento THEN the system SHALL levar o brasão à versão nova e manter as versões anteriores com os mesmos bytes (AD-012).  <!-- event-driven -->

**Independent Test**: Num processo sintético, gerar os cinco documentos e abrir cada DOCX (primeiro parágrafo com a imagem, centralizado, 2,0 cm de largura) e cada PDF (a imagem na primeira página, centralizada, acima do primeiro texto, e nenhuma imagem nas outras páginas); apontar o brasão para um caminho inexistente e ver a versão `FALHOU` com `ERRO_INTERNO`.

---

## Edge Cases

- WHEN o Parecer tem 15 membros ou nomes de 200 caracteres THEN the system SHALL escrever todos os nomes, no parágrafo e nas linhas, passando para uma segunda página se não couberem, sem cortar nem omitir nome.
- WHEN a data do Parecer cai nos doze meses THEN the system SHALL escrever o mês em minúsculas no parágrafo e com inicial maiúscula na linha de local e data ("março" e "Março").
- WHEN o dia do Parecer é 1, 2, 21 ou 31 THEN the system SHALL escrever o cardinal certo ("vinte e um", "trinta e um") e, só no dia 1, o singular "Ao primeiro dia".
- WHEN o ano do Parecer é 2000, 2025, 2100 ou 2101 THEN the system SHALL escrever "dois mil", "dois mil e vinte e cinco", "dois mil e cem" e "dois mil cento e um".
- IF o ano do Parecer está fora de 1000 a 2999 THEN the system SHALL escrever o ano em algarismos no parágrafo, sem recusar a geração.
- IF o nível atual ou o pretendido está fora de 1 a 3999 THEN the system SHALL escrever o nível como foi digitado, sem recusar a geração.
- IF a unidade-mãe da unidade existe mas não é do tipo `CAMPUS` THEN the system SHALL omitir a linha do campus.
- WHEN a portaria tem um único membro `PRESIDENTE` THEN the system SHALL escrever "<nome> (presidente), responsáveis por analisar ..." e só a linha "PRESIDENTE: <nome>".
- WHEN a portaria tem dois `PRESIDENTE` THEN the system SHALL escrever os dois como "(presidente)" e como "PRESIDENTE: <nome>", antes dos membros, que seguem numerados de 1.
- WHEN um nome ou o número da portaria tem caractere de controle ou marcação THEN the system SHALL escrevê-lo limpo e como texto, sem quebrar o arquivo (como os demais documentos).
- WHEN a Tabela de Pontuação em PDF paisagem, o Relatório com muitas páginas ou o Comprovante com centenas de páginas são gerados THEN the system SHALL manter o número de páginas e do sumário que já tinham, com o brasão só na primeira página.
- IF o arquivo do brasão não existe, está vazio ou não começa com a assinatura de PNG THEN the system SHALL falhar a geração (BRAS-10), nunca omitir o brasão.
- IF a geração falha por causa do brasão THEN the system SHALL mostrar a mensagem fixa de `ERRO_INTERNO` e registrar no log só o tipo do erro e o identificador da geração, nunca o caminho do servidor.
- WHEN existem versões do Parecer geradas antes desta feature THEN the system SHALL manter o arquivo e o resumo delas como estão, e a nova versão sair com o texto do modelo.

---

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | Nomes até 200 caracteres e 15 membros (limites existentes); local até 100 (PMOD-29); níveis e anos fora da faixa dos conversores (Edge Cases); caractere de controle e marcação em nomes (`xml_safe`) |
| Failure / partial-failure states | BRAS-10: brasão ausente ou inválido falha a geração e não deixa arquivo; versão `FALHOU` com `ERRO_INTERNO`; sem documento sem brasão |
| Idempotency / retry / duplicate handling | BRAS-11: gerar de novo faz versão nova e mantém as antigas; o pedido repetido segue a regra de uma geração por tipo por vez |
| Auth boundaries & rate limits | N/A because nenhuma rota nova; as rotas do Parecer mantêm o acesso e o 409 somente leitura de BNAV-02 |
| Concurrency / ordering | N/A because o brasão é um arquivo só de leitura e a geração segue a thread única do worker (AD-008); a versão otimista do Parecer continua (PAR-01 original) |
| Data lifecycle / expiry | PMOD-28: `notes` fica no banco, sem leitura, impressão nem alteração; versões geradas antes não mudam (AD-012, BRAS-11); nenhuma migração |
| Observability | BRAS-10: log com o tipo do erro (`EmblemUnavailable`) e o identificador da geração; auditoria da gravação do Parecer sem `notes_length` |
| External-dependency failure | O arquivo do brasão e as fontes são do pacote, não de serviço externo; a falta de um deles falha a geração com erro claro; a IA não participa (PMOD-25) |
| State-transition integrity | PMOD-22 e PMOD-23: as recusas do Parecer e a ordem delas; BRAS-03: o brasão não muda a conta de páginas do Comprovante |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PMOD-01 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-02 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-03 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-04 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-05 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-06 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-07 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-08 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-09 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-10 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-11 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-12 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-13 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-14 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-15 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-16 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-17 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-18 | P1: Texto do Parecer | Implemented | Implemented |
| PMOD-19 | P1: Texto do Parecer | Execute | In Progress |
| PMOD-20 | P1: Gerar o Parecer | Execute | In Progress |
| PMOD-21 | P1: Gerar o Parecer | Execute | In Progress |
| PMOD-22 | P1: Gerar o Parecer | Implemented | Implemented |
| PMOD-23 | P1: Gerar o Parecer | Implemented | Implemented |
| PMOD-24 | P1: Gerar o Parecer | Execute | In Progress |
| PMOD-25 | P1: Gerar o Parecer | Implemented | Implemented |
| PMOD-26 | P1: Etapa 6 sem Observações | Implemented | Implemented |
| PMOD-27 | P1: Etapa 6 sem Observações | Implemented | Implemented |
| PMOD-28 | P1: Etapa 6 sem Observações | Execute | In Progress |
| PMOD-29 | P1: Etapa 6 sem Observações | Implemented | Implemented |
| BRAS-01 | P1: Brasão | Tasks | In Tasks |
| BRAS-02 | P1: Brasão | Tasks | In Tasks |
| BRAS-03 | P1: Brasão | Tasks | In Tasks |
| BRAS-04 | P1: Brasão | Tasks | In Tasks |
| BRAS-05 | P1: Brasão | Tasks | In Tasks |
| BRAS-06 | P1: Brasão | Execute | In Progress |
| BRAS-07 | P1: Brasão | Tasks | In Tasks |
| BRAS-08 | P1: Brasão | Tasks | In Tasks |
| BRAS-09 | P1: Brasão | Execute | In Progress |
| BRAS-10 | P1: Brasão | Execute | In Progress |
| BRAS-11 | P1: Brasão | Tasks | In Tasks |

**Substituições na spec `banca-parecer`** (a marcar na tarefa de documentação): PAR-01 (o campo "observações" sai), PAR-03, PAR-04, PAR-05, PAR-06 e PAR-13 ficam substituídos por PMOD-01 a PMOD-19, PMOD-26 a PMOD-29; PAR-02 e PAR-07 a PAR-12 e PAR-14 seguem em vigor (PMOD-20, PMOD-22 a PMOD-25).

**Coverage:** 40 total, 40 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] O texto do Parecer de um processo sintético é igual, palavra por palavra, ao parágrafo do modelo oficial preenchido, no DOCX e no PDF.
- [ ] Nenhum Parecer gerado contém "Total geral", "Mínimo de referência" nem "Observações" (teste em DOCX, PDF e no modelo de domínio).
- [ ] Os cinco documentos oficiais, em todos os formatos gerados, trazem o brasão como primeiro elemento da primeira página, centralizado e com 2,0 cm de largura (teste que lê o DOCX e o PDF).
- [ ] Sem o arquivo do brasão, nenhum documento é gerado e a versão fica `FALHOU` com `ERRO_INTERNO` (zero documentos sem brasão).
- [ ] O arquivo do brasão está no pacote versionado e o teste de pacote o encontra como PNG de 279 por 351 px.
- [ ] Versões geradas antes da feature mantêm os mesmos bytes depois de gerar uma versão nova.
- [ ] Gate completo do backend e do frontend limpo no fim; nenhuma migração nova.

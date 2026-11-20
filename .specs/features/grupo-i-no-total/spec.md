# Grupo I no total, Tabela sem Status nem Comprovante e resumo da Etapa 4 Specification

> **Nota de substituição:** esta feature substitui PIT-01, PIT-02 e PIT-03 e TELA-01 e TELA-02 da feature `tabela-oficial` (Grupo I em horas, fora do total), TAB-03 e TAB-05 da feature `documentos-gerados` (sete colunas com status e comprovante; horas "sem somá-las aos pontos"), os critérios de 211 pontos de cenário derivado de `tabela-oficial` e `documentos-gerados` (passam a 303 pontos de cenário derivado com o Grupo I) e a decisão de 2026-11-17 que a sustentava. O usuário reverteu a decisão em 2026-11-19, depois de gerar os documentos reais: o Grupo I entra no total, a 1 ponto por hora de PIT.

## Problem Statement

A Tabela de Pontuação gerada não lista o Grupo I (docência, medida em PIT): as horas aparecem só numa tabela à parte e o Total geral não as soma. O usuário quer o Grupo I como uma seção da própria tabela, com uma linha por disciplina, cada hora de PIT valendo 1 ponto e somando no total. As colunas Status e Comprovante da tabela não servem ao usuário. O resumo da Etapa 4 mostra 20 cartões soltos, com rótulos longos, valores zerados e o PIT só por semestre, sem as disciplinas.

## Goals

- [ ] O Grupo I da tabela oficial conta no Total geral, com pontos iguais às horas de PIT (68 h de graduação = 8,00 pontos).
- [ ] A Tabela de Pontuação (DOCX e PDF) traz a seção I com uma linha por oferta, inclui o Grupo I no Total geral e não tem as colunas Status e Comprovante.
- [ ] A Etapa 4 mostra o resumo em painel (total, pontos por grupo, docência por semestre e disciplina, contadores) em vez de cartões soltos.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Mudar a fórmula das horas de PIT (CH docente ÷ 17 × (1 + preparação)) | O usuário pediu só que a hora valha 1 ponto e entre no total |
| Mínimo de carga horária de ensino por regime (Res. 4.644, art. 13, I) e a regra dos 30% do Grupo I | Seguem como evolução; o percentual continua apenas exibido |
| Relatório de Atividades e Comprovante | Não foram pedidos; ver a premissa abaixo |
| Tirar a coluna de situação da tabela de atividades da Etapa 4 | O pedido é só para a Tabela de Pontuação |
| Corrigir o texto "não tem data nem período" que aparece nos alertas das ofertas do Grupo I | Defeito à parte, já corrigido no commit `0422ac3` |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| O Grupo I entra no total | Soma no Total geral, a 1 ponto por hora de PIT, sem limite de pontos (o Grupo I da planilha não tem teto) | Decisão do usuário em 2026-11-19; reverte a de 2026-11-17 e a fórmula do TOTAL da planilha oficial, que não soma o Grupo I | y |
| Linha do Grupo I na Tabela | Item `I.1` (graduação) ou `I.2` (pós-graduação); Atividade = disciplina e período; Quantidade = horas de PIT; Pontuação unitária = 1,00; Total = horas | Pedido do usuário: "1 unidade do PIT são 1 hora/aula" | y |
| Colunas Status e Comprovante | Saem da Tabela de Pontuação (DOCX e PDF); as colunas que ficam são Item, Atividade, Quantidade, Pontuação unitária e Total; a linha sem pontos aparece com Total 0,00 e o motivo continua na seção Alertas; o rodapé deixa de ter contadores de status e de comprovante (pergunta 7, ver abaixo); a tabela deixa de apontar o número do Comprovante, que continua no Comprovante e no Relatório | Pedidos do usuário em 2026-11-19 | y |
| Desenho do resumo da Etapa 4 | Painel em blocos: faixa com Total geral e situação do mínimo; barras de pontos por grupo; bloco Docência (PIT) por semestre e disciplina; potencial e contadores em cartões pequenos | Escolha do usuário em 2026-11-19 | y |
| Como a mudança chega à tabela oficial | Nova versão `OFICIAL` da tabela, com o Grupo I contando no total, oferecida para qualquer interstício. A versão anterior fica marcada como substituída: não é mais sugerida nem escolhível. Todo processo em `RASCUNHO` ou `EM_ANDAMENTO` que a usa passa sozinho para a versão nova, com registro na auditoria; processo `CONCLUIDO` ou `ARQUIVADO` e documentos já gerados não mudam (AD-012) | Respostas do usuário em 2026-11-19 (perguntas 1 e 3 do Design): "o Grupo deve estar dentro do Total, não deve ficar separado" | y |
| Tabela de horas por semestre na Tabela de Pontuação | Continua como resumo, com o título "Horas de PIT por semestre (Grupo I)" e o total em horas | Os totais por semestre continuam úteis ao docente; só deixa de dizer "fora do total de pontos" | y |
| Ofertas do Grupo I fora do interstício | Seguem sem pontuar (`FORA_DO_INTERSTICIO`) e não entram nas horas nem no total | Regra existente do Grupo I, decisão de 2026-11-17 | y |
| Pontos informados à mão no Grupo I | Recusados (422 em `points_override`) em qualquer critério de carga semanal do Grupo I, em qualquer versão de tabela; o valor vem do cálculo | A regra 7 do projeto vale para o que não vem do cálculo automático; o PIT vem do cálculo. Resposta do usuário em 2026-11-19 (pergunta 5) | y |
| Relatório de Atividades e Comprovante | Ficam como estão: a Design conferiu que já tratam o Grupo I (seções 1.1 e 1.2) e não leem `counts_in_total` | Não foram pedidos | y |
| Mínimo de referência da classe | Comparado com o total geral, que inclui o Grupo I | Resposta do usuário em 2026-11-19 (pergunta 2) | y |
| Oferta do Grupo I só com período letivo, sem data | Fora do interstício quando o ano inteiro do período está fora dele; sem inventar datas de semestre | Resposta do usuário em 2026-11-19 (pergunta 4); evita que disciplina antiga some pontos sem aviso | y |
| Disciplinas ainda não validadas no bloco Docência | Aparecem com a etiqueta "Aguardando validação" e ficam fora das horas | Resposta do usuário em 2026-11-19 (pergunta 6) | y |
| Comprovante e status na Tabela | Nada de Comprovante nem de status em lugar nenhum da Tabela: sem colunas, sem o alerta de numeração do Comprovante, sem alertas "sem comprovante" e sem contadores de status ou de comprovante no rodapé; o motivo de uma linha não pontuar continua em Alertas | Resposta do usuário em 2026-11-19 (pergunta 7: "Comprovante e status, se houver") | y |
| VI.14 na versão nova | 3 pontos por ano, como diz o texto da planilha (a versão anterior tinha 6, pela fórmula `C*6` da célula, decisão de 2026-11-17) | Decisão do usuário em 2026-11-19 ("VI.14 são 3 pontos") | y |
| Nome e referência da versão nova | "Tabela oficial de pontuação UFPA, Grupo I no total"; referência: "Tabela oficial de pontuação para progressão docente da UFPA (planilha fornecida em 2026-11-17), com o Grupo I somado ao total a 1 ponto por hora de PIT por decisão do usuário em 2026-11-19" | Resposta do usuário em 2026-11-19 (pergunta 8) | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Grupo I conta no total, a 1 ponto por hora de PIT ⭐ MVP

**User Story**: Como docente, quero que as horas de PIT das minhas disciplinas valham 1 ponto cada e somem no Total geral, porque o Grupo I faz parte da minha pontuação.

**Why P1**: É a regra que muda o total do processo e alimenta a Tabela e o resumo.

**Acceptance Criteria**:

1. WHEN o resultado é calculado com a versão em que o Grupo I conta no total THEN the system SHALL dar a cada oferta do Grupo I, como pontos, as horas de PIT da oferta calculadas como CH docente ÷ 17 semanas × (1 + preparação), com preparação 1 na graduação e 2 na pós-graduação, arredondadas a 2 casas, meio para cima: 68 h na graduação dão 8,00 pontos, 34 h dão 4,00 pontos e 68 h na pós-graduação dão 12,00 pontos  <!-- event-driven -->
2. WHEN o resultado é calculado com essa versão THEN the system SHALL devolver o subtotal do Grupo I como a soma dos pontos das ofertas dentro do interstício e o total geral como a soma dos subtotais dos Grupos I a VIII  <!-- event-driven -->
3. WHEN o resultado é calculado com essa versão THEN the system SHALL continuar devolvendo as horas de PIT de cada oferta, somadas por período letivo e no total, iguais aos pontos do Grupo I  <!-- event-driven -->
4. IF uma oferta do Grupo I está fora do interstício THEN the system SHALL dar a ela 0 ponto e 0 hora, com a razão `FORA_DO_INTERSTICIO`, e SHALL deixá-la fora do subtotal e do total  <!-- unwanted-behavior -->
5. IF uma atividade de critério de carga semanal do Grupo I informa pontos que substituem o cálculo (`points_override`), em qualquer versão da tabela, com o Grupo I dentro ou fora do total THEN the system SHALL responder 422 no campo `points_override`  <!-- unwanted-behavior -->
6. WHERE o processo usa uma versão anterior da tabela, o sistema SHALL calcular com as regras dessa versão, sem alterar resultados já calculados  <!-- optional-feature -->
7. The system SHALL oferecer a versão em que o Grupo I conta no total como a única versão sugerida e escolhível da tabela oficial da UFPA, para qualquer interstício, e SHALL marcar a versão anterior como substituída  <!-- ubiquitous -->
8. The system SHALL continuar exibindo o percentual do Grupo I sobre o total geral, sem emitir alerta por ele  <!-- ubiquitous -->
9. IF uma oferta do Grupo I não tem data nem período de datas e o ano inteiro do seu período letivo (AAAA.N) está fora do interstício THEN the system SHALL tratá-la como fora do interstício (`FORA_DO_INTERSTICIO`), com 0 ponto e 0 hora  <!-- unwanted-behavior -->
10. WHEN a versão nova entra no sistema THEN the system SHALL passar para ela todo processo em `RASCUNHO` ou `EM_ANDAMENTO` que usa a versão anterior, registrando a troca na auditoria, e SHALL deixar sem mudança os processos `CONCLUIDO` ou `ARQUIVADO` e os documentos já gerados  <!-- event-driven -->
11. WHEN a última Tabela de Pontuação gerada de um processo usou uma versão da tabela diferente da escolhida hoje THEN the frontend SHALL mostrar na Etapa 5 o aviso "Gerada com outra versão da tabela de pontuação; gere de novo"  <!-- event-driven -->
12. The system SHALL dar ao item VI.14 3 pontos por ano na versão nova da tabela  <!-- ubiquitous -->

**Independent Test**: Lançar quatro períodos de disciplinas (três ofertas de 68 h em cada um dos três primeiros e duas de 68 h e uma de 34 h no quarto) e ver o subtotal do Grupo I e o total geral com os 92 pontos somados aos dos demais grupos.

---

### P1: Tabela de Pontuação com o Grupo I e sem as colunas Status e Comprovante ⭐ MVP

**User Story**: Como docente, quero ver as disciplinas na própria Tabela de Pontuação, com o Grupo I somado no total, e sem as colunas de status e de comprovante.

**Why P1**: A tabela é o documento entregue; hoje ela omite o Grupo I e mostra uma coluna que o usuário não quer.

**Acceptance Criteria**:

1. WHEN a Tabela de Pontuação é gerada com a versão em que o Grupo I conta no total THEN the system SHALL abrir a lista de grupos com a faixa "I. Docência/atividades de ensino/desempenho didático, avaliado com a participação do corpo discente" e o subtotal do Grupo I  <!-- event-driven -->
2. WHEN a tabela lista as ofertas do Grupo I THEN the system SHALL escrever uma linha por oferta, ordenada por período letivo e depois por título, com o item `I.1` ou `I.2`, a disciplina e o período na coluna Atividade, as horas de PIT em Quantidade, 1,00 em Pontuação unitária, e as horas em Total  <!-- event-driven -->
3. WHEN a tabela é gerada THEN the system SHALL calcular a "Pontuação geral" somando os Grupos I a VIII  <!-- event-driven -->
4. The system SHALL gerar a Tabela de Pontuação em DOCX e em PDF só com as colunas Item, Atividade, Quantidade, Pontuação unitária e Total, sem as colunas Status e Comprovante, sem o valor "Pontuada", "Potencial" ou "Não pontuada" e sem "sem comprovante" em qualquer linha  <!-- ubiquitous -->
5. WHEN uma linha não pontua THEN the system SHALL mostrá-la com Total 0,00 e SHALL manter o motivo (por exemplo, fora do interstício) na seção Alertas  <!-- event-driven -->
6. WHEN a tabela traz a seção de horas por semestre THEN the system SHALL intitulá-la "Horas de PIT por semestre (Grupo I)" e listar as horas de cada período e o total em horas  <!-- event-driven -->
7. WHERE a tabela usada tem o Grupo I fora do total (versão anterior) the system SHALL gerar o documento como antes, sem a seção I, mas sem as colunas Status e Comprovante  <!-- optional-feature -->
8. The system SHALL gerar a Tabela de Pontuação sem nenhuma referência a Comprovante ou a status: sem o alerta de numeração do Comprovante, sem alertas "sem comprovante" e sem contadores de status ou de comprovante no rodapé  <!-- ubiquitous -->

**Independent Test**: Gerar a Tabela de um processo com ofertas do Grupo I e ver a seção I com as disciplinas, o total com o Grupo I somado e nenhuma coluna Status, no DOCX e no PDF.

---

### P1: Resumo da Etapa 4 em painel ⭐ MVP

**User Story**: Como docente, quero ver o resultado da pontuação organizado por importância, com as disciplinas do PIT à vista, para entender a situação do processo sem decifrar 20 cartões.

**Why P1**: O resumo é a primeira coisa que o docente vê na Etapa 4 e hoje não diz o que fazer com os números.

**Acceptance Criteria**:

1. WHEN a Etapa 4 mostra o resumo THEN the frontend SHALL exibir, no topo, o Total geral em pontos com o rótulo "Grupos I a VIII" e, ao lado, a situação do mínimo de referência em texto curto  <!-- event-driven -->
2. WHEN o mínimo de referência não está definido THEN the frontend SHALL exibir "Mínimo não definido" em tamanho de texto comum, sem destaque de valor  <!-- event-driven -->
3. WHEN a Etapa 4 mostra os grupos THEN the frontend SHALL exibir uma linha por grupo com o nome, o subtotal e uma barra proporcional ao total geral, e SHALL exibir os grupos com 0,00 em tom discreto  <!-- event-driven -->
4. WHEN a Etapa 4 mostra a docência THEN the frontend SHALL exibir um bloco "Docência (PIT)" com as ofertas agrupadas por período letivo, cada oferta com a disciplina, o nível e as horas, o total de horas de cada período e o total geral de horas; a oferta ainda não validada aparece com a etiqueta "Aguardando validação" e fica fora das horas  <!-- event-driven -->
5. IF o processo não tem ofertas do Grupo I THEN the frontend SHALL exibir no bloco Docência a mensagem "Nenhuma disciplina lançada no Grupo I"  <!-- unwanted-behavior -->
6. WHEN o potencial (total, com data no interstício e sem data) é maior que 0 THEN the frontend SHALL exibir os valores em cartões pequenos, e SHALL ocultá-los quando todos forem 0  <!-- event-driven -->
7. WHEN a Etapa 4 mostra os contadores THEN the frontend SHALL exibir atividades, com comprovante, pendentes, não pontuadas e com divergências em uma faixa única  <!-- event-driven -->
8. The system SHALL exibir o resumo sem depender só de cor para dizer o que cada valor é, e sem rolagem horizontal da página em tela de 360 px  <!-- ubiquitous -->
9. WHERE a versão da tabela tem o Grupo I fora do total (versão anterior) the frontend SHALL exibir o total como "Grupos II a VIII" e o bloco Docência em horas, fora do total, como antes  <!-- optional-feature -->

**Independent Test**: Abrir a Etapa 4 de um processo com pontos nos Grupos III, VI, VII e VIII e disciplinas do Grupo I e ver o painel com total, barras por grupo e o bloco Docência por semestre.

---

## Edge Cases

- IF um semestre tem só ofertas fora do interstício THEN the frontend SHALL omitir o semestre do bloco Docência e a tabela SHALL omitir as linhas dele.
- WHEN uma oferta tem CH docente que dá horas com 3 ou mais casas decimais THEN the system SHALL arredondar a 2 casas, meio para cima, antes de somar, de modo que a soma das linhas é o subtotal.
- IF o título de uma disciplina passa de 400 caracteres THEN the system SHALL cortá-lo na Tabela como nas demais linhas.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| GI-01 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-02 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-03 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-04 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-05 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-06 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-07 | P1: Grupo I conta no total | Implementing | Implementing |
| GI-08 | P1: Grupo I conta no total | Implementing | Implementing |
| GI-09 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-10 | P1: Grupo I conta no total | Tasks | Implementing |
| GI-11 | P1: Grupo I conta no total | Implementing | Implementing |
| GI-12 | P1: Grupo I conta no total | Tasks | Implementing |
| GTAB-01 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-02 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-03 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-04 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-05 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Tasks | Implementing |
| GTAB-06 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-07 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GTAB-08 | P1: Tabela com o Grupo I e sem Status nem Comprovante | Implementing | Implementing |
| GRES-01 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-02 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-03 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-04 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-05 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-06 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-07 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-08 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |
| GRES-09 | P1: Resumo da Etapa 4 em painel | Implementing | Implementing |

**ID format:** `[CATEGORY]-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Implemented → Verified

**Coverage:** 29 total, 0 mapped to tasks, 29 unmapped ⚠️ (as Tasks mapeiam)

---

## Success Criteria

- [ ] O cenário derivado de 2022–2024 dá 24, 24, 24 e 20 pontos no Grupo I e 211 + 92 = 303 pontos de total geral (teste automatizado).
- [ ] A Tabela gerada, em DOCX e em PDF, tem a seção I com uma linha por oferta, o Total geral com o Grupo I e nenhuma coluna Status nem Comprovante (teste automatizado).
- [ ] A Etapa 4 mostra o painel em blocos com o bloco Docência por semestre e disciplina (teste de componente).

# Tabela Oficial — Specification

**Escopo:** Large (muda a fonte das pontuações, regras já verificadas e testes; sem domínio novo).
**Substitui:** TAB-03, TAB-04, TAB-05, TAB-06, TAB-07 e CALC-14 da feature `pontuacao`, e as regras de sugestão (CLS-02) da `inteligencia-documental`.
**Fonte:** planilha `Modelos/tabela-progressao-docente.xlsx` (fornecida pelo usuário em 2026-11-17), Res. 4.644/2015 e Res. 4.074/2010.

## Problem Statement

O sistema foi construído sobre duas tabelas que o usuário não considera fonte de verdade: a do IFCH (PDF) e a da FASI (tabela preenchida, com erros de numeração e de valores). O usuário forneceu a planilha oficial da UFPA e determinou que só ela vale. Ela difere das anteriores nos pontos, no número de itens (Grupo III com 9, IV com 6, V com 5, VIII com 37 itens numerados de outro modo) e no tratamento do Grupo I, que é horas de PIT e não entra no total. Esta mudança troca a tabela semeada, ajusta o Grupo I, remapeia as regras de sugestão da leitura de documentos e recalcula a aceitação.

## Goals

- [ ] Uma única tabela, a oficial da UFPA, semeada com os 97 itens pontuados, os valores decididos pelo usuário e somas por grupo conferidas.
- [ ] Grupo I em horas de PIT por período, fora do total, com 68 h na graduação dando 8 horas.
- [ ] Todo item sugerido pela leitura de documentos existe na tabela oficial.
- [ ] O sistema no ar (VM) com a tabela oficial e as antigas arquivadas, sem quebrar processo existente.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature     | Reason         |
| ----------- | -------------- |
| Verificar a carga horária mínima de ensino do docente (Res. 4.644, art. 13, I) com as horas de PIT | Fica como evolução; o sistema passa a ter as horas, mas a regra de mínimo por regime não foi pedida |
| Importar a planilha pelo sistema | A semente é gerada uma vez a partir da planilha; a administração por CSV já existe |
| Reenquadrar processos antigos | Processos que escolheram as tabelas antigas continuam com elas |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default  | Rationale | Confirmed? |
| --------------------- | --------------- | --------- | ---------- |
| Fonte de verdade | A planilha `Modelos/tabela-progressao-docente.xlsx` é a única fonte; as tabelas do IFCH (PDF) e da FASI (tabela preenchida) deixam de valer | Decisão do usuário em 2026-11-17 | y |
| Valores divergentes da planilha | VI.14 = 6, VIII.4 = 15, VIII.8 = 15, VIII.12 = 2 (coincidem com a tabela anterior) e II.10 = 10 (texto do item) | Decisão do usuário em 2026-11-17; a planilha traz texto e fórmula diferentes nesses cinco itens | y |
| PIT em horas | O Grupo I é horas de PIT por semestre, fora do total; 68 h na graduação = 8 horas (4 de aula + 4 de preparação); na pós-graduação 12 horas; semestre de 17 semanas | Decisão do usuário em 2026-11-17 e fórmula do TOTAL da planilha, que não soma o Grupo I; as 17 semanas vêm do usuário e a razão de preparação da Res. 4.074/2010, art. 10, I | y |
| Vigência da tabela oficial | Desde 2015-03-24 (data da Res. 4.644, que instituiu o Quadro de Atividades Referenciais), sem fim | A planilha não traz data | n |
| Unidades associadas | FASI e IFCH | A planilha é oficial da UFPA; as unidades semeadas são as duas conhecidas | n |
| Mínimos de referência | Mantidos da Res. 4.644, art. 12 (60, 80, 100 e 120), como alerta de comparação; a planilha só tem uma célula "Total de pontos necessário para progressão" vazia | Norma vigente que a planilha não substitui | n |
| Carga mínima de 20 horas | Abaixo de 20 h não pontua (`CARGA_HORARIA_INSUFICIENTE`); sem horas pontua com alerta | O texto dos itens IV.3 a IV.5 exige "carga horária mínima de 20 h"; sem a informação, a revisão humana decide | n |
| Item VIII.37 | Critério sem pontos, com o texto como regra (equivale a progressão de nível, com relatório validado pela unidade) | A planilha não dá pontuação ao item | n |
| Palestra | VIII.24 ("participação como apresentador em conferências, palestras e mesas redondas"), a mesma descrição do item que o usuário havia indicado como VIII.28 na numeração antiga | A decisão do usuário foi pela descrição; o número mudou | n |
| Curso de extensão concluído | VII.9; outro curso, treinamento e evento: VII.10 | Decisão anterior do usuário; a numeração não mudou no Grupo VII | y |
| Tabelas antigas no banco | Arquivadas e sem unidades, exceto versões usadas por processo, que permanecem | Não quebrar processo existente | n |
| Pontos informados no Grupo I | Recusados (422 em `points_override`) somente onde o Grupo I é medido em horas de PIT (critério de carga semanal, fora do total: `is_pit_criterion`); versões antigas que contam o Grupo I em pontos continuam aceitando o valor informado; o valor vem do cálculo de PIT | O ajuste manual servia para reproduzir o 92 em pontos, que deixa de existir; processos que escolheram as tabelas antigas mantêm o cálculo (ver os edge cases) | n |
| Cenário de aceitação | Derivado: as mesmas quantidades do caso de 2022–2024 lançadas na tabela oficial (IV.4 como um curso de 21 horas); não é um resultado aprovado em processo real | O total aprovado (414) foi calculado com outra tabela | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Tabela oficial da UFPA como única fonte ⭐ MVP

**User Story**: Como docente ou banca, quero que o sistema use somente a tabela oficial de pontuação da UFPA, para que o total reflita a norma.

**Why P1**: O usuário forneceu a planilha oficial e a declarou como única fonte de verdade; as tabelas do IFCH e da FASI deixam de valer.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o sistema é inicializado THEN the system SHALL semear a tabela "Tabela de Pontuação da UFPA", situação `OFICIAL`, vigência desde 2015-03-24, com a referência normativa "Tabela oficial de pontuação para progressão docente da UFPA (planilha fornecida pelo usuário em 2026-11-17)".
2. The system SHALL conter os critérios na numeração da planilha: Grupo I com 2, Grupo II com 16, III com 9, IV com 6, V com 5, VI com 14, VII com 11 e VIII com 37, cada um com a descrição da planilha.
3. The system SHALL usar como pontuação unitária o valor da planilha e, nos cinco itens em que o texto do item e a fórmula da célula divergem, os valores decididos pelo usuário: II.10 = 10, VI.14 = 6, VIII.4 = 15, VIII.8 = 15 e VIII.12 = 2.
4. The system SHALL ter somas das pontuações unitárias dos Grupos II a VIII iguais a 158, 44, 40, 75, 332, 258 e 407, e 1314 no total.
5. WHERE o item é VII.11 (estágio de capacitação técnica) the system SHALL pontuar 1 ponto a cada 30 horas; the system SHALL pontuar por unidade todos os demais itens e SHALL manter o item VIII.37 (afastamento para serviços nos Ministérios) sem pontos, com o texto da planilha como regra.
6. WHERE o item exige carga horária mínima de 20 horas (IV.3, IV.4 e IV.5) the system SHALL registrar a carga mínima no critério e, IF as horas informadas são menores que 20 THEN the system SHALL tratar a atividade como não pontuada, com a razão `CARGA_HORARIA_INSUFICIENTE`.
7. IF as horas de uma atividade de item com carga mínima não foram informadas THEN the system SHALL pontuá-la e emitir o alerta `ALERTA` de código `CARGA_HORARIA_NAO_INFORMADA`.
8. The system SHALL não semear mais as tabelas "Tabela de Pontuação do IFCH" e "Tabela de Pontuação da FASI".
9. WHEN o sistema é inicializado em um banco que contém as tabelas do IFCH ou da FASI THEN the system SHALL arquivá-las e remover suas associações de unidade, exceto as versões escolhidas por algum processo, que SHALL permanecer sem alteração.
10. The system SHALL associar a nova tabela às unidades FASI e IFCH e SHALL manter nela os mínimos de referência por classe da Res. 4.644/2015, art. 12 (60, 80, 100 e 120), que a planilha não traz.
11. WHEN a semeadura roda mais de uma vez THEN the system SHALL não duplicar tabelas, versões, critérios nem associações.
12. WHEN um critério com carga horária mínima é gravado e lido THEN the system SHALL devolver o mesmo valor, por migração que acrescenta o campo ao critério.

**Independent Test**: Consultar a API e conferir a tabela oficial, a contagem por grupo, as somas e os cinco valores decididos.

---

### P1: Grupo I em horas de PIT, fora do total ⭐ MVP

**User Story**: Como docente, quero ver no Grupo I as horas do meu PIT por semestre, e não pontos, porque a planilha oficial não soma o Grupo I no total.

**Why P1**: A planilha lista o Grupo I em HORAS por semestre e a fórmula do TOTAL soma só os Grupos II a VIII; o usuário esclareceu que PIT de 8 são 8 horas.

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL calcular as horas de PIT de cada oferta como CH docente ÷ 17 semanas × (1 + preparação), com preparação 1 na graduação e 2 na pós-graduação, arredondadas a 2 casas pelo critério meio para cima: 68 h na graduação dão 8,00 horas, 34 h dão 4,00 horas e 68 h na pós-graduação dão 12,00 horas.
2. WHEN o resultado é calculado com uma versão cujo Grupo I fica fora do total e tem critério de carga semanal THEN the system SHALL devolver as horas de PIT somadas por período letivo e o total de horas do Grupo I, e SHALL manter em 0 a pontuação, o subtotal e a contribuição do Grupo I ao total geral; WHERE a versão escolhida pelo processo é anterior (Grupo I que entra no total, ou fora do total sem critério de carga semanal) the system SHALL manter o cálculo que o processo já tinha.
3. IF uma atividade do Grupo I informa pontos que substituem o cálculo (`points_override`) numa versão cujo Grupo I fica fora do total e tem critério de carga semanal THEN the system SHALL responder 422 no campo `points_override`; WHERE a versão é anterior (Grupo I que conta pontos) the system SHALL continuar aceitando os pontos informados.

**Independent Test**: Lançar quatro períodos de disciplinas e ver as horas de PIT por período, com o total geral sem o Grupo I.

---

### P1: Regras de sugestão na numeração oficial ⭐ MVP

**User Story**: Como docente, quero que o sistema sugira o item certo da tabela oficial para cada documento.

**Why P1**: A numeração do Grupo VIII da planilha difere do Anexo I da Res. 4.644; as regras da `inteligencia-documental` usavam a numeração antiga.

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL sugerir, para os tipos do Grupo VIII, os itens da tabela oficial: ARTIGO_INTERNACIONAL_INDEXADO VIII.9, ARTIGO_NACIONAL_INDEXADO VIII.10, ARTIGO_NAO_INDEXADO VIII.11, TRABALHO_COMPLETO_CONGRESSO VIII.19, COMUNICACAO_COM_RESUMO VIII.20, COMUNICACAO_SEM_RESUMO VIII.21, APRESENTACAO_TRABALHO_INTERNACIONAL VIII.22, APRESENTACAO_TRABALHO_NACIONAL VIII.23, PALESTRA VIII.24, PATENTE_DEPOSITADA VIII.29, PATENTE_CONCEDIDA VIII.30, REGISTRO_SOFTWARE VIII.33 e CONSULTORIA_AD_HOC VIII.36; os demais tipos de livro e capítulo permanecem em VIII.1 a VIII.4.
2. WHERE um tipo dependia de item que a tabela oficial não tem (BANCA_PROCESSO_SELETIVO e EXTENSAO_EVENTO_MINISTRANTE) the system SHALL tratá-lo como tipo sem item, e SHALL remover os itens alternativos que deixaram de existir (III.12).
3. The system SHALL garantir, por teste, que todo item principal e alternativo de toda regra de sugestão existe na tabela oficial semeada.
4. The system SHALL derivar a quantidade de cada curso (IV.3, IV.4 e IV.5) e de cada evento (IV.6) como 1 por documento, guardando as horas extraídas para a verificação da carga mínima, e SHALL manter por horas somente o estágio de capacitação (VII.11).

**Independent Test**: Rodar o teste que confere todos os itens sugeridos contra a tabela oficial.

---

### P1: Aceitação recalculada ⭐ MVP

**User Story**: Como responsável, quero um teste de aceitação com a tabela oficial, no lugar do caso de 2022–2024 calculado com a tabela da FASI.

**Why P1**: O total 414 vinha da tabela da FASI; com a tabela oficial os mesmos lançamentos dão outro resultado.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN os lançamentos do cenário derivado de 2022–2024 são cadastrados na tabela oficial (II.7 × 4; II.8 × 4; II.12 × 4; III.2 × 1; III.3 × 1; IV.1 × 4; IV.4 × 1 curso de 21 horas; VI.6 × 1; VII.10 × 2; VIII.9, VIII.10, VIII.11 e VIII.36 × 1; Grupo I com 4 períodos: três ofertas de 68 h em cada um dos três primeiros e ofertas de 68 h, 68 h e 34 h no quarto) THEN the system SHALL retornar subtotais II a VIII de 52, 7, 62, 0, 30, 4 e 56 e total geral de 211, e horas de PIT por período de 24, 24, 24 e 20.
2. The system SHALL manter verdes todos os testes que dependiam das tabelas do IFCH e da FASI, atualizados para a tabela oficial, sem remover nem enfraquecer asserção que não codificasse um valor das tabelas antigas, e SHALL registrar no corpo do commit cada asserção cujo valor mudou.

**Independent Test**: Rodar o teste de aceitação e conferir 211.

---

### P1: Etapa 4 com o Grupo I em horas ⭐ MVP

**User Story**: Como docente, quero ver o Grupo I em horas e o total sem ele.

**Why P1**: Evita ler horas de PIT como pontos.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN a Etapa 4 mostra o Grupo I THEN the frontend SHALL exibir a coluna de valor em "horas (PIT)", as horas por período letivo e o total de horas, sem exibir esses valores como pontos.
2. WHEN a Etapa 4 mostra o resumo THEN the frontend SHALL rotular o total como "Total geral (Grupos II a VIII)" e SHALL exibir as horas de PIT à parte.

**Independent Test**: No navegador, lançar disciplinas e conferir horas e total.

---

## Edge Cases

Edge cases are usually unwanted-behavior (IF/THEN) or boundary (WHEN) criteria:

- IF uma atividade com carga mínima tem exatamente 20 horas THEN the system SHALL pontuá-la; WHEN tem 19,99 horas THEN the system SHALL não pontuá-la.
- WHEN o banco já tem a tabela oficial e as tabelas antigas arquivadas THEN the system SHALL não alterar nada na nova inicialização.
- IF um processo existente escolheu uma versão da tabela do IFCH ou da FASI THEN the system SHALL manter essa versão e o cálculo dele inalterados.
- IF a versão escolhida tem o Grupo I fora do total sem critério de carga semanal (tipo IFCH) THEN the system SHALL não tratá-lo como horas de PIT, e a interface SHALL não mostrar o total de horas de PIT.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story       | Phase  | Status  |
| -------------- | ----------- | ------ | ------- |
| OFI-01 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-02 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-03 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-04 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-05 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-06 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-07 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-08 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-09 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-10 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-11 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| OFI-12 | P1: Tabela oficial da UFPA como única fonte | Design | Implemented |
| PIT-01 | P1: Grupo I em horas de PIT, fora do total | Design | Implemented |
| PIT-02 | P1: Grupo I em horas de PIT, fora do total | Design | Implemented |
| PIT-03 | P1: Grupo I em horas de PIT, fora do total | Design | Implemented |
| MAP-01 | P1: Regras de sugestão na numeração oficial | Design | Implemented |
| MAP-02 | P1: Regras de sugestão na numeração oficial | Design | Implemented |
| MAP-03 | P1: Regras de sugestão na numeração oficial | Design | Implemented |
| MAP-04 | P1: Regras de sugestão na numeração oficial | Design | Implemented |
| ACE-01 | P1: Aceitação recalculada | Design | Implemented |
| ACE-02 | P1: Aceitação recalculada | Design | Pending |
| TELA-01 | P1: Etapa 4 com o Grupo I em horas | Design | Implemented |
| TELA-02 | P1: Etapa 4 com o Grupo I em horas | Design | Implemented |

**ID format:** `[CATEGORY]-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Implemented → Verified

**Coverage:** 23 total, 22 Implemented (com teste), 1 Pending (ACE-02: sem teste dedicado, é critério de processo; a suíte atualizada está verde e cada valor alterado está no corpo dos commits)

---

## Success Criteria

- [ ] A tabela oficial semeada tem 2, 16, 9, 6, 5, 14, 11 e 37 critérios e somas de 158, 44, 40, 75, 332, 258 e 407 nos Grupos II a VIII (teste automatizado).
- [ ] O cenário derivado de 2022–2024 dá 211 pontos e 24, 24, 24 e 20 horas de PIT (teste automatizado).
- [ ] Nenhum item de nenhuma regra de sugestão aponta para um item que não existe na tabela oficial (teste automatizado).
- [ ] Na VM, `GET /api/scoring-tables` lista só a tabela oficial como ativa.

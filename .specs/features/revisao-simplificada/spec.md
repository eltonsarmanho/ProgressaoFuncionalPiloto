# Revisão simplificada das atividades Specification

## Problem Statement

Na Etapa 3 o docente revisa atividades que chegam dos documentos, e processos reais têm mais de 100 arquivos. Hoje todas as atividades ficam numa lista só: as que não vão pontuar (fora do interstício, duplicadas, carga horária insuficiente, rejeitadas) se misturam às válidas, a duplicada aparece como uma segunda linha e a validação não garante que a atividade pontue. O docente aperta "Validar" e a Etapa 4 mostra 0 ponto, porque faltava a categoria. O formulário de edição tem mais de 15 campos, a maioria sem uso para quem só quer corrigir um título ou uma data.

## Goals

- [ ] Validar uma atividade que tem categoria a pontua na Etapa 4, sem segunda validação nem edição.
- [ ] A Etapa 3 separa "Atividades válidas" de "Atividades não válidas", mostra o motivo de cada não válida e deixa o docente corrigi-la.
- [ ] Duplicadas viram uma atividade só, com as provas somadas.
- [ ] Só as válidas, com categoria, seguem para as Etapas 4 e 5 e para os documentos gerados.
- [ ] Editar uma atividade pede Título, Data e Categoria; Quantidade e valor manual ficam na Etapa 4.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Grupo I (PIT) no total, Tabela sem Status e sem Comprovante, painel da Etapa 4 | Feature `grupo-i-no-total`, já especificada |
| Corrigir o alerta "não tem data nem período" das ofertas do Grupo I | Defeito à parte |
| Mudar a lista de documentos da Etapa 2 | Não foi pedido |
| Editar período letivo, nível e horas das ofertas do Grupo I | Esses valores vêm do documento e se corrigem reprocessando-o |
| Justificativa em validar, rejeitar, editar e classificar | A regra 5 do projeto continua: agem na hora, sem campo |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Validar pontua | Atividade com categoria e dentro do interstício pontua ao ser validada, com os valores da tabela, sem segunda validação nem edição; vale para todos os grupos | Pedido do usuário em 2026-11-19 | y |
| Quantidade ausente | Assume 1 e emite o alerta `QUANTIDADE_ASSUMIDA` | Resposta "Sim" do usuário em 2026-11-19 | y |
| Atividade sem categoria | Fica entre as válidas com o selo "Precisa de categoria"; "Validar" não é aceito até a categoria ser escolhida; a Etapa 4 só abre sem atividade com esse selo | Decisão do usuário em 2026-11-19 | y |
| Atividades não válidas | São as fora do interstício, com carga horária abaixo do mínimo do item e as rejeitadas pelo usuário; ficam numa seção à parte com o motivo, não seguem para as Etapas 4 e 5 nem para os documentos gerados e voltam a válidas quando o docente as corrige | Decisão do usuário em 2026-11-19 | y |
| Duplicadas | Mescladas em uma atividade só; as provas (documento e página) da outra passam para a mantida; a duplicada some das listas e dos documentos | Decisão do usuário em 2026-11-19 | y |
| Tabela, Relatório e Comprovante só com atividades válidas | Nenhuma atividade fora do interstício, nem duplicada, rejeitada ou com carga insuficiente aparece nesses documentos, nem como "Não pontuada" | A banca avaliadora só quer ver atividades válidas e dentro do interstício; decisão do usuário em 2026-11-19 | y |
| Qual atividade fica na mesclagem | A já validada; se nenhuma ou as duas estão validadas, a criada primeiro | Mantém o trabalho do usuário; sem decisão do usuário | n |
| A duplicada mesclada continua no banco | Fica gravada, marcada como mesclada na mantida, com evento de auditoria; não é apagada | Permite desfazer e preserva o rastro (regra 2) | n |
| Desfazer uma mesclagem | A atividade mantida mostra "N duplicadas mescladas" e um botão "Não é duplicada" que restaura a outra e a marca como distinta | Evita perder uma atividade que não era duplicada; é a regra `MarkActivitiesDistinct` de hoje | n |
| Formulário de edição | Título, Data (ou Início e Fim nas categorias medidas por ano) e Categoria; a Descrição, o texto do Comprovante, as Horas, os Pontos informados e os campos do Grupo I saem | Proposta aceita pelo usuário em 2026-11-19 | y |
| Horas no formulário | Aparecem só quando a categoria tem carga horária mínima (item que pode tornar a atividade não válida por carga insuficiente), para o docente poder corrigir a carga lida errada | Sem isso a atividade não válida por carga não teria como voltar a válida; o usuário aceitou tirar as Horas sem ter visto esse caso | n |
| Data dentro do interstício | O formulário e a API recusam data fora do interstício (422); nas categorias por ano basta o período cruzar o interstício | Decisão do usuário em 2026-11-19; a regra 3 do projeto aceita o período que cruza | y |
| Precisão da data | Aceita dia completo ou só mês e ano, como hoje | Mantém o que o sistema já entende | n |
| Quantidade e valor manual | Passam para "Editar pontuação" da Etapa 4, que também aceita horas nos itens medidos por horas | Decisão do usuário em 2026-11-19 | y |
| Nova atividade manual | Pede Título, Data, Categoria e Quantidade | Sem categoria e quantidade uma atividade manual nunca pontuaria | n |
| Validação em lote | Valida as atividades com categoria e deixa de fora, listando, as sem categoria; vale também para "Validar as confiáveis" | A validação em lote de hoje é tudo ou nada só para versão alterada (409); a falta de categoria não deve travar as demais | n |
| Tamanho da lista | 25 atividades por vez, com "Mostrar mais", busca por título e filtros por situação e por grupo | Processos com mais de 100 arquivos | n |
| Seção de não válidas | Fechada ao abrir a página, com o número total e a contagem por motivo no título | A seção principal é a das válidas | n |
| Atividades já existentes em processos em andamento | Valem as regras novas na primeira abertura da Etapa 3: duplicadas são mescladas e cada atividade vai para a seção que lhe cabe; nenhum dado é apagado | Sem migração de dados | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Validar pontua ⭐ MVP

**User Story**: Como docente, quero que validar uma atividade a faça pontuar na Etapa 4, sem precisar validar de novo nem editar, para o processo andar com menos passos.

**Why P1**: É o defeito que gerou o pedido: validada e com 0 ponto.

**Acceptance Criteria**:

1. WHEN o docente valida uma atividade que tem categoria e está dentro do interstício THEN the system SHALL marcá-la como validada e SHALL pontuá-la na Etapa 4 com o valor unitário da tabela e a quantidade informada, sem outra validação nem edição  <!-- event-driven -->
2. IF uma atividade de item medido por unidade não tem quantidade THEN the system SHALL pontuá-la com quantidade 1 e SHALL emitir o alerta `QUANTIDADE_ASSUMIDA`  <!-- unwanted-behavior -->
3. IF o docente valida uma atividade sem categoria THEN the system SHALL responder 422 no campo `categoria` com a mensagem "Escolha a categoria antes de validar" e SHALL manter a atividade como estava  <!-- unwanted-behavior -->
4. WHEN o docente valida várias atividades de uma vez THEN the system SHALL validar as que têm categoria e SHALL listar, sem validá-las, as que não têm  <!-- event-driven -->
5. WHEN o docente valida uma atividade THEN the system SHALL gravar um evento de auditoria do status, sem pedir justificativa  <!-- event-driven -->
6. The system SHALL oferecer "Validar" só para atividade válida, nunca para uma atividade não válida  <!-- ubiquitous -->

**Independent Test**: Validar uma co-orientação de mestrado com categoria II.5 e ver 8,00 pontos na Etapa 4, sem outro clique.

---

### P1: Etapa 3 em duas seções ⭐ MVP

**User Story**: Como docente com mais de 100 documentos, quero ver as atividades válidas separadas das não válidas, com o motivo de cada não válida, para revisar o que importa e corrigir o que a leitura errou.

**Why P1**: Hoje as não pontuadas se misturam às válidas e o docente não sabe o que fazer com elas.

**Acceptance Criteria**:

1. WHEN a Etapa 3 abre THEN the frontend SHALL exibir duas seções, "Atividades válidas" e "Atividades não válidas", cada uma com o número de atividades no título  <!-- event-driven -->
2. WHEN a seção de válidas é exibida THEN the frontend SHALL listar as atividades dentro do interstício, com categoria ou sem ela, com carga horária suficiente e não rejeitadas, aguardando validação ou validadas, 25 por vez com o botão "Mostrar mais"  <!-- event-driven -->
3. WHEN a seção de válidas é exibida THEN the frontend SHALL oferecer busca por título e filtros por situação (todas, aguardando validação, validadas, precisa de categoria) e por grupo, com o número de atividades de cada filtro  <!-- event-driven -->
4. WHEN uma atividade válida não tem categoria THEN the frontend SHALL mostrar nela o selo "Precisa de categoria" e um seletor de categoria na própria linha, e SHALL aplicar a categoria escolhida na hora, sem justificativa  <!-- event-driven -->
5. WHILE há atividade válida com o selo "Precisa de categoria", the frontend SHALL desabilitar o avanço para a Etapa 4 e SHALL mostrar "N atividades precisam de categoria"  <!-- state-driven -->
6. WHEN a seção de não válidas é exibida THEN the frontend SHALL listar as atividades fora do interstício, com carga horária abaixo do mínimo do item e rejeitadas pelo usuário, cada uma com o motivo em texto  <!-- event-driven -->
7. WHEN uma atividade é não válida por data THEN the frontend SHALL mostrar "Fora do interstício: data dd/mm/aaaa; interstício dd/mm/aaaa a dd/mm/aaaa"; WHEN é por carga horária THEN "Carga horária insuficiente: N h; o item exige M h"; WHEN foi rejeitada THEN "Rejeitada por você"  <!-- event-driven -->
8. WHEN o docente corrige uma atividade não válida de modo que ela deixa de ter o motivo THEN the frontend SHALL passá-la para a seção de válidas, sem recarregar a página  <!-- event-driven -->
9. WHEN o docente reabre uma atividade rejeitada THEN the system SHALL levá-la a "aguardando validação" e a seção de válidas SHALL passar a listá-la  <!-- event-driven -->
10. The frontend SHALL abrir a página com a seção de não válidas fechada, mostrando no título o total e a contagem por motivo  <!-- ubiquitous -->
11. IF não há atividade na seção THEN the frontend SHALL mostrar "Nenhuma atividade válida ainda" ou "Nenhuma atividade não válida"  <!-- unwanted-behavior -->
12. The frontend SHALL exibir as duas seções sem rolagem horizontal da página em tela de 360 px, com títulos de seção navegáveis por teclado e sem usar só a cor para dizer a situação ou o motivo  <!-- ubiquitous -->

**Independent Test**: Abrir um processo com 120 atividades, 10 delas fora do interstício e 3 sem categoria, e ver as válidas em páginas de 25, o selo nas 3, o avanço bloqueado e as 10 na seção fechada com o motivo.

---

### P1: Duplicadas mescladas ⭐ MVP

**User Story**: Como docente, quero que a mesma atividade lida de dois documentos apareça uma vez só, com as duas provas, para não me confundir.

**Why P1**: A duplicada hoje aparece como outra linha "não pontuada" e polui a revisão e a Tabela.

**Acceptance Criteria**:

1. WHEN duas atividades do processo são duplicadas, pela regra de duplicidade existente, THEN the system SHALL mesclá-las em uma atividade só: fica a já validada ou, se nenhuma ou as duas estão validadas, a criada primeiro; as provas (documento e página) da outra passam para a mantida, sem repetir um par documento e página  <!-- event-driven -->
2. WHEN a mesclagem acontece THEN the system SHALL manter a outra atividade no banco, marcada como mesclada na mantida, e SHALL gravar um evento de auditoria com os dois ids  <!-- event-driven -->
3. The system SHALL deixar a atividade mesclada fora das listas, dos totais, da Tabela, do Relatório e do Comprovante  <!-- ubiquitous -->
4. WHEN uma atividade é criada, editada ou o documento dela é reprocessado, e na primeira abertura da Etapa 3 depois da atualização, THEN the system SHALL mesclar as duplicadas do processo  <!-- event-driven -->
5. WHEN a mesclagem é repetida sobre as mesmas atividades THEN the system SHALL não mudar nada  <!-- event-driven -->
6. IF um passo da mesclagem falha THEN the system SHALL não alterar nenhuma atividade nem prova  <!-- unwanted-behavior -->
7. WHEN a atividade mantida tem duplicadas mescladas THEN the frontend SHALL mostrar "N duplicadas mescladas" nela e o botão "Não é duplicada", que restaura a atividade, devolve as provas que vieram dela e a marca como distinta para não ser mesclada de novo  <!-- event-driven -->

**Independent Test**: Duas atividades "Visão Computacional com OpenCV" lidas de dois arquivos viram uma, com as duas provas, e "Não é duplicada" as separa.

---

### P1: Só as válidas seguem ⭐ MVP

**User Story**: Como docente, quero que o que não vale não apareça na pontuação, no Relatório nem no Comprovante, para o dossiê sair só com o que conta.

**Why P1**: Hoje atividades fora do interstício aparecem na Tabela como "Não pontuada".

**Acceptance Criteria**:

1. The system SHALL calcular a pontuação da Etapa 4 e SHALL gerar a Tabela, o Relatório, o Comprovante e a prévia da conclusão só com as atividades válidas  <!-- ubiquitous -->
2. The system SHALL não incluir no Comprovante páginas cuja única atividade é não válida ou mesclada  <!-- ubiquitous -->
3. WHEN o docente corrige uma atividade não válida e ela passa a válida THEN the system SHALL incluí-la no cálculo e nas gerações seguintes  <!-- event-driven -->
4. WHEN a Etapa 4 mostra os contadores THEN the frontend SHALL contá-los só sobre as atividades válidas  <!-- event-driven -->
5. IF há atividade válida sem categoria THEN the system SHALL recusar a geração da Tabela, do Relatório e do Comprovante com 422 `ATIVIDADE_SEM_CATEGORIA`  <!-- unwanted-behavior -->

**Independent Test**: Gerar a Tabela de um processo com atividades fora do interstício e ver que nenhuma linha delas aparece; corrigir a data de uma e ver a linha na próxima geração.

---

### P1: Editar atividade com poucos campos ⭐ MVP

**User Story**: Como docente, quero editar uma atividade só com o título, a data e a categoria, para corrigir um erro de leitura sem preencher um formulário longo.

**Why P1**: O formulário atual tem mais de 15 campos e a maioria vem do documento.

**Acceptance Criteria**:

1. WHEN o docente edita uma atividade THEN the frontend SHALL mostrar os campos Título, Data e Categoria; nas categorias medidas por ano, Início e Fim no lugar da Data; e Horas só quando a categoria tem carga horária mínima  <!-- event-driven -->
2. WHEN o docente salva uma data fora do interstício THEN the system SHALL responder 422 no campo da data com "A data deve estar entre dd/mm/aaaa e dd/mm/aaaa" e SHALL manter a atividade como estava  <!-- event-driven -->
3. WHERE a categoria é medida por ano, o sistema SHALL aceitar o período que cruza o interstício e SHALL recusar o que não o toca  <!-- optional-feature -->
4. WHEN o docente cria uma atividade manual THEN the frontend SHALL pedir Título, Data, Categoria e Quantidade  <!-- event-driven -->
5. WHERE a atividade é uma oferta do Grupo I, the frontend SHALL mostrar só o Título e a Categoria, porque o período e as horas vêm do documento  <!-- optional-feature -->
6. WHEN o docente salva uma edição THEN the system SHALL aplicá-la na hora, sem justificativa, e SHALL gravar o evento de auditoria  <!-- event-driven -->
7. The system SHALL manter o vínculo da atividade com os documentos pela ação "Vincular" da Etapa 3, sem campo de texto de comprovante no formulário  <!-- ubiquitous -->

**Independent Test**: Editar o título e a data de uma atividade e salvar; tentar uma data de 2023 e ver o erro.

---

### P1: Quantidade e valor manual na Etapa 4 ⭐ MVP

**User Story**: Como docente, quero ajustar a quantidade e o valor unitário de uma atividade pontuada na Etapa 4, onde vejo o efeito nos pontos.

**Why P1**: A Quantidade sai do formulário da Etapa 3 e o ajuste manual precisa de um lugar.

**Acceptance Criteria**:

1. WHEN o docente abre "Editar pontuação" de uma atividade na Etapa 4 THEN the frontend SHALL oferecer Quantidade (ou Horas, nos itens medidos por horas) e o valor unitário manual  <!-- event-driven -->
2. WHEN o docente salva THEN the system SHALL recalcular a pontuação na hora, sem justificativa, e SHALL gravar o evento de auditoria  <!-- event-driven -->
3. IF a quantidade informada é negativa ou não numérica THEN the system SHALL responder 422 no campo `quantidade`  <!-- unwanted-behavior -->

**Independent Test**: Mudar a quantidade de uma orientação de 1 para 3 e ver o total triplicar.

---

## Edge Cases

- WHEN uma atividade deixa de ser duplicada por edição do título ou da data THEN the system SHALL não desfazer a mesclagem já feita; o docente usa "Não é duplicada".
- IF a categoria de uma atividade validada é trocada THEN the system SHALL recalcular a pontuação e manter o status validada.
- IF uma atividade não válida por carga horária é corrigida para uma carga suficiente THEN the frontend SHALL passá-la para as válidas com o status que ela tinha.
- IF a mesma atividade tem uma prova em documento fora do interstício e outra em documento dentro dele THEN the system SHALL mantê-la com a prova do documento dentro (AD-019).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| VAL-01 | P1: Validar pontua | Design | Pending |
| VAL-02 | P1: Validar pontua | Design | Pending |
| VAL-03 | P1: Validar pontua | Design | Pending |
| VAL-04 | P1: Validar pontua | Design | Pending |
| VAL-05 | P1: Validar pontua | Design | Pending |
| VAL-06 | P1: Validar pontua | Design | Implementing |
| SEC-01 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-02 | P1: Etapa 3 em duas seções | Design | Implementing |
| SEC-03 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-04 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-05 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-06 | P1: Etapa 3 em duas seções | Design | Implementing |
| SEC-07 | P1: Etapa 3 em duas seções | Design | Implementing |
| SEC-08 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-09 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-10 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-11 | P1: Etapa 3 em duas seções | Design | Pending |
| SEC-12 | P1: Etapa 3 em duas seções | Design | Pending |
| DUP-01 | P1: Duplicadas mescladas | Design | Pending |
| DUP-02 | P1: Duplicadas mescladas | Design | Pending |
| DUP-03 | P1: Duplicadas mescladas | Design | Pending |
| DUP-04 | P1: Duplicadas mescladas | Design | Pending |
| DUP-05 | P1: Duplicadas mescladas | Design | Pending |
| DUP-06 | P1: Duplicadas mescladas | Design | Pending |
| DUP-07 | P1: Duplicadas mescladas | Design | Pending |
| SEG-01 | P1: Só as válidas seguem | Design | Implementing |
| SEG-02 | P1: Só as válidas seguem | Design | Pending |
| SEG-03 | P1: Só as válidas seguem | Design | Pending |
| SEG-04 | P1: Só as válidas seguem | Design | Pending |
| SEG-05 | P1: Só as válidas seguem | Design | Pending |
| EDT-01 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-02 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-03 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-04 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-05 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-06 | P1: Editar atividade com poucos campos | Design | Pending |
| EDT-07 | P1: Editar atividade com poucos campos | Design | Pending |
| QTD-01 | P1: Quantidade e valor manual na Etapa 4 | Design | Pending |
| QTD-02 | P1: Quantidade e valor manual na Etapa 4 | Design | Pending |
| QTD-03 | P1: Quantidade e valor manual na Etapa 4 | Design | Pending |

**ID format:** `[CATEGORY]-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Implemented → Verified

**Coverage:** 40 total, 0 mapped to tasks, 40 unmapped ⚠️ (a Design e as Tasks mapeiam)

---

## Success Criteria

- [ ] Uma atividade com categoria II.5 validada pontua 8,00 na Etapa 4 sem outra ação (teste automatizado de ponta a ponta na API).
- [ ] Um processo com 120 atividades mostra as válidas em páginas de 25 e as não válidas, com motivo, numa seção fechada (teste de componente).
- [ ] A Tabela, o Relatório e o Comprovante de um processo com atividades fora do interstício, duplicadas e rejeitadas não trazem nenhuma delas (teste automatizado).
- [ ] Duas atividades duplicadas viram uma, com as duas provas, e "Não é duplicada" as separa (teste automatizado).

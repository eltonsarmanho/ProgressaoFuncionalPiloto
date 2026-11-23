# Gestão das tabelas de pontuação: tabela em uso por unidade, CRUD na tela e interface melhor (gestao-tabelas) Specification

**Status**: Approved (usuário, 2026-11-23: "sim"; emendas A1 a A10 aprovadas com o desenho em 2026-11-23), incluindo os padrões do agente marcados com "n" e a reescrita da regra 11 do `CLAUDE.md`)
**Origem**: pedido do usuário em 2026-11-23 sobre a tela "Tabelas de pontuação": criar um mecanismo de CRUD onde o ADMIN gerencia e seleciona a tabela em uso, e melhorar a UX da tela. Respostas do usuário na mesma data: a "tabela em uso" é um padrão por unidade; qualquer tabela pode ser usada, com avisos; o CRUD inclui arquivar, excluir e editar critérios na tela; a UX cobre layout e legibilidade e ações visíveis.

## Problem Statement

A tela "Tabelas de pontuação" só lista as tabelas e abre os critérios ("Ver critérios"). O backend já sabe criar, duplicar, versionar, editar critérios, importar CSV e associar unidades (ADM-01 a ADM-11), mas nada disso tem tela, não existe arquivar nem excluir, e não há como o ADMIN dizer qual versão é a tabela em uso de uma unidade: o sistema só sugere a versão vigente associada à unidade (SEL-02) e a etiqueta "Em uso" da tela significa apenas que algum processo já usa aquela versão. A lista também tem colunas apertadas ("Situação" e "Ações" quebram letra a letra) e uma tabela repetida por unidade. Esta feature dá ao ADMIN a gestão completa pela tela, uma marcação explícita da versão em uso por unidade e uma lista legível.

## Goals

- [ ] O ADMIN marca, para cada unidade acadêmica, a versão de tabela em uso, e o processo novo dessa unidade parte dela (sugestão a confirmar, como em SEL-02).
- [ ] O ADMIN cria, duplica, versiona, importa CSV, edita critérios, associa unidades, arquiva e exclui tabelas pela tela, sem usar a API.
- [ ] Nenhuma operação muda o que um processo já gravou nem os documentos gerados (AD-012); nada é excluído ou editado se um processo usa a versão.
- [ ] A lista de tabelas é legível em tela larga e em 360 px, sem quebra de letra por letra, e cada versão mostra suas ações.

## Out of Scope

Explicitamente excluído. Documentado para evitar crescimento do escopo.

| Feature | Reason |
| ------- | ------ |
| Editar critérios de uma versão que um processo usa | ADM-04: segue 409 orientando a criar uma nova versão; a tela mostra essa orientação |
| Mudar o motor de pontuação, os modos de pontuação ou a tabela oficial (`ufpa.json`) | A feature só gerencia tabelas; a pontuação continua determinística em Python (regra 1) |
| Tirar a escolha da tabela por processo na Etapa 4 | O usuário pediu um padrão por unidade, não o fim da escolha por processo (SEL-02 a SEL-07 seguem) |
| Arquivar versões soltas | O arquivamento vale para a tabela inteira (coluna `scoring_tables.archived` já existe); uma versão se retira da lista com a exclusão, quando nenhum processo a usa |
| Comparar duas versões, buscar e agrupar critérios na tela de critérios, explicação das situações com ajuda na tela | O usuário escolheu só layout e ações visíveis; podem virar feature futura |
| Mudar a situação (`OFICIAL`, `PENDENTE_VALIDACAO`) de uma versão existente | Sem pedido; a situação segue como definida ao criar a versão |
| Tornar a versão substituída (AD-023) escolhível de novo | AD-023: a versão substituída não é sugerida nem escolhível; continua somente leitura |
| Mudar documentos já gerados | AD-012: a versão gerada é imutável |

---

## Assumptions & Open Questions

Toda ambiguidade é resolvida ou registrada aqui. "Confirmed? y" é decisão do usuário (2026-11-23); "n" é padrão do agente que o usuário confirma ao aprovar a spec.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| O que é "tabela em uso" | Uma versão de tabela marcada como padrão de uma unidade acadêmica (no máximo uma por unidade); o processo novo da unidade a recebe como sugestão | Resposta do usuário em 2026-11-23: "Padrão por unidade" | y |
| Quem pode | Só o ADMIN faz qualquer escrita; os demais perfis leem (ADM-11) | Padrão de ADM-01 a ADM-11 | y |
| Limite das tabelas | Qualquer tabela pode ser criada, editada e marcada em uso; as não oficiais seguem com os avisos que já existem (`TABELA_PENDENTE_VALIDACAO`, `TABELA_FORA_DE_VIGENCIA`, `TABELA_DE_OUTRA_UNIDADE`). A regra 11 do `CLAUDE.md` passa a dizer que a tabela oficial da UFPA é o padrão inicial da FASI e do IFCH, não a única | Resposta do usuário em 2026-11-23: "Qualquer tabela, avisos" | y |
| Reescrever a regra 11 do `CLAUDE.md` | Feito em 2026-11-23, com a aprovação desta spec | `CLAUDE.md` é instrução do projeto; a mudança nasce da decisão acima | y |
| O que a marcação aceita | Versão de uma tabela não arquivada, associada à unidade e não substituída; vigência não é exigida (fora de vigência vale, com o alerta de SEL-07 ao confirmar no processo) | Padrão do agente; evita bloquear o ADMIN e reaproveita os alertas | y |
| Unidade sem versão em uso | Mantém a sugestão por vigência de SEL-02 (versão associada à unidade, vigente na data final do interstício, a de início mais recente) | Padrão do agente; nenhuma unidade perde a sugestão que tem hoje | y |
| Semente da marcação | Cada unidade que tem a tabela oficial da UFPA associada, nenhuma versão em uso e nenhum evento de marcação anterior passa a ter a versão "Tabela oficial de pontuação UFPA, Grupo I no total" em uso, com auditoria sem usuário; é idempotente e nunca desfaz a decisão do ADMIN (emenda A1 do desenho) | Padrão do agente; é a versão que a sugestão já escolhe hoje (AD-023) | y |
| Justificativa nas operações | A marcação em uso, o arquivamento e a exclusão agem na hora, sem campo de justificativa (como as Etapas 2 a 4); a edição de critério continua exigindo a referência normativa da alteração (ADM-03) e a versão nova continua exigindo vigência e referência (ADM-05) | Padrão do agente; a regra 5 vale para as Etapas 2 a 4, e ADM-03 e ADM-05 já existem | y |
| Arquivar | Arquivar a tabela a tira de toda lista de escolha (sugestão, escolha na Etapa 4 e marcação em uso); processos que a usam continuam lendo e calculando com ela; desarquivar a devolve. Não se arquiva a tabela que tem versão em uso de alguma unidade | Padrão do agente; evita unidade sem tabela em uso por engano | y |
| Excluir versão | Só a versão que nenhum processo usa, que não está em uso de nenhuma unidade e que não substitui outra versão; apaga a versão, os grupos e os critérios; a auditoria fica | Padrão do agente; protege processos e a cadeia de substituição | y |
| Excluir tabela | Só a tabela sem versão usada por processo e sem versão em uso de unidade; apaga a tabela, as versões, os critérios e as associações de unidade; pede confirmação com a lista do que sai, como na regra 9; a auditoria fica | Padrão do agente, no mesmo molde da exclusão de processo | y |
| Etiquetas | "Em uso" passa a significar o padrão da unidade (com a sigla da unidade); o que hoje se chama "Em uso" (algum processo usa a versão) passa a "Usada por processo" | Evita dois sentidos para a mesma palavra | y |
| Filtros da lista | Filtro por unidade e por "mostrar arquivadas" (desligado por padrão) | Parte de "layout e legibilidade" aprovada pelo usuário | y |
| Migração | Uma migração nova cria a tabela da marcação em uso e nenhuma outra; sem apagar coluna | Padrão do agente | y |
| Deploy | Imagens novas do backend e do frontend e migração; só com a autorização do usuário | CLAUDE.md: push e deploy só com autorização | y |

**Open questions:** none - all resolved or logged above (as linhas com "n" são padrões do agente, aprovados com a spec em 2026-11-23).

---

## User Stories

### P1: Tabela em uso por unidade ⭐ MVP

**User Story**: Como ADMIN, quero marcar qual versão de tabela é a em uso de cada unidade, para que os processos novos partam dela sem eu depender da data de vigência.

**Why P1**: É o pedido central: "selecionar a Tabela em USO".

**Acceptance Criteria** (IDs `GTAB-01` a `GTAB-10`):

1. The system SHALL guardar, para cada unidade acadêmica, no máximo uma versão de tabela em uso.  <!-- ubiquitous -->
2. WHERE o usuário é ADMIN the system SHALL permitir marcar uma versão como a em uso de uma unidade, substituindo a marcação anterior dessa unidade, e SHALL registrar evento de auditoria com usuário, unidade, versão anterior e nova versão.  <!-- optional-feature -->
3. IF a versão pertence a uma tabela arquivada ou está substituída THEN the system SHALL recusar a marcação com 409; IF a tabela da versão não está associada à unidade THEN the system SHALL recusar com 422 no campo `unit_id`.  <!-- unwanted-behavior -->
4. WHERE o usuário é ADMIN the system SHALL permitir remover a marcação em uso de uma unidade, voltando a sugestão por vigência, com auditoria.  <!-- optional-feature -->
5. WHEN um usuário abre a pontuação de um processo sem tabela escolhida e a unidade do docente tem versão em uso THEN the system SHALL sugerir essa versão e SHALL não aplicá-la antes da confirmação do usuário.  <!-- event-driven -->
6. IF a unidade do docente não tem versão em uso THEN the system SHALL sugerir a versão pela vigência, como em SEL-02, e SHALL manter o alerta `TABELA_NAO_ENCONTRADA` quando não houver nenhuma.  <!-- unwanted-behavior -->
7. IF a versão em uso não estava vigente na data final do interstício THEN the system SHALL sugeri-la e SHALL emitir o alerta `TABELA_FORA_DE_VIGENCIA` quando o usuário a confirmar, como em SEL-07.  <!-- unwanted-behavior -->
8. WHILE um processo tem tabela escolhida the system SHALL manter essa tabela, qualquer que seja a marcação em uso da unidade, sem recalcular nem reavaliar o processo.  <!-- state-driven -->
9. WHEN o sistema inicia THEN the system SHALL marcar a versão "Tabela oficial de pontuação UFPA, Grupo I no total" como em uso de cada unidade que tem a tabela oficial associada, nenhuma versão em uso e nenhum evento de marcação anterior na auditoria, com um evento de auditoria sem usuário por unidade, e SHALL não remarcar a unidade que o ADMIN desmarcou nem a que perdeu a marcação por substituição, nem regravar numa segunda partida.  <!-- event-driven -->
10. WHEN um usuário autenticado consulta as tabelas THEN the system SHALL devolver, por versão, as unidades para as quais ela está em uso (`default_for_unit_ids`), a quantidade de processos que a usam (`process_count`) e o campo `in_use` com o sentido de hoje (algum processo a usa).  <!-- event-driven -->

**Independent Test**: Num ambiente sintético com duas versões associadas à FASI, marcar a segunda como em uso, abrir a pontuação de um processo novo da FASI e ver a segunda sugerida; trocar a marcação e ver a sugestão mudar; abrir um processo que já tinha tabela escolhida e ver a mesma tabela.

---

### P1: Gestão das tabelas pela tela ⭐ MVP

**User Story**: Como ADMIN, quero criar, duplicar, versionar, importar e associar tabelas pela tela, para não precisar da API.

**Why P1**: ADM-01 a ADM-11 existem só no backend (a interface de administração, P3 da `pontuacao`, nunca foi feita).

**Acceptance Criteria** (IDs `GTAB-11` a `GTAB-17`):

1. WHERE o usuário é ADMIN the frontend SHALL permitir criar uma tabela com nome, unidades associadas, situação, início de vigência e referência normativa, mostrando o erro da API junto do campo.  <!-- optional-feature -->
2. WHERE o usuário é ADMIN the frontend SHALL permitir duplicar uma tabela com o nome novo, criar uma nova versão a partir de outra com início de vigência e referência normativa, e mostrar o 409 de ADM-05 a ADM-07 com a mensagem da API.  <!-- optional-feature -->
3. WHERE o usuário é ADMIN the frontend SHALL permitir enviar um CSV de critérios para criar uma versão e SHALL listar todas as linhas e campos inválidos quando a API responder 422, sem criar a versão.  <!-- optional-feature -->
4. WHERE o usuário é ADMIN the frontend SHALL permitir trocar as unidades associadas a uma tabela.  <!-- optional-feature -->
5. WHERE o usuário não é ADMIN the frontend SHALL mostrar a lista e os critérios sem nenhum botão de escrita, e a API SHALL responder 403 a qualquer escrita.  <!-- optional-feature -->
6. WHEN uma operação é concluída THEN the frontend SHALL atualizar a lista sem recarregar a página e SHALL mostrar a confirmação ou o erro em texto, sem depender só de cor.  <!-- event-driven -->
7. WHEN o ADMIN abre o histórico de uma tabela THEN the frontend SHALL mostrar as versões e os eventos de auditoria devolvidos por ADM-10.  <!-- event-driven -->

**Independent Test**: Pela tela, duplicar uma tabela sintética, criar uma versão nova, enviar um CSV com uma linha inválida e ver a lista de erros, enviar um CSV válido e ver a versão, e abrir o histórico.

---

### P1: Editar critérios na tela ⭐ MVP

**User Story**: Como ADMIN, quero editar os critérios de uma versão na tela, para corrigir pontos e limites sem importar um CSV inteiro.

**Why P1**: Pedido do usuário ("editar critérios na tela").

**Acceptance Criteria** (IDs `GTAB-18` a `GTAB-22`):

1. WHERE o usuário é ADMIN the frontend SHALL permitir editar, por critério de uma versão que nenhum processo usa, os campos que a API aceita em ADM-03, exigindo a referência normativa da alteração.  <!-- optional-feature -->
2. IF a versão é usada por algum processo THEN the frontend SHALL mostrar os critérios somente leitura e SHALL orientar a criar uma nova versão (ADM-04), sem oferecer a edição.  <!-- unwanted-behavior -->
3. IF a versão está substituída ou não é a mais recente da tabela THEN the frontend SHALL mostrar os critérios somente leitura e SHALL indicar o motivo (a versão que a substitui, ou que existe versão mais recente), como a API já recusa com 409.  <!-- unwanted-behavior -->
4. IF a API recusa um valor com 422 THEN the frontend SHALL mostrar a mensagem junto do campo do critério e SHALL manter o que a pessoa digitou.  <!-- unwanted-behavior -->
5. WHEN a edição é gravada THEN the frontend SHALL mostrar o valor novo na lista de critérios sem recarregar a página, e a auditoria SHALL registrar valores anterior e novo (ADM-03).  <!-- event-driven -->

**Independent Test**: Editar a pontuação de um critério de uma versão sintética não usada e ver o valor novo e o evento de auditoria; abrir uma versão usada por um processo e ver a orientação sem botão de edição.

---

### P1: Arquivar e excluir ⭐ MVP

**User Story**: Como ADMIN, quero arquivar uma tabela que não vou mais usar e excluir o que foi criado por engano, para a lista mostrar só o que importa.

**Why P1**: Pedido do usuário ("arquivar" e "excluir").

**Acceptance Criteria** (IDs `GTAB-23` a `GTAB-32`):

1. WHERE o usuário é ADMIN the system SHALL permitir arquivar e desarquivar uma tabela, com auditoria.  <!-- optional-feature -->
2. WHILE uma tabela está arquivada the system SHALL não a sugerir, não oferecê-la na escolha da Etapa 4 e não aceitá-la na marcação em uso, e SHALL manter a leitura e o cálculo dos processos que já a usam.  <!-- state-driven -->
3. IF a tabela tem versão em uso de alguma unidade THEN the system SHALL recusar o arquivamento com 409 listando as unidades.  <!-- unwanted-behavior -->
4. WHERE o usuário é ADMIN the system SHALL permitir excluir uma versão de tabela, apagando a versão, os grupos e os critérios, e SHALL manter os eventos de auditoria; quando a versão apagada é a mais recente e tinha fechado a vigência da anterior (ADM-05), the system SHALL devolver à anterior o fim de vigência da apagada, na mesma transação e com evento de auditoria.  <!-- optional-feature -->
5. IF a versão é usada por algum processo, ou está em uso de alguma unidade, ou substitui outra versão, ou é a única versão da tabela THEN the system SHALL recusar a exclusão com 409 informando o motivo e, para o uso, a quantidade de processos, sem apagar nada; para a única versão, o caminho é excluir a tabela.  <!-- unwanted-behavior -->
6. WHERE o usuário é ADMIN the system SHALL permitir excluir uma tabela, apagando a tabela, as versões, os critérios e as associações de unidade, e SHALL manter os eventos de auditoria.  <!-- optional-feature -->
7. IF a tabela tem versão usada por algum processo ou em uso de alguma unidade THEN the system SHALL recusar a exclusão com 409 e sem apagar nada.  <!-- unwanted-behavior -->
8. WHEN o ADMIN pede a exclusão de uma tabela THEN the frontend SHALL mostrar a confirmação com a lista do que sai (nome, quantidade de versões, de critérios e as unidades associadas) e SHALL só excluir depois da confirmação; a exclusão de uma versão mostra a mesma confirmação com o nome da versão e a quantidade de critérios.  <!-- event-driven -->
9. IF a exclusão ou o arquivamento é pedido por quem não é ADMIN THEN the system SHALL responder 403.  <!-- unwanted-behavior -->
10. WHEN uma exclusão é confirmada THEN the system SHALL registrar um evento de auditoria com usuário, entidade, nome e quantidade de versões e de critérios apagados.  <!-- event-driven -->

**Independent Test**: Criar uma tabela sintética, arquivá-la e ver que some das escolhas; desarquivá-la; excluir uma versão não usada; tentar excluir a versão que um processo usa e ver o 409; excluir a tabela com a confirmação e ver a auditoria.

---

### P1: Lista de tabelas legível e com ações visíveis ⭐ MVP

**User Story**: Como ADMIN, quero ver cada tabela com suas versões e ações claras, para entender o que está em uso e agir sem procurar.

**Why P1**: Pedido do usuário ("melhorar a UX").

**Acceptance Criteria** (IDs `GTAB-33` a `GTAB-40`):

1. The frontend SHALL mostrar cada tabela como um cartão com o nome, as unidades associadas e as versões, e SHALL destacar, em cada cartão, a versão em uso com a sigla da unidade.  <!-- ubiquitous -->
2. The frontend SHALL mostrar por versão: nome, vigência, situação, referência normativa e as etiquetas "Oficial" ou "Pendente de validação", "Em uso (sigla)", "Usada por processo", "Substituída" e "Arquivada", sem quebrar uma palavra em letras isoladas em nenhuma largura de tela.  <!-- ubiquitous -->
3. WHERE o usuário é ADMIN the frontend SHALL mostrar por versão os botões "Ver critérios", "Definir como em uso", "Nova versão a partir desta" e "Excluir versão" e, por tabela, "Importar CSV", "Duplicar", "Unidades", "Histórico", "Arquivar" ou "Desarquivar" e "Excluir tabela", além de "Nova tabela" no cabeçalho da página, com rótulo de texto em cada um.  <!-- optional-feature -->
4. IF uma ação não é permitida pela regra da versão (por exemplo, "Definir como em uso" numa versão substituída, "Excluir versão" numa versão usada) THEN the frontend SHALL mostrar o botão desabilitado com o motivo em texto visível ou como descrição acessível.  <!-- unwanted-behavior -->
5. The frontend SHALL oferecer um filtro por unidade e a opção "Mostrar arquivadas", desligada por padrão, e SHALL mostrar a quantidade de tabelas listadas.  <!-- ubiquitous -->
6. The frontend SHALL funcionar em 360 px de largura sem rolagem horizontal da página, com as versões empilhadas em cartões e com os botões alcançáveis por teclado, com alvo de toque de pelo menos 44 px.  <!-- ubiquitous -->
7. WHILE a lista carrega THE frontend SHALL mostrar um estado de carregamento, e IF a carga falha THEN the frontend SHALL mostrar a mensagem de erro com a opção de tentar de novo.  <!-- state-driven -->
8. The frontend SHALL mostrar, quando nenhuma tabela passa pelo filtro, uma mensagem de lista vazia com a ação "Limpar filtros".  <!-- ubiquitous -->

**Independent Test**: Abrir a tela com as tabelas semeadas em 1280 px e em 360 px e conferir cartões, etiquetas, botões e filtro, sem quebra de letra por letra nem rolagem horizontal; abrir como não ADMIN e ver só leitura.

---

### P1: Coerência com a semente e com as outras regras ⭐ MVP

**User Story**: Como ADMIN, quero que o que eu decido nas tabelas não seja desfeito na próxima partida do sistema nem fique incoerente com as regras já existentes.

**Why P1**: A semente roda a cada partida do backend e, sem estas regras, desfaria arquivar, excluir e marcar.

**Acceptance Criteria** (IDs `GTAB-41` a `GTAB-45`):

1. WHEN o sistema inicia THEN the semente que arquiva as tabelas antigas e desassocia as unidades delas (OFI-09) SHALL não agir sobre a tabela que alguma pessoa já alterou, e SHALL continuar a agir sobre a que nenhuma pessoa tocou.  <!-- event-driven -->
2. IF o ADMIN tenta excluir a tabela oficial da UFPA ou uma de suas versões THEN the system SHALL recusar com 409 e o código `TABELA_OFICIAL_PROTEGIDA`, sem apagar nada; a tabela oficial pode ser arquivada e marcada em uso.  <!-- unwanted-behavior -->
3. IF o ADMIN tira de uma tabela uma unidade que tem a versão dela em uso THEN the system SHALL recusar com 409 e o código `UNIDADE_COM_VERSAO_EM_USO`, listando as siglas, sem alterar as associações.  <!-- unwanted-behavior -->
4. IF a versão escolhida para um processo é de tabela arquivada e não é a versão que o processo já tem THEN the system SHALL recusar com 409 e o código `TABELA_ARQUIVADA`; the sugestão por vigência SHALL ignorar tabela arquivada.  <!-- unwanted-behavior -->
5. WHEN o ADMIN duplica uma tabela, ou cria uma versão numa tabela a partir de versão de outra tabela THEN the system SHALL não copiar o código da norma (`norm_code`) da origem; a nova versão da mesma tabela mantém o código.  <!-- event-driven -->

**Independent Test**: Num ambiente sintético, desmarcar a versão em uso de uma unidade, reiniciar a semente e ver que a unidade continua sem marcação; desarquivar uma tabela antiga, reiniciar a semente e ver que ela continua desarquivada; tentar excluir a tabela oficial e ver o 409.

---

## Edge Cases

- WHEN a unidade tem a versão em uso e o ADMIN cria uma nova versão da mesma tabela que encerra a anterior (ADM-05) THEN the system SHALL manter a marcação na versão antiga até o ADMIN marcar a nova, e SHALL mostrar, no cartão, que a versão em uso está encerrada.
- WHEN a versão em uso é a que foi substituída por uma versão nova (AD-023) THEN the system SHALL desfazer a marcação dessa unidade com auditoria sem usuário e SHALL voltar à sugestão por vigência até o ADMIN marcar outra.
- WHEN duas pessoas marcam a versão em uso da mesma unidade ao mesmo tempo THEN the system SHALL aceitar uma e deixar a outra como a marcação final sem registro duplicado, com um só registro por unidade.
- IF o nome de uma tabela criada ou duplicada já existe (sem diferenciar maiúsculas) THEN the system SHALL responder 422 no campo `name`, como ADM-01 e ADM-02 já fazem.
- WHEN a exclusão de uma tabela falha no meio THEN the system SHALL não apagar nada (uma transação só).
- WHEN a tabela é desarquivada THEN the system SHALL não remarcar nenhuma versão em uso.

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | GTAB-03, GTAB-11, GTAB-18, GTAB-22: validação de nome, vigência, referência e valores dos critérios nas regras de ADM-01 a ADM-09; o CSV mantém o formato de ADM-08 |
| Failure / partial-failure states | GTAB-05, GTAB-07, GTAB-27: recusas com 409 sem apagar nada; a exclusão de tabela é uma transação; a tela mostra erro e permite tentar de novo (GTAB-39) |
| Idempotency / retry / duplicate handling | GTAB-09: a semente da marcação não repete nem regrava; marcar a mesma versão duas vezes não grava evento novo; arquivar o já arquivado não grava evento novo |
| Auth boundaries & rate limits | GTAB-15, GTAB-31: toda escrita é só do ADMIN (403); a leitura é de qualquer usuário autenticado (ADM-11); sem limite de taxa novo |
| Concurrency / ordering | Edge Cases: uma única marcação por unidade garantida pelo banco; a exclusão e a marcação concorrentes acabam em um estado consistente (o 409 vale) |
| Data lifecycle / expiry | GTAB-24, GTAB-26, GTAB-28: arquivar é reversível; excluir é definitivo e mantém só a auditoria; processos e documentos gerados nunca mudam (AD-012) |
| Observability | GTAB-02, GTAB-25, GTAB-32: auditoria de marcar, desmarcar, arquivar, desarquivar e excluir, com usuário; a semente audita sem usuário (GTAB-09) |
| External-dependency failure | N/A because a feature não chama serviço externo nem a IA |
| State-transition integrity | GTAB-03, GTAB-26, GTAB-29: a versão substituída, a tabela arquivada e a versão usada por processo não entram em marcação, escolha nem exclusão; as regras SEL-02 a SEL-07 e ADM-03 a ADM-07 continuam valendo |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| GTAB-01 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-02 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-03 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-04 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-05 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-06 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-07 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-08 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-09 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-10 | P1: Tabela em uso por unidade | Implemented | Implementing |
| GTAB-11 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-12 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-13 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-14 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-15 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-16 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-17 | P1: Gestão das tabelas pela tela | Implemented | Implementing |
| GTAB-18 | P1: Editar critérios na tela | Implemented | Implementing |
| GTAB-19 | P1: Editar critérios na tela | Implemented | Implementing |
| GTAB-20 | P1: Editar critérios na tela | Implemented | Implementing |
| GTAB-21 | P1: Editar critérios na tela | Implemented | Implementing |
| GTAB-22 | P1: Editar critérios na tela | Implemented | Implementing |
| GTAB-23 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-24 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-25 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-26 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-27 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-28 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-29 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-30 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-31 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-32 | P1: Arquivar e excluir | Implemented | Implementing |
| GTAB-33 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-34 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-35 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-36 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-37 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-38 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-39 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-40 | P1: Lista legível e com ações visíveis | Implemented | Implementing |
| GTAB-41 | P1: Coerência com a semente e com as outras regras | Implemented | Implementing |
| GTAB-42 | P1: Coerência com a semente e com as outras regras | Implemented | Implementing |
| GTAB-43 | P1: Coerência com a semente e com as outras regras | Implemented | Implementing |
| GTAB-44 | P1: Coerência com a semente e com as outras regras | Implemented | Implementing |
| GTAB-45 | P1: Coerência com a semente e com as outras regras | Implemented | Implementing |

## Success Criteria

- [ ] Para cada unidade, a marcação em uso aparece na tela e comanda a sugestão do processo novo; um processo que já tinha tabela escolhida não muda.
- [ ] O ADMIN executa pela tela, sem a API, todas as operações de ADM-01 a ADM-10 mais arquivar, excluir e marcar em uso; um não ADMIN não vê nem consegue nenhuma escrita (403).
- [ ] Nenhuma versão usada por processo é editada ou excluída, e nenhum documento gerado muda de conteúdo.
- [ ] A lista não quebra palavra em letras isoladas em 1280 px nem em 360 px, e não rola na horizontal em 360 px.
- [ ] A migração é a única, cria só a tabela da marcação e não apaga coluna; a semente é idempotente e auditada.
- [ ] Gate completo do backend e do frontend limpo no fim; verificação independente com PASS antes do deploy, que só sai com a autorização do usuário.

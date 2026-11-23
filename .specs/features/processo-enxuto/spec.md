# Processo enxuto: Etapa 1 sem os dados institucionais e as observações (processo-enxuto) Specification

**Status**: Approved (usuário, 2026-11-23: "Tirar esses cinco campos da tela e do alerta")
**Origem**: pergunta do usuário em 2026-11-23 sobre para que servem "Nome do responsável", "Cargo do responsável", "Portaria de designação do responsável", "Unidade administrativa responsável" e "Observações" da Etapa 1.

## Problem Statement

A Etapa 1 pede cinco campos que nenhum documento gerado usa (Tabela, Relatório, Comprovante, Requerimento e Parecer não os leem). O único efeito deles é o alerta `DADOS_INCOMPLETOS`, que avisa quando estão em branco. O usuário não entendeu para que servem, e pedir o que não vai a lugar nenhum induz a erro e cria um alerta sem valor. Esta feature tira os cinco campos da tela, da API e da regra de verificação, sem apagar o que já está gravado.

## Goals

- [ ] A Etapa 1 não mostra os cinco campos nem o grupo "Dados institucionais e observações".
- [ ] O alerta `DADOS_INCOMPLETOS` deixa de existir: nenhum processo o recebe.
- [ ] A API de processos não recebe nem devolve os cinco campos.
- [ ] O que já está gravado nas cinco colunas fica no banco, sem uso, e nenhuma migração é criada.

## Out of Scope

Explicitamente excluído. Documentado para evitar crescimento do escopo.

| Feature | Reason |
| ------- | ------ |
| Usar o responsável e a unidade em algum documento (por exemplo, o Requerimento) | Nenhum modelo oficial pede isso; o usuário escolheu tirar os campos |
| Apagar as colunas `resp_name`, `resp_position`, `resp_appointment`, `resp_admin_unit` e `notes` ou migrar dados | Mesma decisão da AD-026: a migração desfaz mal e nada ganha; as colunas ficam sem uso |
| Mudar documentos já gerados | AD-012: a versão gerada é imutável; os documentos nunca usaram esses campos |
| Mudar a ligação do processo com a unidade (`unit_id`) | A unidade do processo é outro campo, escolhido na Etapa 1, e não é a "unidade administrativa responsável" |
| Mudar os campos "Observações" de outras telas (Etapa 6, atividades, versões de tabela) | Pertencem a outras features |
| Apagar eventos de auditoria antigos que mencionam os campos | A auditoria é imutável; só as gravações novas deixam de tratá-los |

---

## Assumptions & Open Questions

Toda ambiguidade é resolvida ou registrada aqui. "Confirmed? y" é decisão do usuário (2026-11-23); "n" é padrão do agente que o usuário confirma ao aprovar a spec.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Quais campos saem | Os cinco da tela: nome, cargo, portaria e unidade do responsável, e as observações do processo | Pedido do usuário em 2026-11-23 | y |
| Alerta `DADOS_INCOMPLETOS` | Sai por inteiro (o código, a regra e a mensagem "Campos não preenchidos"); era o único efeito dos campos | Pedido do usuário em 2026-11-23: "da tela e do alerta" | y |
| Colunas no banco | Ficam, com os valores já gravados, sem leitura, exibição nem alteração; nenhuma migração | Mesma solução da AD-026 (coluna `notes` do Parecer) | n |
| Corpo de `POST` e `PUT` com os campos antigos | Aceito e ignorado: os valores não são gravados nem devolvidos; sem 422, porque o esquema de processo já ignora campos desconhecidos e um cliente antigo não deve quebrar | Padrão do agente; compatível com o esquema atual | n |
| Auditoria da edição | A visão do processo gravada na auditoria deixa de trazer os cinco campos; eventos antigos ficam como estão | Segue da retirada dos campos da entidade | n |
| Deploy | Imagens novas do backend e do frontend; sem migração; só com a autorização do usuário | CLAUDE.md: push e deploy só com autorização | y |

**Open questions:** none - all resolved or logged above (as linhas com "n" são padrões do agente, a confirmar na revisão).

---

## User Stories

### P1: Etapa 1 sem campos que nenhum documento usa ⭐ MVP

**User Story**: Como docente, quero preencher na Etapa 1 só o que o processo usa, para não digitar dados que nenhum documento imprime nem ver alerta por deixá-los em branco.

**Why P1**: Os cinco campos não vão a nenhum documento; mantê-los na tela e no alerta confunde.

**Acceptance Criteria** (IDs `ENX-01` a `ENX-07`):

1. The system SHALL mostrar na Etapa 1 só os campos do docente, da unidade, da modalidade, das classes, denominações e níveis e das datas, sem o grupo "Dados institucionais e observações" e sem os rótulos "Nome do responsável", "Cargo do responsável", "Portaria de designação do responsável", "Unidade administrativa responsável" e "Observações".  <!-- ubiquitous -->
2. WHEN a pessoa cria ou altera um processo sem os cinco campos THEN the system SHALL salvar o processo e devolver `alerts` sem o código `DADOS_INCOMPLETOS`, qualquer que seja o conteúdo antigo das cinco colunas.  <!-- event-driven -->
3. The system SHALL devolver os processos de `POST`, `GET` e `PUT /api/processes` sem as chaves `notes`, `resp_name`, `resp_position`, `resp_appointment` e `resp_admin_unit`.  <!-- ubiquitous -->
4. IF o corpo de `POST /api/processes` ou de `PUT /api/processes/{id}` traz alguma das cinco chaves THEN the system SHALL salvar o processo sem elas, sem gravar o valor enviado e sem responder erro.  <!-- unwanted-behavior -->
5. The system SHALL manter as cinco colunas de `functional_processes` e os valores já gravados, sem lê-los, mostrá-los nem alterá-los quando a pessoa salva o processo, e SHALL NOT criar migração.  <!-- ubiquitous -->
6. The system SHALL NOT emitir o código `DADOS_INCOMPLETOS` em nenhuma verificação de processo, e a lista de códigos de alerta SHALL NOT conter `DADOS_INCOMPLETOS`.  <!-- ubiquitous -->
7. WHEN a pessoa altera um processo THEN the system SHALL gravar na auditoria a visão do processo sem os cinco campos, e SHALL manter intactos os eventos de auditoria anteriores.  <!-- event-driven -->

**Independent Test**: Abrir a Etapa 1 de um processo sintético e ver que os cinco campos não existem; salvar e ver na resposta da API, em `alerts`, nenhum `DADOS_INCOMPLETOS` e nenhuma das cinco chaves; num processo com `resp_name` gravado antes, salvar de novo e ver, no banco, o mesmo texto em `resp_name`.

---

## Edge Cases

- WHEN um cliente antigo envia as cinco chaves no corpo THEN the system SHALL ignorá-las e responder como se não tivessem sido enviadas.
- WHEN um processo criado antes da feature tem valores nas cinco colunas THEN the system SHALL abri-lo na Etapa 1 sem mostrá-los e salvá-lo sem alterá-los no banco.
- WHEN um processo tem todos os outros dados corretos THEN the system SHALL devolver `alerts` vazio, sem o antigo aviso de campos não preenchidos.

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | ENX-04: as cinco chaves enviadas são ignoradas; os demais campos mantêm a validação de antes |
| Failure / partial-failure states | N/A because a retirada não cria caminho de falha novo; a recusa de campos desconhecidos não é usada (ENX-04) |
| Idempotency / retry / duplicate handling | N/A because salvar o processo continua idempotente por versão (PROC-12 original) |
| Auth boundaries & rate limits | N/A because nenhuma rota nova; as rotas de processo mantêm o acesso e o 409 somente leitura |
| Concurrency / ordering | N/A because o controle de versão da linha não muda |
| Data lifecycle / expiry | ENX-05: as cinco colunas e seus valores ficam sem uso; nenhuma migração; ENX-07: auditoria antiga imutável |
| Observability | ENX-07: a auditoria da edição deixa de listar os cinco campos |
| External-dependency failure | N/A because nenhuma dependência externa |
| State-transition integrity | N/A because os estados do processo não mudam; o alerta retirado nunca bloqueou nada (AD-002) |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ENX-01 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-02 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-03 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-04 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-05 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-06 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |
| ENX-07 | P1: Etapa 1 sem campos que nenhum documento usa | Implemented | Implementing |

## Success Criteria

- [ ] Nenhuma tela, resposta de API ou verificação de processo menciona os cinco campos nem `DADOS_INCOMPLETOS`.
- [ ] Um processo com valores antigos nas cinco colunas mantém, no banco, os mesmos valores depois de salvo de novo.
- [ ] Os documentos gerados antes e depois são iguais no conteúdo (os campos nunca foram usados).
- [ ] Gate completo do backend e do frontend limpo no fim; nenhuma migração nova.

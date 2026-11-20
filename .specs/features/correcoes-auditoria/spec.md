# Correções da auditoria de requisitos Specification

**Escopo:** Large (corrige o fluxo de status do processo, uma regra do Grupo I, textos e um risco de edição; reescreve documentação; sem domínio novo nem migração).
**Status:** Draft, aguardando aprovação do usuário.
**Fonte:** `.specs/audits/2026-11-19-auditoria-requisitos.md` (R1, C3, C4, C6 a C11), `CLAUDE.md` (regras 1 a 11), `.specs/STATE.md`. Decisões do usuário em 2026-11-19: (a) corrigir agora o que afeta o uso real; (b) administração de usuários e unidades, troca de senha e backup ficam para a feature `implantacao`; (c) o VI.14 a 3 pontos entra pela versão nova da tabela da feature `grupo-i-no-total`; (d) remover toda referência ao item de valor informado de tabelas antigas, inexistente na tabela oficial, que a auditoria tratou como item do Grupo I.
**IDs:** prefixo `CA` da feature seguido da categoria (`CAINI` iniciar processo, `CAREF` remoção da referência, `CATXT` textos, `CAEDI` edição de atividade, `CADOC` documentação), porque `DOC-xx` já existe em `inteligencia-documental`.

## Problem Statement

O docente não consegue concluir um processo real: nenhuma tela leva o processo de `RASCUNHO` a `EM_ANDAMENTO`, e a conclusão (regra 8) só aparece em `EM_ANDAMENTO`. O código, os testes e a documentação ainda tratam como item do Grupo I um item de valor informado que só existia em tabelas antigas, há textos na tela e nas mensagens que prometem o que o sistema não faz, e uma atividade com pontuação manual gravada recebe 422 em qualquer edição. A documentação de estado (Handoff, decisões, rastreabilidade) está atrasada em relação ao código e à VM.

## Goals

- [ ] O docente inicia o processo na Etapa 1 (e no Painel) sem justificativa, e a Etapa 5 explica o que fazer enquanto ele está em rascunho.
- [ ] `grep -rnE "\bI\.3\b"` fora das pastas proibidas, de `node_modules` e de `.venv` não encontra nada, e o Grupo I sempre exige período letivo, nível e horas.
- [ ] Nenhum texto da tela ou mensagem do servidor promete leitura do documento ou um caminho impossível com a tabela oficial.
- [ ] Editar qualquer campo de uma atividade com pontuação manual gravada que o item não aceita responde 200.
- [ ] `STATE.md`, as specs e os nomes de testes dizem o que o código e a VM fazem, cada correção citando a evidência.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Administração de usuários, unidades e docentes pela tela (R2) | Decisão do usuário em 2026-11-19: feature futura `implantacao` |
| Troca e redefinição de senha (R3) | Decisão do usuário em 2026-11-19: feature futura `implantacao` |
| Backup automático do banco e de `storage/` (R4) | Decisão do usuário em 2026-11-19: feature futura `implantacao` |
| VI.14 a 3 pontos e texto do item (C1) | Decisão do usuário em 2026-11-19: entra pela versão nova da tabela na feature `grupo-i-no-total` |
| Grupo I no total e recusa de pontos digitados no Grupo I em qualquer tabela (GI-05) | Feature `grupo-i-no-total` |
| Mínimo de pontos da estrutura nova (R5), parecer da banca e Etapas 6 a 9 (R6) | Features `normativo` e `banca-parecer` |
| Tela de histórico, LGPD, segurança de borda, 503 com banco fora, métricas (R7 a R10) | Não afetam o uso real agora; seguem como dívida ou nas features futuras |
| Verifier independente de QUA-01..06 e CER-01..05 (R11) | A rastreabilidade só muda onde já há validação registrada (CADOC-07) |
| Remover o modo `VALOR_INFORMADO` do motor | O modo continua para tabelas importadas; só sai a exceção do Grupo I |
| Restringir quem pode iniciar o processo | O backend já decide pela leitura do processo; mudar exige decisão do usuário (Assumptions) |
| Push, deploy, acesso à VM | Só com autorização explícita do usuário |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| O backend já aceita `RASCUNHO` → `EM_ANDAMENTO` | Sim: `_FORWARD` em `backend/app/domain/entities/process.py:23-26` contém o par, `ChangeProcessStatus` (`backend/app/application/use_cases/processes.py:213-243`) grava o evento `STATUS` com justificativa opcional e `POST /api/processes/{id}/status` (`backend/app/presentation/api/processes.py:66-78`) o expõe. O trabalho de iniciar é de frontend, com teste de API de caracterização | Conferido no código em 2026-11-19; `test_process_updates_api.py:131-147` já cobre a transição pela SECRETARIA | y |
| Quem pode iniciar | Qualquer usuário que lê o processo: ADMIN, SECRETARIA da unidade e DOCENTE vinculado (`can_transition` aceita o par sem olhar papel; `can_read_process` em `access_policy.py:23-26` decide o 404). A tela mostra o botão a todos que veem a Etapa 1 | Comportamento atual do servidor; restringir ao dono ou ADMIN (como arquivar, regra 9) exigiria mudar o domínio. **Decisão do usuário** | n |
| Justificativa ao iniciar | Nenhuma: iniciar não é alteração de processo em andamento (PROC-13 vale para o processo já `EM_ANDAMENTO`) nem está nas Etapas 2 a 4 (regra 5) | `fundacao` PROC-13; o processo em `RASCUNHO` aceita alteração sem justificativa | y |
| Confirmação antes de iniciar | Modal "Iniciar processo" com o aviso de que não há volta a rascunho e que cada alteração na Etapa 1 passa a pedir justificativa; botões "Iniciar" e "Cancelar"; sem campo de justificativa | A transição não tem volta (`_FORWARD`); a regra 5 trata das Etapas 2 a 4 | n |
| Botão no Painel | Sim, como P2: botão "Iniciar" na linha do processo em `RASCUNHO`, com o mesmo modal | O Painel já tem Arquivar e Excluir por linha (regra 9); a Etapa 1 basta para o MVP | n |
| Comportamento correto de C11 | O servidor, ao editar, limpa a pontuação manual (`points_override`) que o corpo reenvia igual à gravada quando o item não a aceita, e grava o resto; valor novo não aceito continua 422. O frontend continua reenviando o corpo inteiro (`activityBody`) | Não reenviar o campo (opção do frontend) apagaria em silêncio a pontuação manual válida de tabelas que a aceitam e o `informed_points` de itens de valor informado; limpar só o que o item recusa mantém o que vale e deixa a auditoria com o valor anterior | n |
| C11 se confirma | Sim, pelo código: `frontend/src/activityBody.ts:4` reenvia `informed_points` e `points_override` em todo PUT; `UpdateActivity` (`scoring.py:515-547`) chama `normalize_activity`, que recusa `points_override` em item PIT (`scoring.py:304-314`) e em item que não é de carga semanal ou sem item (`scoring.py:323-329`). Com a tabela oficial, qualquer `points_override` gravado dá 422 em qualquer edição, pela Etapa 3 (`ActivityForm`, `ActivityRow`) ou pela Etapa 4 (`ScoreEditor`, `ProcessScoring`). `informed_points` não tem recusa e não causa 422 | Conferido no código em 2026-11-19; o valor gravado vem de tabela trocada depois (processo criado com outra versão) ou da API | y |
| Grupo I depois da remoção | O Grupo I sempre exige período letivo `AAAA.N`, nível e horas e o item segue o nível (I.1 graduação, I.2 pós-graduação), também quando o corpo traz outro item ou a tabela tem um critério de valor informado no grupo 1 | Regra 11 do `CLAUDE.md`: o Grupo I tem só os itens I.1 e I.2 | y |
| Cobertura do modo `VALOR_INFORMADO` | Os testes que usavam o item de valor informado no grupo 1 passam a usar um critério sintético no grupo 8, "Item de valor informado (sintético)", numerado depois do último item do grupo, com limite de 10 pontos, na tabela sintética de teste | Mantém os testes de pontos informados, limite por atividade e recusa de valor unitário manual sem inventar item do Grupo I | y |
| Nomes das tabelas sintéticas de teste | "Tabela Sintética Alternativa de Teste" e "Tabela Sintética com Grupo I em Pontos" (hoje "Tabela Alternativa de Teste" e "Tabela de Teste com Grupo I em Pontos") | Regra 11: teste com outra tabela declara no nome que ela é sintética | y |
| Alcance da remoção da sigla | Todo arquivo versionado ou não, fora de `Documentos/`, `Modelos/`, `test/`, `corpus-reports/`, `requeriment.txt`, `node_modules`, `.venv`, `dist` e `.git`, inclusive registros históricos (`tasks.md`, `validation.md`), o relatório de auditoria, `STATE.md` e `CLAUDE.md` | Decisão (d) do usuário em 2026-11-19 | y |
| Citações de 211 e 303 | "Cenário derivado" é escrito na mesma frase em toda citação de 211 ou 303 pontos em `spec.md` e `design.md` das features, `STATE.md`, `docs/` e docstrings ou nomes de teste; `tasks.md`, `validation.md` e `verification*.md` de features fechadas são registro histórico e não mudam por isso | C10 da auditoria; reescrever o histórico por um rótulo não muda nenhuma decisão | n |
| Itens B1, C5, M7 e "status desatualizados" do pedido | B1 e C5 já resolvidos (C5 pela AD-023). M7 e "status desatualizados" foram lidos como a rastreabilidade desatualizada (CADOC-07, CADOC-08) e a GP-DEL-07 (CADOC-09); o relatório de auditoria não tem item M7 | O relatório não define M7; se M7 for outro achado, o usuário diz qual | n |
| Ordem em relação a `grupo-i-no-total` | Esta feature é executada antes; o design aprovado de `grupo-i-no-total` só tem a sigla reescrita (CAREF-05), sem mudar decisão | `grupo-i-no-total` tem Design aprovado e não tem tarefas; se for implementada antes, T8 e T11 conciliam com GI-05 | n |
| C12 e C13 | Nada a fazer: a regra 6 já diz "a partir de 70% (0,70)" e a C13 foi descartada pela própria auditoria | `CLAUDE.md` atual | y |

**Open questions:** none - all resolved or logged above (as linhas com `n` pedem confirmação do usuário na aprovação da spec).

---

## User Stories

### P1: Iniciar o processo na Etapa 1 ⭐ MVP

**User Story**: Como docente (ou secretaria da unidade), quero iniciar o processo na Etapa 1 para que ele saia de rascunho e eu possa concluí-lo depois de gerar os documentos.

**Why P1**: Sem isso nenhum processo chega à conclusão (regra 8) nem libera espaço no servidor.

**Acceptance Criteria**:

1. WHILE o processo aberto na Etapa 1 está em `RASCUNHO` the frontend SHALL mostrar o botão "Iniciar processo" fora do formulário de dados, ao lado da etiqueta de status. <!-- CAINI-01 -->
2. WHILE o processo aberto na Etapa 1 está em `EM_ANDAMENTO`, `CONCLUIDO` ou `ARQUIVADO`, ou a Etapa 1 cria um processo novo, the frontend SHALL não mostrar o botão "Iniciar processo". <!-- CAINI-02 -->
3. WHEN o usuário clica em "Iniciar processo" THEN the frontend SHALL abrir o modal "Iniciar processo" com o texto "Depois de iniciado, o processo não volta a rascunho e cada alteração na Etapa 1 passa a pedir justificativa.", os botões "Iniciar" e "Cancelar" e nenhum campo de justificativa. <!-- CAINI-03 -->
4. WHEN o usuário confirma em "Iniciar" THEN the frontend SHALL enviar `POST /api/processes/{id}/status` com `{"status": "EM_ANDAMENTO", "expected_version": <versão do processo exibido>}` e sem `justificativa`. <!-- CAINI-04 -->
5. WHEN o servidor responde 200 ao iniciar THEN the frontend SHALL fechar o modal, mostrar a etiqueta "Em andamento", esconder o botão e usar a versão devolvida no próximo "Salvar" da Etapa 1. <!-- CAINI-05 -->
6. IF o servidor responde 409 ao iniciar (versão desatualizada ou processo que já saiu de rascunho) THEN the frontend SHALL mostrar a mensagem do servidor em `role="alert"` no modal e recarregar o processo com `GET /api/processes/{id}`, de modo que a etiqueta mostre o status atual. <!-- CAINI-06 -->
7. IF o servidor responde 404, 422 ou outro erro ao iniciar THEN the frontend SHALL mostrar a mensagem do servidor (`errorMessage`) em `role="alert"` no modal, manter o botão "Iniciar" habilitado e não mudar a etiqueta. <!-- CAINI-07 -->
8. WHEN ADMIN, SECRETARIA da unidade ou DOCENTE vinculado envia `RASCUNHO` → `EM_ANDAMENTO` sem `justificativa` THEN the system SHALL responder 200 com `status` `EM_ANDAMENTO` e `version` acrescida de 1, e gravar um evento de auditoria `STATUS` com `{"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}` e justificativa vazia. <!-- CAINI-08 -->
9. IF o usuário não lê o processo (SECRETARIA de outra unidade ou DOCENTE de outro docente) THEN the system SHALL responder 404 à mudança de status e não alterar o processo. <!-- CAINI-09 -->

**Independent Test**: Abrir a Etapa 1 de um processo em rascunho, clicar em "Iniciar processo", confirmar e ver a etiqueta "Em andamento"; salvar uma alteração sem justificativa e ver o 422 no campo `justificativa`.

---

### P1: Etapa 5 explica a conclusão de um processo em rascunho ⭐ MVP

**User Story**: Como docente, quero saber na Etapa 5 por que não vejo o botão de concluir, para não procurar em vão.

**Why P1**: Hoje a seção some sem explicação em `RASCUNHO` (`ProcessGenerated.tsx:120`).

**Acceptance Criteria**:

1. WHILE o processo está em `RASCUNHO` the frontend SHALL mostrar na Etapa 5 a seção "Concluir o processo" com o texto "Inicie o processo na Etapa 1 para poder concluir.", um link "Ir para a Etapa 1" para `/processos/{id}` e nenhum botão "Concluir e excluir documentos de entrada". <!-- CAINI-10 -->
2. WHILE o processo está em `EM_ANDAMENTO` the frontend SHALL mostrar a seção "Concluir o processo" com o botão "Concluir e excluir documentos de entrada", como hoje, sem o texto de rascunho. <!-- CAINI-11 -->

**Independent Test**: Abrir a Etapa 5 de um processo em rascunho e ver o texto e o link; iniciar o processo e ver o botão de concluir.

---

### P2: Iniciar o processo pelo Painel

**User Story**: Como docente, quero iniciar o processo direto da lista do Painel.

**Why P2**: A Etapa 1 já resolve; o Painel economiza um clique e segue o padrão de Arquivar e Excluir.

**Acceptance Criteria**:

1. WHILE uma linha do Painel mostra um processo em `RASCUNHO` the frontend SHALL mostrar nela o botão "Iniciar" com `aria-label` "Iniciar processo de {nome do docente}"; linhas em outro status SHALL não o mostrar. <!-- CAINI-12 -->
2. WHEN o usuário clica em "Iniciar" no Painel e confirma THEN the frontend SHALL usar o mesmo modal de CAINI-03 e a mesma chamada de CAINI-04 e, com 200, mostrar a etiqueta "Em andamento" na linha e atualizar a contagem por status sem recarregar a página. <!-- CAINI-13 -->
3. IF o servidor responde 409 ao iniciar pelo Painel THEN the frontend SHALL mostrar a mensagem do servidor no modal e recarregar a lista de processos. <!-- CAINI-14 -->

**Independent Test**: No Painel, iniciar um processo em rascunho e ver a etiqueta e a contagem mudarem.

---

### P1: O Grupo I tem só I.1 e I.2 ⭐ MVP

**User Story**: Como mantenedor, quero que o código, os testes e os documentos não tratem como item do Grupo I o item de valor informado de tabelas antigas, inexistente na tabela oficial, para que ninguém volte a pontuar por ele.

**Why P1**: Decisão (d) do usuário; a exceção em `_apply_group1` (`scoring.py:271-283`) deixa o Grupo I sem período letivo, nível nem horas quando o critério é de valor informado.

**Acceptance Criteria**:

1. WHEN uma atividade do grupo 1 é criada ou editada, com qualquer `item_number` e em qualquer versão de tabela (inclusive uma com critério de valor informado no grupo 1) THEN the system SHALL exigir período letivo no formato `AAAA.N` (422 em `academic_period`), nível (422 em `level`) e horas (422 em `horas`) e gravar o item conforme o nível (1 para graduação, 2 para pós-graduação). <!-- CAREF-01 -->
2. WHERE a versão de tabela tem um critério `VALOR_INFORMADO` fora do grupo 1 the system SHALL gravar o `informed_points` da atividade nesse critério e o motor SHALL pontuá-lo com o valor informado limitado a `max_points`, com o ajuste de limite `ATIVIDADE` (antes e depois) no resultado. <!-- CAREF-02 -->
3. IF o corpo traz `unit_points_override` numa atividade de critério `VALOR_INFORMADO` THEN the system SHALL responder 422 em `unit_points_override`. <!-- CAREF-03 -->
4. The system SHALL nomear as tabelas de teste derivadas da oficial como "Tabela Sintética Alternativa de Teste" e "Tabela Sintética com Grupo I em Pontos", e o critério de valor informado delas como "Item de valor informado (sintético)", no grupo 8. <!-- CAREF-04 -->
5. The system SHALL não ter nenhuma linha que case com `grep -rnE "\bI\.3\b"`, com `grep -rniE "avalia[cç][aã]o (pelo corpo )?discente"` nem com `grep -rniE "student.?evaluation"`, executados na raiz excluindo `Documentos/`, `Modelos/`, `test/`, `corpus-reports/`, `requeriment.txt`, `node_modules`, `.venv`, `dist` e `.git`. <!-- CAREF-05 -->
6. The system SHALL ter na regra 11 do `CLAUDE.md` a frase "O Grupo I tem só os itens I.1 e I.2, em horas de PIT." no lugar da frase atual sobre o Grupo I. <!-- CAREF-06 -->

**Independent Test**: Criar pela API uma atividade do grupo 1 com o item 3 numa tabela sintética que tem critério de valor informado no grupo 1 e receber 422 em `academic_period`; rodar os três `grep` e ver saída vazia.

---

### P1: Textos que dizem o que o sistema faz ⭐ MVP

**User Story**: Como docente, quero que a tela e as mensagens descrevam o que o sistema realmente faz, para não esperar valor lido do documento nem tentar um caminho que a tabela oficial não tem.

**Why P1**: Regra 1 (a IA não pontua) e C6 da auditoria; a mensagem atual de `points_override` (`scoring.py:328`) indica um caminho impossível com a tabela oficial.

**Acceptance Criteria**:

1. WHILE o item da atividade aberta no editor de pontuação da Etapa 4 é `VALOR_INFORMADO` the frontend SHALL mostrar a nota "Neste item a pontuação é um valor informado na atividade, não calculado pela tabela: esta tela não o altera." e nenhum texto com "lidos do documento". <!-- CATXT-01 -->
2. IF o corpo traz `points_override` numa atividade sem item ou cujo critério não é `CARGA_SEMANAL` THEN the system SHALL responder 422 em `points_override` com a mensagem "Esta tabela não aceita pontuação manual neste item; nos itens por unidade ou por bloco de horas, informe o valor unitário". <!-- CATXT-02 -->
3. IF `points_override` está fora de 0 a 10000 THEN the system SHALL responder 422 em `points_override` com a mensagem "Pontuação manual deve estar entre 0 e 10000". <!-- CATXT-03 -->
4. IF `informed_points` está fora de 0 a 10000 THEN the system SHALL responder 422 em `informed_points` com a mensagem "Pontos informados deve estar entre 0 e 10000", sem mudança em relação a hoje. <!-- CATXT-04 -->

**Independent Test**: Abrir o editor de um item de valor informado (tabela sintética) e ler a nota; enviar `points_override` num item por unidade e ler a mensagem nova.

---

### P1: Editar atividade com pontuação manual gravada ⭐ MVP

**User Story**: Como docente, quero editar qualquer campo de uma atividade que ficou com pontuação manual gravada de uma tabela anterior, sem receber erro por um campo que não vejo.

**Why P1**: C11 da auditoria, confirmado no código: hoje a edição dá 422 e não há campo para limpar.

**Acceptance Criteria**:

1. WHEN um PUT de atividade traz `points_override` igual ao gravado e o critério da atividade não aceita pontuação manual (item PIT, critério que não é `CARGA_SEMANAL` ou atividade sem item) THEN the system SHALL responder 200, gravar a atividade com `points_override` vazio e os demais campos do corpo, e registrar no evento `UPDATE` da auditoria o valor anterior de `points_override`. <!-- CAEDI-01 -->
2. IF um PUT de atividade traz `points_override` diferente do gravado e o critério não aceita pontuação manual THEN the system SHALL responder 422 em `points_override` (mensagem de CATXT-02, ou a de horas de PIT no item PIT) e não gravar nada. <!-- CAEDI-02 -->
3. WHERE o critério aceita pontuação manual (`CARGA_SEMANAL` que não é PIT, em tabela sintética) the system SHALL manter o `points_override` reenviado igual ao gravado. <!-- CAEDI-03 -->
4. WHEN o título de uma atividade da tabela oficial com `points_override` gravado é editado com o corpo montado como `activityBody` (todos os campos reenviados) THEN the system SHALL responder 200 com o título novo e `points_override` nulo. <!-- CAEDI-04 -->

**Independent Test**: Gravar `points_override` numa atividade pelo repositório, editar o título pela API com o corpo inteiro e receber 200.

---

### P2: Documentação de estado alinhada ao código e à VM

**User Story**: Como líder do projeto, quero que `STATE.md`, as specs e os nomes de testes digam o que o código e a VM fazem, para retomar o trabalho sem decidir por informação velha.

**Why P2**: Não muda o uso real, mas a auditoria mostrou decisões e status atrasados (C4, C7 a C10) que já levaram a afirmações falsas.

**Acceptance Criteria**:

1. WHEN a feature termina THEN the system SHALL ter a seção Handoff de `.specs/STATE.md` reescrita com: HEAD e branch conferidos no git; a VM em `a136faf` (migração `0008`); a lista dos commits locais não enviados ao `origin` (`git log origin/feat/inteligencia-documental..HEAD`); a feature corrente e a seguinte (`grupo-i-no-total`); o gate atual (contagens do backend e do frontend medidas no HEAD); sem a lista de arquivos "uncommitted" e sem o deploy de `documentos-gerados` como pendente. <!-- CADOC-01 -->
2. The system SHALL ter em AD-017 e AD-019 de `STATE.md` a nota de que a parte "linha de 0 ponto" (rejeitada ou fora do interstício nas Etapas 3 e 4) foi substituída pela AD-022, que leva essas atividades à seção de não válidas e as tira da Etapa 4. <!-- CADOC-02 -->
3. The system SHALL ter na coluna Quantidade da tabela de taxonomias de `.specs/features/inteligencia-documental/design.md`: IV.1 e IV.2 "1 por ação"; V.1, VI.10 e VI.12 "anos completos do período no interstício (`QUANTIDADE_ESTIMADA`)", conforme `_PER_YEAR` em `backend/app/domain/rules/quantity_rules.py:26-41`. <!-- CADOC-03 -->
4. The system SHALL não ter `real case`, `caso real` nem `real_case` em nomes, fixtures ou docstrings de `test_scoring_engine.py`, `test_scoring_golden.py`, `test_scoring_characterization.py` e `test_generated_table_acceptance.py`; os nomes novos usam `derived_case` ou "cenário derivado" e declaram a tabela sintética quando o teste usa uma. <!-- CADOC-04 -->
5. The system SHALL escrever "cenário derivado" na mesma frase de toda citação de 211 ou 303 pontos em `spec.md` e `design.md` das features, em `STATE.md`, em `docs/` e em docstrings de teste. <!-- CADOC-05 -->
6. The system SHALL ter, nas dívidas do `STATE.md`, no lugar de "Grupo I do caso real com 16 pontos sem explicação", a dívida "Grupo I: os 303 pontos de `grupo-i-no-total` vêm de 92 horas de PIT de um cenário derivado; os documentos reais somam 76 h (auditoria de 2026-11-19, C10); conferir no processo real depois do deploy da versão nova da tabela". <!-- CADOC-06 -->
7. WHEN um requisito de `inteligencia-documental/spec.md` tem status diferente de `Verified` e uma passagem do Verifier independente registrada (`validation.md` ou `verification-fora.md`) lhe dá PASS THEN the system SHALL mudar o status para `Verified` e citar a passagem e a seção na nota de cobertura; QUA-01..06 e CER-01..05 SHALL continuar `Implementing`. <!-- CADOC-07 -->
8. The system SHALL ter os 22 requisitos `Implemented` de `tabela-oficial/spec.md` com status `Verified`, citando `tabela-oficial/validation.md` (veredito PASS, linha por requisito), e ACE-02 SHALL continuar `Pending` com a nota PARTIAL da validação. <!-- CADOC-08 -->
9. The system SHALL ter em GP-DEL-07 de `gestao-processos/spec.md` "tarefa de leitura `PENDENTE` ou `PROCESSANDO`" no lugar de "tarefa `PROCESSING`", conforme `_ACTIVE_JOB` em `backend/app/infrastructure/database/repositories.py:1121`. <!-- CADOC-09 -->
10. The system SHALL ter em `tabela-oficial/spec.md` (PIT-01..03, TELA-01..02) e em `documentos-gerados/spec.md` (TAB-03, TAB-05) uma nota de substituição que aponta para `grupo-i-no-total` e AD-023, recíproca à nota que `grupo-i-no-total/spec.md` já tem. <!-- CADOC-10 -->
11. The system SHALL ter a pergunta aberta (1) da AD-022 reescrita sem a sigla: a tabela oficial não tem item de valor informado; o item de valor informado de tabelas antigas, inexistente na tabela oficial, só existia na tabela antiga do IFCH e no rascunho da FASI. <!-- CADOC-11 -->

**Independent Test**: Ler o Handoff e conferir HEAD, VM e commits locais com `git log`; rodar os `grep` de CADOC-04 e CAREF-05 e ver saída vazia.

---

## Edge Cases

- IF dois usuários iniciam o mesmo processo ao mesmo tempo THEN the system SHALL aceitar o primeiro e responder 409 ao segundo (versão desatualizada ou transição não permitida), e o frontend SHALL mostrar a mensagem e recarregar (CAINI-06).
- IF o usuário edita a Etapa 1 com dados não salvos e inicia o processo THEN the frontend SHALL manter os campos digitados no formulário e só trocar a etiqueta e a versão (o início não salva os dados).
- WHEN um processo `EM_ANDAMENTO` é salvo na Etapa 1 sem justificativa THEN the system SHALL responder 422 em `justificativa`, como já faz (PROC-13); o campo "Justificativa da alteração" já existe na tela.
- IF o PUT de atividade traz `points_override` nulo e há valor gravado THEN the system SHALL gravar nulo, como hoje.
- WHEN a atividade com `points_override` gravado e não aceito é editada só no valor unitário (`ScoreEditor`) THEN the system SHALL responder 200 e limpar o `points_override` (CAEDI-01).

---

## Implicit-requirement dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | CATXT-02, CATXT-03, CAREF-01, CAREF-03 |
| Failure / partial-failure states | CAINI-06, CAINI-07, CAEDI-02 (422 não grava nada) |
| Idempotency / retry / duplicate handling | CAINI-06 (segundo início responde 409); CAEDI-01 (reenvio igual não falha) |
| Auth boundaries & rate limits | CAINI-08, CAINI-09; limite de requisições N/A because a feature não cria rota |
| Concurrency / ordering | `expected_version` em CAINI-04 e edge case de início simultâneo |
| Data lifecycle / expiry | N/A because nada é apagado além do `points_override` não aceito, auditado em CAEDI-01 |
| Observability | CAINI-08 e CAEDI-01 (eventos de auditoria) |
| External-dependency failure | N/A because a feature não chama a MariTalk nem serviço externo |
| State-transition integrity | CAINI-01, CAINI-02, CAINI-08, CAINI-10, CAINI-11 |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CAINI-01 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-02 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-03 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-04 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-05 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-06 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-07 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-08 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-09 | P1: Iniciar o processo na Etapa 1 | Tasks | Pending |
| CAINI-10 | P1: Etapa 5 explica a conclusão | Tasks | Pending |
| CAINI-11 | P1: Etapa 5 explica a conclusão | Tasks | Pending |
| CAINI-12 | P2: Iniciar pelo Painel | Tasks | Pending |
| CAINI-13 | P2: Iniciar pelo Painel | Tasks | Pending |
| CAINI-14 | P2: Iniciar pelo Painel | Tasks | Pending |
| CAREF-01 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CAREF-02 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CAREF-03 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CAREF-04 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CAREF-05 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CAREF-06 | P1: O Grupo I tem só I.1 e I.2 | Tasks | Pending |
| CATXT-01 | P1: Textos que dizem o que o sistema faz | Tasks | Pending |
| CATXT-02 | P1: Textos que dizem o que o sistema faz | Tasks | Pending |
| CATXT-03 | P1: Textos que dizem o que o sistema faz | Tasks | Pending |
| CATXT-04 | P1: Textos que dizem o que o sistema faz | Tasks | Pending |
| CAEDI-01 | P1: Editar atividade com pontuação manual gravada | Tasks | Pending |
| CAEDI-02 | P1: Editar atividade com pontuação manual gravada | Tasks | Pending |
| CAEDI-03 | P1: Editar atividade com pontuação manual gravada | Tasks | Pending |
| CAEDI-04 | P1: Editar atividade com pontuação manual gravada | Tasks | Pending |
| CADOC-01 | P2: Documentação de estado | Tasks | Pending |
| CADOC-02 | P2: Documentação de estado | Tasks | Pending |
| CADOC-03 | P2: Documentação de estado | Tasks | Pending |
| CADOC-04 | P2: Documentação de estado | Tasks | Pending |
| CADOC-05 | P2: Documentação de estado | Tasks | Pending |
| CADOC-06 | P2: Documentação de estado | Tasks | Pending |
| CADOC-07 | P2: Documentação de estado | Tasks | Pending |
| CADOC-08 | P2: Documentação de estado | Tasks | Pending |
| CADOC-09 | P2: Documentação de estado | Tasks | Pending |
| CADOC-10 | P2: Documentação de estado | Tasks | Pending |
| CADOC-11 | P2: Documentação de estado | Tasks | Pending |

**ID format:** `[CATEGORY]-[NUMBER]`, com a categoria prefixada por `CA` (esta feature).

**Status values:** Pending → In Design → In Tasks → Implementing → Implemented → Verified

**Coverage:** 39 total, 39 mapped to tasks (ver `tasks.md`), 0 unmapped.

---

## Success Criteria

- [ ] Um processo criado na Etapa 1 é iniciado, tem os três documentos gerados e é concluído pela Etapa 5, sem chamada manual à API (teste de componente e teste de API).
- [ ] Os `grep` de CAREF-05 e CADOC-04 devolvem saída vazia.
- [ ] Editar o título de uma atividade com `points_override` gravado na tabela oficial responde 200 (teste de integração).
- [ ] O gate do backend (`ruff` e `pytest`) e o do frontend (`lint`, `build`, testes) passam no HEAD, sem teste apagado sem substituto.

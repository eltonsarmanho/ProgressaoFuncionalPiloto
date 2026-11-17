# Pontuação — Specification

**Escopo:** Complex (regras normativas, cálculo, estado, persistência e auditoria).
**Fontes:** `docs/referencias/normas/FONTES.md` (itens 8 e 9), tabela do IFCH, tabela preenchida da FASI 2022–2024, Res. 4.644/2015 e Res. 4.074/2010.

## Problem Statement

O docente soma à mão, em PDF, as pontuações de dezenas de atividades de um interstício, conferindo a tabela da unidade, as notas de dupla pontuação e os limites. O resultado do caso real tem erro de soma (96 no lugar de 92 no Grupo I) e a tabela da FASI tem pontos diferentes dos da IFCH sem norma que as sustente. A feature entrega o cálculo determinístico e rastreável da pontuação de um processo, com tabelas versionadas por unidade, atividades cadastradas e validadas por pessoas, e verificações que apontam inconsistências sem corrigi-las.

## Goals

- [ ] Reproduzir exatamente o caso real FASI 2022–2024: subtotais 92, 120, 15, 95, 0, 30, 6, 56 e total 414.
- [ ] Calcular qualquer pontuação em código determinístico, com a fórmula aplicada e o critério visíveis em cada linha.
- [ ] Impedir a contagem em dobro e a contagem de atividade fora do interstício, mostrando a razão a cada caso.
- [ ] Manter as tabelas versionadas, com vigência e norma, sem que uma versão usada por processo mude.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature     | Reason         |
| ----------- | -------------- |
| Upload, OCR, extração e classificação por IA das atividades | Feature `inteligencia-documental`; aqui só o cadastro manual e o status de revisão |
| Ligar atividade a documento e página de origem | Depende do upload; aqui só a nota de comprovante |
| Gerar a Tabela de Pontuação em DOCX/PDF | Feature `documentos-gerados` |
| Carga horária mínima de ensino (Res. 4.644, art. 13, I) | O sistema não conhece a carga horária alocada do docente |
| Decidir aprovação ou reprovação | Decisão humana da banca; o sistema só compara com o mínimo de referência |
| Reenquadramento dos mínimos nas classes novas | Sem norma; feature `normativo` e decisão humana |
| Ler tabela de pontuação a partir de PDF | Importação por CSV; extração por IA de tabelas ficaria sem validação |
| Dispensa por cargo de direção, aceleração, tutoria de Titular e carreira EBTT | Sem caso real; tratado por análise humana |
| Explicar a divergência 118,35 × 92 do Grupo I | Falta regra; depende de esclarecimento do usuário |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default  | Rationale | Confirmed? |
| --------------------- | --------------- | --------- | ---------- |
| Fórmula do Grupo I (FASI) | CARGA_SEMANAL: horas docente ÷ 17 semanas × (1 + preparação); preparação 1 na graduação e 2 na pós-graduação (Res. 4.074/2010, art. 10, I) | Informada pelo usuário em 2026-11-17; o art. 10, I foi conferido no texto oficial; as 17 semanas não constam da resolução | y |
| Caso real e Grupo I | Os testes de aceitação usam os pontos declarados na tabela preenchida (24, 24, 24 e 20 = 92) como pontos informados, com datas dentro do interstício. O usuário confirma que 92 é o valor correto | Decisão do usuário em 2026-11-17. Com a CH docente da declaração, as ofertas listadas no Relatório de Atividades dentro do interstício somam 76; os 16 pontos restantes não são explicados pelos documentos fornecidos | y |
| CH docente do Cálculo Computacional II (2023.1) | 68 h, como na declaração; a CH docente de 20 h do Relatório de Atividades está errada. Em geral o sistema usa a CH docente informada pelo usuário e não escolhe entre fontes | Decisão do usuário em 2026-11-17 | y |
| Grupo I e o início do interstício | O Grupo I segue a mesma verificação de datas das demais atividades: oferta fora do interstício não pontua, com razão `FORA_DO_INTERSTICIO` | Decisão do usuário em 2026-11-17 | y |
| Entrada do Grupo I | A atividade do Grupo I chega por componente curricular e período letivo, com CH disciplina, CH docente, nível e datas com mês e ano, como na declaração da unidade | Estrutura mostrada pelo usuário em 2026-11-17; o item I.1 (graduação) usa HORAS como unidade | y |
| Item I.3 (avaliação pelo corpo discente) | Fica fora da exigência de período letivo, nível e horas do Grupo I (ATV-02): é `VALOR_INFORMADO`, com limite de 10 pontos, e guarda só os pontos informados | A spec exigia os três campos para todo o Grupo I, mas esse item não tem horas nem componente curricular. Lacuna achada na execução (T17) | n |
| Desempate da sugestão de tabela (SEL-02) | Entre as versões das tabelas da unidade válidas na data final do interstício, vale a de início de vigência mais recente | A spec não dizia; escolher a norma mais nova é a leitura natural. Lacuna achada pelo Verificador (iteração 1) | n |
| Tabela duplicada sem unidades (SEL-01 × ADM-02) | Nasce sem unidades e só passa a ser sugerida depois de associada; SEL-01 vale para tabelas em uso | Evita duas tabelas sugeridas para a mesma unidade; lacuna achada pelo Verificador | n |
| Verificação de 360 px (TELA-08) | Teste estático de CSS; a ausência de rolagem horizontal real fica para teste em navegador, na implantação | jsdom não calcula layout | n |
| Datas só com mês e ano | Valem como o mês inteiro (primeiro ao último dia); mês que atravessa o limite do interstício gera `INTERSTICIO_PARCIAL` | As declarações trazem "Mai/22 a Mai/22"; sem dia não há como ser mais preciso | n |
| Quem entra no total | Atividade manual entra como `VALIDADA`; atividade de origem diferente de `MANUAL` entra como `AGUARDANDO_REVISAO` e fica fora do total (pontuação potencial à parte) | Decisão do usuário em 2026-11-17 | y |
| Justificativa em alterações | Obrigatória sempre que quantidade, horas, classificação, pontos informados ou status de uma atividade mudam | Prompt: edição manual mediante registro da justificativa | y |
| Arredondamento | Meio para cima, 2 casas decimais, só no modo `CARGA_SEMANAL`; as demais contas são exatas | Os exemplos reais são inteiros; regra simples e determinística | n |
| Blocos de horas | Parte inteira de horas ÷ bloco; resto desprezado | "A cada N horas" nas tabelas; 21 h / 3 = 7 no caso real | n |
| Tabela da FASI | Semeada da tabela preenchida de 2022–2024, situação `PENDENTE_VALIDACAO`, numeração do Anexo I da Res. 4.644; divergências do IFCH e anomalias da numeração marcadas para revisão | Não há norma FASI separada (usuário); a tabela preenchida contém erros aparentes de digitação (VIII.5, VIII.38, VIII.39) | n |
| Grupo I no total | IFCH: não conta (obs. c da tabela oficial). FASI: conta (a tabela preenchida soma 92 no total de 414). Configurado por versão | Os dois documentos fornecidos divergem; a escolha segue cada documento | n |
| 30% do Grupo I | Não aplicado como regra; o percentual é apenas exibido | O texto do Anexo I (obs. c, Res. 4.771/2016) é ambíguo e o caso aprovado tem 22,2%; decisão humana | n |
| Interstício das atividades | Evento com data: dentro, conta; fora, não conta. Período: sobreposição parcial conta com a quantidade informada e alerta; sem sobreposição, não conta; sem data, conta com alerta | Sem proporcionalizar para não inventar regra; o usuário informa a quantidade referente ao interstício | n |
| Duplicidade | Mesmo título normalizado e períodos que se sobrepõem; a atividade criada depois sai do total até ser rejeitada ou justificada como distinta | Prompt: impedir dupla pontuação; nota do Grupo VI e do Grupo IV | n |
| Comprovante | Esta feature guarda só uma nota de texto; falta de nota gera alerta e não tira pontos. Ligação a documentos entra em `inteligencia-documental` | Upload e extração ainda não existem | n |
| Mínimos de referência | 60/80/100/120 pela classe atual, só na estrutura da Res. 4.644; estrutura nova: `NAO_DEFINIDO` com alerta | Res. 4.644, art. 12; nenhuma norma encontrada reenquadra os mínimos nas classes novas | n |
| Exigência do art. 13, II | Alerta, nunca bloqueio, quando DE ou 40 h têm Grupos IV e V zerados | O artigo admite exceções legais que o sistema não conhece | n |
| Resultado calculado sob demanda | Sem gravar o resultado: ele é recalculado a cada consulta; o instantâneo para documentos entra em `documentos-gerados` | Cálculo determinístico e barato; evita resultado desatualizado | n |
| Permissões | ADMIN gerencia tabelas; todos os perfis autenticados leem; atividades seguem o acesso do processo | Mesma política da `fundacao` | n |
| Importação | CSV em UTF-8, tudo ou nada | Importação determinística; ler PDF de tabela fica fora | n |
| Limites do sistema | Quantidade e horas até 10000; título até 300 caracteres; nota de comprovante até 500 | Evita entradas absurdas; valores ajustáveis no Design | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Catálogo de tabelas de pontuação versionadas ⭐ MVP

**User Story**: Como sistema, preciso conhecer as tabelas de pontuação de cada unidade, com versões, vigência e norma, para calcular sem regras embutidas em código ou prompt.

**Why P1**: Sem tabela não há cálculo, e a tabela da FASI difere da do IFCH em 17 itens (Assunções).

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL representar uma tabela de pontuação como um nome com versões; cada versão tem início de vigência obrigatório, fim de vigência opcional, referência normativa obrigatória, situação (`OFICIAL`, `PENDENTE_VALIDACAO`) e os grupos I a VIII com seus critérios.
2. The system SHALL representar cada critério com grupo, número do item, descrição, unidade de contagem, modo de pontuação (`POR_UNIDADE`, `POR_BLOCO_DE_HORAS`, `CARGA_SEMANAL`, `VALOR_INFORMADO`), pontuação unitária, horas por bloco (modo `POR_BLOCO_DE_HORAS`), semanas por semestre e razão de preparação (modo `CARGA_SEMANAL`), limite máximo opcional, comprovantes aceitos e regras específicas em texto.
3. WHEN o sistema é inicializado pela primeira vez THEN the system SHALL semear a tabela "Tabela de Pontuação do IFCH", situação `OFICIAL`, com os critérios numerados como no Anexo I da Res. 4.644/2015 (Grupo I: 3; II: 16; III: 12; IV: 7; V: 6; VI: 14; VII: 11; VIII: 66) e as pontuações do PDF oficial, referência normativa "Tabela de Pontuação do IFCH em complementação ao Anexo I da Res. 4.644/2015-CONSEPE".
4. WHEN o sistema é inicializado pela primeira vez THEN the system SHALL semear a tabela "Tabela de Pontuação da FASI", situação `PENDENTE_VALIDACAO`, com a mesma numeração e as pontuações da tabela preenchida de 2022–2024, e referência normativa "Tabela preenchida FASI/Campus Cametá, interstício 2022–2024 (sem norma localizada)".
5. The system SHALL marcar, na tabela da FASI, os 17 critérios dos Grupos II a VII cuja pontuação difere da do IFCH (II.9, II.12, II.16, III.2, III.6, III.7, III.8, III.9, IV.2, IV.4, IV.5, IV.7, VI.10, VI.11, VI.12, VII.9, VII.10) e os critérios VIII.5, VIII.6, VIII.7, VIII.38 e VIII.39, com a anotação da diferença, para revisão humana.
6. The system SHALL configurar, por versão de tabela, se o Grupo I conta no total: não na tabela do IFCH (obs. c da tabela oficial) e sim na da FASI (a tabela preenchida soma o Grupo I no total de 414).
7. WHERE a tabela é a da FASI the system SHALL definir os critérios I.1 e I.2 em modo `CARGA_SEMANAL` com 17 semanas por semestre e razões de preparação 1 (graduação, I.1) e 2 (pós-graduação, I.2), e o critério I.3 (avaliação pelo corpo discente) em modo `VALOR_INFORMADO` com limite de 10 pontos.
8. WHEN um usuário autenticado consulta as tabelas THEN the system SHALL listar tabelas, versões (com vigência, situação e referência) e, para cada versão, os grupos e critérios em ordem de grupo e item.

**Independent Test**: Consultar a API e conferir as duas tabelas semeadas, o número de critérios por grupo e a lista das divergências da FASI.

---

### P1: Tabela aplicada ao processo ⭐ MVP

**User Story**: Como docente ou secretaria, quero que o processo use uma tabela de pontuação identificada e fixa, para que o cálculo não mude sem eu saber.

**Why P1**: Prompt: não presumir que uma unidade usa a tabela de outra.

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL associar cada tabela a uma ou mais unidades acadêmicas; na semente, a tabela do IFCH ao IFCH e a da FASI à FASI.
2. WHEN um usuário abre a pontuação de um processo sem tabela escolhida THEN the system SHALL sugerir a versão da tabela associada à unidade do docente e vigente na data final do interstício, e SHALL não aplicá-la antes da confirmação do usuário.
3. IF não existe versão associada à unidade do docente e vigente na data final do interstício THEN the system SHALL emitir alerta `REQUER_ANALISE_NORMATIVA` com código `TABELA_NAO_ENCONTRADA` e SHALL exigir escolha explícita do usuário.
4. WHEN o usuário escolhe a versão da tabela THEN the system SHALL gravá-la no processo e registrar evento de auditoria com usuário, versão anterior, nova versão e justificativa.
5. IF a tabela escolhida pertence a unidade diferente da do docente THEN the system SHALL exigir justificativa (422 no campo `justificativa`) e emitir alerta `ALERTA` com código `TABELA_DE_OUTRA_UNIDADE`.
6. IF a versão escolhida tem situação `PENDENTE_VALIDACAO` THEN the system SHALL emitir alerta `REQUER_ANALISE_NORMATIVA` com código `TABELA_PENDENTE_VALIDACAO` em todo resultado calculado com ela.
7. IF a versão escolhida não estava vigente na data final do interstício THEN the system SHALL emitir alerta `ALERTA` com código `TABELA_FORA_DE_VIGENCIA`.
8. WHILE um processo usa uma versão de tabela the system SHALL recusar com 409 qualquer alteração dos critérios dessa versão.
9. WHEN o usuário troca a tabela de um processo que já tem atividades THEN the system SHALL reavaliar cada atividade pelo grupo e item na nova versão e SHALL marcar `SEM_ENQUADRAMENTO` as que não existirem nela.

**Independent Test**: Abrir o processo FASI, ver a sugestão da tabela FASI, confirmar e ver o alerta de tabela pendente de validação.

---

### P1: Atividades do processo ⭐ MVP

**User Story**: Como docente ou secretaria, quero cadastrar, classificar e validar as atividades do interstício, para montar a tabela de pontuação mesmo sem IA.

**Why P1**: O sistema deve funcionar com cadastro manual quando a IA está indisponível; a feature de IA criará atividades pela mesma estrutura.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o usuário cria uma atividade manual THEN the system SHALL persistir processo, grupo e número do item (opcionais), título, descrição, data do evento ou período (início e fim), entradas do modo de pontuação, nota de comprovante e origem `MANUAL`, com status `VALIDADA`.
2. WHERE a atividade é do Grupo I the system SHALL exigir período letivo (formato `AAAA.N`), nível (`GRADUACAO` ou `POS_GRADUACAO`) e horas de CH docente, SHALL aceitar a CH da disciplina como informação opcional e SHALL derivar o item: I.1 para `GRADUACAO` e I.2 para `POS_GRADUACAO`.
3. WHEN uma atividade é criada com origem diferente de `MANUAL` THEN the system SHALL gravá-la com status `AGUARDANDO_REVISAO`.
4. The system SHALL restringir o status armazenado da atividade a `AGUARDANDO_REVISAO`, `VALIDADA` e `REJEITADA`.
5. IF a atividade é criada sem grupo e item, ou com um item inexistente na versão da tabela do processo THEN the system SHALL salvá-la como não pontuada com razão `SEM_ENQUADRAMENTO`.
6. IF a quantidade é negativa, maior que 10000, ou não inteira em critério `POR_UNIDADE` THEN the system SHALL responder 422 com erro no campo `quantidade`.
7. IF as horas são negativas ou maiores que 10000 em critério `POR_BLOCO_DE_HORAS` ou `CARGA_SEMANAL` THEN the system SHALL responder 422 com erro no campo `horas`.
8. WHEN o grupo, o item, a quantidade, as horas ou os pontos informados de uma atividade são alterados THEN the system SHALL exigir justificativa (422 no campo `justificativa`) e registrar evento de auditoria com os valores anterior e novo.
9. WHEN o usuário muda o status de uma atividade THEN the system SHALL exigir justificativa e registrar evento de auditoria; WHEN uma atividade `REJEITADA` volta a `AGUARDANDO_REVISAO` THEN the system SHALL tratá-la como nova revisão.
10. WHERE uma atividade pode se enquadrar em mais de um item the system SHALL permitir registrar itens candidatos com justificativa da escolha, e SHALL pontuar somente o item escolhido.
11. WHILE o processo está `CONCLUIDO` ou `ARQUIVADO` the system SHALL rejeitar criação, alteração e exclusão de atividades com 409.
12. IF um usuário DOCENTE solicita atividades de processo que não é seu, ou um usuário SECRETARIA solicita atividades de processo de unidade a que não pertence THEN the system SHALL responder 404.
13. IF duas gravações da mesma atividade usam a mesma versão THEN the system SHALL aceitar a primeira e responder 409 à segunda.
14. WHEN o usuário lista as atividades de um processo THEN the system SHALL retornar todas, com filtros por grupo e por status, em ordem de grupo, item e data.

**Independent Test**: Cadastrar à mão as atividades do caso real e vê-las listadas por grupo.

---

### P1: Cálculo determinístico da pontuação ⭐ MVP

**User Story**: Como banca, quero que a pontuação seja calculada por regras fixas e rastreáveis, para confiar no total.

**Why P1**: Prompt: a pontuação é calculada por código Python determinístico, nunca pelo LLM.

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL calcular a pontuação em código determinístico com aritmética decimal, sem uso de modelo de linguagem, e SHALL devolver o mesmo resultado para as mesmas atividades e a mesma versão de tabela.
2. WHERE o modo do critério é `POR_UNIDADE` the system SHALL calcular pontos = quantidade × pontuação unitária.
3. WHERE o modo do critério é `POR_BLOCO_DE_HORAS` the system SHALL calcular blocos = parte inteira de (horas ÷ horas por bloco) e pontos = blocos × pontuação unitária; 21 horas com bloco de 3 horas e 5 pontos dão 7 blocos e 35 pontos; 2 horas com bloco de 3 dão 0 pontos.
4. WHERE o modo do critério é `CARGA_SEMANAL` the system SHALL calcular pontos = horas ÷ semanas × (1 + razão de preparação), arredondados a 2 casas pelo critério meio para cima: 68 h na graduação dão 8,00; 34 h dão 4,00; 68 h na pós-graduação dão 12,00; 20 h na graduação dão 2,35.
5. WHERE o modo do critério é `VALOR_INFORMADO` the system SHALL usar os pontos informados limitados ao máximo do critério.
6. WHERE o critério é `CARGA_SEMANAL` the system SHALL permitir informar pontos que substituem o cálculo, exigindo justificativa, e SHALL marcar a atividade com o alerta `ALERTA` de código `PONTOS_AJUSTADOS_MANUALMENTE`.
7. WHERE um critério ou grupo tem limite máximo the system SHALL limitar a soma dos pontos ao limite e SHALL registrar o alerta `ALERTA` de código `LIMITE_APLICADO` com os pontos antes e depois.
8. The system SHALL contar no total apenas atividades com status `VALIDADA`, com critério existente na versão da tabela, não excluídas por interstício ou duplicidade e em grupo que conta no total.
9. WHERE o grupo da versão não conta no total the system SHALL tratar as atividades do grupo como não pontuadas, com razão `GRUPO_NAO_CONTA`, e subtotal 0.
10. The system SHALL calcular a pontuação potencial das atividades `AGUARDANDO_REVISAO` separadamente e SHALL não incluí-la no total geral.
11. The system SHALL retornar subtotal de cada grupo (I a VIII), total geral, pontuação potencial, quantidade de atividades, quantidade com comprovante, quantidade pendente (`AGUARDANDO_REVISAO`), quantidade não pontuada e quantidade com alertas.
12. The system SHALL retornar, para cada atividade, o critério (grupo e item), a pontuação unitária, a quantidade efetiva, a fórmula aplicada em texto, os pontos, a situação (`PONTUADA`, `POTENCIAL`, `NAO_PONTUADA`) e as razões e alertas.
13. The system SHALL retornar o percentual do Grupo I sobre o total geral, sem emitir alerta por esse percentual.
14. WHEN as atividades do caso real FASI 2022–2024 são cadastradas na tabela da FASI (Grupo I: 4 atividades com datas dentro do interstício e pontos informados 24, 24, 24 e 20; II.7 × 4; II.8 × 4; II.12 × 4; III.2 × 1; III.3 × 1; IV.1 × 4; IV.4 com 21 horas; VI.6 × 1; VII.10 × 2; VIII.11, VIII.12, VIII.13 e VIII.66 × 1) THEN the system SHALL retornar subtotais I a VIII de 92, 120, 15, 95, 0, 30, 6 e 56 e total geral de 414.

**Independent Test**: Lançar o caso real e comparar os subtotais com a tabela preenchida de 2022–2024.

---

### P1: Verificações: interstício, duplicidade e requisitos ⭐ MVP

**User Story**: Como banca, quero ver inconsistências e dupla pontuação antes de confiar no total, sem que o sistema corrija nada por mim.

**Why P1**: Prompt: impedir dupla pontuação, verificar o interstício e sinalizar falta de documentação, sempre sem corrigir dados.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN a data da atividade é informada só com mês e ano (por exemplo, "Mai/22 a Mai/22") THEN the system SHALL tratá-la como o período do primeiro ao último dia do mês.
2. IF a data do evento da atividade está fora do interstício do processo THEN the system SHALL tratá-la como não pontuada com razão `FORA_DO_INTERSTICIO`.
3. IF o período da atividade começa antes ou termina depois do interstício, mas o intervalo se sobrepõe a ele THEN the system SHALL pontuá-la com a quantidade informada e emitir alerta `ALERTA` de código `INTERSTICIO_PARCIAL`, sem proporcionalizar.
4. IF a atividade não tem data nem período THEN the system SHALL pontuá-la e emitir alerta `ALERTA` de código `DATA_AUSENTE`.
5. IF duas atividades do mesmo processo têm o mesmo título (ignorando maiúsculas, acentos e espaços repetidos) e datas ou períodos que se sobrepõem THEN the system SHALL excluir do total a atividade criada depois, com razão `DUPLICIDADE`, até o usuário rejeitá-la ou registrar justificativa de que é distinta.
6. WHEN o usuário registra a justificativa de que duas atividades são distintas THEN the system SHALL contar ambas e SHALL gravar a justificativa em evento de auditoria.
7. IF duas atividades do Grupo VI têm o mesmo título e períodos que se sobrepõem, como membro e presidente da mesma comissão THEN the system SHALL aplicar a regra de duplicidade (nota do Grupo VI).
8. IF uma atividade não tem nota de comprovante THEN the system SHALL emitir alerta `ALERTA` de código `SEM_COMPROVANTE` e SHALL manter a atividade no total.
9. IF o regime do docente é `DE` ou `40H` e a soma dos subtotais dos Grupos IV e V é 0 THEN the system SHALL emitir alerta `ALERTA` de código `SEM_EXTENSAO_OU_PESQUISA`, com referência à Res. 4.644/2015, art. 13, II.
10. The system SHALL registrar, na versão da tabela, os mínimos de referência por classe atual: 60 (A), 80 (B), 100 (C) e 120 (D), referência Res. 4.644/2015, art. 12, aplicáveis somente quando a estrutura de carreira do processo é a da Res. 4.644.
11. WHEN o total é calculado THEN the system SHALL informar a comparação com o mínimo de referência como `ATINGE`, `NAO_ATINGE` ou `NAO_DEFINIDO`, sem decidir sobre o resultado do processo.
12. IF a estrutura de carreira do processo é a da Lei 15.141/2025 THEN the system SHALL informar `NAO_DEFINIDO` e emitir alerta `REQUER_ANALISE_NORMATIVA` de código `MINIMO_NAO_DEFINIDO`.
13. The system SHALL emitir os alertas desta história com código, severidade, mensagem em português e referência normativa, e SHALL nunca alterar, apagar ou bloquear o salvamento dos dados informados.

**Independent Test**: Lançar duas atividades com o mesmo título e período e ver a segunda excluída com razão DUPLICIDADE.

---

### P1: Etapa 4 na interface ⭐ MVP

**User Story**: Como docente sem conhecimento técnico, quero ver e editar a tabela de pontuação do meu processo.

**Why P1**: ETAPA 4 do fluxo do prompt; fatia vertical demonstrável.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o usuário abre um processo THEN the frontend SHALL habilitar a Etapa 4 "Pontuação" na navegação, mantendo as etapas 2, 3 e 5 a 9 como "em breve".
2. WHEN a Etapa 4 é aberta THEN the frontend SHALL exibir a tabela com as colunas Grupo, Item, Atividade, Quantidade, Pontuação unitária, Total, Comprovante e Status, agrupada de I a VIII.
3. WHEN a Etapa 4 é aberta THEN the frontend SHALL exibir o subtotal de cada grupo, o total geral, a pontuação potencial, o percentual do Grupo I, a comparação com o mínimo de referência e os contadores de atividades, comprovantes, pendentes, não pontuadas e com divergências.
4. WHEN o usuário cria ou edita uma atividade THEN the frontend SHALL exibir os campos conforme o modo do critério (no Grupo I: período letivo, nível e horas) e, na edição, SHALL exigir a justificativa antes de enviar.
5. IF o backend retorna 422 THEN the frontend SHALL exibir a mensagem junto ao campo indicado.
6. WHEN o processo não tem tabela escolhida THEN the frontend SHALL exibir a sugestão, a situação e a referência normativa da tabela e pedir confirmação antes de calcular.
7. The frontend SHALL exibir os alertas e as razões de cada atividade com a referência normativa, agrupados por severidade.
8. The frontend SHALL ser utilizável em largura de 360 px sem rolagem horizontal, exibindo a tabela como cartões empilhados.

**Independent Test**: No navegador, abrir o processo, confirmar a tabela e lançar uma atividade de cada modo.

---

### P2: Administração das tabelas

**User Story**: Como ADMIN, quero criar, duplicar, versionar e importar tabelas de pontuação, para atender cada faculdade e instituto sem alterar o código.

**Why P2**: Prompt: criar, duplicar, editar, importar, definir vigência, associar à unidade, registrar a norma de cada alteração e manter versões anteriores.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHERE o usuário é ADMIN the system SHALL permitir criar uma tabela com nome único, unidades associadas e primeira versão com vigência e referência normativa.
2. WHEN o ADMIN duplica uma tabela THEN the system SHALL criar uma tabela nova, com o nome informado, copiando a última versão, e SHALL manter as duas independentes.
3. WHEN o ADMIN altera critérios de uma versão não usada por processo THEN the system SHALL exigir a referência normativa da alteração e registrar evento de auditoria com valores anterior e novo.
4. IF o ADMIN altera critérios de uma versão usada por algum processo THEN the system SHALL responder 409 orientando a criar uma nova versão.
5. WHEN o ADMIN cria uma nova versão a partir de outra THEN the system SHALL copiar os critérios, exigir início de vigência e referência normativa e, se há versão sem data final, encerrá-la no dia anterior ao início da nova.
6. IF o encerramento deixaria um processo existente com data final em ou após o início da nova versão sem a versão que ele usa THEN the system SHALL responder 409 sem criar a versão.
7. IF a vigência de uma versão se sobrepõe à de outra versão da mesma tabela THEN the system SHALL responder 409.
8. WHEN o ADMIN envia um CSV em UTF-8 com as colunas `grupo`, `item`, `descricao`, `unidade`, `modo`, `pontos`, `horas_por_bloco`, `limite` THEN the system SHALL criar uma nova versão com todas as linhas válidas.
9. IF alguma linha do CSV é inválida THEN the system SHALL responder 422 listando todas as linhas e campos inválidos e SHALL não criar a versão.
10. WHEN o ADMIN consulta o histórico THEN the system SHALL listar todas as versões, vigências, referências e eventos de auditoria, e SHALL manter as versões anteriores somente leitura.
11. IF um usuário que não é ADMIN tenta criar, duplicar, alterar ou importar tabela THEN the system SHALL responder 403.

**Independent Test**: Importar um CSV com um erro e depois outro correto, e conferir a nova versão.

---

### P3: Interface de administração das tabelas

**User Story**: Como ADMIN, quero telas para gerir as tabelas, sem usar a API diretamente.

**Why P3**: Conforto; a API já cobre a necessidade.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHERE o usuário é ADMIN the frontend SHALL exibir a lista de tabelas e versões, com vigência, situação e referência.
2. WHERE o usuário é ADMIN the frontend SHALL permitir duplicar uma tabela, criar uma nova versão e enviar um CSV, exibindo os erros por linha.
3. WHEN a tabela da FASI é aberta THEN the frontend SHALL destacar os critérios marcados para revisão humana.

**Independent Test**: Duplicar a tabela da FASI pela interface e importar um CSV.

---

## Edge Cases

Edge cases are usually unwanted-behavior (IF/THEN) or boundary (WHEN) criteria:

- WHEN as horas não são múltiplo do bloco THEN the system SHALL desprezar o resto (22 horas com bloco de 3 horas dão 7 blocos).
- IF a soma dos pontos de um critério ultrapassa o limite THEN the system SHALL aplicar o limite e emitir `LIMITE_APLICADO`.
- IF o interstício do processo tem datas inválidas THEN the system SHALL tratar a verificação de interstício das atividades como `NAO_VERIFICAVEL` e SHALL não emitir `FORA_DO_INTERSTICIO`.
- IF o processo não tem tabela escolhida THEN the system SHALL responder o cálculo com total 0, razão `SEM_TABELA` em cada atividade e o alerta `TABELA_NAO_ENCONTRADA` ou a sugestão.
- IF o título da atividade tem mais de 300 caracteres ou a nota de comprovante mais de 500 THEN the system SHALL responder 422 no campo correspondente.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation. IDs numeram os critérios de cada história na ordem em que aparecem.

| Requirement ID | Story       | Phase  | Status  |
| -------------- | ----------- | ------ | ------- |
| TAB-01 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-02 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-03 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-04 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-05 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-06 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-07 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| TAB-08 | P1: Catálogo de tabelas de pontuação versionadas | Design | Verified |
| SEL-01 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-02 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-03 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-04 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-05 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-06 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-07 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-08 | P1: Tabela aplicada ao processo | Design | Verified |
| SEL-09 | P1: Tabela aplicada ao processo | Design | Verified |
| ATV-01 | P1: Atividades do processo | Design | Verified |
| ATV-02 | P1: Atividades do processo | Design | Verified |
| ATV-03 | P1: Atividades do processo | Design | Verified |
| ATV-04 | P1: Atividades do processo | Design | Verified |
| ATV-05 | P1: Atividades do processo | Design | Verified |
| ATV-06 | P1: Atividades do processo | Design | Verified |
| ATV-07 | P1: Atividades do processo | Design | Verified |
| ATV-08 | P1: Atividades do processo | Design | Verified |
| ATV-09 | P1: Atividades do processo | Design | Verified |
| ATV-10 | P1: Atividades do processo | Design | Verified |
| ATV-11 | P1: Atividades do processo | Design | Verified |
| ATV-12 | P1: Atividades do processo | Design | Verified |
| ATV-13 | P1: Atividades do processo | Design | Verified |
| ATV-14 | P1: Atividades do processo | Design | Verified |
| CALC-01 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-02 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-03 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-04 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-05 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-06 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-07 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-08 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-09 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-10 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-11 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-12 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-13 | P1: Cálculo determinístico da pontuação | Design | Verified |
| CALC-14 | P1: Cálculo determinístico da pontuação | Design | Verified |
| VERIF-01 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-02 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-03 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-04 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-05 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-06 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-07 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-08 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-09 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-10 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-11 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-12 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| VERIF-13 | P1: Verificações: interstício, duplicidade e requisitos | Design | Verified |
| TELA-01 | P1: Etapa 4 na interface | Design | Verified |
| TELA-02 | P1: Etapa 4 na interface | Design | Verified |
| TELA-03 | P1: Etapa 4 na interface | Design | Verified |
| TELA-04 | P1: Etapa 4 na interface | Design | Verified |
| TELA-05 | P1: Etapa 4 na interface | Design | Verified |
| TELA-06 | P1: Etapa 4 na interface | Design | Verified |
| TELA-07 | P1: Etapa 4 na interface | Design | Verified |
| TELA-08 | P1: Etapa 4 na interface | Design | Verified |
| ADM-01 | P2: Administração das tabelas | Design | Verified |
| ADM-02 | P2: Administração das tabelas | Design | Verified |
| ADM-03 | P2: Administração das tabelas | Design | Verified |
| ADM-04 | P2: Administração das tabelas | Design | Verified |
| ADM-05 | P2: Administração das tabelas | Design | Verified |
| ADM-06 | P2: Administração das tabelas | Design | Verified |
| ADM-07 | P2: Administração das tabelas | Design | Verified |
| ADM-08 | P2: Administração das tabelas | Design | Verified |
| ADM-09 | P2: Administração das tabelas | Design | Verified |
| ADM-10 | P2: Administração das tabelas | Design | Verified |
| ADM-11 | P2: Administração das tabelas | Design | Verified |
| ADMUI-01 | P3: Interface de administração das tabelas | Design | Verified |
| ADMUI-02 | P3: Interface de administração das tabelas | Design | Verified |
| ADMUI-03 | P3: Interface de administração das tabelas | Design | Verified |

**ID format:** `[CATEGORY]-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 80 total, 80 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] O caso real FASI 2022–2024 produz exatamente os subtotais 92, 120, 15, 95, 0, 30, 6 e 56 e o total 414, em teste automatizado.
- [ ] Nenhuma pontuação do sistema passa por modelo de linguagem; o cálculo roda sem rede.
- [ ] Uma atividade duplicada ou fora do interstício nunca entra no total e mostra a razão.
- [ ] Um docente lança e valida as atividades de um interstício e vê a tabela completa em menos de 15 minutos, sem instrução.

# Documentos Gerados — Specification

**Escopo:** Complex (domínio novo: montagem de PDF a partir de originais, DOCX, redação por IA com revisão humana, histórico imutável de documentos).
**Depende de:** `fundacao` (processo, acesso, auditoria), `pontuacao` e `tabela-oficial` (resultado calculado, AD-006), `inteligencia-documental` (documentos, páginas, vínculos atividade-página, job em processo, AD-008, AD-009).
**Fontes:** o prompt do projeto (módulos 7 a 9), `Modelos/Comprovante Documentos_2020_2024.pdf`, `Modelos/RELATÓRIO DE ATIVIDADES Completo.pdf`, `Modelos/Modelo Relatorio Atividades 1.pdf`, `Modelos/ANEXO II - Modelo Relatório de Atividades - Julho 2016.pdf`, `Modelos/ordenamentodecomoosdocumentosdevemestarsequenciadosnorelatrio.pdf`.

## Problem Statement

Hoje o docente lança e valida atividades, vincula cada uma à página que a prova e vê a pontuação, mas monta à mão os três documentos que acompanham o processo: a Tabela de Pontuação, o Relatório de Atividades e o Comprovante de Documentos. Essa montagem repete dados que o sistema já tem e é onde mais surgem erros de ordem, de numeração e de página esquecida. A feature gera esses três documentos a partir do processo, sempre com o resultado determinístico da pontuação, e deixa o usuário revisar tudo antes da versão final.

## Goals

- [ ] A Tabela de Pontuação sai em DOCX e PDF com os mesmos valores da tela de pontuação, incluindo o total e os subtotais por grupo.
- [ ] O Comprovante sai em PDF, na ordem dos grupos e itens da tabela, com sumário, numeração de páginas e as páginas originais anexadas sem alteração do conteúdo.
- [ ] O Relatório de Atividades sai em DOCX e PDF a partir de seções que o usuário revisa e edita, com redação da MariTalk que não acrescenta nenhum fato que não esteja nos dados da atividade.
- [ ] Cada geração fica registrada como uma versão imutável, com o instantâneo do que foi usado, e pode ser baixada de novo sem recalcular.
- [ ] A geração cabe nos 384 MB do backend da VM, sem LibreOffice.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| Ler e revisar o Requerimento e a Portaria da banca | Entradas da feature `banca-parecer` |
| Minuta do Parecer | Feature `banca-parecer`; a IA nunca decide o resultado |
| Converter DOCX em PDF com LibreOffice | Decisão do usuário (2026-11-18): PDF montado direto em Python, pela memória e pela CPU da VM |
| PDF visualmente idêntico ao DOCX | Consequência da decisão acima; os dois têm o mesmo conteúdo e a mesma ordem, a aparência pode diferir |
| Editar o modelo institucional do Relatório pela interface | O modelo é um arquivo de configuração versionado; a edição pela interface fica para depois |
| Assinatura eletrônica e envio por e-mail | Não pedidos |
| Declaração de pagamento de exercícios anteriores e demais itens da lista de ordenamento que não são produzidos pelo sistema | O sistema produz só os três documentos; a ordem do dossiê completo é informada como lembrete, sem gerá-los |
| Alterar atividade, quantidade ou classificação a partir da geração | A geração só lê o processo; correções são feitas nas Etapas 2 e 3 |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Como gerar o PDF | DOCX com python-docx; PDF direto em Python (PyMuPDF para o Comprovante, que junta páginas originais; um gerador de PDF simples para a Tabela e o Relatório); sem LibreOffice | Decisão do usuário em 2026-11-18, pela VM de 1 CPU e 384 MB | y |
| Escopo | Tabela, Relatório e Comprovante; Requerimento, Portaria e Parecer ficam em `banca-parecer` | Decisão do usuário em 2026-11-18 | y |
| Quais atividades entram | Só as de status VALIDADA com grupo e item definidos; as demais ficam fora e são contadas no aviso do documento | Atividade sugerida pela IA ainda não é um fato validado | n |
| Origem das páginas do Comprovante | As páginas dos vínculos atividade-página (`activity_evidence`); o usuário pode acrescentar, remover e reordenar páginas por atividade antes de gerar; o arranjo é guardado como rascunho do processo | O prompt pede "escolher páginas" e "reorganizar manualmente"; a inteligência documental já guarda o vínculo com a página | n |
| Atividade sem página vinculada | Entra no Comprovante com o título e a linha "Sem comprovante anexado"; o resultado traz o alerta `ATIVIDADE_SEM_COMPROVANTE` | Não esconder a falta; quem decide é o usuário | n |
| Mesma página em mais de uma atividade | A página é anexada uma vez, na primeira atividade na ordem do documento; nas demais há uma remissão ("ver comprovante nº N, p. X"); o usuário pode forçar a repetição informando a justificativa | O prompt manda evitar repetir o mesmo documento sem justificativa | n |
| Numeração de páginas | Cada página anexada é colocada, sem nenhuma alteração de conteúdo, numa folha com uma faixa de rodapé acrescentada abaixo; o número vai nessa faixa, nunca sobre o conteúdo original | Preserva assinaturas e textos (o prompt proíbe alterar os comprovantes) | n |
| Imagem enviada como comprovante (PNG, JPEG) | Vira uma página do tamanho da imagem, com a mesma faixa de rodapé | O sistema aceita imagens no envio | n |
| Limite de tamanho | No máximo 400 páginas anexadas por Comprovante e 60 MB de saída; acima disso a geração é recusada com `COMPROVANTE_GRANDE_DEMAIS` | O backend tem 384 MB; as 400 páginas são processadas uma por vez | n |
| Execução | A geração roda como tarefa no worker em processo (AD-008), com estado GERANDO, PRONTO ou FALHOU, e a tela consulta o estado | Um Comprovante de 400 páginas leva mais que uma requisição aceitável | n |
| Estrutura do Relatório | Seções 1 a 6 do prompt (Didáticas com 1.1 graduação, 1.2 pós-graduação e 1.3 orientações; 2 Pesquisa; 3 Extensão; 4 Administrativas; 5 Culturais e artísticas; 6 Outras), definidas num arquivo de configuração versionado (`report_templates`); o cabeçalho institucional (Serviço Público Federal, UFPA, campus, faculdade) é lido do processo e da unidade | O prompt manda a estrutura ser configurável, pois os modelos divergem | n |
| Mapa de grupo para seção | Grupo I → 1.1 e 1.2 (pelo nível); II → 1.3; III → 6 (subtítulo "Participação em bancas e comissões examinadoras"); IV → 3; V → 2; VI → 4; VII → 6 (subtítulo "Capacitação"); VIII → 6; a seção 5 só recebe atividades que o usuário mover para ela | A tabela oficial não tem grupo cultural nem de banca na estrutura do modelo; o mapa é dado de configuração e pode mudar sem código | n |
| Redação pela MariTalk | A IA recebe só os campos da atividade (título, tipo, datas, carga horária, período letivo, descrição já mascarada), nunca o texto bruto de documentos; a resposta passa por uma conferência determinística (todo número, data e nome da descrição precisa estar nos campos); falhando, vale o texto-modelo determinístico | AD-009: a saída da IA não é confiável e o prompt proíbe inventar | n |
| Edição das seções | Cada seção do Relatório tem texto editável; o texto editado pelo usuário é a fonte do documento e a IA não o reescreve depois | O prompt exige revisão e edição antes da geração | n |
| Versão final | Cada geração cria uma nova versão numerada (1, 2, 3...), imutável; a versão guarda o arquivo, o hash SHA-256 e o instantâneo (versão da tabela, total, atividades, arranjo) | AD-006: o resultado não é gravado, então o instantâneo do documento é o histórico | n |
| Processo concluído ou arquivado | Pode-se gerar e baixar documentos; não se altera rascunho do Relatório nem arranjo do Comprovante | A geração só lê o processo | n |
| Quem acessa | Mesma política do processo (AccessPolicy): fora do acesso o documento não existe (404) | Padrão do projeto | n |
| Dados pessoais nos arquivos | Os arquivos ficam no armazenamento do backend com nome interno, sem o nome do docente; o download informa um nome legível construído pelo servidor; a auditoria guarda identificadores, nunca o conteúdo | Os documentos têm dados de terceiros | n |
| Tabela de pontuação do Grupo I | Mostra as horas de PIT por semestre e o total em horas, separadas do total de pontos | `tabela-oficial` (Grupo I em horas, fora do total) | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Tabela de Pontuação em DOCX e PDF ⭐ MVP

**User Story**: Como docente ou membro da banca, quero a Tabela de Pontuação do processo em DOCX e PDF, para anexá-la ao dossiê com os mesmos valores que vejo na tela.

**Why P1**: É o documento mais simples (só leitura do cálculo determinístico) e prova o ciclo completo: gerar, guardar a versão, baixar.

**Acceptance Criteria**:

1. WHEN o usuário pede a Tabela de Pontuação THEN the system SHALL calcular o resultado no momento com o motor determinístico (AD-006) e gerar a versão em DOCX e em PDF com o mesmo resultado.  <!-- event-driven -->
2. The system SHALL escrever no documento o cabeçalho com nome do docente, classe e nível atuais e pretendidos, unidade, interstício e nome e referência normativa da versão da tabela usada.  <!-- ubiquitous -->
3. The system SHALL escrever uma linha por atividade pontuada com grupo, item, atividade, quantidade, pontuação unitária, total, comprovante (número no Comprovante, ou "sem comprovante") e status, na ordem dos grupos e itens.  <!-- ubiquitous -->
4. The system SHALL escrever o subtotal de cada grupo, a pontuação geral e as contagens de atividades, de comprovantes, pendentes, não pontuadas e com divergências, todos iguais aos do resultado do motor.  <!-- ubiquitous -->
5. WHERE a tabela da versão mede o Grupo I em horas de PIT fora do total, the system SHALL escrever as horas por semestre e o total em horas numa seção separada, sem somá-las aos pontos.  <!-- optional-feature -->
6. The system SHALL escrever no documento os alertas da pontuação (limites aplicados, carga horária insuficiente, data final ausente) com o texto que a tela mostra.  <!-- ubiquitous -->
7. IF o processo não tem atividade VALIDADA THEN the system SHALL recusar a geração com o código `SEM_ATIVIDADES_VALIDADAS`.  <!-- unwanted-behavior -->
8. IF o processo ainda não tem versão de tabela escolhida THEN the system SHALL recusar a geração com o código `TABELA_NAO_ESCOLHIDA`.  <!-- unwanted-behavior -->

**Independent Test**: Com as atividades do cenário de aceitação de 211 pontos, gerar a Tabela e conferir no DOCX e no PDF o total 211, os subtotais 52, 7, 62, 0, 30, 4 e 56 e as horas 24, 24, 24 e 20 (total 92).

---

### P1: Comprovante de Documentos em PDF ⭐ MVP

**User Story**: Como docente, quero o Comprovante com as páginas originais anexadas na ordem da tabela, para entregar o dossiê sem montar o PDF à mão.

**Why P1**: É o documento que mais custa ao docente e o que mais depende dos vínculos com as páginas já gravados.

**Acceptance Criteria**:

1. WHEN o usuário gera o Comprovante THEN the system SHALL produzir um PDF com a capa de identificação (docente, classe e nível, unidade, interstício), o sumário e, a seguir, para cada grupo e item da tabela da versão escolhida que tenha atividade, o título do grupo e do item com a nomenclatura da tabela.  <!-- event-driven -->
2. The system SHALL escrever, sob cada item, uma entrada por atividade com o título, a identificação do documento de origem (nome original do arquivo e a página) e as páginas originais anexadas.  <!-- ubiquitous -->
3. The system SHALL anexar cada página original sem alterar o conteúdo, a posição e o tamanho do conteúdo: a página é colocada numa folha com uma faixa de rodapé acrescentada abaixo, que leva o número da página do Comprovante.  <!-- ubiquitous -->
4. The system SHALL numerar todas as páginas do Comprovante em sequência a partir da capa e escrever no sumário o número da primeira página de cada grupo, de cada item e de cada atividade.  <!-- ubiquitous -->
5. WHEN a mesma página do mesmo documento está ligada a mais de uma atividade THEN the system SHALL anexá-la uma só vez e escrever nas demais a remissão ao número do Comprovante em que ela está.  <!-- event-driven -->
6. WHERE o usuário marcou a repetição de uma página com justificativa THEN the system SHALL anexá-la de novo naquela atividade e registrar a justificativa no arranjo.  <!-- optional-feature -->
7. IF uma atividade não tem página vinculada nem acrescentada THEN the system SHALL incluí-la com a linha "Sem comprovante anexado" e acrescentar o alerta `ATIVIDADE_SEM_COMPROVANTE` ao resultado.  <!-- unwanted-behavior -->
8. WHEN o documento de origem é uma imagem THEN the system SHALL usar a imagem como uma página do tamanho dela, com a mesma faixa de rodapé.  <!-- event-driven -->
9. IF o total de páginas anexadas passa de 400 ou o PDF final passa de 60 MB THEN the system SHALL recusar a geração com o código `COMPROVANTE_GRANDE_DEMAIS`, sem gravar arquivo parcial.  <!-- unwanted-behavior -->
10. IF o arquivo original de uma página não está mais no armazenamento ou a página não existe THEN the system SHALL falhar a geração com o código `ORIGINAL_INDISPONIVEL`, informando o documento e a página, sem gravar arquivo parcial.  <!-- unwanted-behavior -->
11. The system SHALL montar o PDF lendo uma página original por vez e liberando a memória das imagens entre as páginas, de modo que o pico de memória não passe de 320 MB com 400 páginas digitalizadas.  <!-- ubiquitous -->

**Independent Test**: Gerar o Comprovante de um processo sintético com 3 grupos e 5 atividades, uma delas sem página e duas apontando a mesma página, e conferir ordem, sumário, numeração, remissão e alerta no PDF, e que o conteúdo de cada página anexada é idêntico ao original.

---

### P1: Arranjo manual do Comprovante ⭐ MVP

**User Story**: Como docente, quero escolher, acrescentar, remover e reordenar as páginas de cada atividade antes de gerar, para que o Comprovante saia como eu quero entregar.

**Why P1**: O prompt exige reorganização manual antes da geração final e a escolha das páginas a anexar.

**Acceptance Criteria**:

1. WHEN o usuário abre o arranjo de um processo sem arranjo salvo THEN the system SHALL montá-lo a partir dos vínculos atividade-página, na ordem dos grupos e itens da tabela e, dentro do item, na ordem de data da atividade.  <!-- event-driven -->
2. WHEN o usuário acrescenta uma página de um documento do processo a uma atividade THEN the system SHALL guardá-la no arranjo, na posição pedida.  <!-- event-driven -->
3. WHEN o usuário remove uma página do arranjo THEN the system SHALL deixá-la fora do Comprovante, sem apagar o vínculo atividade-página nem o documento.  <!-- event-driven -->
4. WHEN o usuário reordena atividades dentro de um item ou páginas dentro de uma atividade THEN the system SHALL guardar a nova ordem e usá-la na geração.  <!-- event-driven -->
5. The system SHALL manter a ordem dos grupos e dos itens da tabela, sem permitir mover uma atividade para um item diferente do que a pontuação lhe deu.  <!-- ubiquitous -->
6. IF o usuário indica um documento ou página que não pertence ao processo THEN the system SHALL responder 404.  <!-- unwanted-behavior -->
7. WHEN o usuário salva o arranjo com uma versão desatualizada THEN the system SHALL responder 409, sem sobrescrever o arranjo mais novo (bloqueio otimista).  <!-- event-driven -->
8. WHEN uma atividade é revalidada, rejeitada ou muda de item depois que o arranjo foi salvo THEN the system SHALL mostrar o arranjo com o aviso de que ele está desatualizado e usar, na geração, só as atividades atuais.  <!-- event-driven -->

**Independent Test**: Reordenar duas páginas e remover uma, salvar, gerar e ver no PDF a ordem nova e a página removida ausente, com o vínculo ainda existente na Etapa 3.

---

### P1: Relatório de Atividades em DOCX e PDF com revisão ⭐ MVP

**User Story**: Como docente, quero o Relatório de Atividades redigido a partir das atividades validadas, para revisar cada seção e gerar o documento sem digitar tudo.

**Why P1**: É o documento institucional central; a redação fiel aos dados é o ponto de maior risco e por isso exige revisão e conferência determinística.

**Acceptance Criteria**:

1. WHEN o usuário abre o rascunho do Relatório pela primeira vez THEN the system SHALL criar as seções da configuração do modelo (1.1, 1.2, 1.3, 2, 3, 4, 5, 6) com as atividades validadas distribuídas pelo mapa de grupo para seção.  <!-- event-driven -->
2. The system SHALL organizar a seção 1.1 e a seção 1.2 por período letivo (semestre), com disciplina, curso, carga horária e período, e a seção 1.3 por modalidade de orientação, separando concluídas e em andamento.  <!-- ubiquitous -->
3. WHEN o usuário pede a redação de uma seção THEN the system SHALL enviar à MariTalk só os campos das atividades da seção e propor, para cada atividade, uma descrição formal.  <!-- event-driven -->
4. The system SHALL aceitar a descrição proposta pela IA somente se cada número, data e nome próprio dela aparecer nos campos da atividade enviados; a descrição que não passa nessa conferência é descartada e substituída pelo texto-modelo determinístico, com o aviso `REDACAO_REJEITADA` na seção.  <!-- ubiquitous -->
5. IF a MariTalk está indisponível, devolve erro ou ultrapassa 60 segundos THEN the system SHALL usar o texto-modelo determinístico e registrar o aviso `REDACAO_INDISPONIVEL`, sem bloquear o rascunho.  <!-- unwanted-behavior -->
6. The system SHALL nunca enviar à MariTalk o texto bruto das páginas dos documentos nem dados pessoais mascarados.  <!-- ubiquitous -->
7. WHEN o usuário edita o texto de uma seção ou de uma atividade THEN the system SHALL guardar o texto editado como definitivo e SHALL NOT sobrescrevê-lo com uma nova redação da IA.  <!-- event-driven -->
8. WHEN o usuário move uma atividade para outra seção THEN the system SHALL guardar a escolha no rascunho e usá-la na geração.  <!-- event-driven -->
9. WHEN o usuário gera o Relatório THEN the system SHALL produzir o DOCX e o PDF com o cabeçalho institucional, a identificação do docente e do interstício e todas as seções, usando o texto guardado no rascunho.  <!-- event-driven -->
10. IF uma atividade validada não tem descrição e não tem título THEN the system SHALL recusar a geração com o código `ATIVIDADE_SEM_DESCRICAO`, citando a atividade.  <!-- unwanted-behavior -->
11. WHILE uma seção não tem nenhuma atividade, the system SHALL omiti-la do documento e listá-la como vazia no rascunho.  <!-- state-driven -->
12. The system SHALL nunca acrescentar ao Relatório objetivos, resultados, metodologias ou qualquer informação que não esteja nos campos das atividades ou no texto digitado pelo usuário.  <!-- ubiquitous -->

**Independent Test**: Com uma resposta da MariTalk simulada que inclui um número inventado e outra fiel, conferir que a primeira vira o texto-modelo com `REDACAO_REJEITADA` e a segunda é aceita; editar uma seção, redigir de novo e ver que o texto editado permanece.

---

### P1: Versões imutáveis e download ⭐ MVP

**User Story**: Como docente, quero guardar cada geração como uma versão e baixá-la depois, para entregar exatamente o que foi gerado.

**Why P1**: Sem histórico não há como saber o que foi entregue (AD-006).

**Acceptance Criteria**:

1. WHEN uma geração termina THEN the system SHALL gravar uma versão numerada do documento (tipo, formato, número, hash SHA-256, tamanho, autor, data), sem nunca alterar uma versão já gravada.  <!-- event-driven -->
2. The system SHALL guardar, em cada versão, o instantâneo do que foi usado: identificador e nome da versão da tabela, total e subtotais, a lista de atividades com grupo, item e quantidade, o arranjo e os alertas.  <!-- ubiquitous -->
3. WHEN o usuário baixa uma versão THEN the system SHALL entregar o arquivo gravado, sem regerá-lo, com o tipo de conteúdo do formato e um nome de arquivo legível montado pelo servidor.  <!-- event-driven -->
4. WHILE uma geração está em andamento, the system SHALL responder o estado GERANDO e SHALL recusar um segundo pedido igual do mesmo processo com 409.  <!-- state-driven -->
5. IF a geração falha THEN the system SHALL registrar o estado FALHOU com um código e uma mensagem sem dados pessoais, sem gravar arquivo parcial, e permitir uma nova tentativa.  <!-- unwanted-behavior -->
6. IF o processo é de outro docente fora do acesso do usuário THEN the system SHALL responder 404 a qualquer operação sobre seus documentos gerados.  <!-- unwanted-behavior -->
7. WHEN uma geração é pedida, termina ou falha THEN the system SHALL registrar um evento de auditoria com identificadores e códigos, sem texto dos documentos.  <!-- event-driven -->
8. IF o servidor reinicia com uma geração em andamento THEN the system SHALL marcar essa geração como FALHOU com o código `INTERROMPIDA` na partida.  <!-- unwanted-behavior -->

**Independent Test**: Gerar a Tabela duas vezes, conferir as versões 1 e 2 com hashes e instantâneos, baixar a versão 1 depois de mudar uma atividade e ver que o arquivo é o original.

---

### P1: Etapa 4, Documentos, na interface ⭐ MVP

**User Story**: Como docente, quero uma etapa na interface onde gero e baixo os três documentos e acompanho o estado, para fechar o processo sem sair do sistema.

**Why P1**: Sem a tela a feature não existe para o usuário.

**Acceptance Criteria**:

1. The system SHALL mostrar a etapa "Documentos" no processo com três blocos (Tabela de Pontuação, Relatório de Atividades, Comprovante), cada um com o botão de gerar, o estado e o histórico de versões com download em cada formato.  <!-- ubiquitous -->
2. WHEN o usuário abre o bloco do Relatório THEN the system SHALL mostrar as seções com o texto editável, os avisos da seção e o botão de pedir a redação.  <!-- event-driven -->
3. WHEN o usuário abre o bloco do Comprovante THEN the system SHALL mostrar o arranjo por grupo, item e atividade, com adicionar, remover e reordenar páginas e a marcação de repetição com justificativa.  <!-- event-driven -->
4. WHILE uma geração está em andamento, the system SHALL mostrar o estado e consultar o servidor a cada 3 segundos até PRONTO ou FALHOU.  <!-- state-driven -->
5. IF a geração termina com alertas THEN the system SHALL listá-los no bloco, com o texto em português.  <!-- unwanted-behavior -->
6. The system SHALL mostrar um aviso antes do botão de gerar quando houver atividades não validadas, informando quantas ficam de fora.  <!-- ubiquitous -->
7. The system SHALL funcionar sem barra de rolagem horizontal da página em 360 px de largura.  <!-- ubiquitous -->

**Independent Test**: Teste de componente da etapa com a API simulada: gerar, ver GERANDO, ver PRONTO e os links de download; abrir o arranjo e reordenar.

---

### P2: Lembrete da ordem do dossiê

**User Story**: Como docente, quero ver a ordem em que os documentos do dossiê devem ser entregues, para não esquecer nenhum.

**Why P2**: O modelo de ordenamento lista documentos que o sistema não produz; o lembrete evita esquecimento sem ampliar o escopo.

**Acceptance Criteria**:

1. The system SHALL mostrar na etapa Documentos a lista ordenada do modelo de ordenamento (requerimento à CPPD, portaria da última progressão, declaração de pagamento de exercícios anteriores, e os demais itens do modelo), marcando quais o sistema gera.  <!-- ubiquitous -->
2. The system SHALL ler a lista de um arquivo de configuração versionado e nunca de texto digitado no código da tela.  <!-- ubiquitous -->

**Independent Test**: Abrir a etapa e ver a lista na ordem do arquivo de configuração, com os três documentos gerados marcados.

---

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | CMP-09 e REL-07 (texto editado limitado a 20 000 caracteres por seção) |
| Failure / partial-failure states | CMP-09, CMP-10, VER-05, VER-08: nenhum arquivo parcial |
| Idempotency / retry / duplicate handling | VER-04 (segundo pedido igual recusado), CMP-05 (página repetida), nova tentativa após FALHOU |
| Auth boundaries & rate limits | VER-06 (404 fora do acesso); um pedido de geração por tipo e processo por vez (VER-04) já limita a carga; rate limit adicional N/A because o uso é autenticado e por processo |
| Concurrency / ordering | ARR-07 (bloqueio otimista do arranjo), VER-04 |
| Data lifecycle / expiry | As versões ficam enquanto o processo existir; exclusão de versão antiga N/A because não foi pedida e o histórico é o registro do que foi entregue |
| Observability | VER-07 (auditoria), logs com identificadores e códigos |
| External-dependency failure | REL-05 (MariTalk indisponível), CMP-10 (original ausente) |
| State-transition integrity | VER-04 (GERANDO → PRONTO/FALHOU), VER-08 (reinício) |

---

## Edge Cases

- IF uma página original é muito grande (acima de 50 megapixels ao renderizar) THEN the system SHALL anexá-la como página vetorial ou de imagem sem rasterizá-la, e SHALL NOT falhar a geração por causa disso.
- IF o nome do docente ou o título de uma atividade tem caracteres fora do latim básico THEN the system SHALL escrevê-los corretamente no DOCX e no PDF.
- IF o interstício tem menos de uma atividade por grupo THEN the system SHALL omitir os grupos vazios do Comprovante e do Relatório, e mostrá-los com zero na Tabela de Pontuação.
- WHEN duas atividades têm o mesmo título no mesmo item THEN the system SHALL listar as duas, cada uma com as suas páginas.
- IF o arranjo salvo referencia um documento que foi excluído depois THEN the system SHALL tratá-lo como `ORIGINAL_INDISPONIVEL` na geração e marcar a entrada como inválida no arranjo.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TAB-01 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-02 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-03 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-04 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-05 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-06 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-07 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| TAB-08 | P1: Tabela de Pontuação em DOCX e PDF | Design | Pending |
| CMP-01 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-02 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-03 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-04 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-05 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-06 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-07 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-08 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-09 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-10 | P1: Comprovante de Documentos em PDF | Design | Pending |
| CMP-11 | P1: Comprovante de Documentos em PDF | Design | Pending |
| ARR-01 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-02 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-03 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-04 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-05 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-06 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-07 | P1: Arranjo manual do Comprovante | Design | Pending |
| ARR-08 | P1: Arranjo manual do Comprovante | Design | Pending |
| REL-01 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-02 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-03 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-04 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-05 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-06 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-07 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-08 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-09 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-10 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-11 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| REL-12 | P1: Relatório de Atividades em DOCX e PDF com revisão | Design | Pending |
| VER-01 | P1: Versões imutáveis e download | Design | Pending |
| VER-02 | P1: Versões imutáveis e download | Design | Pending |
| VER-03 | P1: Versões imutáveis e download | Design | Pending |
| VER-04 | P1: Versões imutáveis e download | Design | Pending |
| VER-05 | P1: Versões imutáveis e download | Design | Pending |
| VER-06 | P1: Versões imutáveis e download | Design | Pending |
| VER-07 | P1: Versões imutáveis e download | Design | Pending |
| VER-08 | P1: Versões imutáveis e download | Design | Pending |
| UIG-01 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-02 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-03 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-04 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-05 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-06 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| UIG-07 | P1: Etapa 4, Documentos, na interface | Design | Pending |
| ORD-01 | P2: Lembrete da ordem do dossiê | - | Pending |
| ORD-02 | P2: Lembrete da ordem do dossiê | - | Pending |

**ID format:** `[CATEGORY]-[NUMBER]` (e.g., `AUTH-01`, `CART-03`, `NOTIF-02`)

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 56 total, 0 mapped to tasks, 56 unmapped ⚠️ (esperado na fase Specify)

**Mapping notes:** the numbering of each requirement follows the order of the acceptance criteria inside its story (TAB-01 is criterion 1 of the Tabela story, CMP-05 is criterion 5 of the Comprovante story, and so on; the "Implicit-Requirement Dimensions" table refers to them by these IDs).

---

## Success Criteria

- [ ] A Tabela gerada para o cenário de aceitação mostra 211 pontos, os subtotais 52, 7, 62, 0, 30, 4 e 56 e as horas 24, 24, 24, 20 (92), no DOCX e no PDF.
- [ ] O Comprovante de um processo sintético tem páginas idênticas às originais, numeração contínua e sumário correto, com pico de memória abaixo de 320 MB em 400 páginas digitalizadas sintéticas.
- [ ] Nenhuma descrição aceita no Relatório contém número, data ou nome que não esteja nos campos da atividade.
- [ ] Uma versão gerada é baixada de novo, byte a byte igual, depois de mudanças no processo.
- [ ] Nenhum dado pessoal real entra em teste, fixture ou commit; os testes usam documentos sintéticos.

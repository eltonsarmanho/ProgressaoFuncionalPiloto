# Documentos Gerados — Specification

**Escopo:** Complex (domínio novo: montagem de PDF a partir de originais, DOCX, redação por IA com revisão humana, histórico imutável de documentos).
**Depende de:** `fundacao` (processo e a transição de status `ProcessStatus`, acesso, auditoria), `pontuacao` e `tabela-oficial` (resultado calculado, AD-006), `inteligencia-documental` (documentos, páginas, vínculos atividade-página, job em processo, AD-008, AD-009).
**Fontes:** o prompt do projeto (módulos 7 a 9), `Modelos/Comprovante Documentos_2020_2024.pdf`, `Modelos/RELATÓRIO DE ATIVIDADES Completo.pdf`, `Modelos/Modelo Relatorio Atividades 1.pdf`, `Modelos/Modelo Relatorio Atividades 2.docx` (recebido em 2026-11-18), `Modelos/ANEXO II - Modelo Relatório de Atividades - Julho 2016.pdf`, `Modelos/ordenamentodecomoosdocumentosdevemestarsequenciadosnorelatrio.pdf`.

## Problem Statement

Hoje o docente lança e valida atividades, vincula cada uma à página que a prova e vê a pontuação, mas monta à mão os três documentos que acompanham o processo: a Tabela de Pontuação, o Relatório de Atividades e o Comprovante de Documentos. Essa montagem repete dados que o sistema já tem e é onde mais surgem erros de ordem, de numeração e de página esquecida. A feature gera esses três documentos a partir do processo, sempre com o resultado determinístico da pontuação, e deixa o usuário revisar tudo antes da versão final.

## Goals

- [ ] A Tabela de Pontuação sai em DOCX e PDF com os mesmos valores da tela de pontuação, incluindo o total e os subtotais por grupo.
- [ ] O Comprovante sai em PDF, na ordem dos grupos e itens da tabela, com sumário, numeração de páginas e as páginas originais anexadas sem alteração do conteúdo.
- [ ] O Relatório de Atividades sai em DOCX e PDF a partir de seções que o usuário revisa e edita, com redação da MariTalk que não acrescenta nenhum fato que não esteja nos dados da atividade.
- [ ] Cada geração fica registrada como uma versão imutável, com o instantâneo do que foi usado, e pode ser baixada de novo sem recalcular.
- [ ] A geração cabe nos 384 MB do backend da VM, sem LibreOffice.
- [ ] Ao concluir o processo, depois que os três documentos estão gerados, os documentos de entrada são excluídos do servidor e deixam de ocupar espaço, sem perder nenhum documento gerado.

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
| Restaurar documentos de entrada depois da exclusão, ou fazer backup antes | A exclusão é irreversível por pedido do usuário; a VM não tem backup (dívida registrada no `STATE.md`) e o usuário é avisado na confirmação |
| Excluir versões geradas antigas ou aplicar política de retenção | Decisão do usuário (2026-11-18): todas as versões ficam; elas são os documentos entregues |
| Excluir o processo, os documentos gerados ou o JSON estruturado da extração na conclusão | O pedido trata dos documentos de entrada; ver a assunção sobre o que fica |

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
| Imagem enviada como comprovante (PNG, JPEG) | Vira uma página do tamanho da imagem, com a mesma faixa de rodapé; o JPEG de qualquer tamanho entra sem decodificar; o PNG é aceito até 12 megapixels e acima disso a geração é recusada com `IMAGEM_GRANDE_DEMAIS` | Medido no protótipo: o PNG de 12 megapixels custa cerca de 103 MB de memória e o de 40 megapixels cerca de 324 MB, contra 384 MB do backend. Decisão do usuário em 2026-11-18 | y |
| Limite de tamanho | No máximo 400 páginas anexadas por Comprovante e 60 MB de saída; acima disso a geração é recusada com `COMPROVANTE_GRANDE_DEMAIS` | O backend tem 384 MB; as 400 páginas são processadas uma por vez | n |
| Execução da geração | A geração roda como tarefa no worker em processo (AD-008), com estado GERANDO, PRONTO ou FALHOU, e a tela consulta o estado | Um Comprovante de 400 páginas leva mais que uma requisição aceitável | n |
| Execução da redação | A redação de uma seção roda como tarefa em segundo plano no mesmo worker, com estado GERANDO, PRONTO ou FALHOU na seção; a tela consulta a cada 3 segundos; a chamada à MariTalk tem prazo de 60 segundos e, esgotado ou com erro, vale o texto-modelo com `REDACAO_INDISPONIVEL` e a tarefa termina em PRONTO | Uma requisição de até 60 segundos prenderia a tela e passaria do tempo padrão do nginx. Decisão do usuário em 2026-11-18 | y |
| Licença do PyMuPDF | O PyMuPDF (AGPL-3.0) continua como dependência do projeto | O usuário aceitou a licença em 2026-11-18; é registro de decisão, não parecer jurídico | y |
| Numeração da etapa | A etapa nova é a Etapa 5, "Documentos gerados"; a Etapa 2 já se chama Documentos e a Etapa 4 é a Pontuação | Decisão do usuário em 2026-11-18 | y |
| Retenção das versões geradas | Todas as versões ficam enquanto o processo existir; o tamanho de cada versão aparece no histórico | As versões são o que foi entregue (AD-006). Decisão do usuário em 2026-11-18 | y |
| Estrutura do Relatório | Segue o `Modelo Relatorio Atividades 2.docx` (A4, Times New Roman, cabeçalho centralizado com Serviço Público Federal, Universidade Federal do Pará e a faculdade; título; nome, professor com classe e nível, faculdade, período de interstício; "ATIVIDADES DESENVOLVIDAS") com as seções 1 Didáticas (a graduação por "Nº Período de AAAA", disciplina e carga horária; pós-graduação; orientações), 2 Pesquisa, 3 Extensão, 4 Administração, 5 Atividades culturais e/ou artísticas, 6 Outras atividades; os títulos e a ordem vêm de um arquivo de configuração versionado (`report_templates`), que também admite o estilo narrativo do `Modelo Relatorio Atividades 1.pdf`; o cabeçalho institucional vem do processo e da unidade; o brasão não é incluído (a configuração aceita um arquivo de imagem depois) | O prompt manda a estrutura ser configurável; o DOCX recebido do usuário confirma as seis seções e o formato de campos de cada entrada | y |
| Campos que o sistema não tem | Os campos dos modelos que a atividade não guarda (fonte do recurso, colaboradores, bolsista, número da portaria, quando não estão no título nem na descrição) não são inventados: a linha só aparece quando o dado existe; o usuário pode digitá-lo no texto editável da seção | O prompt proíbe acrescentar informação que não esteja nos documentos de origem | n |
| Mapa de grupo para seção | Grupo I → 1.1 e 1.2 (pelo nível); II → 1.3; III → 6 (subtítulo "Participação em bancas e comissões examinadoras"); IV → 3; V → 2; VI → 4; VII → 6 (subtítulo "Capacitação"); VIII → 6; a seção 5 só recebe atividades que o usuário mover para ela | A tabela oficial não tem grupo cultural nem de banca na estrutura do modelo; o mapa é dado de configuração e pode mudar sem código | n |
| Redação pela MariTalk | A IA recebe só os campos da atividade (título, tipo, datas, carga horária, período letivo, descrição já mascarada), nunca o texto bruto de documentos; a resposta passa por uma conferência determinística (todo número, data e nome da descrição precisa estar nos campos); falhando, vale o texto-modelo determinístico | AD-009: a saída da IA não é confiável e o prompt proíbe inventar | n |
| Edição das seções | Cada seção do Relatório tem texto editável; o texto editado pelo usuário é a fonte do documento e a IA não o reescreve depois | O prompt exige revisão e edição antes da geração | n |
| Versão final | Cada geração cria uma nova versão numerada (1, 2, 3...), imutável; a versão guarda o arquivo, o hash SHA-256 e o instantâneo (versão da tabela, total, atividades, arranjo) | AD-006: o resultado não é gravado, então o instantâneo do documento é o histórico | n |
| Processo arquivado, concluído e a geração | Processo arquivado sem exclusão gera e baixa os três documentos; processo concluído (originais excluídos) gera só a Tabela e o Relatório e baixa todas as versões; nenhum dos dois altera o rascunho do Relatório nem o arranjo do Comprovante, que ficam somente leitura | A geração só lê o processo; sem os originais não há como montar o Comprovante | n |
| Concluir exclui os documentos de entrada | A transição existente do processo para CONCLUIDO passa a ser "Concluir e excluir documentos de entrada": exige uma versão PRONTO de cada documento (`ARTEFATOS_PENDENTES`), pede confirmação irreversível com o número de arquivos e o espaço a liberar, exclui do armazenamento os arquivos originais enviados, os textos extraídos das páginas e os trechos de evidência (dados pessoais), e só então marca o processo como CONCLUIDO (somente leitura) | Pedido do usuário em 2026-11-18: os documentos de entrada não devem ocupar espaço do servidor quando os artefatos gerais estão prontos. A interpretação (o que sai, o que fica, em que ordem) é a minha | n |
| O que fica depois da exclusão | Ficam os metadados do documento (nome original, tipo, número de páginas, tamanho, hash) marcados `ARQUIVO_EXCLUIDO`, os vínculos atividade-página (só os números), as atividades, o JSON estruturado das execuções de extração (`extraction_runs.raw_json`, imutável por gatilho e sem o texto das páginas) e todos os documentos gerados com todas as suas versões | O pedido nomeia arquivos, textos e trechos; apagar o JSON exigiria mudar o gatilho de imutabilidade da extração e tirar da atividade a prova do que foi extraído | n |
| Qual versão vale para concluir | Basta existir uma versão PRONTO de cada tipo (Tabela, Relatório, Comprovante); a tela avisa quando a versão mais recente de um tipo está desatualizada, sem impedir | O usuário pode ter entregue uma versão anterior de propósito; bloquear por defasagem impediria a conclusão | n |
| Quem conclui e conflito | Valem as regras de papel, de acesso e de versão (`expected_version`) da transição de status existente (`ChangeProcessStatus`); a rota genérica de status recusa o alvo CONCLUIDO com `CONCLUSAO_EXIGE_EXCLUSAO` | Reaproveita a regra existente e impede concluir sem excluir | n |
| Exclusão parcial e repetição | Arquivo já ausente no armazenamento conta como removido; se algum arquivo não sai, o processo continua EM_ANDAMENTO com o alerta `EXCLUSAO_PARCIAL` e o pedido pode ser repetido; os arquivos já excluídos continuam excluídos; repetir num processo já concluído responde 200 sem alterar nada | Pedido do usuário (idempotência e nova tentativa) | n |
| Conclusão durante outra operação | Com geração, redação ou processamento de documento em andamento a conclusão é recusada com `OPERACAO_EM_ANDAMENTO` | Excluir um arquivo que o worker lê faria a geração ou o OCR falhar | n |
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
3. The system SHALL escrever a tabela com 7 colunas (item, como "I.1", atividade, quantidade, pontuação unitária, total, comprovante e status), uma linha por atividade pontuada, com o grupo como uma faixa que traz o nome da tabela e o subtotal (também para grupos sem atividade, com zero), na ordem dos grupos e itens, e com o comprovante escrito como o número no Comprovante ou "sem comprovante".  <!-- ubiquitous -->
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
3. The system SHALL anexar cada página original sem alterar o conteúdo, a posição e o tamanho do conteúdo, mantendo a rotação, as anotações e os campos preenchidos: a página é colocada numa folha com uma faixa de rodapé acrescentada abaixo, que leva o número da página do Comprovante; a única exceção é a página com rotação e área de recorte menor que a página, tratada em CMP-12.  <!-- ubiquitous -->
4. The system SHALL numerar todas as páginas do Comprovante em sequência a partir da capa e escrever no sumário o número da primeira página de cada grupo, de cada item e de cada atividade.  <!-- ubiquitous -->
5. WHEN a mesma página do mesmo documento está ligada a mais de uma atividade THEN the system SHALL anexá-la uma só vez e escrever nas demais a remissão ao número do Comprovante em que ela está.  <!-- event-driven -->
6. WHERE o usuário marcou a repetição de uma página com justificativa THEN the system SHALL anexá-la de novo naquela atividade e registrar a justificativa no arranjo.  <!-- optional-feature -->
7. IF uma atividade não tem página vinculada nem acrescentada THEN the system SHALL incluí-la com a linha "Sem comprovante anexado" e acrescentar o alerta `ATIVIDADE_SEM_COMPROVANTE` ao resultado.  <!-- unwanted-behavior -->
8. WHEN o documento de origem é uma imagem JPEG, ou uma imagem PNG de até 12 megapixels, THEN the system SHALL usar a imagem como uma página do tamanho dela, com a mesma faixa de rodapé, sem decodificar o JPEG.  <!-- event-driven -->
9. IF o total de páginas anexadas passa de 400 ou o PDF final passa de 60 MB THEN the system SHALL recusar a geração com o código `COMPROVANTE_GRANDE_DEMAIS`, sem gravar arquivo parcial.  <!-- unwanted-behavior -->
10. IF o arquivo original de uma página não está mais no armazenamento ou a página não existe THEN the system SHALL falhar a geração com o código `ORIGINAL_INDISPONIVEL`, informando o documento e a página, sem gravar arquivo parcial.  <!-- unwanted-behavior -->
11. The system SHALL montar o PDF lendo uma página original por vez e liberando a memória das imagens entre as páginas, de modo que o pico de memória não passe de 320 MB com 400 páginas digitalizadas.  <!-- ubiquitous -->
12. IF a página original tem rotação e uma área de recorte menor que a página THEN the system SHALL anexá-la rasterizada a 200 dpi (JPEG, qualidade 92), preservando o que se vê, e SHALL acrescentar ao resultado o alerta `PAGINA_RASTERIZADA` com o documento e a página.  <!-- unwanted-behavior -->
13. IF o documento de origem é uma imagem PNG acima de 12 megapixels THEN the system SHALL recusar a geração com o código `IMAGEM_GRANDE_DEMAIS`, citando o documento, antes de montar qualquer página e sem gravar arquivo parcial.  <!-- unwanted-behavior -->

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
3. WHEN o usuário pede a redação de uma seção THEN the system SHALL registrar a tarefa de redação com o estado GERANDO na seção, responder 202 sem esperar a MariTalk e, em segundo plano, enviar à MariTalk só os campos das atividades da seção e propor, para cada atividade, uma descrição formal.  <!-- event-driven -->
4. The system SHALL aceitar a descrição proposta pela IA somente se cada número, data e nome próprio dela aparecer nos campos da atividade enviados; a descrição que não passa nessa conferência é descartada e substituída pelo texto-modelo determinístico, com o aviso `REDACAO_REJEITADA` na seção.  <!-- ubiquitous -->
5. IF a MariTalk está indisponível, devolve erro ou ultrapassa 60 segundos na tarefa de redação THEN the system SHALL usar o texto-modelo determinístico, registrar o aviso `REDACAO_INDISPONIVEL` na seção e terminar a tarefa em PRONTO, sem bloquear o rascunho.  <!-- unwanted-behavior -->
6. The system SHALL nunca enviar à MariTalk o texto bruto das páginas dos documentos nem dados pessoais mascarados.  <!-- ubiquitous -->
7. WHEN o usuário edita o texto de uma seção ou de uma atividade THEN the system SHALL guardar o texto editado como definitivo e SHALL NOT sobrescrevê-lo com uma nova redação da IA.  <!-- event-driven -->
8. WHEN o usuário move uma atividade para outra seção THEN the system SHALL guardar a escolha no rascunho e usá-la na geração.  <!-- event-driven -->
9. WHEN o usuário gera o Relatório THEN the system SHALL produzir o DOCX e o PDF com o cabeçalho institucional, a identificação do docente e do interstício e todas as seções, usando o texto guardado no rascunho.  <!-- event-driven -->
10. IF uma atividade validada não tem descrição e não tem título THEN the system SHALL recusar a geração com o código `ATIVIDADE_SEM_DESCRICAO`, citando a atividade.  <!-- unwanted-behavior -->
11. WHILE uma seção não tem nenhuma atividade, the system SHALL omiti-la do documento e listá-la como vazia no rascunho.  <!-- state-driven -->
12. The system SHALL nunca acrescentar ao Relatório objetivos, resultados, metodologias ou qualquer informação que não esteja nos campos das atividades ou no texto digitado pelo usuário.  <!-- ubiquitous -->
13. WHILE a seção tem uma tarefa de redação em estado GERANDO, the system SHALL recusar um segundo pedido de redação da mesma seção com 409 e o código `REDACAO_EM_ANDAMENTO`, sem recusar a edição das demais seções.  <!-- state-driven -->
14. IF o servidor reinicia com uma tarefa de redação em estado GERANDO THEN the system SHALL marcá-la como FALHOU com o código `INTERROMPIDA` na partida, sem alterar nenhum texto do rascunho.  <!-- unwanted-behavior -->
15. IF a tarefa de redação falha por erro interno THEN the system SHALL marcá-la como FALHOU com o código `ERRO_INTERNO`, manter os textos do rascunho como estavam e permitir um novo pedido.  <!-- unwanted-behavior -->

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
9. The system SHALL manter todas as versões geradas enquanto o processo existir, inclusive depois da conclusão, e mostrar o tamanho de cada versão no histórico.  <!-- ubiquitous -->

**Independent Test**: Gerar a Tabela duas vezes, conferir as versões 1 e 2 com hashes e instantâneos, baixar a versão 1 depois de mudar uma atividade e ver que o arquivo é o original.

---

### P1: Etapa 5, Documentos gerados, na interface ⭐ MVP

**User Story**: Como docente, quero uma etapa na interface onde gero e baixo os três documentos e acompanho o estado, para fechar o processo sem sair do sistema.

**Why P1**: Sem a tela a feature não existe para o usuário.

**Acceptance Criteria**:

1. The system SHALL mostrar a Etapa 5, "Documentos gerados", no processo com três blocos (Tabela de Pontuação, Relatório de Atividades, Comprovante), cada um com o botão de gerar, o estado e o histórico de versões com download em cada formato.  <!-- ubiquitous -->
2. WHEN o usuário abre o bloco do Relatório THEN the system SHALL mostrar as seções com o texto editável, os avisos da seção e o botão de pedir a redação.  <!-- event-driven -->
3. WHEN o usuário abre o bloco do Comprovante THEN the system SHALL mostrar o arranjo por grupo, item e atividade, com adicionar, remover e reordenar páginas e a marcação de repetição com justificativa.  <!-- event-driven -->
4. WHILE uma geração está em andamento, the system SHALL mostrar o estado e consultar o servidor a cada 3 segundos até PRONTO ou FALHOU.  <!-- state-driven -->
5. IF a geração termina com alertas THEN the system SHALL listá-los no bloco, com o texto em português.  <!-- unwanted-behavior -->
6. The system SHALL mostrar um aviso antes do botão de gerar quando houver atividades não validadas, informando quantas ficam de fora.  <!-- ubiquitous -->
7. The system SHALL funcionar sem barra de rolagem horizontal da página em 360 px de largura.  <!-- ubiquitous -->
8. WHILE uma seção do Relatório está com a redação em estado GERANDO, the system SHALL mostrar o estado na seção e consultar o servidor a cada 3 segundos até PRONTO ou FALHOU, mantendo as demais seções editáveis, e recarregar o texto da seção quando terminar.  <!-- state-driven -->
9. WHEN o usuário aciona "Concluir e excluir documentos de entrada" THEN the system SHALL mostrar a confirmação de ação irreversível com o número de arquivos e o espaço a liberar, os documentos gerados que faltam, e só enviar o pedido depois da confirmação explícita.  <!-- event-driven -->

**Independent Test**: Teste de componente da etapa com a API simulada: gerar, ver GERANDO, ver PRONTO e os links de download; abrir o arranjo e reordenar.

---

### P1: Concluir o processo e excluir os documentos de entrada ⭐ MVP

**User Story**: Como docente, quero que, depois de gerados os três documentos, a conclusão do processo exclua os documentos de entrada do servidor, para que eles não ocupem espaço nem guardem dados pessoais além do necessário.

**Why P1**: Pedido do usuário (2026-11-18). A VM é compartilhada e tem pouco disco, e os originais têm dados pessoais de terceiros; depois que a Tabela, o Relatório e o Comprovante estão prontos, os originais deixam de ser necessários.

**Acceptance Criteria**:

1. IF o processo não tem versão PRONTO da Tabela, do Relatório e do Comprovante THEN the system SHALL recusar a conclusão com 422 e o código `ARTEFATOS_PENDENTES`, listando os tipos que faltam, sem excluir nenhum arquivo.  <!-- unwanted-behavior -->
2. IF há geração, redação de seção ou processamento de documento em andamento no processo THEN the system SHALL recusar a conclusão com 409 e o código `OPERACAO_EM_ANDAMENTO`, sem excluir nenhum arquivo.  <!-- unwanted-behavior -->
3. WHEN o usuário consulta a conclusão THEN the system SHALL informar o número de arquivos originais ainda armazenados, o espaço total em bytes que a exclusão libera e, para cada tipo de documento gerado, se há versão PRONTO.  <!-- event-driven -->
4. IF o pedido de conclusão não traz a confirmação explícita THEN the system SHALL responder 422 com o código `CONFIRMACAO_OBRIGATORIA`, sem excluir nenhum arquivo.  <!-- unwanted-behavior -->
5. WHEN o usuário confirma a conclusão THEN the system SHALL excluir do armazenamento os arquivos originais enviados, os textos extraídos das páginas e os trechos de evidência de todos os documentos do processo.  <!-- event-driven -->
6. The system SHALL manter, depois da exclusão, os metadados de cada documento (nome original, tipo, número de páginas, tamanho, hash) marcados `ARQUIVO_EXCLUIDO`, os vínculos atividade-página (só os números), as atividades e todos os documentos gerados com todas as suas versões.  <!-- ubiquitous -->
7. WHEN todos os arquivos do processo foram removidos, conferido de novo na mesma transação da mudança de status, THEN the system SHALL mudar o processo para CONCLUIDO, e SHALL NOT mudá-lo antes disso.  <!-- event-driven -->
8. IF a remoção de algum arquivo falha THEN the system SHALL manter o processo EM_ANDAMENTO, responder com o alerta `EXCLUSAO_PARCIAL` com as contagens de removidos e pendentes, manter excluídos os arquivos que já saíram e permitir repetir o pedido.  <!-- unwanted-behavior -->
9. WHEN a conclusão é repetida THEN the system SHALL tratar como removido o arquivo que já não está no armazenamento, completar só o que falta e, num processo já CONCLUIDO, responder 200 sem alterar nada.  <!-- event-driven -->
10. WHEN uma tentativa de conclusão termina, com sucesso ou com `EXCLUSAO_PARCIAL`, THEN the system SHALL registrar um evento de auditoria com o número de arquivos e de bytes removidos e pendentes, sem nome de arquivo nem conteúdo.  <!-- event-driven -->
11. WHILE o processo tem documento marcado `ARQUIVO_EXCLUIDO`, the system SHALL recusar a geração do Comprovante com 422 e o código `ORIGINAIS_EXCLUIDOS`.  <!-- state-driven -->
12. IF o usuário pede o arquivo ou uma página de um documento marcado `ARQUIVO_EXCLUIDO` THEN the system SHALL responder 410 com o código `ARQUIVO_EXCLUIDO`.  <!-- unwanted-behavior -->
13. WHILE o processo está CONCLUIDO, the system SHALL permitir gerar a Tabela e o Relatório de novo, a partir do arranjo e do rascunho gravados, e baixar toda versão gerada.  <!-- state-driven -->
14. IF a rota genérica de mudança de status pede o alvo CONCLUIDO THEN the system SHALL recusá-la com 409 e o código `CONCLUSAO_EXIGE_EXCLUSAO`, sem alterar o processo.  <!-- unwanted-behavior -->
15. The system SHALL aplicar à conclusão as regras de papel, de acesso (404 fora do acesso) e de versão (409 com `expected_version` desatualizada) da transição de status existente, e só aceitar a conclusão de um processo EM_ANDAMENTO.  <!-- ubiquitous -->

**Independent Test**: Num processo sintético EM_ANDAMENTO com 3 documentos e as três versões PRONTO, concluir com confirmação e ver os 3 arquivos sumirem do armazenamento, o processo CONCLUIDO, os metadados marcados, o Comprovante recusado com `ORIGINAIS_EXCLUIDOS`, a visualização de uma página respondendo 410 e todas as versões geradas ainda baixáveis byte a byte; repetir com um arquivo travado e ver `EXCLUSAO_PARCIAL`, o processo EM_ANDAMENTO e a segunda tentativa concluir.

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
| Input validation & bounds | CMP-09, CMP-13 (PNG acima de 12 megapixels) e REL-07 (texto editado limitado a 20 000 caracteres por seção); DEL-04 (confirmação obrigatória) |
| Failure / partial-failure states | CMP-09, CMP-10, VER-05, VER-08: nenhum arquivo parcial; REL-14 e REL-15 (redação interrompida ou com erro); DEL-08 (exclusão parcial) |
| Idempotency / retry / duplicate handling | VER-04 (segundo pedido igual recusado), REL-13 (segunda redação da mesma seção recusada), CMP-05 (página repetida), nova tentativa após FALHOU; DEL-09 (conclusão repetida) |
| Auth boundaries & rate limits | VER-06 e DEL-15 (404 fora do acesso, papéis da transição existente); um pedido de geração por tipo e processo por vez (VER-04) já limita a carga; rate limit adicional N/A because o uso é autenticado e por processo |
| Concurrency / ordering | ARR-07 (bloqueio otimista do arranjo), VER-04, REL-13; DEL-02 (conclusão com operação em andamento), DEL-07 (conferência na mesma transação) |
| Data lifecycle / expiry | VER-09 (as versões ficam; exclusão de versão antiga N/A because o usuário decidiu manter todas); DEL-05, DEL-06 e DEL-12 (exclusão dos documentos de entrada na conclusão) |
| Observability | VER-07 e DEL-10 (auditoria), logs com identificadores e códigos |
| External-dependency failure | REL-05 (MariTalk indisponível), CMP-10 (original ausente), DEL-08 (armazenamento que não remove) |
| State-transition integrity | VER-04 (GERANDO → PRONTO/FALHOU), VER-08 e REL-14 (reinício); DEL-07 e DEL-14 (CONCLUIDO só pela conclusão com exclusão) |

---

## Edge Cases

- IF uma página original é muito grande (acima de 50 megapixels ao renderizar) THEN the system SHALL anexá-la como página vetorial ou de imagem sem rasterizá-la, e SHALL NOT falhar a geração por causa disso.
- IF o nome do docente ou o título de uma atividade tem caracteres fora do latim básico THEN the system SHALL escrevê-los corretamente no DOCX e no PDF.
- IF o interstício tem menos de uma atividade por grupo THEN the system SHALL omitir os grupos vazios do Comprovante e do Relatório, e mostrá-los com zero na Tabela de Pontuação.
- WHEN duas atividades têm o mesmo título no mesmo item THEN the system SHALL listar as duas, cada uma com as suas páginas.
- IF o arranjo salvo referencia um documento que foi excluído depois THEN the system SHALL tratá-lo como `ORIGINAL_INDISPONIVEL` na geração e marcar a entrada como inválida no arranjo.
- IF o documento de origem é um PNG com mais de 12 megapixels THEN the system SHALL recusar a geração com `IMAGEM_GRANDE_DEMAIS`; o JPEG da mesma dimensão SHALL entrar normalmente (CMP-08 e CMP-13).
- WHEN o processo não tem nenhum documento de entrada e as três versões estão PRONTO THEN the system SHALL concluí-lo sem arquivos a excluir, informando zero arquivos e zero bytes.
- IF um documento é enviado ao processo enquanto a conclusão está em andamento THEN the system SHALL não concluir o processo nesse pedido e responder `EXCLUSAO_PARCIAL`, pois a conferência final (DEL-07) encontra um arquivo que ainda existe.
- WHEN o Comprovante, a Tabela ou o Relatório já gerado é baixado depois da conclusão THEN the system SHALL entregar o arquivo gravado, sem depender de nenhum documento de entrada.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TAB-01 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | Implementing |
| TAB-02 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | Implementing |
| TAB-03 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | In Tasks |
| TAB-04 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | Implementing |
| TAB-05 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | In Tasks |
| TAB-06 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | In Tasks |
| TAB-07 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | Implementing |
| TAB-08 | P1: Tabela de Pontuação em DOCX e PDF | Tasks | In Tasks |
| CMP-01 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-02 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-03 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-04 | P1: Comprovante de Documentos em PDF | Tasks | Implementing |
| CMP-05 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-06 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-07 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-08 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-09 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-10 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-11 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-12 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| CMP-13 | P1: Comprovante de Documentos em PDF | Tasks | In Tasks |
| ARR-01 | P1: Arranjo manual do Comprovante | Tasks | Implementing |
| ARR-02 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-03 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-04 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-05 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-06 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-07 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| ARR-08 | P1: Arranjo manual do Comprovante | Tasks | In Tasks |
| REL-01 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-02 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-03 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-04 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-05 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-06 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-07 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-08 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-09 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-10 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-11 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-12 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-13 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | Implementing |
| REL-14 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| REL-15 | P1: Relatório de Atividades em DOCX e PDF com revisão | Tasks | In Tasks |
| VER-01 | P1: Versões imutáveis e download | Tasks | Implementing |
| VER-02 | P1: Versões imutáveis e download | Tasks | In Tasks |
| VER-03 | P1: Versões imutáveis e download | Tasks | Implementing |
| VER-04 | P1: Versões imutáveis e download | Tasks | Implementing |
| VER-05 | P1: Versões imutáveis e download | Tasks | Implementing |
| VER-06 | P1: Versões imutáveis e download | Tasks | In Tasks |
| VER-07 | P1: Versões imutáveis e download | Tasks | In Tasks |
| VER-08 | P1: Versões imutáveis e download | Tasks | In Tasks |
| VER-09 | P1: Versões imutáveis e download | Tasks | In Tasks |
| UIG-01 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-02 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-03 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-04 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-05 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-06 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-07 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-08 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| UIG-09 | P1: Etapa 5, Documentos gerados, na interface | Tasks | In Tasks |
| DEL-01 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-02 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-03 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | Implementing |
| DEL-04 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-05 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-06 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-07 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-08 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | Implementing |
| DEL-09 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-10 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-11 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-12 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | Implementing |
| DEL-13 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| DEL-14 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | Implementing |
| DEL-15 | P1: Concluir o processo e excluir os documentos de entrada | Tasks | In Tasks |
| ORD-01 | P2: Lembrete da ordem do dossiê | Tasks | In Tasks |
| ORD-02 | P2: Lembrete da ordem do dossiê | Tasks | In Tasks |

**ID format:** `[CATEGORY]-[NUMBER]` (e.g., `AUTH-01`, `CART-03`, `NOTIF-02`)

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 79 total, 79 mapped to tasks, 0 unmapped (tabela de cobertura em `tasks.md`)

**Mapping notes:** the numbering of each requirement follows the order of the acceptance criteria inside its story (TAB-01 is criterion 1 of the Tabela story, CMP-05 is criterion 5 of the Comprovante story, and so on; the "Implicit-Requirement Dimensions" table refers to them by these IDs).

---

## Success Criteria

- [ ] A Tabela gerada para o cenário de aceitação mostra 211 pontos, os subtotais 52, 7, 62, 0, 30, 4 e 56 e as horas 24, 24, 24, 20 (92), no DOCX e no PDF.
- [ ] O Comprovante de um processo sintético tem páginas idênticas às originais, numeração contínua e sumário correto, com pico de memória abaixo de 320 MB em 400 páginas digitalizadas sintéticas.
- [ ] Nenhuma descrição aceita no Relatório contém número, data ou nome que não esteja nos campos da atividade.
- [ ] Uma versão gerada é baixada de novo, byte a byte igual, depois de mudanças no processo.
- [ ] Concluir um processo sintético remove do armazenamento todos os arquivos de entrada (zero arquivos em `uploads/{process_id}`), sem tocar em nenhum arquivo em `generated/`, e o espaço informado na confirmação é igual ao removido.
- [ ] Nenhum dado pessoal real entra em teste, fixture ou commit; os testes usam documentos sintéticos.

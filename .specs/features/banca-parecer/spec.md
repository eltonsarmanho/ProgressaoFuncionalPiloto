# Banca, Parecer, Requerimento e checklist do dossiê Specification

## Problem Statement

Depois da Etapa 5, o docente ainda monta à mão o Requerimento à CPPD e confere sozinho se o dossiê está completo. A banca recebe a portaria de designação, faz a avaliação e redige o Parecer do zero, copiando a pontuação da Tabela. Hoje as Etapas 6 a 9 da navegação aparecem como "em breve" e nada disso tem requisito. A feature fecha o ciclo: registra a portaria da banca (lida do PDF e conferida pela pessoa), gera a minuta do Parecer por texto-modelo, com a conclusão escolhida por uma pessoa, gera o Requerimento pelo modelo oficial da PROGEP e mostra o checklist do dossiê.

## Goals

- [ ] O docente ou a secretaria registra a portaria da banca, enviando o PDF (número, data e membros extraídos com a página de origem e conferidos) ou digitando os dados.
- [ ] A minuta do Parecer sai em DOCX e PDF, com os mesmos totais da última Tabela de Pontuação e a conclusão escolhida pela pessoa. A IA não participa do texto.
- [ ] O Requerimento sai em DOCX e PDF pelo modelo oficial da PROGEP, preenchido com os dados do processo.
- [ ] O checklist mostra, na ordem do arquivo de configuração, cada documento do dossiê com a situação (gerado, registrado, marcado como entregue ou pendente).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Perfil de membro da banca (login, convite, assinatura no sistema) | Decisão do usuário em 2026-11-20: só docente e secretaria usam o sistema; a banca recebe os arquivos por fora |
| Redação do Parecer por IA | Decisão do usuário em 2026-11-20: texto-modelo fixo; a IA nunca decide nem redige o resultado |
| Modelo de Requerimento da FASI (dirigido à direção) | Decisão do usuário em 2026-11-20: só o modelo público da PROGEP. Os arquivos de `Modelos/` não podem ser abertos por agentes |
| Parte "REVISÃO" do modelo da PROGEP | O sistema monta processos de progressão ou promoção, não pedidos de revisão |
| Protocolo no SIPAC, assinatura digital e tramitação | Fora do sistema; o checklist só lembra |
| Verificações de elegibilidade (titulação, mínimo de pontos) | Feature `normativo` |
| Gerar a Portaria da banca | A portaria é ato da unidade; o sistema só a lê |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Escopo | Requerimento, Portaria da banca, minuta do Parecer e checklist do dossiê | Escolha do usuário em 2026-11-20 | y |
| Quem usa | Os perfis que já acessam o processo (dono DOCENTE, SECRETARIA da unidade, ADMIN), com as regras de acesso atuais | Escolha do usuário em 2026-11-20 | y |
| Modelo do Requerimento | Modelo oficial público da PROGEP (`docs/referencias/normas/PROGEP-Modelo-Requerimento-Progressao-Promocao.docx`): cabeçalho MEC, UFPA e PROGEP; título; "Prezado Sr. Presidente da CPPD,"; opção "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO"; parágrafo preenchido; local e data; assinatura; SIAPE; observação da LGPD | Escolha do usuário em 2026-11-20 | y |
| Linha "Belém, ___ de ___ de 202__" do topo do modelo | Sai; fica só a linha de local e data antes de "Nestes termos, pede deferimento." | O modelo tem duas linhas de data; uma só evita data divergente no mesmo papel | y |
| Local e data do Requerimento | Cidade digitada na Etapa 7 (sem cidade: linha em branco "__________"); data = data de abertura do processo, por extenso ("10 de março de 2025") | A data de abertura já existe no processo; a cidade não existe em nenhum cadastro | y |
| "Avaliação de desempenho em anexo, realizada na data de ___" | Data do Parecer da última minuta `PRONTO`; sem Parecer, a linha em branco "___/___/___" | O Parecer da banca é a avaliação de desempenho do processo | y |
| Texto do Parecer | Texto-modelo fixo, com seções determinísticas; a pessoa edita só os campos da Etapa 6 (conclusão, data, local, observações) | Escolha do usuário em 2026-11-20 | y |
| Totais do Parecer | Copiados do instantâneo da última Tabela `PRONTO`; se o total atual difere do da Tabela, a geração é recusada com `TABELA_DESATUALIZADA` | O Parecer e a Tabela entregues à banca não podem divergir (AD-012) | y |
| Conclusão do Parecer | `FAVORAVEL` ou `DESFAVORAVEL`, escolhida pela pessoa, sem valor inicial; o sistema não sugere conclusão pelo total nem pelo mínimo | Regra 1 do projeto e a decisão de 2026-11-18 ("a IA nunca decide o resultado") | y |
| Entrada da Portaria | Envio do PDF ou imagem com extração (número, data, membros) e página de origem, conferida e editável; também dá para digitar sem arquivo | Escolha do usuário em 2026-11-20 | y |
| Uma portaria por processo | Uma portaria ativa; enviar outra substitui a anterior (o arquivo anterior sai do disco, a auditoria guarda o evento) | Uma banca por processo de progressão | y |
| Portaria da banca e as Etapas 2 a 5 | A portaria não aparece na Etapa 2, não gera atividade, não pontua e não entra no Comprovante | É documento da banca, não comprovante de atividade | y |
| Mascaramento | O texto da portaria vai à IA com o mesmo mascaramento da Etapa 2 (CPF, RG, e-mail e telefone mascarados; nomes ficam, porque são o dado a extrair) | Regra de dados do projeto e EXT-07 | y |
| Navegação | Etapa 6 "Banca e Parecer"; Etapa 7 "Requerimento e dossiê"; a navegação passa a ter 7 etapas e deixa de mostrar etapas "em breve" | As Etapas 8 e 9 não têm requisito; o Requerimento cita a data do Parecer | y |
| Ordem do checklist | Requerimento; Portaria da última progressão; Declaração de pagamento de exercícios anteriores; Relatório; Tabela; Comprovante; Currículo Lattes; Portaria da banca; Parecer da banca (no arquivo de configuração versionado) | Ordem atual do `dossier_order.json` com os dois documentos da banca ao fim | y |
| Itens que o sistema não produz | A pessoa marca "Entregue" ou desmarca, sem justificativa (regra 5); a marca fica gravada no processo, com auditoria | O sistema não tem como saber se a portaria da última progressão foi juntada | y |
| Conclusão do processo sem Requerimento ou Parecer | Permitida; a confirmação da conclusão lista, como aviso, os documentos da banca e o Requerimento que nunca foram gerados | Concluir torna o processo somente leitura (regra 8); o aviso evita perder a chance de gerar | y |
| Classe, denominação e nível nos documentos | Exatamente os informados pelo servidor na Etapa 1; o sistema não deduz a classe seguinte, a denominação nem o nível | Decisão do usuário em 2026-11-20: há saltos na carreira e as denominações mudam com o tempo (requisito NMOV-01 do `normativo`) | y |
| Limites | Observações do Parecer até 5 000 caracteres; até 15 membros; nome do membro até 200 caracteres; cidade até 100; número da portaria até 50; arquivo da portaria até 20 MB (o limite atual por arquivo) | Limites da mesma ordem dos campos existentes | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Registrar a portaria da banca ⭐ MVP

**User Story**: Como docente ou secretaria, quero enviar a portaria que designa a banca e conferir o número, a data e os membros que o sistema leu, para usar esses dados no Parecer sem redigitar.

**Why P1**: O Parecer não tem membros nem portaria sem este registro.

**Acceptance Criteria**:

1. WHEN a pessoa envia na Etapa 6 um PDF, PNG ou JPEG da portaria da banca THEN the system SHALL guardar o arquivo no processo como "Portaria da banca" e colocar a leitura na fila de processamento existente.  <!-- event-driven -->
2. WHEN a leitura da portaria termina THEN the system SHALL preencher o número da portaria, a data da portaria e a lista de membros (nome e função: `PRESIDENTE`, `MEMBRO` ou `SUPLENTE`), cada valor com a página de origem.  <!-- event-driven -->
3. IF um valor extraído não aparece no texto da página citada THEN the system SHALL deixá-lo vazio e mostrar o aviso `VALOR_SEM_ORIGEM` no campo.  <!-- unwanted-behavior -->
4. The system SHALL enviar à IA só o texto da portaria mascarado pela regra da Etapa 2, nunca o arquivo nem o texto sem máscara.  <!-- ubiquitous -->
5. WHEN a pessoa edita o número, a data ou a lista de membros e salva THEN the system SHALL gravar os valores informados, marcar cada valor editado como "informado pela pessoa" e registrar o evento na auditoria, sem pedir justificativa.  <!-- event-driven -->
6. WHEN a pessoa preenche os dados da portaria sem enviar arquivo THEN the system SHALL aceitar o registro com os mesmos campos e a origem "informado pela pessoa".  <!-- event-driven -->
7. IF a leitura falha (erro da IA, tempo esgotado ou texto ilegível) THEN the system SHALL mostrar a situação `FALHOU` com o motivo, manter os campos editáveis e oferecer "Ler de novo".  <!-- unwanted-behavior -->
8. WHEN a pessoa envia outra portaria e confirma a substituição THEN the system SHALL apagar o arquivo anterior do disco, ler o novo e registrar a substituição na auditoria.  <!-- event-driven -->
9. The system SHALL manter a portaria da banca fora da Etapa 2, das atividades, da pontuação e do Comprovante.  <!-- ubiquitous -->
10. IF o arquivo passa de 20 MB ou não é PDF, PNG ou JPEG THEN the system SHALL recusar o envio com 422 e a mensagem do limite.  <!-- unwanted-behavior -->
11. IF a lista tem mais de 15 membros, um nome vazio ou com mais de 200 caracteres, ou o número da portaria passa de 50 caracteres THEN the system SHALL recusar a gravação com 422 indicando o campo.  <!-- unwanted-behavior -->
12. IF duas pessoas gravam os dados da portaria a partir da mesma versão THEN the system SHALL aceitar a primeira e responder 409 à segunda.  <!-- unwanted-behavior -->

**Independent Test**: Enviar uma portaria sintética com três membros (provedor de IA falso), ver número, data e membros com a página de origem, corrigir um nome e ver a marca "informado pela pessoa"; com a IA falhando, digitar os dados à mão.

---

### P1: Gerar a minuta do Parecer ⭐ MVP

**User Story**: Como docente ou secretaria, quero gerar a minuta do Parecer com a pontuação da Tabela, os dados da portaria e a conclusão que a banca decidiu, para entregá-la à banca pronta para assinar.

**Why P1**: É o documento que a banca precisa produzir e hoje redige do zero.

**Acceptance Criteria**:

1. The system SHALL oferecer na Etapa 6 os campos da minuta: conclusão (`FAVORAVEL` ou `DESFAVORAVEL`, sem valor inicial), data do Parecer, local e observações da banca.  <!-- ubiquitous -->
2. WHEN a pessoa pede "Gerar Parecer" com a conclusão escolhida, ao menos um membro registrado e uma Tabela `PRONTO` THEN the system SHALL gerar uma versão do Parecer em DOCX e em PDF, imutável e numerada como os demais documentos gerados.  <!-- event-driven -->
3. The system SHALL montar o Parecer, nesta ordem, com: cabeçalho (UFPA e unidade do processo); título "PARECER"; identificação (docente, SIAPE, unidade, modalidade, classe, denominação e nível atuais e pretendidos, como informados na Etapa 1); portaria da banca (número e data); interstício; documentos analisados (Tabela, Relatório e Comprovante com o número da versão usada); pontos por grupo (I a VIII) e Total geral; mínimo de referência; conclusão; observações; local e data; uma linha de assinatura por membro, com nome e função.  <!-- ubiquitous -->
4. The system SHALL copiar os pontos por grupo, o Total geral e o mínimo de referência do instantâneo da última Tabela `PRONTO` do processo.  <!-- ubiquitous -->
5. WHEN a conclusão é `FAVORAVEL` THEN the system SHALL escrever "A banca manifesta-se FAVORÁVEL à <progressão|promoção> de <docente>, do nível <n> da classe <X> (<denominação atual>) para o nível <m> da classe <Y> (<denominação pretendida>), referente ao interstício de <dd/mm/aaaa> a <dd/mm/aaaa>."; WHEN é `DESFAVORAVEL` THEN the system SHALL escrever a mesma frase com "DESFAVORÁVEL".  <!-- event-driven -->
6. WHERE o mínimo de referência é "não definido" the system SHALL escrever no Parecer "Mínimo de referência: não definido pela norma aplicável", sem número.  <!-- optional-feature -->
7. IF falta a conclusão THEN the system SHALL recusar a geração com 422 `CONCLUSAO_AUSENTE`.  <!-- unwanted-behavior -->
8. IF não há membro registrado THEN the system SHALL recusar a geração com 422 `BANCA_SEM_MEMBROS`.  <!-- unwanted-behavior -->
9. IF não há Tabela `PRONTO` THEN the system SHALL recusar a geração com 422 `TABELA_AUSENTE`.  <!-- unwanted-behavior -->
10. IF o Total geral calculado agora difere do Total geral da última Tabela `PRONTO` THEN the system SHALL recusar a geração com 422 `TABELA_DESATUALIZADA` e a mensagem "A pontuação mudou depois da última Tabela; gere a Tabela de novo".  <!-- unwanted-behavior -->
11. The system SHALL gerar o texto do Parecer sem chamar a IA.  <!-- ubiquitous -->
12. The system SHALL nunca preencher nem sugerir a conclusão a partir do total, do mínimo ou de qualquer outro dado.  <!-- ubiquitous -->
13. IF as observações passam de 5 000 caracteres ou o local passa de 100 THEN the system SHALL recusar a gravação com 422 indicando o campo.  <!-- unwanted-behavior -->
14. WHEN a pessoa pede o Parecer de novo THEN the system SHALL gerar a versão seguinte e manter as anteriores no histórico e no disco.  <!-- event-driven -->

**Independent Test**: Num processo sintético com Tabela `PRONTO`, portaria com três membros e conclusão `FAVORAVEL`, gerar o Parecer e conferir no DOCX e no PDF as seções na ordem, o Total igual ao da Tabela, a frase da conclusão e três linhas de assinatura; mudar uma atividade validada e ver a recusa `TABELA_DESATUALIZADA`.

---

### P1: Gerar o Requerimento pelo modelo da PROGEP ⭐ MVP

**User Story**: Como docente, quero o Requerimento à CPPD preenchido com os dados do processo, para não redigitar nome, SIAPE, classes, níveis e interstício.

**Why P1**: É o primeiro documento do dossiê e o único que todo processo exige.

**Acceptance Criteria**:

1. WHEN a pessoa pede "Gerar Requerimento" na Etapa 7 THEN the system SHALL gerar uma versão do Requerimento em DOCX e em PDF, imutável e numerada como os demais documentos gerados.  <!-- event-driven -->
2. The system SHALL montar o Requerimento com o cabeçalho "MINISTÉRIO DA EDUCAÇÃO", "UNIVERSIDADE FEDERAL DO PARÁ" e "PRÓ-REITORIA DE DESENVOLVIMENTO E GESTÃO DE PESSOAL", o título "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)", "Prezado Sr. Presidente da CPPD," e a opção "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO".  <!-- ubiquitous -->
3. The system SHALL escrever o parágrafo do pedido com o nome do docente, a matrícula SIAPE, a carreira marcada ("(X) Magistério Superior"), a unidade de lotação, "progressão" ou "promoção" conforme a modalidade, o nível, a classe e a denominação atuais e pretendidos, como informados na Etapa 1, e o interstício no formato dd/mm/aaaa a dd/mm/aaaa.  <!-- ubiquitous -->
4. WHERE o processo tem um Parecer `PRONTO` the system SHALL escrever no Requerimento a data do último Parecer como data da avaliação de desempenho; sem Parecer, a linha em branco "___/___/___".  <!-- optional-feature -->
5. The system SHALL terminar o Requerimento com "<cidade>, <data de abertura por extenso>.", "Nestes termos, pede deferimento.", a linha de assinatura, "Assinatura do (a) requerente", "Matrícula SIAPE: <siape>" e a observação da LGPD do modelo.  <!-- ubiquitous -->
6. WHERE a cidade não foi informada the system SHALL escrever "__________" no lugar da cidade.  <!-- optional-feature -->
7. The system SHALL não incluir a parte "REVISÃO" nem as instruções de revisão do modelo.  <!-- ubiquitous -->
8. The system SHALL gerar o texto do Requerimento sem chamar a IA.  <!-- ubiquitous -->

**Independent Test**: Num processo sintético de promoção do nível 4 da classe B para o nível 1 da classe C, gerar o Requerimento e conferir no DOCX e no PDF o cabeçalho, o parágrafo preenchido, a data de abertura por extenso, a linha de data da avaliação em branco e, depois de gerar um Parecer, a data do Parecer.

---

### P2: Checklist do dossiê

**User Story**: Como docente, quero ver, na ordem de entrega, o que já está pronto e o que falta no dossiê, para protocolar sem esquecer nada.

**Why P2**: O dossiê pode ser montado sem o checklist; ele evita esquecimento.

**Acceptance Criteria**:

1. The system SHALL mostrar na Etapa 7 a lista de documentos do dossiê na ordem do arquivo de configuração versionado: Requerimento; Portaria da última progressão; Declaração de pagamento de exercícios anteriores; Relatório; Tabela; Comprovante; Currículo Lattes; Portaria da banca; Parecer da banca.  <!-- ubiquitous -->
2. WHEN um documento gerado pelo sistema tem versão `PRONTO` THEN the system SHALL mostrar o item como "Gerado", com o número da última versão e o link de download.  <!-- event-driven -->
3. WHEN a portaria da banca está registrada com ao menos um membro THEN the system SHALL mostrar o item "Portaria da banca" como "Registrada".  <!-- event-driven -->
4. WHEN a pessoa marca ou desmarca "Entregue" num item que o sistema não produz THEN the system SHALL gravar a marca no processo e registrar o evento na auditoria, sem pedir justificativa.  <!-- event-driven -->
5. The system SHALL mostrar como "Pendente" todo item sem versão `PRONTO`, sem registro e sem marca.  <!-- ubiquitous -->
6. WHERE a última Tabela foi gerada com outra versão da tabela de pontuação the system SHALL mostrar no item "Tabela" o aviso existente "Gerada com outra versão da tabela de pontuação; gere de novo".  <!-- optional-feature -->
7. WHEN a pessoa abre a confirmação de concluir o processo THEN the system SHALL listar como aviso o Requerimento, a Portaria da banca e o Parecer que estão pendentes, sem impedir a conclusão.  <!-- event-driven -->

**Independent Test**: Num processo sintético só com Tabela, Relatório e Comprovante, abrir a Etapa 7 e ver três itens "Gerado" e seis "Pendente"; marcar "Currículo Lattes" como "Entregue", recarregar e ver a marca.

---

### P1: Etapas 6 e 7 na navegação ⭐ MVP

**User Story**: Como docente, quero chegar à banca e ao dossiê pelas etapas do processo, como nas etapas anteriores.

**Why P1**: Sem a navegação, as telas novas não são alcançáveis.

**Acceptance Criteria**:

1. The system SHALL mostrar na navegação do processo sete etapas, com a Etapa 6 "Banca e Parecer" e a Etapa 7 "Requerimento e dossiê", e nenhuma etapa "em breve".  <!-- ubiquitous -->
2. WHILE o processo está `ARQUIVADO` ou `CONCLUIDO` the system SHALL mostrar as Etapas 6 e 7 só para leitura e recusar envio de portaria, gravação de dados e geração com 409, como nas etapas anteriores.  <!-- state-driven -->
3. IF a pessoa não tem acesso ao processo THEN the system SHALL responder 404 a toda rota da portaria, do Parecer, do Requerimento e do checklist.  <!-- unwanted-behavior -->

**Independent Test**: Abrir um processo sintético e navegar até as Etapas 6 e 7; arquivar o processo e ver os botões desabilitados e o 409 da API.

---

## Edge Cases

- IF a portaria lida não traz nenhum membro THEN the system SHALL deixar a lista vazia, mostrar o aviso `MEMBROS_NAO_ENCONTRADOS` e permitir digitar os membros.
- IF a mesma pessoa aparece duas vezes na lista de membros (mesmo nome, ignorando maiúsculas e acentos) THEN the system SHALL recusar a gravação com 422 `MEMBRO_REPETIDO`.
- WHEN o processo é concluído THEN the system SHALL apagar o arquivo da portaria da banca junto com os demais arquivos de entrada e manter número, data e membros.
- WHEN o processo é excluído THEN the system SHALL apagar a portaria da banca, os dados dela, as marcas do checklist, os Pareceres e os Requerimentos com o restante do processo.
- IF um pedido de Parecer ou de Requerimento chega enquanto outro do mesmo tipo está `GERANDO` THEN the system SHALL recusá-lo com o código já usado pelos demais documentos gerados.
- IF o backend reinicia durante a geração do Parecer ou do Requerimento THEN the system SHALL marcar a versão como `FALHOU` com `INTERROMPIDA` (AD-012).

---

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | PORT-10, PORT-11, PAR-13, MEMBRO_REPETIDO; tipos e tamanho do arquivo |
| Failure / partial-failure states | PORT-07 (leitura que falha), versão `FALHOU`/`INTERROMPIDA` (AD-012), nenhum arquivo parcial |
| Idempotency / retry / duplicate handling | PORT-08 (substituição explícita), "Ler de novo", uma geração por tipo por vez |
| Auth boundaries & rate limits | BNAV-03 (404 fora do acesso), perfis atuais; rate limit N/A because o uso é autenticado e por processo, e a geração já é uma por vez |
| Concurrency / ordering | PORT-12 (versão otimista), uma geração por tipo por vez |
| Data lifecycle / expiry | Conclusão apaga o arquivo da portaria e mantém os dados; exclusão do processo apaga tudo; versões geradas ficam enquanto o processo existir (AD-012) |
| Observability | Auditoria da portaria, das edições, da substituição e das marcas do checklist; geração com o registro existente |
| External-dependency failure | PORT-07: a IA falha e a pessoa digita; o Parecer e o Requerimento não dependem da IA (PAR-11, REQ-08) |
| State-transition integrity | BNAV-02 (somente leitura em `ARQUIVADO` e `CONCLUIDO`); DOS-07 (aviso na conclusão) |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PORT-01 | P1: Portaria da banca | Design | Pending |
| PORT-02 | P1: Portaria da banca | Implementing | Implementing |
| PORT-03 | P1: Portaria da banca | Design | Pending |
| PORT-04 | P1: Portaria da banca | Design | Pending |
| PORT-05 | P1: Portaria da banca | Implementing | Implementing |
| PORT-06 | P1: Portaria da banca | Design | Pending |
| PORT-07 | P1: Portaria da banca | Implementing | Implementing |
| PORT-08 | P1: Portaria da banca | Design | Pending |
| PORT-09 | P1: Portaria da banca | Design | Pending |
| PORT-10 | P1: Portaria da banca | Design | Pending |
| PORT-11 | P1: Portaria da banca | Design | Pending |
| PORT-12 | P1: Portaria da banca | Design | Pending |
| PAR-01 | P1: Minuta do Parecer | Implementing | Implementing |
| PAR-02 | P1: Minuta do Parecer | Design | Pending |
| PAR-03 | P1: Minuta do Parecer | Implementing | Implementing |
| PAR-04 | P1: Minuta do Parecer | Design | Pending |
| PAR-05 | P1: Minuta do Parecer | Design | Pending |
| PAR-06 | P1: Minuta do Parecer | Design | Pending |
| PAR-07 | P1: Minuta do Parecer | Design | Pending |
| PAR-08 | P1: Minuta do Parecer | Design | Pending |
| PAR-09 | P1: Minuta do Parecer | Design | Pending |
| PAR-10 | P1: Minuta do Parecer | Design | Pending |
| PAR-11 | P1: Minuta do Parecer | Design | Pending |
| PAR-12 | P1: Minuta do Parecer | Implementing | Implementing |
| PAR-13 | P1: Minuta do Parecer | Design | Pending |
| PAR-14 | P1: Minuta do Parecer | Design | Pending |
| REQ-01 | P1: Requerimento | Design | Pending |
| REQ-02 | P1: Requerimento | Design | Pending |
| REQ-03 | P1: Requerimento | Design | Pending |
| REQ-04 | P1: Requerimento | Design | Pending |
| REQ-05 | P1: Requerimento | Implementing | Implementing |
| REQ-06 | P1: Requerimento | Design | Pending |
| REQ-07 | P1: Requerimento | Design | Pending |
| REQ-08 | P1: Requerimento | Design | Pending |
| DOS-01 | P2: Checklist do dossiê | Design | Pending |
| DOS-02 | P2: Checklist do dossiê | Design | Pending |
| DOS-03 | P2: Checklist do dossiê | Design | Pending |
| DOS-04 | P2: Checklist do dossiê | Design | Pending |
| DOS-05 | P2: Checklist do dossiê | Design | Pending |
| DOS-06 | P2: Checklist do dossiê | Design | Pending |
| DOS-07 | P2: Checklist do dossiê | Design | Pending |
| BNAV-01 | P1: Etapas 6 e 7 | Design | Pending |
| BNAV-02 | P1: Etapas 6 e 7 | Design | Pending |
| BNAV-03 | P1: Etapas 6 e 7 | Design | Pending |

**Coverage:** 44 total, 0 mapped to tasks, 44 unmapped (Design pendente)

---

## Success Criteria

- [ ] Num processo sintético, a pessoa vai da portaria ao Parecer e ao Requerimento sem redigitar nome, SIAPE, classes, níveis, interstício, totais nem membros.
- [ ] O Total geral do Parecer é sempre igual ao da última Tabela entregue (zero divergências nos testes).
- [ ] Nenhuma chamada à IA na geração do Parecer e do Requerimento; a conclusão nunca aparece preenchida sem ação da pessoa.

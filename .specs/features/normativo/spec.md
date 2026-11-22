# Base de normas e regras de elegibilidade (normativo) Specification

## Problem Statement

As regras institucionais do sistema (estruturas de carreira, interstício por classe, tabela de pontuação, mínimos de pontos) citam a norma só como texto solto (`norm_reference`). O docente vê um alerta e não consegue abrir a norma que o fundamenta. As fontes estão listadas num arquivo de documentação (`docs/referencias/normas/FONTES.md`) que ninguém vê na tela. Nenhuma verificação confere a titulação exigida para a classe pretendida. A feature cria a base de normas, liga cada regra e cada alerta a uma norma cadastrada e acrescenta a verificação de titulação.

## Goals

- [ ] O ADMIN cadastra, edita e arquiva normas (título, tipo, órgão, datas, vigência, fonte e arquivo), e a base começa com as fontes públicas já coletadas.
- [ ] Todo alerta de verificação mostra a norma que o fundamenta, com o link para a fonte ou o arquivo, quando a regra está ligada a uma norma cadastrada.
- [ ] O processo de promoção cuja classe pretendida exige doutorado mostra o alerta `TITULACAO_INSUFICIENTE` quando a titulação do docente é menor, citando a norma.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| IA que pesquisa ou responde sobre normas | Decisão do usuário em 2026-11-20: base de normas e regras, sem IA |
| Mínimo de pontos para as classes da estrutura nova (Lei 15.141/2025) | Decisão do usuário em 2026-11-20: continua "não definido" até existir norma |
| Memorial para Titular, declaração de não ajuizamento e avaliação de desempenho | O usuário escolheu só a verificação de titulação em 2026-11-20 |
| Tela para editar estruturas de carreira e regras | Fica para a feature `implantacao` (administração); as regras continuam editadas como dados versionados |
| Bloquear o processo por elegibilidade | AD-002: verificadores só alertam, nunca bloqueiam nem corrigem |
| Busca no texto dos PDFs das normas | Não pedida |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Natureza da feature | Base versionada de normas e regras de elegibilidade ligadas a elas; alertas citam a norma; sem IA | Escolha do usuário em 2026-11-20 | y |
| Verificações novas | Só a titulação exigida pela classe pretendida | Escolha do usuário em 2026-11-20 | y |
| Mínimo da estrutura nova | Continua `NAO_DEFINIDO` | Escolha do usuário em 2026-11-20 | y |
| Campos da norma | Código único (ex.: `LEI-12772-2012`), título, tipo (`LEI`, `RESOLUCAO`, `INSTRUCAO_NORMATIVA`, `MANUAL`, `TABELA`, `OUTRO`), órgão emissor, data de publicação, vigência (início e fim opcionais), URL da fonte, arquivo PDF opcional e observação | Os campos que `FONTES.md` já registra para cada fonte | y |
| Normas semeadas | Lei 12.772/2012 (texto compilado), Res. 4.644/2015-CONSEPE, Res. 4.074/2010-CONSEPE, IN 1/2026-IFCH, Manual do Servidor da PROGEP (progressão e promoção), tabela de correlação da PROGEP (jan/2025) e Tabela oficial de pontuação da UFPA; cada uma com a URL de `FONTES.md` (a tabela oficial sem URL) e sem arquivo anexado | As fontes já coletadas; a planilha da tabela oficial está em `Modelos/` e não sai de lá | y |
| Excluir norma | Não existe; a norma é arquivada e continua aparecendo nas regras e nos alertas, com "(arquivada)" | Uma regra ligada nunca pode perder a fonte (AD-002) | y |
| Ligação das regras | Cada estrutura de carreira, versão de tabela de pontuação e regra de titulação guarda o código da norma, além do texto atual de `norm_reference` (artigo e parágrafo) | O texto continua dizendo o artigo; o código aponta a norma; nada se perde dos dados atuais | y |
| Regra de titulação semeada | Na estrutura da Lei 12.772 com a redação da Lei 15.141/2025, as classes C (Associado) e D (Titular) exigem doutorado, com a norma "Manual do Servidor da PROGEP" (texto de 12/11/2026). A estrutura da Res. 4.644/2015 fica sem regra de titulação | É a única fonte lida que fixa titulação por classe; regra sem fonte não é criada (AD-002) | y |
| Quando a titulação é conferida | Só quando a classe pretendida difere da atual (promoção); a progressão dentro da mesma classe não é conferida | A exigência é de acesso à classe | y |
| Ordem das titulações | `GRADUACAO` < `ESPECIALIZACAO` < `MESTRADO` < `DOUTORADO` | Ordem dos valores já cadastrados | y |
| Quem vê as normas | Toda pessoa autenticada lê a lista e abre fonte e arquivo; só o ADMIN cadastra, edita, anexa e arquiva | As normas são públicas; a manutenção é administrativa | y |
| Arquivo da norma | PDF de até 20 MB, guardado no volume do servidor; trocar o arquivo substitui o anterior, com auditoria | Mesmo limite por arquivo do envio de documentos | y |
| Origem e destino do processo | O servidor informa a classe, a denominação e o nível atuais e pretendidos; o sistema não deduz a classe seguinte, a denominação nem o nível. O movimento fora da sequência usual (salto) recebe `MODALIDADE_INCOMPATIVEL` como `ALERTA`, não mais como `ERRO` | Decisão do usuário em 2026-11-20: as denominações mudam com o tempo e a carreira tem saltos (hoje A Assistente, B Adjunto, C Associado, D Titular) | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Base de normas ⭐ MVP

**User Story**: Como ADMIN, quero cadastrar as normas que fundamentam as regras do sistema, com a fonte e o arquivo, para que toda regra aponte uma norma conferível.

**Why P1**: Sem a base, não há norma para ligar às regras nem para mostrar nos alertas.

**Acceptance Criteria**:

1. WHEN o ADMIN cadastra uma norma com código, título, tipo, órgão emissor e data de publicação THEN the system SHALL gravá-la com situação ativa e registrar o evento na auditoria.  <!-- event-driven -->
2. IF o código já existe, ou falta código, título, tipo, órgão ou data de publicação THEN the system SHALL recusar com 422 indicando o campo.  <!-- unwanted-behavior -->
3. IF o fim da vigência é anterior ao início THEN the system SHALL recusar com 422 no campo do fim da vigência.  <!-- unwanted-behavior -->
4. IF a URL da fonte não começa com `https://` ou `http://` THEN the system SHALL recusar com 422 no campo da URL.  <!-- unwanted-behavior -->
5. WHEN o ADMIN anexa um PDF de até 20 MB a uma norma THEN the system SHALL guardar o arquivo, substituir o anterior se houver e registrar o evento na auditoria.  <!-- event-driven -->
6. IF o arquivo anexado não é PDF ou passa de 20 MB THEN the system SHALL recusar com 422 e a mensagem do limite.  <!-- unwanted-behavior -->
7. WHEN o ADMIN edita os campos de uma norma THEN the system SHALL gravar a mudança, sem alterar o código, e registrar os valores anteriores na auditoria.  <!-- event-driven -->
8. WHEN o ADMIN arquiva uma norma THEN the system SHALL marcá-la como arquivada, manter as ligações com as regras e mostrá-la com "(arquivada)" onde for citada.  <!-- event-driven -->
9. IF uma pessoa sem o perfil ADMIN tenta cadastrar, editar, anexar ou arquivar uma norma THEN the system SHALL responder 403.  <!-- unwanted-behavior -->
10. IF duas edições da mesma norma partem da mesma versão THEN the system SHALL aceitar a primeira e responder 409 à segunda.  <!-- unwanted-behavior -->
11. The system SHALL semear, quando o código ainda não existe, as normas Lei 12.772/2012, Res. 4.644/2015-CONSEPE, Res. 4.074/2010-CONSEPE, IN 1/2026-IFCH, Manual do Servidor da PROGEP, tabela de correlação da PROGEP e Tabela oficial de pontuação da UFPA, com a URL registrada em `FONTES.md`.  <!-- ubiquitous -->
12. The system SHALL não apagar nem alterar, na semeadura, uma norma que já existe com o mesmo código.  <!-- ubiquitous -->

**Independent Test**: Como ADMIN, cadastrar uma norma sintética, anexar um PDF sintético, editar o título, arquivar e ver "(arquivada)"; como DOCENTE, receber 403 ao tentar cadastrar.

---

### P1: Regras e alertas ligados à norma ⭐ MVP

**User Story**: Como docente, quero abrir a norma citada em cada alerta, para conferir de onde vem a regra.

**Why P1**: É o motivo da base: tornar cada regra conferível.

**Acceptance Criteria**:

1. The system SHALL ligar a um código de norma cadastrada cada estrutura de carreira, cada versão de tabela de pontuação e cada regra de titulação, mantendo o texto de `norm_reference` com o artigo.  <!-- ubiquitous -->
2. The system SHALL ligar a estrutura da Res. 4.644/2015 a `RES-4644-2015-CONSEPE`, a estrutura da Lei 15.141/2025 a `LEI-12772-2012` e as versões da tabela oficial de pontuação a `TABELA-OFICIAL-UFPA`.  <!-- ubiquitous -->
3. WHEN um alerta de verificação vem de uma regra ligada a uma norma THEN the system SHALL mostrar junto do alerta o título da norma, o texto de `norm_reference` e o link "Ver norma" para a URL da fonte ou para o arquivo anexado.  <!-- event-driven -->
4. WHERE a norma tem arquivo anexado the system SHALL apontar o link "Ver norma" para o arquivo; sem arquivo, para a URL; sem nenhum dos dois, mostrar só o título.  <!-- optional-feature -->
5. IF a regra não está ligada a nenhuma norma cadastrada THEN the system SHALL mostrar só o texto de `norm_reference`, como hoje.  <!-- unwanted-behavior -->
6. The system SHALL incluir no alerta da API o código e o título da norma, além do texto de `norm_reference`.  <!-- ubiquitous -->

**Independent Test**: Num processo sintético com interstício menor que o exigido, ver o alerta da Etapa 1 com "Lei 12.772/2012" e o link "Ver norma"; num alerta de regra sem norma ligada (dado sintético), ver só o texto.

---

### P1: Titulação exigida pela classe pretendida ⭐ MVP

**User Story**: Como docente ou secretaria, quero ser avisado quando a classe pretendida exige uma titulação que o docente não tem cadastrada, antes de montar o processo.

**Why P1**: É a verificação de elegibilidade escolhida pelo usuário.

**Acceptance Criteria**:

1. WHEN a verificação do processo roda e a classe pretendida difere da atual, a estrutura de carreira aplicável tem regra de titulação para a classe pretendida e a titulação do docente é menor que a exigida THEN the system SHALL emitir o alerta `TITULACAO_INSUFICIENTE` com severidade `ALERTA`.  <!-- event-driven -->
2. The system SHALL escrever no alerta "A classe <classe pretendida> (<denominação pretendida>) exige <titulação exigida>; a titulação cadastrada do docente é <titulação>.", com a norma da regra.  <!-- ubiquitous -->
3. WHEN a titulação do docente é igual ou maior que a exigida THEN the system SHALL não emitir `TITULACAO_INSUFICIENTE`.  <!-- event-driven -->
4. WHEN a classe pretendida é igual à atual (progressão dentro da classe) THEN the system SHALL não conferir a titulação.  <!-- event-driven -->
5. WHERE a estrutura de carreira aplicável não tem regra de titulação para a classe pretendida the system SHALL não emitir `TITULACAO_INSUFICIENTE`.  <!-- optional-feature -->
6. The system SHALL semear na estrutura da Lei 12.772 com a redação da Lei 15.141/2025 a exigência de doutorado para as classes C e D, ligada à norma `MANUAL-PROGEP-PROGRESSAO`.  <!-- ubiquitous -->
7. The system SHALL nunca bloquear a criação, a edição nem o andamento do processo por `TITULACAO_INSUFICIENTE`.  <!-- ubiquitous -->
8. WHEN a titulação do docente é corrigida no cadastro THEN the system SHALL recalcular a verificação do processo na próxima leitura e deixar de mostrar o alerta que não se aplica mais.  <!-- event-driven -->

**Independent Test**: Docente sintético com mestrado, promoção da classe B para a C na estrutura nova: alerta `TITULACAO_INSUFICIENTE` com o Manual da PROGEP; trocar para doutorado: o alerta some; progressão de C1 para C2 com mestrado: nenhum alerta.

---

### P1: Origem e destino informados pelo servidor ⭐ MVP

**User Story**: Como servidor, quero informar de onde e para onde vou (classe, denominação e nível), porque a carreira tem saltos e as denominações mudam com o tempo.

**Why P1**: Hoje um salto legítimo aparece como `ERRO`, e a denominação só vale se coincidir com a estrutura cadastrada.

**Acceptance Criteria**:

1. The system SHALL usar a classe, a denominação e o nível atuais e pretendidos exatamente como o servidor os informou na Etapa 1, nas verificações, nas telas e nos documentos gerados, sem deduzir a classe seguinte, a denominação nem o nível.  <!-- ubiquitous -->
2. WHEN a promoção informada não vai do último nível da classe atual ao primeiro nível da classe imediatamente seguinte THEN the system SHALL emitir `MODALIDADE_INCOMPATIVEL` com severidade `ALERTA` e o texto "A promoção informada não segue a sequência usual (último nível da classe atual para o primeiro nível da classe seguinte); confira a norma que fundamenta o salto.".  <!-- event-driven -->
3. WHEN a progressão informada não fica na mesma classe avançando exatamente um nível THEN the system SHALL emitir `MODALIDADE_INCOMPATIVEL` com severidade `ALERTA` e o texto "A progressão informada não segue a sequência usual (um nível acima, na mesma classe); confira a norma que fundamenta o salto.".  <!-- event-driven -->
4. The system SHALL nunca bloquear nem alterar o processo por `MODALIDADE_INCOMPATIVEL` ou `DENOMINACAO_DIVERGENTE`.  <!-- ubiquitous -->
5. WHEN o ADMIN altera as denominações de uma estrutura de carreira (numa versão que nenhum processo usa, por CARR-08, ou numa versão nova) THEN the system SHALL usar as novas denominações em `DENOMINACAO_DIVERGENTE` na verificação seguinte, que lê as denominações da versão como estão gravadas quando roda, sem mudar a denominação informada nos processos nem os documentos já gerados.  <!-- event-driven -->

**Independent Test**: Promoção sintética de A1 para C1 na estrutura nova: `MODALIDADE_INCOMPATIVEL` como `ALERTA`, com o texto do salto, e o processo segue para as próximas etapas; promoção de B4 para C1: nenhum alerta de modalidade; o ADMIN troca "Associado" por outra denominação sintética na classe C de uma versão que nenhum processo usa (CARR-08) e a verificação de um processo sintético que informou "Associado" nessa versão passa a mostrar `DENOMINACAO_DIVERGENTE`, com a denominação informada intacta.

---

### P2: Lista de normas para todos

**User Story**: Como docente, quero ver as normas que o sistema usa, com a vigência e o link, para entender as regras da progressão.

**Why P2**: Os alertas já levam à norma; a lista é consulta adicional.

**Acceptance Criteria**:

1. The system SHALL mostrar a toda pessoa autenticada a página "Normas", com título, tipo, órgão, data de publicação, vigência, link para a fonte ou o arquivo e as regras ligadas a cada norma (estrutura de carreira, tabela de pontuação, titulação).  <!-- ubiquitous -->
2. The system SHALL esconder da lista padrão as normas arquivadas e mostrá-las com o filtro "Mostrar arquivadas".  <!-- ubiquitous -->
3. WHERE a pessoa tem o perfil ADMIN the system SHALL mostrar na página os botões de cadastrar, editar, anexar arquivo e arquivar.  <!-- optional-feature -->

**Independent Test**: Como DOCENTE, abrir "Normas" e ver as sete normas semeadas sem botões de edição; como ADMIN, ver os botões.

---

### P2: Mínimo não definido com a norma

**User Story**: Como docente, quero entender por que o mínimo de pontos aparece como "não definido" na estrutura nova.

**Why P2**: O valor não muda; só a explicação fica conferível.

**Acceptance Criteria**:

1. WHILE a estrutura de carreira aplicável é a da Lei 15.141/2025 the system SHALL continuar com o mínimo de referência `NAO_DEFINIDO`, sem número.  <!-- state-driven -->
2. WHERE o mínimo é `NAO_DEFINIDO` the system SHALL mostrar na Etapa 4 "Mínimo não definido: a Res. 4.644/2015, art. 12, fixa mínimos só para as classes da estrutura antiga", com o link "Ver norma" para `RES-4644-2015-CONSEPE`.  <!-- optional-feature -->

**Independent Test**: Num processo sintético na estrutura nova, abrir a Etapa 4 e ver o texto e o link; na estrutura antiga, ver o mínimo numérico como hoje.

---

## Edge Cases

- IF o código de norma ligado a uma regra não existe na base (dado antigo ou erro de semeadura) THEN the system SHALL tratar a regra como sem norma (NLINK-05) e registrar um aviso no log do backend com o código.
- IF a titulação do docente não está cadastrada THEN the system SHALL não emitir `TITULACAO_INSUFICIENTE` (o cadastro do docente já exige a titulação).
- WHEN a semeadura roda numa base que já tem as sete normas THEN the system SHALL não criar duplicata nem auditoria nova.
- WHEN o processo cruza 01/01/2025 e já recebe `REQUER_ANALISE_NORMATIVA` THEN the system SHALL conferir a titulação pela estrutura aplicável ao fim do interstício, a mesma regra que escolhe a estrutura hoje.

---

## Implicit-Requirement Dimensions

| Dimensão | Tratamento |
| -------- | ---------- |
| Input validation & bounds | NBASE-02, NBASE-03, NBASE-04, NBASE-06 |
| Failure / partial-failure states | Arquivo gravado só depois de validado; NLINK-05 e o código inexistente (Edge Cases) |
| Idempotency / retry / duplicate handling | NBASE-11 e NBASE-12 (semeadura idempotente); código único (NBASE-02) |
| Auth boundaries & rate limits | NBASE-09 (403 fora do ADMIN); leitura para toda pessoa autenticada (NLIST-01); rate limit N/A because as rotas de escrita são só do ADMIN |
| Concurrency / ordering | NBASE-10 (versão otimista) |
| Data lifecycle / expiry | Norma nunca é excluída, só arquivada (NBASE-08); arquivo substituído sai do disco |
| Observability | Auditoria de cadastro, edição, anexo e arquivamento; aviso no log para código inexistente |
| External-dependency failure | N/A because a feature não chama serviço externo (a URL é só um link aberto pelo navegador) |
| State-transition integrity | Ativa para arquivada e de volta não é pedido: arquivar é a única transição (NBASE-08); alertas nunca bloqueiam (NTIT-07) |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| NBASE-01 | P1: Base de normas | Implemented | Implemented |
| NBASE-02 | P1: Base de normas | Implemented | Implemented |
| NBASE-03 | P1: Base de normas | Implemented | Implemented |
| NBASE-04 | P1: Base de normas | Implemented | Implemented |
| NBASE-05 | P1: Base de normas | Implemented | Implemented |
| NBASE-06 | P1: Base de normas | Implemented | Implemented |
| NBASE-07 | P1: Base de normas | Implemented | Implemented |
| NBASE-08 | P1: Base de normas | Implemented | Implemented |
| NBASE-09 | P1: Base de normas | Implemented | Implemented |
| NBASE-10 | P1: Base de normas | Implemented | Implemented |
| NBASE-11 | P1: Base de normas | Implemented | Implemented |
| NBASE-12 | P1: Base de normas | Implemented | Implemented |
| NLINK-01 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NLINK-02 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NLINK-03 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NLINK-04 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NLINK-05 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NLINK-06 | P1: Regras e alertas ligados à norma | Implemented | Implemented |
| NTIT-01 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-02 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-03 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-04 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-05 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-06 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-07 | P1: Titulação exigida | Implemented | Implemented |
| NTIT-08 | P1: Titulação exigida | Implemented | Implemented |
| NMOV-01 | P1: Origem e destino informados | Implemented | Implemented |
| NMOV-02 | P1: Origem e destino informados | Implemented | Implemented |
| NMOV-03 | P1: Origem e destino informados | Implemented | Implemented |
| NMOV-04 | P1: Origem e destino informados | Implemented | Implemented |
| NMOV-05 | P1: Origem e destino informados | Implemented | Implemented |
| NLIST-01 | P2: Lista de normas | Implemented | Implemented |
| NLIST-02 | P2: Lista de normas | Implemented | Implemented |
| NLIST-03 | P2: Lista de normas | Implemented | Implemented |
| NMIN-01 | P2: Mínimo não definido | Implemented | Implemented |
| NMIN-02 | P2: Mínimo não definido | Implemented | Implemented |

**Coverage:** 36 total, 36 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] 100% dos alertas de verificação de carreira, de tabela e de titulação citam uma norma cadastrada com link.
- [ ] As sete normas semeadas aparecem na VM depois do deploy, sem duplicata em partidas seguintes.
- [ ] O caso sintético de promoção B→C com mestrado mostra `TITULACAO_INSUFICIENTE`, e com doutorado não mostra.

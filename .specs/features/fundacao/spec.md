# Fundação — Specification

**Escopo:** Complex (domínio novo, regras normativas conflitantes, autenticação, persistência).
**Fontes:** `docs/referencias/normas/FONTES.md`. Toda regra abaixo cita sua origem.

## Problem Statement

O docente prepara o processo de progressão/promoção sem nenhuma verificação: identificação funcional, interstício e modalidade são preenchidos à mão e chegam à banca com erros. O Requerimento real de 16/11/2026 pede "PROMOÇÃO do Nível 4 da Classe D (...) para o Nível 2 da Classe D" e se identifica como "Associado D, Nível I", três afirmações mutuamente incompatíveis. A fundação entrega a base executável do sistema (stack, banco, autenticação) e o cadastro de docentes e processos, com verificação determinística, auditada e sem correção automática da identificação funcional e do interstício, conforme a estrutura de carreira vigente na data aplicável.

## Goals

- [ ] `docker compose up` sobe frontend, backend, postgres e nginx numa VM Ubuntu limpa, com migrações aplicadas e health check verde.
- [ ] Um usuário autenticado cadastra um docente e um processo e vê todas as inconsistências de identificação/interstício detectadas pelas regras, sem que o sistema altere os dados informados.
- [ ] Os dois casos reais (processo FASI 2022–2024 e Requerimento 2024–2026) produzem exatamente os resultados de verificação definidos em PROC-10 e PROC-11.
- [ ] Toda alteração em docente ou processo fica registrada em trilha de auditoria com usuário, data/hora, valor anterior, valor novo e justificativa.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Upload, OCR e extração de documentos | Feature `inteligencia-documental` |
| Verificar se atividades estão dentro do interstício (regras 3 e 4 da seção 4 do prompt) | Depende de atividades extraídas; feature `inteligencia-documental`/`pontuacao`. A fundação entrega só o intervalo do interstício como valor de domínio reutilizável |
| Tabelas de pontuação, critérios e pontuação mínima (Res. 4.644, art. 12) | Feature `pontuacao` |
| Agente normativo e base de normas | Feature `normativo`. Na fundação, as duas estruturas de carreira são dados semeados com fonte citada |
| Requerimento, portaria, banca e parecer | Feature `banca-parecer` |
| Carreira EBTT | Nenhum documento de referência ou caso real é EBTT. Modelo de dados aceita carreira como entidade, mas apenas Magistério Superior é semeado |
| Login institucional (SSO/SIGAA/gov.br) | Sem especificação de integração disponível; contas locais nesta versão |
| Backup/restauração, rate limiting global, hardening de nginx | Feature `implantacao` (exceto o limite de tentativas de login, AUTH-04) |
| Reenquadramento automático entre a estrutura antiga e a nova (Lei 12.772, Anexo II / art. 35) | Exige decisão administrativa; o sistema apenas sinaliza (CARR-05) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Perfis de acesso | Três perfis: ADMIN (gerencia usuários, unidades e estruturas de carreira), SECRETARIA (cria e acessa processos da(s) sua(s) unidade(s)), DOCENTE (cria e acessa apenas os próprios processos) | Prompt pede autorização e controle por processo; banca entra em `banca-parecer` | y |
| Estrutura de carreira aplicável | A versão cuja vigência contém a **data final** do interstício. Antes de 01/01/2025: estrutura da Res. 4.644/2015 (A1–A2, B1–B2, C1–C4, D1–D4, E). A partir de 01/01/2025: Lei 12.772 com redação da Lei 15.141/2025 (A, B1–B4, C1–C4, D) | O direito nasce ao completar o interstício (Res. 4.644, art. 29); é a regra mais simples que separa os dois casos reais | y |
| Interstício que cruza 01/01/2025 | Aceitar a classe informada em qualquer das duas nomenclaturas e emitir alerta `REQUER_ANALISE_NORMATIVA`; nunca converter | Documentos reais de 2025 (Portaria 89/2025-CCAME) ainda usam a nomenclatura antiga; reenquadramento é ato administrativo | y |
| Interstício mínimo | Progressão: 24 meses em ambas as estruturas. Promoção: 24 meses na estrutura antiga (Res. 4.644, art. 5º); na nova, 36 meses para a Classe B e 24 meses para C e D (Lei 12.772, art. 12, §3º) | Texto das normas; a regra de dispensa do art. 12, §7º (interstício considerado cumprido em 01/01/2025) não é aplicada automaticamente, gera `REQUER_ANALISE_NORMATIVA` quando a data final é 01/01/2025 | y |
| Contagem de meses | Meses civis completos entre data inicial e data final (23/11/2024 → 23/11/2026 = 24 meses; 23/11/2024 → 22/11/2026 = 23 meses) | Formato de todos os interstícios reais (mesmo dia, dois anos depois) | y |
| Verificações nunca bloqueiam o salvamento | Processo é salvo com qualquer combinação de dados; as verificações produzem alertas (`ERRO`, `ALERTA`, `REQUER_ANALISE_NORMATIVA`) exibidos ao usuário | Prompt: "Não corrigir automaticamente informações divergentes"; o docente precisa salvar rascunhos incompletos | y |
| Justificativa em alterações | Obrigatória para alterar processo com status `EM_ANDAMENTO`; opcional em `RASCUNHO` | Equilibra rastreabilidade (seção 13) com a fricção do preenchimento inicial | y |
| Status do processo | `RASCUNHO` → `EM_ANDAMENTO` → `CONCLUIDO`; `ARQUIVADO` alcançável de qualquer status por ADMIN ou dono; `CONCLUIDO` e `ARQUIVADO` são somente leitura | Dashboard pede "processos em andamento"; estados mínimos para isso | y |
| Sessão | Cookie HttpOnly, Secure, SameSite=Strict, expiração por inatividade de 30 min e absoluta de 8 h; token CSRF em requisições de escrita | Sessão por cookie exige proteção CSRF (seção 17) | y |
| Senhas | Hash Argon2id; mínimo 10 caracteres | Prática atual recomendada | y |
| Um docente, vários processos | Permitido, inclusive simultâneos (Res. 4.644, art. 6º) | Norma permite requerer mais de uma progressão ao mesmo tempo | y |
| Docente ↔ usuário | O cadastro de docente existe independentemente de conta de usuário; um usuário DOCENTE pode ser vinculado a no máximo um docente | Secretaria cadastra docentes que não usam o sistema | y |
| Nova versão de carreira com outra versão aberta (CARR-08) | O cadastro fecha automaticamente a versão aberta no dia anterior ao início da nova (CARR-09), desde que nenhum processo existente mude de versão (CARR-10). Vigências que se sobrepõem a uma versão já fechada continuam recusadas (409) | Decisão do usuário após o Verificador (2026-11-16): um passo só para o ADMIN, sem alterar as regras de processos existentes | y |
| Interstício insuficiente com datas inválidas (PROC-09) | Com data final anterior ou igual à inicial, emite só `INTERSTICIO_DATAS_INVALIDAS`, e não `INTERSTICIO_INSUFICIENTE` | Decisão do usuário (2026-11-16): a duração não faz sentido com datas inválidas | y |
| Duração em dias (PROC-02) | Dias = data final − data inicial, sem contar o dia final (23/11/2024 → 23/11/2026 = 730 dias) | Padrão do agente; convenção usual de intervalo de datas | n |
| Referência normativa de `DADOS_INCOMPLETOS` (PROC-04) | Cita "Res. 4.644/2015-CONSEPE" genericamente, porque nenhuma norma exige esses campos | Padrão do agente; evita inventar artigo | n |

**Open questions:** none - all resolved or logged above (as assumptions aguardando confirmação do usuário).

---

## User Stories

### P1: Stack executável ⭐ MVP

**User Story**: Como responsável pela implantação, quero subir todo o sistema com um comando para instalá-lo na VM da UFPA.

**Why P1**: Sem stack não há nada a demonstrar; todas as features seguintes dependem dela.

**Acceptance Criteria**:

1. WHEN `docker compose up -d` é executado com um `.env` válido THEN the system SHALL iniciar os serviços frontend, backend, postgres e nginx e `GET /api/health` via nginx SHALL responder 200 com `{"status":"ok","database":"ok"}` em até 120 s.
2. WHEN o backend inicia THEN the system SHALL aplicar todas as migrações Alembic pendentes antes de aceitar requisições.
3. IF o postgres está inacessível THEN `GET /api/health` SHALL responder 503 com `{"status":"degraded","database":"unavailable"}`.
4. The system SHALL armazenar dados do postgres e o diretório `storage/` em volumes nomeados que sobrevivem a `docker compose down` sem `-v`.
5. The repository SHALL conter `.env.example` com todas as variáveis usadas e nenhum valor secreto real.
6. The system SHALL nunca incluir o valor de `MARITALK_API_KEY` em respostas HTTP, bundle do frontend ou logs.
7. IF uma variável obrigatória de ambiente está ausente THEN o backend SHALL encerrar na inicialização com mensagem que nomeia a variável faltante, sem exibir valores de outras variáveis.

**Independent Test**: Numa máquina com Docker, `cp .env.example .env`, preencher, `docker compose up -d`, `curl http://localhost/api/health` → 200.

---

### P1: Autenticação e controle de acesso ⭐ MVP

**User Story**: Como usuário do sistema, quero entrar com minhas credenciais e acessar só os processos que me cabem, para que documentos pessoais de docentes permaneçam privados (LGPD).

**Why P1**: Os dados são pessoais e funcionais; nada pode ser exposto sem autenticação.

**Acceptance Criteria**:

1. WHEN credenciais válidas são enviadas a `POST /api/auth/login` THEN the system SHALL criar sessão em cookie HttpOnly/Secure/SameSite=Strict e responder 200 com id, nome e perfil do usuário.
2. IF as credenciais são inválidas THEN the system SHALL responder 401 com a mensagem "Usuário ou senha inválidos", idêntica para usuário inexistente e senha errada.
3. IF uma requisição a qualquer endpoint `/api/*` exceto `/api/health` e `/api/auth/login` chega sem sessão válida THEN the system SHALL responder 401.
4. IF ocorrem 5 falhas de login para o mesmo e-mail em 15 minutos THEN the system SHALL responder 429 a novas tentativas desse e-mail até o fim da janela de 15 minutos.
5. WHEN a sessão fica 30 minutos sem requisição ou atinge 8 horas desde o login THEN the system SHALL invalidá-la e a próxima requisição SHALL receber 401.
6. IF uma requisição de escrita (POST/PUT/PATCH/DELETE) autenticada não traz o token CSRF válido da sessão THEN the system SHALL responder 403.
7. The system SHALL armazenar senhas apenas como hash Argon2id.
8. IF um usuário DOCENTE solicita um processo que não pertence ao docente vinculado a ele THEN the system SHALL responder 404.
9. IF um usuário SECRETARIA solicita um processo de unidade acadêmica à qual não está vinculado THEN the system SHALL responder 404.
10. WHEN um ADMIN cria um usuário THEN the system SHALL exigir e-mail único, nome, perfil e senha com no mínimo 10 caracteres, e responder 422 nomeando o campo inválido em caso de violação.
11. WHEN `POST /api/auth/logout` é chamado THEN the system SHALL invalidar a sessão no servidor.

**Independent Test**: Criar ADMIN via script de inicialização, logar, criar um DOCENTE, verificar que ele não acessa processo de outro docente.

---

### P1: Cadastro de docente ⭐ MVP

**User Story**: Como docente ou secretaria, quero cadastrar os dados funcionais do docente uma única vez para reutilizá-los em todos os processos.

**Why P1**: Todo processo e todo documento gerado partem da identificação do docente.

**Acceptance Criteria**:

1. WHEN um docente é cadastrado THEN the system SHALL persistir nome completo, matrícula SIAPE, titulação, cargo, carreira, unidade acadêmica, faculdade, campus e regime de trabalho.
2. IF a matrícula SIAPE não contém exatamente 7 dígitos THEN the system SHALL responder 422 com erro no campo `siape`.
3. IF já existe docente com a mesma matrícula SIAPE THEN the system SHALL responder 409 sem criar duplicata.
4. The system SHALL restringir titulação a {GRADUACAO, ESPECIALIZACAO, MESTRADO, DOUTORADO} e regime de trabalho a {20H, 40H, DE}.
5. WHEN um docente é editado THEN the system SHALL registrar evento de auditoria conforme AUD-01.

**Independent Test**: Cadastrar o docente do caso real (SIAPE de 7 dígitos, FASI, Campus Tocantins/Cametá, DE) e reabri-lo com os mesmos valores.

---

### P1: Cadastro do processo e do interstício ⭐ MVP

**User Story**: Como docente ou secretaria, quero abrir um processo informando situação funcional atual, pretendida e interstício, para iniciar a preparação documental.

**Why P1**: É a ETAPA 1 do fluxo; todas as demais etapas pertencem a um processo.

**Acceptance Criteria**:

1. WHEN um processo é criado THEN the system SHALL persistir docente, modalidade (PROGRESSAO|PROMOCAO), classe/denominação/nível atuais, classe/denominação/nível pretendidos, data inicial, data final, data de abertura, observações e dados institucionais (nome e cargo do responsável, portaria de designação do responsável, unidade administrativa responsável), atribuindo identificador único e status `RASCUNHO`.
2. WHEN um processo é salvo THEN the system SHALL calcular e exibir a duração do interstício em meses civis completos e em dias.
3. The system SHALL salvar o processo exatamente com os valores informados, mesmo quando houver alertas de verificação, e nunca alterar esses valores automaticamente.
4. WHEN um processo é salvo ou consultado THEN the system SHALL executar as verificações PROC-05 a PROC-09 e CARR-01 a CARR-05 e retornar a lista de alertas, cada um com código, severidade (`ERRO`, `ALERTA`, `REQUER_ANALISE_NORMATIVA`), mensagem em português e referência normativa.
5. IF a data final é anterior ou igual à data inicial THEN the system SHALL emitir alerta `ERRO` com código `INTERSTICIO_DATAS_INVALIDAS`.
6. IF a data final é posterior à data de abertura do processo THEN the system SHALL emitir alerta `ALERTA` com código `INTERSTICIO_NAO_CONCLUIDO`.
7. IF a modalidade é PROGRESSAO e a classe pretendida difere da classe atual, ou o nível pretendido não é o nível atual + 1 THEN the system SHALL emitir alerta `ERRO` com código `MODALIDADE_INCOMPATIVEL` (Res. 4.644, art. 1º, parágrafo único; Lei 12.772, art. 12).
8. IF a modalidade é PROMOCAO e a classe pretendida não é a classe imediatamente seguinte à atual, ou o nível atual não é o último da classe atual, ou o nível pretendido não é o primeiro da classe pretendida THEN the system SHALL emitir alerta `ERRO` com código `MODALIDADE_INCOMPATIVEL`.
9. IF a duração do interstício em meses civis é menor que o mínimo da estrutura aplicável (CARR-03) THEN the system SHALL emitir alerta `ERRO` com código `INTERSTICIO_INSUFICIENTE`, informando meses apurados e mínimo exigido.
10. WHEN o caso FASI 2022–2024 é cadastrado (PROMOCAO, atual Classe C Nível 4 "Adjunto", pretendido Classe D Nível 1 "Associado", 23/11/2022 a 23/11/2024, abertura em 2025) THEN the system SHALL aplicar a estrutura Res. 4.644/2015, calcular 24 meses e emitir zero alertas `ERRO`.
11. WHEN o caso do Requerimento 2024–2026 é cadastrado como escrito, com todos os campos opcionais preenchidos (PROMOCAO, atual Classe D Nível 4 "Associado", pretendido Classe D Nível 2 "Associado", 23/11/2024 a 23/11/2026, abertura em 16/11/2026) THEN the system SHALL aplicar a estrutura Lei 15.141/2025 e emitir exatamente este conjunto de códigos: `MODALIDADE_INCOMPATIVEL`, `CLASSE_INEXISTENTE_NA_ESTRUTURA` (a Classe D da estrutura nova tem só um nível), `DENOMINACAO_DIVERGENTE` (na estrutura nova, Associado é a Classe C), `INTERSTICIO_NAO_CONCLUIDO` (data final 23/11/2026 posterior à abertura em 16/11/2026) e `INTERSTICIO_CRUZA_REESTRUTURACAO` (começa antes de 01/01/2025).
12. WHILE o processo está `CONCLUIDO` ou `ARQUIVADO` the system SHALL rejeitar alterações com 409.
13. IF um processo `EM_ANDAMENTO` é alterado sem justificativa THEN the system SHALL responder 422 com erro no campo `justificativa`.
14. WHEN um usuário lista processos THEN the system SHALL retornar apenas os processos permitidos pelo seu perfil (AUTH-08, AUTH-09), com status, docente, modalidade, interstício e contagem de alertas por severidade.

**Independent Test**: Cadastrar os dois casos reais e comparar a lista de alertas com PROC-10 e PROC-11.

---

### P1: Estruturas de carreira versionadas ⭐ MVP

**User Story**: Como sistema, preciso conhecer a estrutura de carreira vigente em cada data para verificar classes, níveis e interstícios sem regras embutidas em prompt ou código ad hoc.

**Why P1**: É pré-condição de PROC-07 a PROC-11 e a mudança de 2025 é exigência explícita de teste.

**Acceptance Criteria**:

1. The system SHALL selecionar a versão de estrutura de carreira cuja vigência contém a data final do interstício.
2. The system SHALL semear duas versões do Magistério Superior, cada uma com classes, denominações, níveis, regras de interstício e referência normativa: "Res. 4.644/2015-CONSEPE" (vigência até 31/12/2024) e "Lei 12.772/2012 com redação da Lei 15.141/2025" (vigência a partir de 01/01/2025).
3. The system SHALL obter o interstício mínimo da versão aplicável: progressão 24 meses nas duas versões; promoção 24 meses na versão Res. 4.644; na versão Lei 15.141, 36 meses para Classe B e 24 meses para Classes C e D.
4. IF a classe ou o nível informado (atual ou pretendido) não existe na versão aplicável THEN the system SHALL emitir alerta `ERRO` com código `CLASSE_INEXISTENTE_NA_ESTRUTURA`.
5. IF o interstício começa antes de 01/01/2025 e termina em ou após 01/01/2025 THEN the system SHALL emitir alerta `REQUER_ANALISE_NORMATIVA` com código `INTERSTICIO_CRUZA_REESTRUTURACAO`, citando a Lei 15.141/2025.
6. IF a denominação informada não corresponde à classe informada na versão aplicável THEN the system SHALL emitir alerta `ALERTA` com código `DENOMINACAO_DIVERGENTE`, mostrando a denominação esperada.
7. IF não existe versão de estrutura vigente na data final do interstício THEN the system SHALL emitir alerta `REQUER_ANALISE_NORMATIVA` com código `ESTRUTURA_NAO_CADASTRADA` e pular as verificações dependentes de estrutura.
8. WHERE o usuário é ADMIN the system SHALL permitir cadastrar nova versão de estrutura de carreira com vigência e referência normativa obrigatória, sem editar versões já usadas por processos.
9. WHEN um ADMIN cadastra uma versão cuja vigência começa depois do início de uma versão sem data final THEN the system SHALL encerrar a versão aberta no dia anterior ao início da nova e registrar evento de auditoria UPDATE com `valid_to` anterior (nulo) e novo.
10. IF encerrar a versão aberta deixaria algum processo existente com data final em ou após o início da nova versão THEN the system SHALL responder 409 sem criar a nova versão nem alterar a versão aberta.

**Independent Test**: Testes unitários de domínio com datas 31/12/2024 e 01/01/2025 e com os dois casos reais.

---

### P1: Trilha de auditoria ⭐ MVP

**User Story**: Como banca ou instância revisora, quero saber quem alterou cada informação, quando e por quê, para confiar nos documentos gerados.

**Why P1**: Seção 13 do prompt: histórico obrigatório; nenhum agente/usuário altera dados sem registro.

**Acceptance Criteria**:

1. WHEN um docente, processo, usuário ou estrutura de carreira é criado, alterado ou arquivado THEN the system SHALL gravar evento de auditoria com usuário, data/hora UTC, entidade, id, campos alterados com valor anterior e novo, e justificativa (quando houver).
2. The system SHALL impedir alteração ou exclusão de eventos de auditoria pela API.
3. WHEN um usuário autorizado consulta o histórico de um processo THEN the system SHALL retornar os eventos em ordem cronológica.
4. The system SHALL registrar nos logs de aplicação apenas identificadores (ids, códigos de evento), nunca nome, SIAPE ou outros dados pessoais do docente.

**Independent Test**: Alterar o nível pretendido de um processo `EM_ANDAMENTO` com justificativa e verificar o evento com valores anterior/novo.

---

### P1: Interface web — Etapa 1 ⭐ MVP

**User Story**: Como docente sem conhecimento técnico, quero telas simples de login, painel, cadastro de docente e Etapa 1 do processo, para operar o sistema sem ajuda.

**Why P1**: Fatia vertical demonstrável; sem interface o usuário-alvo não opera o sistema.

**Acceptance Criteria**:

1. WHEN o usuário acessa qualquer rota sem sessão THEN o frontend SHALL redirecionar para a tela de login.
2. WHEN o usuário autenticado abre o painel THEN o frontend SHALL exibir total de processos, processos por status e lista dos processos permitidos com contagem de alertas por severidade.
3. WHEN o usuário salva a Etapa 1 THEN o frontend SHALL exibir a duração do interstício e a lista de alertas agrupada por severidade, com a referência normativa de cada alerta.
4. The frontend SHALL exibir a navegação das 9 etapas do processo, com a Etapa 1 ativa e as etapas 2–9 desabilitadas e rotuladas "em breve".
5. IF o backend retorna 422 THEN o frontend SHALL exibir a mensagem junto ao campo indicado.
6. The frontend SHALL ser utilizável em largura de 360 px sem rolagem horizontal.

**Independent Test**: Fluxo manual no navegador: login → cadastrar docente → criar processo → ver alertas.

---

### P2: Unidades acadêmicas

**User Story**: Como ADMIN, quero cadastrar unidades acadêmicas (campus, instituto, faculdade) para vincular docentes, secretarias e, depois, tabelas de pontuação.

**Why P2**: Uma unidade semeada (FASI/Campus Tocantins-Cametá) basta para o MVP; o cadastro completo é necessário antes de `pontuacao`.

**Acceptance Criteria**:

1. WHERE o usuário é ADMIN the system SHALL permitir criar, editar e arquivar unidades acadêmicas com nome, sigla, tipo (CAMPUS, INSTITUTO, FACULDADE) e unidade-mãe opcional.
2. IF uma unidade arquivada é selecionada em novo docente ou processo THEN the system SHALL responder 422.
3. WHEN o sistema é inicializado pela primeira vez THEN the system SHALL semear o Campus Universitário do Tocantins/Cametá, a Faculdade de Sistemas de Informação (FASI) e o IFCH.

---

## Edge Cases

- WHEN o interstício termina em 31/12/2024 THEN the system SHALL usar a versão Res. 4.644/2015; WHEN termina em 01/01/2025 THEN the system SHALL usar a versão Lei 15.141/2025.
- WHEN a data inicial é 29/02/2024 THEN the system SHALL contar meses civis tratando 28/02 como fim de mês em ano não bissexto (29/02/2024 → 28/02/2026 = 24 meses).
- IF dois usuários salvam o mesmo processo simultaneamente THEN the system SHALL aceitar a primeira gravação e responder 409 à segunda (controle por versão da linha), sem perda silenciosa.
- IF o processo referencia docente arquivado THEN the system SHALL manter a leitura e bloquear novos processos para esse docente com 422.
- IF campos opcionais (observações, dados institucionais) estão vazios THEN the system SHALL salvar o processo e emitir alerta `ALERTA` com código `DADOS_INCOMPLETOS` listando os campos vazios.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --- | --- |
| Input validation & bounds | DOC-02, DOC-04, AUTH-10, PROC-05 |
| Failure / partial-failure states | INFRA-03, INFRA-07; gravações em transação única (processo + auditoria) |
| Idempotency / retry / duplicate handling | DOC-03 (SIAPE único); criação de processo não é idempotente por desenho (Res. 4.644, art. 6º permite processos simultâneos) |
| Auth boundaries & rate limits | AUTH-03, AUTH-04, AUTH-06, AUTH-08, AUTH-09 |
| Concurrency / ordering | Edge case de gravação simultânea (409) |
| Data lifecycle / expiry | AUTH-05 (sessão); arquivamento em vez de exclusão para docente/processo/unidade; retenção de auditoria sem expiração nesta feature |
| Observability | AUD-04 (logs sem dados pessoais); INFRA-01 (health check) |
| External-dependency failure | N/A because a fundação não chama serviços externos (MariTalk entra em `inteligencia-documental`); postgres coberto por INFRA-03 |
| State-transition integrity | PROC-12, PROC-13; transições de status listadas em Assumptions |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| INFRA-01 | P1: Stack executável | Design | Implementing |
| INFRA-02 | P1: Stack executável | Design | Implementing |
| INFRA-03 | P1: Stack executável | Design | Implementing |
| INFRA-04 | P1: Stack executável | Design | Implementing |
| INFRA-05 | P1: Stack executável | Design | Implementing |
| INFRA-06 | P1: Stack executável | Design | Implementing |
| INFRA-07 | P1: Stack executável | Design | Implementing |
| AUTH-01 | P1: Autenticação | Design | Implementing |
| AUTH-02 | P1: Autenticação | Design | Implementing |
| AUTH-03 | P1: Autenticação | Design | Implementing |
| AUTH-04 | P1: Autenticação | Design | Implementing |
| AUTH-05 | P1: Autenticação | Design | Implementing |
| AUTH-06 | P1: Autenticação | Design | Implementing |
| AUTH-07 | P1: Autenticação | Design | Implementing |
| AUTH-08 | P1: Autenticação | Design | Implementing |
| AUTH-09 | P1: Autenticação | Design | Implementing |
| AUTH-10 | P1: Autenticação | Design | Implementing |
| AUTH-11 | P1: Autenticação | Design | Implementing |
| DOC-01 | P1: Cadastro de docente | Design | Implementing |
| DOC-02 | P1: Cadastro de docente | Design | Implementing |
| DOC-03 | P1: Cadastro de docente | Design | Implementing |
| DOC-04 | P1: Cadastro de docente | Design | Implementing |
| DOC-05 | P1: Cadastro de docente | Design | Implementing |
| PROC-01 | P1: Processo e interstício | Design | Implementing |
| PROC-02 | P1: Processo e interstício | Design | Implementing |
| PROC-03 | P1: Processo e interstício | Design | Implementing |
| PROC-04 | P1: Processo e interstício | Design | Implementing |
| PROC-05 | P1: Processo e interstício | Design | Implementing |
| PROC-06 | P1: Processo e interstício | Design | Implementing |
| PROC-07 | P1: Processo e interstício | Design | Implementing |
| PROC-08 | P1: Processo e interstício | Design | Implementing |
| PROC-09 | P1: Processo e interstício | Design | Implementing |
| PROC-10 | P1: Processo e interstício | Design | Implementing |
| PROC-11 | P1: Processo e interstício | Design | Implementing |
| PROC-12 | P1: Processo e interstício | Design | Implementing |
| PROC-13 | P1: Processo e interstício | Design | Implementing |
| PROC-14 | P1: Processo e interstício | Design | Implementing |
| CARR-01 | P1: Estruturas de carreira | Design | Implementing |
| CARR-02 | P1: Estruturas de carreira | Design | Implementing |
| CARR-03 | P1: Estruturas de carreira | Design | Implementing |
| CARR-04 | P1: Estruturas de carreira | Design | Implementing |
| CARR-05 | P1: Estruturas de carreira | Design | Implementing |
| CARR-06 | P1: Estruturas de carreira | Design | Implementing |
| CARR-07 | P1: Estruturas de carreira | Design | Implementing |
| CARR-08 | P1: Estruturas de carreira | Design | Implementing |
| CARR-09 | P1: Estruturas de carreira | Design | Implementing |
| CARR-10 | P1: Estruturas de carreira | Design | Implementing |
| AUD-01 | P1: Trilha de auditoria | Design | Implementing |
| AUD-02 | P1: Trilha de auditoria | Design | Implementing |
| AUD-03 | P1: Trilha de auditoria | Design | Implementing |
| AUD-04 | P1: Trilha de auditoria | Design | Implementing |
| UI-01 | P1: Interface web | Design | Implementing |
| UI-02 | P1: Interface web | Design | Implementing |
| UI-03 | P1: Interface web | Design | Implementing |
| UI-04 | P1: Interface web | Design | Implementing |
| UI-05 | P1: Interface web | Design | Implementing |
| UI-06 | P1: Interface web | Design | Implementing |
| UNIT-01 | P2: Unidades acadêmicas | Design | Implementing |
| UNIT-02 | P2: Unidades acadêmicas | Design | Implementing |
| UNIT-03 | P2: Unidades acadêmicas | Design | Implementing |

IDs numeram os critérios de cada história na ordem em que aparecem (ex.: PROC-11 = 11º critério de "Processo e interstício").

**Coverage:** 60 total, 60 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Instalação limpa na VM (`docker compose up -d`) com health check 200 em até 120 s.
- [ ] PROC-10 e PROC-11 passam como testes de aceitação automatizados usando os dados dos dois casos reais.
- [ ] Zero ocorrências de nome/SIAPE do docente nos logs da aplicação após a suíte de testes de integração.
- [ ] Um docente cadastra perfil e processo e vê os alertas em menos de 5 minutos, sem instrução.

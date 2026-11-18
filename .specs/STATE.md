# STATE

## Decisions

### AD-001
- **Decision**: Clean Architecture em quatro camadas: `domain` e `application` em Python puro, sem importar FastAPI, SQLAlchemy, httpx ou `app.infrastructure`; a regra é verificada por teste de arquitetura.
- **Reason**: Exigência do usuário; regras de negócio testáveis e provedor de IA substituível.
- **Trade-off**: Mais código de mapeamento (entidades ↔ modelos ORM ↔ schemas).
- **Scope**: todo o backend, todas as features
- **Date**: 2026-11-16
- **Status**: active

### AD-002
- **Decision**: Regras institucionais (estruturas de carreira, tabelas de pontuação, normas) são dados versionados com vigência e `norm_reference` obrigatória. Verificadores são funções puras que retornam alertas (ERRO/ALERTA/REQUER_ANALISE_NORMATIVA) e nunca bloqueiam nem corrigem dados informados.
- **Reason**: Proibição de inventar regras e de corrigir divergências; normas mudam (Lei 15.141/2025) e variam por unidade (FASI ≠ IFCH).
- **Trade-off**: Regras complexas exigem um schema de definição em vez de código direto.
- **Scope**: `fundacao` (carreira), `pontuacao`, `normativo`, `banca-parecer`
- **Date**: 2026-11-16
- **Status**: active

### AD-003
- **Decision**: Autenticação por sessão no servidor (tabela `sessions` no Postgres; cookie HttpOnly guarda o token, banco guarda só o hash) com token CSRF em header; sem JWT.
- **Reason**: Revogação imediata (logout, expiração por inatividade), sem segredo de assinatura para gerenciar.
- **Trade-off**: Uma consulta ao banco por requisição autenticada.
- **Scope**: backend e frontend
- **Date**: 2026-11-16
- **Status**: active

### AD-004
- **Decision**: Testes de integração rodam contra PostgreSQL real (container efêmero ou `TEST_DATABASE_URL`), nunca SQLite.
- **Reason**: JSONB, citext, enums e locks otimistas se comportam de forma diferente no SQLite.
- **Trade-off**: A suíte de integração exige Docker.
- **Scope**: todas as features
- **Date**: 2026-11-16
- **Status**: active

### AD-005
- **Decision**: A MariTalk é acessada pelo endpoint compatível com OpenAI em `MARITALK_API_BASE`, com o modelo `MARITALK_MODEL`; se a chamada falhar por erro de modelo, há uma nova tentativa com `sabia-4-br-sp`. A chave fica só no backend.
- **Reason**: Instrução do usuário (2026-11-16).
- **Trade-off**: Dependência da compatibilidade OpenAI da Maritaca.
- **Scope**: `inteligencia-documental`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-16
- **Status**: active

### AD-006
- **Decision**: O resultado da pontuação de um processo é calculado sob demanda a partir da versão da tabela e das atividades, e não é persistido. A tabela `scoring_results` do prompt não é criada em `pontuacao`.
- **Reason**: Resultado gravado fica desatualizado a cada edição de atividade; o cálculo determinístico é barato e reproduzível.
- **Trade-off**: Não há histórico de totais até `documentos-gerados`, que grava o próprio instantâneo no documento gerado.
- **Scope**: `pontuacao`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-17
- **Status**: active

### AD-007
- **Decision**: Tabelas de pontuação usam tabelas relacionais (versão → grupos → critérios), diferente das estruturas de carreira, que guardam a definição em JSONB.
- **Reason**: Critérios são editados um a um, importados por CSV, comparados entre versões e consultados por (grupo, item); linhas permitem constraints, migrações e consultas.
- **Trade-off**: Mais código de mapeamento e mais joins que um JSON por versão.
- **Scope**: `pontuacao`, `normativo`
- **Date**: 2026-11-17
- **Status**: active

### AD-008
- **Decision**: O processamento de documentos roda numa thread única dentro do processo do backend, com tarefas e estados no PostgreSQL (`FOR UPDATE SKIP LOCKED`), e não em Celery e Redis.
- **Reason**: A VM tem 1 CPU e pouca memória livre; o prompt admite começar assim (seção 18) e os casos de uso não mudam quando a fila externa chegar.
- **Trade-off**: Sem escala horizontal nem reentrega automática além da recuperação na partida; a thread morre com o app.
- **Scope**: `inteligencia-documental`, `documentos-gerados`
- **Date**: 2026-11-17
- **Status**: active

### AD-009
- **Decision**: A saída da IA é tratada como não confiável: resposta em JSON com schema estrito, mais a verificação determinística de que cada valor extraído aparece no texto da página citada (senão vira `null` com aviso). O item de pontuação vem de uma tabela de regras versionada, nunca da IA. A IA recebe só texto.
- **Reason**: O prompt proíbe inventar datas, cargas horárias, participantes e títulos; a validação determinística garante a regra mesmo se o modelo errar.
- **Trade-off**: A verificação pode recusar valor certo por formatação e exige normalizar datas e números; campos vazios pedem digitação.
- **Scope**: `inteligencia-documental`, `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-17
- **Status**: active

### AD-010
- **Decision**: A data final de uma designação só é derivada de um prazo escrito no texto: a IA devolve o trecho literal `term` ("por 2 (dois) anos"), o código o confere na página, lê numerais e palavras e soma ao início (`end = start + prazo`), com o aviso `DATA_FIM_DERIVADA`; sem prazo, o item por ano de exercício com só a data de início é período aberto até o fim do interstício, com `DATA_FIM_AUSENTE`. Itens que não são por ano mantêm o dia único. O período aberto vale também para a atividade cadastrada à mão: a quantidade pontuada é o menor valor entre a informada e os anos completos do período dentro do interstício (sem quantidade informada, os anos completos), nunca acima do que a pessoa digitou, com o alerta `DATA_FIM_AUSENTE` na linha de pontuação (TER-05).
- **Reason**: A portaria de Diretor valia 0 ponto porque a data de início sozinha era um dia; a IA não pode calcular nem inventar a data final (AD-009).
- **Trade-off**: Prazo escrito de outra forma não é lido e cai no período aberto; o usuário confere a data derivada, que fica editável.
- **Scope**: `inteligencia-documental`, `pontuacao`
- **Date**: 2026-11-17
- **Status**: active

## Handoff

- **Feature**: `.specs/features/inteligencia-documental` (Complex): **implementada**, Fases 1-16 (T1-T117) commitadas na branch `feat/inteligencia-documental` (empilhada sobre `feat/pontuacao` sobre `feat/fundacao`; main intocada). PRs abertos no GitHub: #1 `feat/fundacao`, #2 `feat/pontuacao`, #3 `feat/inteligencia-documental`. Depois: `documentos-gerados` → `banca-parecer` → `normativo` → `implantacao`
- **Verificação**: quatro passagens do Verificador independente (`validation.md`: passagem 1 FAIL, 2, 3 e 4 PASS com lacunas) e seis rodadas de correção (fases 11-16; REAL, VER, SEG, TER, QUA, CER = 139 requisitos). A rodada 6 (T113-T117, CER-01..05) corrige o certificado em inglês de participação com carga horária (tipo `CERTIFICADO`, enquadramento em VII.10 com o alerta `ENQUADRADO_COMO_CAPACITACAO`, prompt em inglês): precisa de novo deploy; em "Resolution (round 6)", não re-verificada; A Fase 15 (T107-T112: rótulo de equipe e nome de outra pessoa na coordenação, negação da indexação, redação comum de extensão, pinos dos mutantes sobreviventes, variantes numeradas, registro) está em "Resolution (round 5)" e **não foi re-verificada pelo Verificador**; QUA-01..06 seguem `Implementing`
- **Gate no HEAD**: backend `ruff` limpo e 3751 testes passando (3 `maritalk_live` desmarcados com `MARITALK_MODEL=sabia-4-thinking` no `.env`; 6 num checkout sem `.env`); frontend `eslint` limpo, build e 184 testes passando com `REQUIRE_DIST=1`; teste de aceitação da `tabela-oficial` (211 pontos) verde
- **Decisões pendentes do usuário**: (1) regra de fração de ano para o Vice (cerca de 3,5 meses, 20 pontos por ano; hoje vale 0 por ano completo); (2) política do nome parcial do docente (D1: 5 documentos do próprio docente vão para revisão porque o texto traz só 2 dos 3 nomes); (3) atividade rejeitada em validação em lote; (4) unidade do VIII.36 ("por unidade" na tabela, "ano/revista" na descrição); (5) política da quantidade 0 (item por ano com menos de um ano completo vale 0 e pede a quantidade); (6) se "por mais N anos" sem "prorrogável" é prazo; (7) a regra de contenção de títulos (um título dentro do outro, na mesma página, tipo e data, vira uma atividade; títulos que diferem por numeral ou letra isolada, como "Nível 1" e "Nível 2", já não se reúnem desde T111)
- **Próximo passo**: push da branch e redeploy na VM com os commits das Fases 15 e 16 (d6dca43 é o que está no ar; os commits de `e08e95f` em diante, mais os registros em `.specs`, ainda não estão; só código do backend, do rótulo do frontend e testes, sem migração), com aprovação explícita do usuário para cada ação remota; uma quinta rodada do Verificador na Fase 15 se o usuário quiser. Nenhum push, deploy, acesso à VM ou chamada real à MariTalk foi feito na rodada 5
- **Dívidas**: teste de 360 px só estático; sem backup; sem troca de senha; rotas de negócio devolvem 500 com banco fora do ar; `api/client.ts` só envia JSON; Grupo I do caso real com 16 pontos sem explicação; mínimos das classes novas sem regra; antivírus ausente na VM; itens informativos da passagem 2 (PIPE-02/ACC-02, `--fake-ai`, teste de lock, nginx do servidor fora do repositório, data final inclusiva); limites conhecidos da Fase 15 em "Resolution (round 5)" (pesquisadora e coordenadora na mesma frase vai para revisão; título de projeto com duas palavras capitalizadas entre papel e nome idem); D3, D5, D6 e D7 de `corpus-reports/ANALISE.md` são variação da IA ou dado a revisar
- **Documentos reais** (`Documentos/`, não versionados): 44 PDFs e 1 PNG; só scripts locais os leem (`corpus-reports/` fica fora do git)
- **MariTalk**: `sabia-4-thinking` em `https://chat.maritaca.ai/api` (Bearer), saída em JSON estrito; modelo do `.env`; erro de modelo cai em `sabia-4-br-sp`
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; ver `docs/deploy/vm.md`). No ar desde 2026-11-18: commit d6dca43 (rodada 5; antes 9533966, retorno pela imagem `inteligencia-9533966`) (`fundacao` + `pontuacao` + `tabela-oficial` + `inteligencia-documental`, até a Fase 14), migração 0004, tabela oficial UFPA semeada (FASI e IFCH associadas; tabelas antigas arquivadas; a VM não tinha processos), chave MariTalk configurada no `.env` da VM, nginx do servidor e do projeto com `client_max_body_size 120m`, backend com `mem_limit` 384 MB (uso em repouso 96 MB). Os commits da Fase 15 não têm migração nem mudança de configuração: só código do backend e testes. Pontos de retorno: imagens `pontuacao-369f710` e `fundacao-360eefb`, dump `backups/progressao-pre-docs-2026-11-18.sql.gz`, cópias de configuração em `backups/`. Credenciais do ADMIN em /opt/progressao/.admin-credentials
- **Uncommitted files**: none (`test/`, `requeriment.txt` sem versionar)
- **Branch**: feat/inteligencia-documental

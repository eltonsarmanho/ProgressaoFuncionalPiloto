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

### AD-011
- **Decision**: Os documentos gerados não usam LibreOffice nem conversão de DOCX em PDF: DOCX com python-docx, PDF gerado com reportlab (Liberation Serif versionada no repositório) e PDF montado com as páginas originais por PyMuPDF; PDF e DOCX têm o mesmo conteúdo e a mesma ordem, a aparência pode diferir.
- **Reason**: A VM tem 1 CPU e 384 MB para o backend; as bibliotecas somam cerca de 24 MB e foram medidas com dados sintéticos (pico de 74 MB num Comprovante de 411 páginas). Instrução do usuário (2026-11-18); a licença AGPL do PyMuPDF foi aceita pelo usuário na mesma data (não é parecer jurídico).
- **Trade-off**: O DOCX não foi testado no Word, só em LibreOffice no ambiente de desenvolvimento; reportlab 5.1.0 é recente (queda para 4.5.1 se a suíte falhar).
- **Scope**: `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-18
- **Status**: active

### AD-012
- **Decision**: Cada geração de documento vira uma versão imutável (gatilho no banco), numerada só quando chega a `PRONTO`, com arquivo, SHA-256 e instantâneo do que foi usado; a geração perdida num reinício vira `FALHOU` com `INTERROMPIDA` e não é reenfileirada; todas as versões ficam enquanto o processo existir.
- **Reason**: O resultado da pontuação não é gravado (AD-006), então a versão é o único registro do que foi entregue; falha não gasta número; repetir uma geração interrompida não é seguro de decidir sozinho.
- **Trade-off**: Sem reentrega automática (diferente de `processing_jobs`, AD-008) e o volume cresce sem retenção, até 60 MB por Comprovante.
- **Scope**: `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-18
- **Status**: active

### AD-013
- **Decision**: As páginas originais entram no Comprovante sem alterar o conteúdo (rotação, anotações e campos preservados; o número vai numa faixa de rodapé acrescentada, nunca sobre o original; rasterizar só como fallback alertado), e a ordem e a numeração vêm de um plano puro do domínio compartilhado entre a Tabela e o Comprovante, que usa só metadados.
- **Reason**: O prompt proíbe alterar os comprovantes; a Tabela cita números do Comprovante antes de ele existir e depois que os originais forem excluídos.
- **Trade-off**: O sumário tem capacidade fixa de linhas por página; página rotacionada com recorte perde o formato vetorial (`PAGINA_RASTERIZADA`); PNG acima de 12 megapixels é recusado.
- **Scope**: `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-18
- **Status**: active

### AD-014
- **Decision**: A redação por IA do Relatório recebe só os campos da atividade (nunca texto bruto de página nem dado pessoal mascarado), roda como tarefa em segundo plano com estado na seção, só vale depois de uma conferência determinística (número, data, nome e palavra nova) e cai no texto-modelo se falhar ou passar de 60 s; texto editado pelo usuário nunca é reescrito.
- **Reason**: Estende a AD-009 ao sentido da geração; o prompt proíbe inventar fatos e uma requisição de 60 s não cabe na tela nem no nginx. Decisão do usuário (2026-11-18).
- **Trade-off**: A conferência não pega afirmação qualitativa feita só de palavras permitidas (a revisão humana cobre); a tarefa ocupa a thread única por até 60 s.
- **Scope**: `documentos-gerados`, `banca-parecer`
- **Date**: 2026-11-18
- **Status**: active

### AD-015
- **Decision**: Concluir o processo significa "concluir e excluir documentos de entrada": só com versão PRONTO de Tabela, Relatório e Comprovante e confirmação irreversível, o sistema exclui os arquivos originais, os textos extraídos das páginas e os trechos de evidência, mantém metadados (marcados `ARQUIVO_EXCLUIDO`), vínculos e todos os documentos gerados, e só depois de remover todos os arquivos muda o processo para CONCLUIDO; a rota genérica de status recusa o alvo CONCLUIDO.
- **Reason**: Pedido do usuário (2026-11-18): os documentos de entrada não devem ocupar espaço do servidor nem guardar dados pessoais depois que os artefatos estão prontos. A interpretação está como assunção não confirmada em `documentos-gerados/spec.md`.
- **Trade-off**: Irreversível e sem backup na VM; depois da conclusão o Comprovante não pode ser regerado e o JSON estruturado das extrações permanece.
- **Scope**: `documentos-gerados`, `fundacao` (transição de status), `inteligencia-documental` (leitura de arquivos e textos)
- **Date**: 2026-11-18
- **Status**: active

### AD-016
- **Decision**: O documento fora do interstício é decidido no analisador, uma vez por leitura: se toda atividade extraída com data tem estado de período `FORA` (a mesma verificação de SUG-09), o documento termina `PROCESSADO` com `status_code` `DOCUMENTO_FORA_DO_INTERSTICIO`, sem atividade criada e sem `REQUER_REVISAO`; o alerta também entra nos avisos da leitura com um `detail` (data do documento, precisão e datas do interstício) que a lista da Etapa 2 usa para a faixa. Classificar e vincular atividade a um documento assim respondem 409 com o mesmo código; a regra só muda ao reprocessar (o interstício gravado no alerta é o da leitura).
- **Reason**: Pedido do usuário (2026-11-18): só o que aconteceu dentro do interstício conta, e o documento fora dele não deve seguir para as Etapas 3, 4 e 5. Reaproveita o `PeriodState` de SUG-09 e o Reprocessar existente; o código de alerta é texto, sem coluna nova nem migração.
- **Trade-off**: A reavaliação é manual (mudar o interstício na Etapa 1 não atualiza os documentos já lidos até reprocessá-los); sem exceção para incluir o documento; um rascunho de leitura anterior rejeitado pelo reprocessamento continua como linha rejeitada de 0 ponto; a contagem de documentos fora do interstício é somada pela tela, não pela API. Suposição não confirmada: `Confirmed = n` na linha "Regra do documento fora do interstício" da spec.
- **Scope**: `inteligencia-documental`, `documentos-gerados`
- **Date**: 2026-11-18
- **Status**: active

### AD-017
- **Decision**: O documento que passa a estar fora do interstício depois de reprocessado não rejeita sozinho as atividades que o usuário já editou ou validou: elas permanecem ligadas ao documento, e FORA-03 diz só que nenhuma atividade é criada a partir dele. O seletor de vínculo da Etapa 3 não oferece documento fora do interstício, e o alerta `DOCENTE_DIVERGENTE` não é gravado para um documento inteiramente fora (o analisador retorna antes da checagem do docente).
- **Reason**: Rejeitar trabalho já editado ou validado seria perda silenciosa de decisão do usuário (regra 1 e regra 5 do `CLAUDE.md`); a pontuação já recusa a data fora do período (linha `FORA_DO_INTERSTICIO` de 0 ponto), então nenhum ponto errado chega ao total. Decisão padrão do líder após o Verificador independente (`verification-fora.md`, D1 a D3), sujeita a mudança pelo usuário.
- **Trade-off**: A Etapa 2 pode mostrar a faixa ao lado de `activity_count` maior que 0, e a atividade mantida segue na Etapa 3 com linha de 0 ponto; a faixa não avisa disso (uma segunda linha na faixa foi considerada e não implementada).
- **Scope**: `inteligencia-documental`
- **Date**: 2026-11-18
- **Status**: superseded in part by AD-019 (atividades editadas ou validadas); o seletor da Etapa 3 e o `DOCENTE_DIVERGENTE` seguem valendo

### AD-018
- **Decision**: O processo passa a poder ser arquivado e excluído do Painel. Excluir é definitivo, só para ADMIN ou dono, em qualquer status, com confirmação que lista o que sai (documentos de entrada, atividades, documentos gerados); apaga na mesma transação tudo o que depende do processo e, depois do commit, os arquivos do disco; a auditoria guarda o evento `DELETE` com os valores anteriores e nunca é apagada. Documento em leitura, geração ou redação em andamento recusa a exclusão (409 `OPERACAO_EM_ANDAMENTO`). Docente e unidade permanecem.
- **Reason**: Pedido do usuário em 2026-11-18 e 2026-11-19 ("Aplique Mudança de Deletar e Arquivar no menu principal"). Revisa a linha "arquivamento em vez de exclusão" da `fundacao` para processos.
- **Trade-off**: Não há lixeira nem desarquivar. A migração `0007` troca a função dos gatilhos de imutabilidade dos documentos gerados para deixar passar o `DELETE` só sob `app.process_purge`; o valor `DELETE` de `audit_action` não se desfaz. O botão Excluir aparece para todos e o 403 vira mensagem no modal, porque o resumo do processo não traz o dono.
- **Scope**: `gestao-processos`
- **Date**: 2026-11-19
- **Status**: active

### AD-019
- **Decision**: Quando o reprocessamento torna um documento fora do interstício, o sistema rejeita, com auditoria (`DOCUMENTO_FORA_DO_INTERSTICIO`), todas as atividades ligadas só a esse documento, inclusive as já editadas ou validadas pelo usuário; a atividade que tem também evidência de outro documento permanece, sem a evidência do documento fora. Substitui a parte de AD-017 que mantinha as atividades editadas ou validadas.
- **Reason**: Pedido do usuário em 2026-11-18 ("Remover"): o documento fora do interstício é identificado só na Etapa 2 e não segue para as próximas etapas.
- **Trade-off**: Trabalho já validado pelo usuário é rejeitado sozinho; a rejeição é auditada e a atividade continua no histórico (não é apagada do banco).
- **Implementation (T146)**: o processamento em segundo plano (`ProcessDocument`) aplica a regra na mesma unidade de trabalho que grava o resultado da leitura fora do interstício, porque só ali o alerta é conhecido; a auditoria da rejeição tem usuário vazio (ação do sistema) e justificativa `DOCUMENTO_FORA_DO_INTERSTICIO`; o vínculo removido da atividade que fica também é auditado; a atividade rejeitada mantém a evidência (como qualquer rascunho rejeitado) e segue como linha rejeitada de 0 ponto nas Etapas 3 e 4, fora da Tabela, do Relatório e do Comprovante.
- **Scope**: `inteligencia-documental` (FORA-03, T146)
- **Date**: 2026-11-18
- **Status**: active

### AD-020
- **Decision**: O limite da conferência determinística da redação por IA do Relatório (REL-12, B-D3) é aceito como limite conhecido: um nome próprio inventado em minúsculas com até 3 palavras novas e uma afirmação invertida ("Não ministrou...") passam em `check_wording`. A AD-014 continua valendo; o texto da IA leva o selo "IA", é revisado e editável pelo usuário, e a revisão humana é a barreira final. Nenhum código muda.
- **Reason**: Decisão do usuário (2026-11-18): aceito como limite conhecido. Endurecer a conferência (baixar `max_new_words`, tratar negações como vocabulário novo) derrubaria mais texto fiel para o texto-modelo.
- **Trade-off**: Uma frase falsa feita de palavras já permitidas pode chegar ao Relatório se o usuário não a notar na revisão; baixar `max_new_words` ou tratar negações como vocabulário novo ficam como opção futura.
- **Scope**: `documentos-gerados` (REL-12), `banca-parecer`
- **Date**: 2026-11-18
- **Status**: active

### AD-021
- **Decision**: O `extraction_runs.raw_json` fica depois da conclusão e da exclusão dos documentos de entrada (B-D9): o registro imutável da extração mantém o nome do docente e os títulos extraídos; o gatilho de imutabilidade da extração não muda. A AD-015 segue como está.
- **Reason**: Decisão do usuário (2026-11-18): aceito e mantido; o dado é do próprio docente e o mesmo dado está vivo nas atividades; apagar o JSON exigiria mudar o gatilho e tirar da atividade a prova do que foi extraído.
- **Trade-off**: Dados extraídos (nome, títulos) permanecem no banco depois da exclusão dos arquivos e do texto das páginas.
- **Scope**: `documentos-gerados` (DEL-05, AD-015), `inteligencia-documental`
- **Date**: 2026-11-18
- **Status**: active

### AD-022
- **Decision**: A Etapa 3 separa "Atividades válidas" de "Atividades não válidas". A validade é calculada no servidor por `classify_activity` (domínio, `activity_validity.py`) e nunca gravada (AD-006 preservado); o motor de pontuação, a Tabela, o Relatório, o Comprovante (por `eligible_activities` e `load_generation_inputs`) e a lista da Etapa 3 (`validity` em `ActivityOut`) usam a mesma função, na mesma ordem de saídas antecipadas do motor. Só as válidas seguem para as Etapas 4 e 5 e para os documentos gerados; "Validar" exige categoria e atividade válida (422 `categoria` ou `status`) e é o que pontua. Duplicadas são mescladas: a coluna `activities.merged_into_id` (UUID nulo, chave estrangeira `NO ACTION`, índice parcial `WHERE merged_into_id IS NOT NULL`) aponta para a mantida, e `activity_evidences.origin_activity_id` guarda de qual atividade cada prova veio; o `status` não ganha valor novo. A mesclagem roda na escrita (criar, editar, fim da leitura do documento) e uma vez por abertura da Etapa 3 (`POST /api/processes/{id}/activities/merge-duplicates`, nunca num `GET`); "Não é duplicada" (`separate`) a reverte, devolve as provas e marca as duas como distintas. Migração `0008_activity_merge`.
- **Reason**: Pedido do usuário em 2026-11-19 (revisão simplificada: processos reais têm mais de 100 atividades, as que não pontuam se misturavam às válidas, a duplicada aparecia como segunda linha e "Validar" podia deixar 0 ponto por falta de categoria). Desenho aprovado em 2026-11-19; D1 a D4 em `design.md`.
- **Trade-off**: A coluna em vez de um valor `MESCLADA` em `activity_status` evita um `ALTER TYPE ... ADD VALUE` que não se desfaz (como o `DELETE` da `0007`) e mantém o `downgrade` em `DROP COLUMN`; em troca, a lista da Etapa 3 e os cálculos precisam ignorar as mescladas. `NO ACTION` deixa o `DELETE` do processo (AD-018) apagar tudo numa instrução, com a checagem ao fim dela. A lista vem inteira e a paginação, a busca e os filtros rodam no navegador (D3). A mesclagem fora da escrita e da abertura da Etapa 3 não existe: `find_duplicates` é O(n²). AD-012 preservado: as versões já geradas não mudam, só as gerações novas usam a regra. A migração `0008` só vai à VM num deploy autorizado pelo usuário.
- **Implementation**: T1-T42, as correções T45-T55 (lotes 1 a 6) e T56-T62 (rodada 1 do Verifier: 3 mutantes mortos, teste de mesclada nos três documentos, `ATIVIDADE_SEM_CATEGORIA` no worker, decisões do Verifier na spec). Gate final no HEAD: backend `ruff` limpo e 5281 testes passando (3 `deselected`, `maritalk_live`); frontend `lint` e `build` limpos e 563 testes passando em 41 arquivos.
- **Open questions**: (1) itens `VALOR_INFORMADO` não têm campo de pontos na interface depois da EDT-01 (o servidor aceita `informed_points` e `points_override`, nenhum formulário os mostra). Conferido em 2026-11-19: a tabela oficial UFPA, a única ligada às unidades (FASI e IFCH), não tem nenhum item `VALOR_INFORMADO`; o I.3 ("Avaliação pelo corpo discente, até 10 pontos") só existe na tabela antiga do IFCH (Res. 4.644/2015) e no rascunho da FASI, que nenhuma unidade usa. Nada a construir agora; se uma tabela com esse tipo de item voltar a ser usada, a escolha do usuário é o campo "Pontos" no editor da Etapa 4 (opção A); (2) as telas de arranjo do Comprovante e o rascunho do relatório respondem 422 enquanto houver atividade válida sem categoria.
- **Scope**: `revisao-simplificada` (VAL, SEC, DUP, SEG, EDT, QTD), `documentos-gerados` (`eligible_activities`, `load_generation_inputs`, SEG-05), `gestao-processos` (DELETE com a chave nova)
- **Date**: 2026-11-19
- **Status**: active

## Handoff

- **Feature**: `.specs/features/inteligencia-documental` (Complex): **implementada**, Fases 1-17 (T1-T140) commitadas na branch `feat/inteligencia-documental` (empilhada sobre `feat/pontuacao` sobre `feat/fundacao`; main intocada). PRs abertos no GitHub: #1 `feat/fundacao`, #2 `feat/pontuacao`, #3 `feat/inteligencia-documental`. Depois: `documentos-gerados` (implementada e verificada, ver abaixo) → `banca-parecer` → `normativo` → `implantacao`
- **Rodada 8 (documento fora do interstício, T141-T145, FORA-01..09)**: implementada e commitada (AD-016); regra pura `document_period.py`, analisador sem atividade para o documento fora, API com `outside_interstice`, `document_date` e datas do interstício, 409 `DOCUMENTO_FORA_DO_INTERSTICIO` em Classificar e Criar atividade (vínculo), faixa e resumo na Etapa 2; sem migração; Verificador independente rodou (`verification-fora.md`, 50 mutantes, 43 mortos, 3 equivalentes e 4 lacunas de teste, estas fechadas no frontend): FORA-01, 02, 04 a 09 `Verified`, FORA-03 `Verified` em 2026-11-18 depois da T146 (AD-019: a atividade ligada só ao documento fora é rejeitada com auditoria, também a editada ou validada), pelo Verificador B de `documentos-gerados` (`verification-b.md`, mutantes T01 a T11 mortos, execução real no navegador); lacuna B14 (data do documento tirada de um período) fica com o backend
- **Rodada 7 (interface, T118-T140, UIM-01..23)**: Etapas 2, 3 e 4 com colunas legíveis, botões curtos que agem na hora, modais (`Modal`), sem campo de justificativa (o backend aceita e grava se enviada), regra de confiança de 70%, selecionar todas e validar por confiança, valor unitário manual por atividade (migração **0005**, `unit_points_override`); precisa de novo deploy com `alembic upgrade head`; em "Resolution (round 7)" com a verificação independente (32 mutantes, 26 mortos, 7 sobreviventes fechados em T139); decisões pendentes listadas lá
- **Verificação**: quatro passagens do Verificador independente (`validation.md`: passagem 1 FAIL, 2, 3 e 4 PASS com lacunas) e seis rodadas de correção (fases 11-16; REAL, VER, SEG, TER, QUA, CER = 139 requisitos). A rodada 6 (T113-T117, CER-01..05) corrige o certificado em inglês de participação com carga horária (tipo `CERTIFICADO`, enquadramento em VII.10 com o alerta `ENQUADRADO_COMO_CAPACITACAO`, prompt em inglês): precisa de novo deploy; em "Resolution (round 6)", não re-verificada; A Fase 15 (T107-T112: rótulo de equipe e nome de outra pessoa na coordenação, negação da indexação, redação comum de extensão, pinos dos mutantes sobreviventes, variantes numeradas, registro) está em "Resolution (round 5)" e **não foi re-verificada pelo Verificador**; QUA-01..06 seguem `Implementing`
- **Gate no HEAD** (`969273e`, cópia limpa): backend `ruff` limpo e 5048 testes passando (3 `maritalk_live` desmarcados); frontend `eslint` limpo, build e 374 testes passando com `REQUIRE_DIST=1`; teste de aceitação da `tabela-oficial` (211 pontos) verde
- **Decisões pendentes do usuário**: (1) regra de fração de ano para o Vice (cerca de 3,5 meses, 20 pontos por ano; hoje vale 0 por ano completo); (2) política do nome parcial do docente (D1: 5 documentos do próprio docente vão para revisão porque o texto traz só 2 dos 3 nomes); (3) atividade rejeitada em validação em lote; (4) unidade do VIII.36 ("por unidade" na tabela, "ano/revista" na descrição); (5) política da quantidade 0 (item por ano com menos de um ano completo vale 0 e pede a quantidade); (6) se "por mais N anos" sem "prorrogável" é prazo; (7) a regra de contenção de títulos (um título dentro do outro, na mesma página, tipo e data, vira uma atividade; títulos que diferem por numeral ou letra isolada, como "Nível 1" e "Nível 2", já não se reúnem desde T111)
- **Feature `documentos-gerados`** (Complex, 79 requisitos TAB, CMP, ARR, REL, VER, UIG, DEL e ORD, T1-T125): **concluída e verificada, implantação aprovada pelo usuário e em preparação**. Tabela, Relatório e Comprovante, versões imutáveis, conclusão com exclusão dos documentos de entrada e Etapa 5 estão commitadas na branch `feat/inteligencia-documental` (AD-011 a AD-015, AD-019). Dois Verificadores independentes (`verification-a.md` e `verification-b.md`, ambos PASS) e a rodada de correção T112-T125 (commits `2c18cf0..969273e`); relatório consolidado em `.specs/features/documentos-gerados/validation.md` (PASS): 79 requisitos `Verified` (CMP-01 e REL-12 fechados pelas decisões do usuário de 2026-11-18: critério do CMP-01 alinhado ao sumário com o título do item cortado, REL-12 limite conhecido aceito, AD-020); sensor com 308 mutantes, 281 mortos, 8 equivalentes e 19 lacunas de teste fechadas; gate no HEAD `969273e`: backend `ruff` limpo e 5048 testes passando, frontend lint limpo, build ok e 374 testes passando. **T110** (contagem de páginas com rotação e recorte no corpus real) está **adiada por tempo indeterminado (decisão do líder, sem necessidade funcional; o usuário disse "faça a melhor escolha, não sei decidir")**, sem ler `Documentos/`; o fallback `PAGINA_RASTERIZADA` já está implementado e testado e o usuário pode reabrir a tarefa
- **Implantação de `documentos-gerados`**: o usuário aprovou publicar na VM ("Sim", 2026-11-18); o deploy está sendo preparado a partir do HEAD depois do commit que registra essas decisões, e ainda não foi feito: a VM continua em `b58e276` (migração 0005) e nada foi enviado. Cada ação remota (push, envio das imagens, `up`) segue o roteiro de `docs/deploy/vm.md`. O `alembic upgrade head` aplica `0006_generated_documents` e depois `0007_process_purge` (a 0007 depende da 0006, é de `gestao-processos` e entra junto se a imagem sai de um commit que contém `b88b178`, como o HEAD); o `ALTER TYPE ... ADD VALUE` da 0007 não se desfaz e o retorno seguro é o dump anterior; a API de excluir processo (0007) entra no ar sem a tela de arquivar e excluir do Painel (T5 e T6 de `gestao-processos`), que **não está commitada** (arquivos de outra sessão: `frontend/src/api/types.ts`, `pages/Dashboard*`, `components/ProcessDialogs.tsx`); aceito pelo padrão do líder, sem objeção do usuário; a conclusão do processo é irreversível e a VM não tem backup; notas em `docs/deploy/vm.md`
- **Decisões do usuário em `documentos-gerados` (2026-11-18)**: aprovada a publicação na VM; REL-12 aceito como limite conhecido (AD-020); `raw_json` mantido (AD-021); títulos do Relatório ("RELATÓRIO DE ATIVIDADES" e das seções) confirmados contra o modelo real; CMP-01 alinhado (título do item cortado com reticências no sumário, números completos); T110 adiada pelo líder. **Decidido em 2026-11-19**: a Tabela de Pontuação fica depois do Relatório na ordem do dossiê (`dossier_order.json`, ORD-01), como já está. **Ainda pendentes**: (b) quem pode concluir (padrão: qualquer usuário com acesso, pela regra de `ChangeProcessStatus`); (c) estimativa de 60 MB no pedido do Comprovante (A-D6, não implementada); (d) itens cosméticos (cabeçalhos "Tamanho" e "Confiança" da Etapa 2, dois botões "Fechar" na conclusão); (e) redação do critério DEL-12 (não há rota de página); (f) a lista antiga de decisões de `inteligencia-documental` acima
- **Próximo passo**: deploy de `documentos-gerados` na VM, aprovado pelo usuário, a partir do HEAD depois do commit que registra as decisões (a VM está em `b58e276`; a imagem nova traz as migrações 0006 e 0007; o `docs/deploy/vm.md` tem o roteiro, o ponto de retorno e o aviso de irreversibilidade, e a nota de "só descreve" ali precisa ser atualizada quando o deploy rodar). Em seguida os pontos ainda pendentes acima e `banca-parecer`. Nenhum push, deploy, acesso à VM ou chamada real à MariTalk foi feito até este registro
- **Dívidas**: teste de 360 px só estático; sem backup; sem troca de senha; rotas de negócio devolvem 500 com banco fora do ar; `api/client.ts` só envia JSON; Grupo I do caso real com 16 pontos sem explicação; mínimos das classes novas sem regra; antivírus ausente na VM; itens informativos da passagem 2 (PIPE-02/ACC-02, `--fake-ai`, teste de lock, nginx do servidor fora do repositório, data final inclusiva); limites conhecidos da Fase 15 em "Resolution (round 5)" (pesquisadora e coordenadora na mesma frase vai para revisão; título de projeto com duas palavras capitalizadas entre papel e nome idem); D3, D5, D6 e D7 de `corpus-reports/ANALISE.md` são variação da IA ou dado a revisar
- **Documentos reais** (`Documentos/`, não versionados): 44 PDFs e 1 PNG; só scripts locais os leem (`corpus-reports/` fica fora do git)
- **MariTalk**: `sabia-4-thinking` em `https://chat.maritaca.ai/api` (Bearer), saída em JSON estrito; modelo do `.env`; erro de modelo cai em `sabia-4-br-sp`
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; ver `docs/deploy/vm.md`). **No ar desde 2026-11-19 (noite): commit a136faf (`revisao-simplificada` verificada com PASS, migração 0008 `activity_merge`, head 0008 na VM; retorno pelas imagens `merge-pre-a136faf` e dump `progressao-pre-revisao-simplificada-2026-11-19.sql.gz`; fumaça sintética 17 de 17; branch publicada, PR #3 atualizado).** Antes, desde 2026-11-19: commit 62c9c04 e, só no frontend, d3823fc (Painel com Arquivar e Excluir, `gestao-processos` verificada; retorno `painel-pre-d3823fc`) (`documentos-gerados` completa, regra de documento fora do interstício, migrações 0006 e 0007; retorno pelas imagens `docs-pre-62c9c04` e dump `progressao-pre-documentos-gerados-2026-11-19.sql.gz`; fumaça sintética aprovada). Antes, desde 2026-11-18: commit b58e276 (rodadas 5 a 7: certificado em inglês, Etapas 2, 3 e 4 da interface, migração 0005 `unit_points_override`; retorno pelas imagens `round5-d6dca43` e `inteligencia-9533966`, dump `backups/progressao-pre-round7-2026-11-18.sql.gz`) (`fundacao` + `pontuacao` + `tabela-oficial` + `inteligencia-documental`, até a Fase 14), migração 0004, tabela oficial UFPA semeada (FASI e IFCH associadas; tabelas antigas arquivadas; a VM não tinha processos), chave MariTalk configurada no `.env` da VM, nginx do servidor e do projeto com `client_max_body_size 120m`, backend com `mem_limit` 384 MB (uso em repouso 96 MB). Os commits da Fase 15 não têm migração nem mudança de configuração: só código do backend e testes. Pontos de retorno: imagens `pontuacao-369f710` e `fundacao-360eefb`, dump `backups/progressao-pre-docs-2026-11-18.sql.gz`, cópias de configuração em `backups/`. Credenciais do ADMIN em /opt/progressao/.admin-credentials
- **Uncommitted files**: `frontend/src/api/types.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Dashboard.test.tsx` e `frontend/src/components/ProcessDialogs.tsx` (trabalho de outra sessão, tela de arquivar e excluir de `gestao-processos`); `test/` e `requeriment.txt` sem versionar
- **Branch**: feat/inteligencia-documental

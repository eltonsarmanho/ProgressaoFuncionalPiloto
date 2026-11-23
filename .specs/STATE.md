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
- **Status**: superseded in part by AD-019 (atividades editadas ou validadas); a parte "linha de 0 ponto" (`FORA_DO_INTERSTICIO` e rejeitada nas Etapas 3 e 4) foi substituída pela AD-022, que leva essas atividades à seção de não válidas e as tira da Etapa 4; o seletor da Etapa 3 e o `DOCENTE_DIVERGENTE` seguem valendo

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
- **Status**: active; a parte "linha rejeitada de 0 ponto nas Etapas 3 e 4" foi substituída pela AD-022, que leva as atividades rejeitadas ou fora do interstício à seção de não válidas da Etapa 3 e as tira da Etapa 4, dos documentos gerados e da pontuação

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
- **Open questions**: (1) itens `VALOR_INFORMADO` não têm campo de pontos na interface depois da EDT-01. Com a tabela oficial, o servidor recusa `points_override` em todos os critérios (422) e grava `informed_points` sem efeito, porque só um critério `VALOR_INFORMADO` o lê (corrigido em 2026-11-19 pela auditoria de consistência). Conferido em 2026-11-19: a tabela oficial UFPA, a única ligada às unidades (FASI e IFCH), não tem nenhum item `VALOR_INFORMADO`; o item de valor informado de tabelas antigas, inexistente na tabela oficial, só existia na tabela antiga do IFCH (Res. 4.644/2015) e no rascunho da FASI, que nenhuma unidade usa. Nada a construir agora; se uma tabela com esse tipo de item voltar a ser usada, a escolha do usuário é o campo "Pontos" no editor da Etapa 4 (opção A); (2) as telas de arranjo do Comprovante e o rascunho do relatório respondem 422 enquanto houver atividade válida sem categoria.
- **Scope**: `revisao-simplificada` (VAL, SEC, DUP, SEG, EDT, QTD), `documentos-gerados` (`eligible_activities`, `load_generation_inputs`, SEG-05), `gestao-processos` (DELETE com a chave nova)
- **Date**: 2026-11-19
- **Status**: active

### AD-023
- **Decision**: O Grupo I (docência, I.1 e I.2) entra no Total geral a 1 ponto por hora de PIT, pela versão nova da tabela oficial UFPA ("Tabela oficial de pontuação UFPA, Grupo I no total"), com o grupo 1 `counts_in_total` verdadeiro e o VI.14 a 3 pontos por ano, como diz o texto da planilha. A versão anterior fica marcada como substituída (`scoring_table_versions.superseded_by_id`, migração `0009`): não é sugerida nem escolhível. No deploy, todo processo em `RASCUNHO` ou `EM_ANDAMENTO` que a usa passa sozinho para a nova, com um evento de auditoria por processo; `CONCLUIDO`, `ARQUIVADO` e documentos já gerados não mudam (AD-012), e a Etapa 5 avisa quando a última Tabela foi gerada com outra versão. A oferta do Grupo I só com período letivo fica fora do interstício quando o ano inteiro está fora. A Tabela de Pontuação não traz nada de Comprovante nem de status. Pontos digitados no Grupo I são recusados em qualquer tabela: é exceção registrada à regra 7 do `CLAUDE.md` (as horas de PIT vêm só do cálculo).
- **Reason**: Decisões do usuário em 2026-11-19 depois de gerar os documentos reais ("o Grupo deve estar dentro do Total, não deve ficar separado"; "VI.14 são 3 pontos"; "Comprovante e status, se houver"). Substitui a decisão de 2026-11-17, que não tinha AD: a planilha oficial como única fonte, com o Grupo I em horas fora do total e o VI.14 a 6 pontos (fórmula `C*6` da célula), registrada só em `docs/referencias/normas/FONTES.md` e no `notes` de `ufpa.json`.
- **Trade-off**: A troca automática é a única mudança de processo feita sem pedido do usuário, por isso é auditada, restrita aos estados editáveis e idempotente. A versão nova entra pelo seed (sem copiar dados para o Alembic); a `0009` é só de esquema. Processos concluídos com a versão antiga seguem sem o Grupo I.
- **Implementation**: feature `grupo-i-no-total` (spec e design aprovados em 2026-11-19; D1 a D12 em `design.md`). Implementada em 2026-11-20 (T1 a T33 commitadas na branch `feat/inteligencia-documental`; a verificação independente T34 vem depois). Até o deploy dela, o sistema no ar segue com o Grupo I fora do total e o VI.14 a 6; o roteiro do deploy está em `docs/deploy/vm.md` (seção "Deploy do Grupo I no total"), sem nada executado.
- **Scope**: `grupo-i-no-total`; substitui PIT-01..03 e TELA-01..02 de `tabela-oficial`, TAB-03 e TAB-05 de `documentos-gerados`
- **Date**: 2026-11-19
- **Status**: active

### AD-024
- **Decision**: As regras institucionais citam a norma por `norm_code`, um código de texto resolvido na tabela `norms` (sem chave estrangeira), além do texto de `norm_reference`, que continua dizendo o artigo. Cada estrutura de carreira (`career_versions.norm_code`), cada versão de tabela de pontuação (`scoring_table_versions.norm_code`) e cada regra de titulação (`required_titration` por classe e `required_titration_norm_code` na definição JSONB da versão) guarda o código; o alerta do domínio ganha `norm_code`; os casos de uso resolvem os códigos dos alertas numa só consulta (`cite_norms`) e a API devolve `norm_code`, `norm_title`, `norm_url`, `norm_file_url` e `norm_archived`. Código sem norma cadastrada vira alerta só com o texto, com um aviso no log do backend. A norma nunca é excluída: só arquivada, e continua citada com "(arquivada)". Só o ADMIN escreve; toda pessoa autenticada lê a lista e abre a fonte ou o arquivo (PDF de até 20 MB, em `storage/norms/`). O servidor informa a classe, a denominação e o nível de origem e de destino do processo, e nenhum caminho do sistema deduz a classe seguinte, a denominação nem o nível: o movimento fora da sequência usual (salto) emite `MODALIDADE_INCOMPATIVEL` como `ALERTA`, não mais como `ERRO`, e `TITULACAO_INSUFICIENTE` (também `ALERTA`) confere a titulação do docente quando a classe pretendida difere da atual. Os alertas nunca bloqueiam (AD-002). Migração `0010_norms` só de esquema; as ligações dos dados que já estão na VM entram pelo seed, idempotente e auditado (`actor` nulo), como na AD-023.
- **Reason**: Pedido do usuário em 2026-11-20: uma base de normas e regras de elegibilidade, sem IA; só a titulação como verificação nova; mínimo da estrutura nova continua "não definido"; origem e destino informados pelo servidor porque as denominações mudam com o tempo e a carreira tem saltos. Spec e design aprovados em 2026-11-22 (`.specs/features/normativo/`).
- **Trade-off**: Sem chave estrangeira, o código pode apontar para uma norma ausente; o tratamento é o alerta só com o texto e o aviso no log, em troca de migrar antes do seed. Um código por alerta: o alerta tem uma fonte principal, e o texto de `norm_reference` continua citando as duas normas quando cita. O texto do alerta de salto deixa de impedir: quem informa um salto legítimo segue em frente, e a confirmação da norma é do usuário. Documentos já gerados guardam só `norm_reference` e não mudam (AD-012). Tabelas legadas arquivadas (IFCH e FASI) ficam sem `norm_code`. A migração `0010` e as ligações do seed só chegam à VM num deploy autorizado, com dump antes; o roteiro está em `docs/deploy/vm.md` (seção "Deploy das normas"), sem nada executado.
- **Implementation**: feature `normativo` (T1 a T29 na branch `feat/inteligencia-documental`; a verificação independente T30 vem depois). Testes que mudaram por causa do requisito novo (NMOV-02/03: `ERRO` virou `ALERTA`) estão nos commits de T1.
- **Scope**: `normativo` (NBASE, NLINK, NTIT, NMOV, NLIST, NMIN); toca `inteligencia-documental` (verificação do processo) e `tabela-oficial` (versão de tabela)
- **Date**: 2026-11-22
- **Status**: active

### AD-025
- **Decision**: A portaria da banca é uma entidade própria (`board_ordinances`, uma por processo), fora de `documents`, com o arquivo no mesmo armazenamento de entrada do processo (`uploads/<processo>`) e o estado da leitura na própria linha (`SEM_ARQUIVO`, `PENDENTE`, `LENDO`, `LIDA`, `FALHOU`). Nenhuma consulta das Etapas 2 a 5, do vínculo, do Comprovante, da conclusão ou da exclusão a vê por acidente (PORT-09). A leitura é um executor novo na thread única do worker (AD-008), depois da geração e da redação e antes do OCR: extrai o texto, mascara (EXT-07), manda só o texto mascarado à MariTalk com schema estrito, confere cada valor no texto original da página citada (AD-009) e nunca sobrescreve o que a pessoa digitou. O Parecer e o Requerimento são dois tipos novos de documento gerado (`generated_kind` ganha `REQUERIMENTO` e `PARECER`), com versão imutável, fila e instantâneo da AD-012, e o texto de ambos é montado por regras puras do domínio, sem IA (PAR-11, REQ-08). A conclusão do Parecer (`FAVORAVEL` ou `DESFAVORAVEL`) é sempre escolhida pela pessoa: sem valor inicial, nunca sugerida pelo total nem pelo mínimo (PAR-12, regra 1). O Parecer copia os totais do instantâneo da última Tabela `PRONTO` e é recusado com `TABELA_DESATUALIZADA` se o total atual ou a versão da tabela de pontuação mudou. A classe, a denominação e o nível dos documentos são os seis campos que o servidor digitou na Etapa 1 (AD-024). O checklist do dossiê vem do `dossier_order.json` (nove itens, cada um com `key` e `source`), com as marcas "Entregue" em `dossier_deliveries`; o botão Concluir sai da Etapa 5 e vai para a Etapa 7, e a confirmação avisa, sem bloquear, o que da banca ainda não foi gerado ou registrado (DOS-07). A navegação passa a ter sete etapas.
- **Reason**: Pedido do usuário em 2026-11-20: fechar o ciclo depois da Etapa 5 com o Requerimento pelo modelo público da PROGEP, a portaria da banca lida do PDF e conferida, a minuta do Parecer e o checklist do dossiê; só docente e secretaria usam o sistema, a banca recebe os arquivos por fora; a IA nunca decide nem redige o resultado. Um `Document` com papel novo exigiria filtro em nove lugares e esbarraria no SHA-256 único por processo. Spec, design e tarefas aprovados em 2026-11-22 (`.specs/features/banca-parecer/`).
- **Trade-off**: O arquivo da portaria divide o armazenamento e o limite de 20 MB do processo, mas sai na conclusão com os demais arquivos de entrada (número, data e membros ficam; o `raw_json` da leitura também, como o da AD-021). A leitura ocupa a thread única do executor: uma portaria por processo, curta, com o OCR das Etapas 2 esperando na fila (AD-008). O `ALTER TYPE generated_kind ADD VALUE` da migração `0011` não se desfaz: o `downgrade` remove as tabelas e os enums novos, mas `REQUERIMENTO` e `PARECER` ficam no tipo, então o caminho seguro de volta é o dump. A auditoria da portaria guarda número, data, contagens e campos alterados, nunca o nome de um membro (terceiro). Tabela gerada antes desta feature não guarda o mínimo no instantâneo: o Parecer usa o mínimo calculado na hora (o total já foi conferido igual). A carreira do Requerimento vem da estrutura do docente, e só `MAGISTERIO_SUPERIOR` existe; código desconhecido deixa as duas opções sem marca. Ficam fora o modelo de Requerimento da FASI, a parte "REVISÃO" do modelo da PROGEP, o perfil de membro da banca, o protocolo no SIPAC e as verificações de elegibilidade (`normativo`). Concluir sem Requerimento ou Parecer é permitido, com aviso.
- **Implementation**: feature `banca-parecer` (T1 a T50 na branch `feat/inteligencia-documental`; a verificação independente T51 vem depois). A migração `0011_board_opinion` (`down_revision = "0010"`) só chega à VM num deploy autorizado, depois da `0010` do `normativo` e com dump antes; o roteiro está em `docs/deploy/vm.md` (seção "Deploy da banca e do Parecer"), sem nada executado.
- **Scope**: `banca-parecer` (PORT, PAR, REQ, DOS, BNAV); toca `documentos-gerados` (tipos de documento e conclusão), `inteligencia-documental` (executor de leitura e mascaramento) e a navegação do processo
- **Date**: 2026-11-22
- **Status**: active

### AD-026
- **Decision**: O Parecer segue o modelo oficial da banca: o cabeçalho (Universidade Federal do Pará, o campus quando a unidade-mãe é do tipo `CAMPUS`, a unidade), o título "PARECER", a linha de local e data e um parágrafo único com a data por extenso, a Portaria, os titulares, o docente, o interstício, a classe pretendida e a decisão (APROVARAM ou NÃO APROVARAM), seguido das linhas "PRESIDENTE:" e "MEMBRO n:". O documento não imprime Total geral, mínimo de referência, documentos analisados, pontos por grupo nem observações. As recusas (`CONCLUSAO_AUSENTE`, `BANCA_SEM_MEMBROS`, `TABELA_AUSENTE`, `TABELA_DESATUALIZADA`, nessa ordem) e o instantâneo da versão ficam como eram (AD-012); `BANCA_SEM_MEMBROS` passa a valer também para a portaria que só tem suplentes. O campo "observações" sai da tela, da API (corpo com `notes` dá 422) e do repositório; a coluna `board_opinions.notes` fica no banco, sem leitura nem escrita, e sem migração. Os cinco documentos gerados (Tabela, Relatório, Comprovante, Requerimento e Parecer) levam o brasão da UFPA com 2,0 cm de largura, centralizado, como primeiro elemento da primeira página (no Comprovante, só na capa), com 3 mm de espaço abaixo. O brasão é o PNG `backend/app/infrastructure/documents/assets/ufpa.png`, lido do pacote; se o arquivo falta, está vazio ou não é PNG, a geração falha com `EmblemUnavailable`, a versão fecha como `FALHOU` com `ERRO_INTERNO` e nenhum arquivo é guardado. O PDF do Parecer usa a Liberation Sans (título e linha de local e data) além da Serif.
- **Reason**: Pedidos do usuário em 2026-11-23: o Parecer deve ser igual ao modelo oficial da banca e todo documento oficial gerado deve levar o brasão da UFPA no topo.
- **Trade-off**: A coluna `notes` fica morta no banco (retirá-la exigiria uma migração que se desfaz mal e nada ganha). `BANCA_SEM_MEMBROS` agora também recusa a portaria sem titulares. As fontes Liberation Sans Regular e Bold (OFL) entram no repositório ao lado das Serif. Versões já geradas ficam sem brasão e, no caso do Parecer, com o texto antigo (AD-012); só as versões novas mudam. O IFCH sai com o cabeçalho de duas linhas enquanto o ADMIN não ligar a unidade ao campus. A conta do mínimo continua no instantâneo do Parecer, embora o documento não a imprima.
- **Implementation**: feature `layout-oficial` (T1 a T24 na branch `feat/inteligencia-documental`; a verificação independente T25 vem depois). Sem migração e sem semeadura. A imagem do backend precisa ser refeita porque o brasão está dentro de `app`; o roteiro está em `docs/deploy/vm.md` (seção "Deploy do layout oficial"), sem nada executado. Na `banca-parecer`, PAR-03 a PAR-06 e PAR-13 ficam substituídos e PAR-01 alterado.
- **Scope**: `layout-oficial` (PMOD, BRAS); toca `banca-parecer` (Parecer e Etapa 6), `documentos-gerados` (os escritores dos cinco documentos) e a Etapa 6 do frontend
- **Date**: 2026-11-23
- **Status**: active

### AD-027
- **Decision**: A Etapa 1 e a API de processos deixam de ter os cinco campos "Nome do responsável", "Cargo do responsável", "Portaria de designação do responsável", "Unidade administrativa responsável" e "Observações", e o alerta `DADOS_INCOMPLETOS` deixa de existir. As cinco colunas de `functional_processes` ficam no banco com os valores já gravados, sem leitura, exibição nem alteração; o corpo de `POST` e `PUT` que ainda traga as chaves antigas é aceito e as ignora.
- **Reason**: Pergunta do usuário em 2026-11-23: nenhum documento gerado (Tabela, Relatório, Comprovante, Requerimento e Parecer) lê esses campos; o único efeito era o alerta de campo em branco. O usuário escolheu tirá-los da tela e do alerta.
- **Trade-off**: As colunas ficam mortas no banco (retirá-las exigiria uma migração que se desfaz mal e nada ganha, como em AD-026). Se um documento oficial passar a pedir o responsável, o campo volta por uma feature nova, com o documento e a posição definidos.
- **Implementation**: feature `processo-enxuto` (ENX-01 a ENX-07), sem migração e sem semeadura. Imagens novas do backend e do frontend no deploy, que só sai com a autorização do usuário.
- **Scope**: `processo-enxuto`; toca `fundacao` (PROC-01 e o alerta `DADOS_INCOMPLETOS`) e a Etapa 1 do frontend
- **Date**: 2026-11-23
- **Status**: active

### AD-028
- **Decision**: O ADMIN gerencia as tabelas de pontuação pela tela e marca, por unidade acadêmica, a versão em uso (no máximo uma por unidade), que passa a ser a sugestão do processo novo; sem marcação vale a sugestão por vigência de SEL-02. Qualquer tabela pode ser criada e usada, com os avisos que já existem. Arquivar vale para a tabela inteira (reversível); excluir vale para versão ou tabela que nenhum processo usa e que não está em uso de unidade. A versão substituída (AD-023) segue sem poder ser marcada nem escolhida.
- **Reason**: Pedido do usuário em 2026-11-23: um CRUD para gerenciar e selecionar a tabela em uso e uma interface melhor. Respostas: padrão por unidade, qualquer tabela com avisos, arquivar, excluir e editar critérios na tela, layout e ações visíveis.
- **Trade-off**: A regra 11 do `CLAUDE.md` deixa de dizer que a oficial é a única tabela em uso (passa a ser a em uso inicial); mais um conceito (a marcação por unidade) ao lado da escolha por processo; uma migração nova. A sugestão por vigência fica como alternativa para unidade sem marcação.
- **Implementation**: feature `gestao-tabelas` (GTAB-01 a GTAB-45). Imagens novas do backend e do frontend e a migração no deploy, que só sai com a autorização do usuário.
- **Scope**: `gestao-tabelas`; toca `pontuacao` (SEL-02 e a tela de administração, ADM e P3) e `grupo-i-no-total` (AD-023)
- **Date**: 2026-11-23
- **Status**: active

## Handoff

- **Medido em 2026-11-23** (antes do commit que grava este Handoff): HEAD `98992b0`, branch `feat/inteligencia-documental`, `git status --porcelain` só com `backend/img/`, `requeriment.txt` e `test/` sem versionar (o `stash@{0}` antigo não é desta feature e não foi tocado). O `origin/feat/inteligencia-documental` está em `7bb7b84`.
- **Commits locais não enviados**: `git log --oneline 7bb7b84..HEAD` lista `processo-enxuto` (AD-027, sem migração), a spec, o desenho e as tarefas da `gestao-tabelas` e as 37 tarefas da execução (T1 a T37); o commit que grava este Handoff vem depois do HEAD medido. A lista por fase está em `docs/deploy/vm.md` (seção "Deploy da gestão de tabelas", "Commits a publicar").
- **VM**: em `c839d28` (`layout-oficial`, sem migração; antes, `dd5e21f` com `normativo` e `banca-parecer`, migrações `0010` e `0011`, head 0011), no ar desde 2026-11-23 com a autorização do usuário; o registro dos deploys está em `docs/deploy/vm.md`. O `origin` contém o registro desse deploy (`7bb7b84`); os commits de `processo-enxuto` e de `gestao-tabelas` **não foram enviados ao GitHub**; push só com a autorização do usuário.
- **Feature corrente**: `.specs/features/gestao-tabelas` (Large, 45 requisitos GTAB-01 a GTAB-45, AD-028): T1 a T37 implementadas e commitadas (migração `0012_unit_defaults`, marcação da versão em uso por unidade e semente, arquivar e excluir com prévia e bloqueios por código, motivos na lista, a tela em cartões com filtros, diálogos de criar, unidades, duplicar, nova versão, CSV, em uso, arquivar, excluir, editar critério e histórico, e a seção "Deploy da gestão de tabelas" em `docs/deploy/vm.md`). Falta a T38, o Verifier independente (autor diferente; renderização em 360 px e 1280 px num navegador sem cabeça, ou o risco residual registrado), e depois `validate_state.py gestao-tabelas`. O deploy (migração `0012`, imagens novas, dump antes) só sai com a autorização do usuário.
- **Feature seguinte**: depois da verificação de `gestao-tabelas` e do deploy autorizado: `implantacao`. `grupo-i-no-total`, `normativo`, `banca-parecer` e `layout-oficial` já estão no ar; a nota de `processo-enxuto` (verificada) segue junto no próximo deploy.
- **Gate atual** (HEAD `98992b0` mais a documentação da T37, medido em 2026-11-23): backend `ruff` limpo e 6728 testes passando (6727 na rodada completa de 19 min mais o teste instável conhecido `test_a_database_error_while_claiming_does_not_kill_the_thread`, que falhou sob carga e passou ao rodar sozinho; 3 `deselected`, `maritalk_live`); frontend `eslint` limpo, `tsc` e `vite build` ok e 916 testes passando em 61 arquivos.
- **Decisões pendentes do usuário** (`inteligencia-documental`): (1) regra de fração de ano para o Vice (cerca de 3,5 meses, 20 pontos por ano; hoje vale 0 por ano completo); (2) política do nome parcial do docente (D1: 5 documentos do próprio docente vão para revisão porque o texto traz só 2 dos 3 nomes); (3) atividade rejeitada em validação em lote; (4) unidade do VIII.36 ("por unidade" na tabela, "ano/revista" na descrição); (5) política da quantidade 0 (item por ano com menos de um ano completo vale 0 e pede a quantidade); (6) se "por mais N anos" sem "prorrogável" é prazo; (7) a regra de contenção de títulos (um título dentro do outro, na mesma página, tipo e data, vira uma atividade). De `documentos-gerados`: (b) quem pode concluir (padrão: qualquer usuário com acesso, pela regra de `ChangeProcessStatus`); (c) estimativa de 60 MB no pedido do Comprovante (A-D6, não implementada); (d) itens cosméticos (cabeçalhos "Tamanho" e "Confiança" da Etapa 2, dois botões "Fechar" na conclusão); (e) redação do critério DEL-12 (não há rota de página). A pergunta aberta (1) da AD-022 está resolvida: nada a construir enquanto a tabela oficial não tiver item de valor informado.
- **Verificação das features anteriores**: `inteligencia-documental` tem 136 requisitos `Verified` e 35 `Implementing` (SEG-01, UIM-01..23, QUA-01..06, CER-01..05, sem passagem do Verifier com PASS); `tabela-oficial` tem 22 `Verified` e ACE-02 `Pending` (PARTIAL por definição); `documentos-gerados` e `revisao-simplificada` estão `Verified`. T110 de `documentos-gerados` (contagem de páginas com rotação e recorte no corpus real) segue adiada por decisão do líder.
- **Dívidas**: teste de 360 px só estático; sem backup; sem troca de senha; rotas de negócio devolvem 500 com banco fora do ar; `api/client.ts` só envia JSON; Grupo I: os 303 pontos de `grupo-i-no-total` vêm de 92 horas de PIT de um cenário derivado; os documentos reais somam 76 h (auditoria de 2026-11-19, C10); conferir no processo real depois do deploy da versão nova da tabela; mínimos das classes novas sem regra; `reference_minimum` decide o mínimo pelo prefixo do nome da tabela (`backend/app/domain/rules/scoring_verification.py:20,51`), frágil e fora do escopo de `normativo` (AD-024); a URL semeada da Res. 4.644/2015 em `FONTES.md` é uma pasta, não o PDF (o ADMIN anexa o PDF público na página Normas); antivírus ausente na VM; itens informativos da passagem 2 (PIPE-02/ACC-02, `--fake-ai`, teste de lock, nginx do servidor fora do repositório, data final inclusiva); limites conhecidos da Fase 15 em "Resolution (round 5)" (pesquisadora e coordenadora na mesma frase vai para revisão; título de projeto com duas palavras capitalizadas entre papel e nome idem); D3, D5, D6 e D7 de `corpus-reports/ANALISE.md` são variação da IA ou dado a revisar
- **Documentos reais** (`Documentos/`, não versionados): 44 PDFs e 1 PNG; só scripts locais os leem (`corpus-reports/` fica fora do git).
- **MariTalk**: `sabia-4-thinking` em `https://chat.maritaca.ai/api` (Bearer), saída em JSON estrito; modelo do `.env`; erro de modelo cai em `sabia-4-br-sp`.
- **Deploy**: https://progressao.srv1633081.hstgr.cloud (VM compartilhada; ver `docs/deploy/vm.md`). **No ar desde 2026-11-23: commit c839d28 (`layout-oficial`, sem migração; o registro está em `docs/deploy/vm.md`); antes, desde 2026-11-23, `dd5e21f` (`normativo` e `banca-parecer`, migrações 0010 e 0011). Antes disso, desde 2026-11-20: commit f18f162 (`correcoes-auditoria` e `grupo-i-no-total` verificadas com PASS, migração 0009, tabela oficial nova com o Grupo I no total e VI.14 a 3, processo real em rascunho trocado para a versão nova com auditoria; retorno pelas imagens `grupo-i-pre-f18f162` e dump `progressao-pre-grupo-i-no-total-2026-11-20.sql.gz`; fumaça sintética 23 de 23).** Antes, desde 2026-11-19 (noite): commit a136faf (`revisao-simplificada` verificada com PASS, migração 0008 `activity_merge`, head 0008 na VM; retorno pelas imagens `merge-pre-a136faf` e dump `progressao-pre-revisao-simplificada-2026-11-19.sql.gz`; fumaça sintética 17 de 17; branch publicada, PR #3 atualizado).** Antes, desde 2026-11-19: commit 62c9c04 e, só no frontend, d3823fc (Painel com Arquivar e Excluir, `gestao-processos` verificada; retorno `painel-pre-d3823fc`) (`documentos-gerados` completa, regra de documento fora do interstício, migrações 0006 e 0007; retorno pelas imagens `docs-pre-62c9c04` e dump `progressao-pre-documentos-gerados-2026-11-19.sql.gz`; fumaça sintética aprovada). Antes, desde 2026-11-18: commit b58e276 (rodadas 5 a 7: certificado em inglês, Etapas 2, 3 e 4 da interface, migração 0005 `unit_points_override`; retorno pelas imagens `round5-d6dca43` e `inteligencia-9533966`, dump `backups/progressao-pre-round7-2026-11-18.sql.gz`) (`fundacao` + `pontuacao` + `tabela-oficial` + `inteligencia-documental`, até a Fase 14), migração 0004, tabela oficial UFPA semeada (FASI e IFCH associadas; tabelas antigas arquivadas; a VM não tinha processos), chave MariTalk configurada no `.env` da VM, nginx do servidor e do projeto com `client_max_body_size 120m`, backend com `mem_limit` 384 MB (uso em repouso 96 MB). Os commits da Fase 15 não têm migração nem mudança de configuração: só código do backend e testes. Pontos de retorno: imagens `pontuacao-369f710` e `fundacao-360eefb`, dump `backups/progressao-pre-docs-2026-11-18.sql.gz`, cópias de configuração em `backups/`. Credenciais do ADMIN em /opt/progressao/.admin-credentials
- **Branch**: feat/inteligencia-documental

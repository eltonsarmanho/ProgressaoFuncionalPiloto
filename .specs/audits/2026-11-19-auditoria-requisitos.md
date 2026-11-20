# Auditoria de requisitos e consistência (2026-11-19)

Escopo: todas as features em `.specs/features/`, `STATE.md`, `CLAUDE.md`, `docs/`, o código do backend e do frontend e a VM. Leitura só de dados sintéticos e do seed da tabela oficial (`ufpa.json`); `Documentos/` e `Modelos/` não foram abertos.

Legenda da coluna "Conferido": **sim** = o líder reconferiu no código ou na VM; **agente** = apontado por um dos dois auditores independentes e não reconferido item a item.

## 1. Versão na VM

| Item | Situação |
| ---- | -------- |
| No ar | `a136faf` (revisão simplificada), migração `0008`, backend saudável |
| Local, não publicado | `ec3873a` (DELETE remove diretórios vazios) e `0422ac3` (alerta de data das ofertas do Grupo I): código, sem migração |
| GitHub | `origin/feat/inteligencia-documental` em `a136faf`; os commits seguintes não foram enviados |

## 2. Requisitos e etapas que faltam

### Alto

| # | O que falta | Evidência | Conferido | Sugestão |
| - | ----------- | --------- | --------- | -------- |
| R1 | **O processo não sai de "Rascunho" pela interface.** Nenhuma tela envia `EM_ANDAMENTO`; a conclusão (regra 8) exige `EM_ANDAMENTO`, então o docente não consegue concluir nem liberar espaço. A justificativa da Etapa 1 (PROC-13) também nunca é pedida | `backend/app/domain/entities/process.py:23-26`; `frontend/src/components/ProcessDialogs.tsx:29` (única chamada de status de processo, para `ARQUIVADO`); `frontend/src/pages/ProcessGenerated.tsx:120` | sim | Botão "Iniciar processo" no Painel e na Etapa 1 (`RASCUNHO` → `EM_ANDAMENTO`), ou permitir concluir a partir de `RASCUNHO` |
| R2 | **Administração só pela API.** Usuários (criar, listar; sem editar, desativar, trocar papel), unidades (criar, editar, arquivar) e estruturas de carreira não têm tela; o menu do ADMIN só tem "Tabelas de pontuação". Cadastrar um docente com login exige chamada manual à API | `backend/app/presentation/api/users.py:16,34`, `units.py:30-48`; `frontend/src/components/Layout.tsx:12`; `frontend/src/App.tsx` (sem rota de administração além de tabelas) | sim | Story "Administração de usuários, unidades e docentes" |
| R3 | **Sem troca nem redefinição de senha** | `backend/app/presentation/api/auth.py` (só login, logout, me); dívida em `STATE.md` | sim | Troca pelo próprio usuário (senha atual + nova) e redefinição pelo ADMIN |
| R4 | **Sem backup automático**, com duas ações irreversíveis (conclusão apaga os arquivos de entrada; exclusão de processo) e `storage/` sem cópia | `docs/deploy/vm.md` ("Avisos"); dívida "sem backup" em `STATE.md` | agente | Backup diário do banco e do volume, com retenção e restauração testada (`implantacao`) |
| R5 | **Mínimo de pontos sempre "não definido" na estrutura de carreira nova** (Lei 15.141), que é a do interstício real | `backend/app/domain/rules/scoring_verification.py:51-52`; dívida em `STATE.md` | agente | Regra no `normativo`, com a fonte |
| R6 | **Etapas reais da progressão sem requisito**: parecer da banca, requerimento e portaria (`banca-parecer`), protocolo e assinatura, elegibilidade além de interstício e classe; as Etapas 6 a 9 aparecem na navegação como "em breve" sem spec | `frontend/src/components/StepNav.tsx`; `documentos-gerados/spec.md` (fora de escopo) | agente | Specs de `banca-parecer` e `normativo` |

### Médio

| # | O que falta | Conferido |
| - | ----------- | --------- |
| R7 | Histórico do processo (`GET /processes/{id}/history`) sem tela; lista e edição de docentes sem link; arquivar docente sem tela | sim (rota de histórico sem uso no frontend) |
| R8 | LGPD: retenção da auditoria, do JSON da IA e dos docentes; aviso de privacidade; pedidos do titular | agente |
| R9 | Segurança de borda: sem cabeçalhos CSP/HSTS/X-Frame-Options e sem limite de requisições no nginx do projeto; sem antivírus | agente |
| R10 | Banco fora do ar devolve 500 (deveria ser 503); sem métricas nem alertas | agente |
| R11 | QUA-01..06 e CER-01..05 (inteligência documental) nunca passaram pelo Verifier independente | agente |

### Planejado e não feito

`grupo-i-no-total` (28 requisitos, Design revisado aguardando aprovação), `banca-parecer`, `normativo`, `implantacao` (sem spec), T110 de `documentos-gerados`, 7 decisões pendentes de inteligência documental (`STATE.md`).

## 3. Inconsistências (do tipo do I.3)

| # | Gravidade | Afirmação | Fato | Conferido | Correção |
| - | --------- | --------- | ---- | --------- | -------- |
| C1 | Alta | O item VI.14 diz "3 pontos por ano" no texto que o docente lê | O sistema dá 6 pontos por ano (decisão do usuário de 2026-11-17, registrada só em `review_note`). É o único item cujo texto diverge do valor | sim (`ufpa.json`, critério 6.14) | Mostrar o valor decidido junto do texto, ou anotar a descrição |
| C2 | Alta | `STATE.md` e o design da revisão diziam que o servidor aceita `points_override` | Com a tabela oficial, `points_override` dá 422 em todos os 100 critérios; `informed_points` é gravado e não tem efeito | sim (`scoring.py:304-329`) | Corrigido nesta auditoria |
| C3 | Alta | I.3 citado como item existente | Não existe na tabela oficial; só na tabela antiga do IFCH e no rascunho da FASI | sim | Corrigido em `STATE.md` e no design da revisão; ainda citado em `scoring.py:274-276,308-309`, `pontuacao/spec.md:48` e em nomes de testes |
| C4 | Alta | Handoff do `STATE.md` diz que o deploy não foi feito, que a tela de arquivar não está commitada e lista arquivos "uncommitted" | A VM está em `a136faf`; a tela está commitada; o `git status` está limpo; a feature corrente (`grupo-i-no-total`) não aparece | agente | Reescrever o Handoff |
| C5 | Alta | Decisões de 2026-11-17 (planilha como fonte, Grupo I fora do total) e de 2026-11-19 (Grupo I no total) | Nenhuma tem AD no `STATE.md` | agente | AD-023 (a desta feature) com a de 11-17 marcada como substituída |
| C6 | Média | `ScoreEditor` diz que os pontos de `VALOR_INFORMADO` são "lidos do documento" | Nenhum código de extração preenche esse campo (seria contra a regra 1). Hoje a frase não aparece, porque a tabela oficial não tem esse tipo de item | sim (`ScoreEditor.tsx:15-16`) | Trocar o texto ou remover o ramo |
| C7 | Média | Design da inteligência documental: IV.1/IV.2 "por ano", V.1 "por projeto", VI.10/VI.12 "por designação" | A tabela e `quantity_rules.py` contam de outro jeito | agente | Alinhar o design ao código |
| C8 | Média | AD-017 e AD-019 falam em "linha de 0 ponto" para rejeitada e fora do interstício | Depois da AD-022 essas atividades não chegam à Etapa 4 | agente | Anotar a substituição |
| C9 | Média | Testes com nome "caso real" ou "avaliação discente" usam tabela sintética ou cenário derivado (o total 414 do teste em miniatura está obsoleto) | `test_scoring_engine.py:549`, `test_activity_create.py:325`, `test_scoring_golden.py` | agente | Renomear |
| C10 | Média | Os 303 pontos da `grupo-i-no-total` vêm de 92 horas de um cenário derivado; os documentos reais somam 76 h; a dívida "16 pontos do Grupo I" é do modelo antigo | `FONTES.md:43`, `test_scoring_golden.py:91-92` | agente | Escrever "cenário derivado" em toda citação de 211 e 303; reescrever a dívida |
| C11 | Média | `activityBody.ts` reenvia `informed_points` e `points_override` em toda edição: uma atividade antiga com `points_override` gravado receberia 422 em qualquer edição, sem campo para limpar | `frontend/src/activityBody.ts:4` | agente (risco não reproduzido) | Não reenviar campos sem tela, ou limpar ao editar |
| C12 | Baixa | Regra 6 diz "acima de 70%"; o código usa "a partir de 70%" (`>= 0.70`) | `confidence.py`, `trust.ts` | agente | Alinhar o texto da regra |
| C13 | Baixa | A auditoria de consistência disse que o `CLAUDE.md` tem 9 regras | Tem 10 (a regra 10 entrou no commit `69ec5ed`) | sim (achado do auditor descartado) | Nada a fazer |

## 4. Consequência para a feature `grupo-i-no-total`

Com o Grupo I no total, I.1 e I.2 passam a dar pontos sem nenhuma entrada manual (GI-05 recusa `points_override` e a regra 7 recusa `unit_points_override` em carga semanal). Isso é uma exceção à regra 7 do `CLAUDE.md` e entra na AD-023 e no texto da regra quando a feature for implementada.

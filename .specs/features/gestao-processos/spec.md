# Gestão de processos Specification

**Status**: Approved (pedido do usuário em 2026-11-18; padrões abaixo registrados como suposições)

## Problem Statement

No Painel o usuário vê os processos, mas não consegue arquivar nem excluir um. O backend já aceita arquivar (`POST /api/processes/{id}/status`), mas a tela não oferece o botão; excluir não existe. A especificação da `fundacao` previa "arquivamento em vez de exclusão"; o usuário pediu agora as duas ações, então a exclusão definitiva passa a existir, com confirmação e rastro na auditoria.

## Goals

- [ ] Arquivar e excluir um processo direto da lista do Painel.
- [ ] Excluir apaga tudo que pertence ao processo (documentos, arquivos, atividades, documentos gerados) e deixa só o evento de auditoria.

## Out of Scope

| Item | Motivo |
| --- | --- |
| Desarquivar | Não foi pedido; a regra de transição da `fundacao` não o permite |
| Exclusão em lote | Não foi pedido |
| Lixeira / restauração | A exclusão é definitiva (confirmada na tela) |

## User Stories

### P1: Arquivar processo no Painel ⭐ MVP

**Acceptance Criteria**:

1. WHEN o processo não está ARQUIVADO THEN o card do Painel SHALL mostrar o botão "Arquivar".
2. WHEN o usuário clica em "Arquivar" THEN the system SHALL abrir um modal de confirmação ("Arquivar o processo de <docente>? Ele fica somente leitura.") e só arquivar depois da confirmação.
3. WHEN confirmado THEN the system SHALL chamar `POST /api/processes/{id}/status` com `ARQUIVADO` e a versão atual, e o card SHALL passar a mostrar o selo "Arquivado" sem recarregar a página.
4. WHEN o processo já está ARQUIVADO THEN o card SHALL não mostrar "Arquivar".
5. IF o usuário não é ADMIN nem dono do processo THEN the system SHALL responder 403 e o modal SHALL mostrar a mensagem.
6. IF a versão mudou (409) THEN o modal SHALL mostrar o erro e a lista SHALL ser recarregada.

### P1: Excluir processo ⭐ MVP

**Acceptance Criteria**:

1. WHEN o usuário é ADMIN ou dono THEN o card do Painel SHALL mostrar o botão "Excluir" em qualquer status.
2. WHEN o usuário clica em "Excluir" THEN the system SHALL abrir um modal que diz que a exclusão é definitiva e lista o que será apagado (quantidade de documentos de entrada, de atividades e de documentos gerados), e SHALL só excluir ao clicar em "Excluir definitivamente".
3. WHEN confirmado THEN `DELETE /api/processes/{id}` SHALL apagar, na mesma transação, atividades, candidatos, evidências, documentos de entrada (com execuções, páginas e tarefas), documentos gerados (com seus arquivos), rascunho do relatório, arranjo do Comprovante, tarefas de redação e o próprio processo; SHALL responder 204.
4. WHEN o banco confirmou THEN the system SHALL remover do disco os arquivos dos documentos de entrada e dos gerados; IF algum arquivo não puder ser removido THEN the system SHALL registrar o aviso no log (sem caminho completo nem dado pessoal) e a exclusão SHALL continuar válida.
5. The system SHALL gravar um evento de auditoria `DELETE` do processo, com os valores anteriores do processo, e SHALL manter todos os eventos de auditoria anteriores (a auditoria nunca é apagada).
6. IF o usuário não é ADMIN nem dono THEN the system SHALL responder 403; IF o processo não existe ou não é legível THEN 404.
7. IF há documento de entrada em processamento (tarefa de leitura `PENDENTE` ou `PROCESSANDO`) OR geração de documento `GERANDO` OR redação em andamento THEN the system SHALL responder 409 `OPERACAO_EM_ANDAMENTO` e não apagar nada.
8. WHEN a exclusão termina THEN o card SHALL sair da lista e os totais SHALL ser atualizados, sem recarregar a página.
9. IF qualquer passo da transação falha THEN nada SHALL ser apagado (tudo ou nada) e nenhum arquivo SHALL ser removido.
10. WHEN o processo foi excluído THEN qualquer rota do processo SHALL responder 404.

## Edge Cases

- Processo com documentos já excluídos pela conclusão (`ARQUIVO_EXCLUIDO`): sem arquivo para remover; segue normal.
- Processo sem nenhum documento: exclui o processo e os registros auxiliares.
- Dois cliques / duas abas: a segunda chamada recebe 404; o front trata 404 como "já excluído" e recarrega a lista.
- Os documentos gerados são imutáveis por gatilho no banco: a exclusão do processo é a única operação que pode apagá-los (ver design).

## Assumptions

| Suposição | Padrão adotado |
| --- | --- |
| Quem pode excluir | ADMIN ou dono (mesma regra de arquivar) |
| Em quais status | Qualquer um, inclusive CONCLUIDO e ARQUIVADO |
| Justificativa | Não há campo; a confirmação no modal basta (regra 5 do CLAUDE.md vale só para as Etapas 2 a 4, e aqui a auditoria guarda o evento) |
| Docente e unidade | Permanecem; só o processo e o que depende dele saem |

## Requirement Traceability

| ID | Story | Status |
| --- | --- | --- |
| GP-ARQ-01..06 | Arquivar processo no Painel | Verified |
| GP-DEL-01..10 | Excluir processo | Verified |

(Os números seguem a ordem dos critérios acima: ARQ-01 = critério 1 etc.)

## Success Criteria

- [ ] Do Painel, arquivar e excluir funcionam com confirmação; excluir não deixa nenhum registro nem arquivo do processo, só a auditoria.

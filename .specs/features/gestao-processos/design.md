# Gestão de processos Design

**Spec**: `.specs/features/gestao-processos/spec.md`

## Decisões

- **GP-D1 Rota**: `DELETE /api/processes/{id}` → 204. Caso de uso `DeleteProcess` em `application/use_cases/processes.py` (mesma base `_ProcessUseCase`; dono = criador ou docente vinculado, como em `ChangeProcessStatus`; 403 `Forbidden` com mensagem "Apenas ADMIN ou o dono do processo podem excluí-lo").
- **GP-D2 Porta de exclusão**: nova porta `ProcessPurgeRepository` (ou método em repositório existente, a critério do implementador seguindo o padrão de `PurgeRepository` da conclusão) com `busy_reasons(process_id)` e `delete_all(process_id) -> list[StoredFile]`, em `infrastructure/database/repositories.py`. Ordem de exclusão (FKs sem cascade para `functional_processes`): wording jobs, comprovante layout, report draft, generated_files, generated_documents, activities (cascade leva candidatos e evidências), documents (cascade leva runs, pages, jobs, evidências), processo. Coleta antes os caminhos de arquivo (`documents.storage_path` e arquivos gerados) para apagar depois do commit.
- **GP-D3 Imutabilidade**: os gatilhos `generated_documents_guard` e `generated_files_guard` bloqueiam DELETE. A migration `0007` recria as funções de gatilho para deixar passar DELETE quando `current_setting('app.process_purge', true) = 'on'`; o repositório executa `SET LOCAL app.process_purge = 'on'` só dentro da transação da exclusão. UPDATE continua bloqueado sempre. Teste prova: DELETE direto continua falhando; DELETE sob a configuração passa; fora da transação a configuração não vale.
- **GP-D4 Ocupado**: 409 `OPERACAO_EM_ANDAMENTO` se existir `processing_jobs` com status `PROCESSING`/`PENDING` (a critério: só os que de fato rodam; documentos na fila contam) de documentos do processo, `generated_documents.status = GERANDO` ou `report_wording_jobs` em andamento.
- **GP-D5 Arquivos**: depois do `commit`, `LocalStorage`/`GeneratedStorage` removem os arquivos; falha de remoção só vira log (`logger.warning` com id do documento, sem caminho).
- **GP-D6 Auditoria**: `AuditService.record(... AuditAction.DELETE, before=audit_view(process), after=None)`; confirmar que `audit_logs` não tem FK para o processo (a trilha sobrevive).
- **GP-D7 Prévia do modal**: contagens vêm de um campo novo em `ProcessSummary`? Não: usar `GET /api/processes/{id}/delete-preview` → `{documents, activities, generated_documents}` (apenas contagens, sem dado pessoal). Caso de uso `GetProcessDeletePreview` (leitura, ADMIN/dono ou qualquer leitor? só quem pode excluir; senão 403).
- **GP-D8 Front**: em `Dashboard.tsx`, cada card ganha botões "Arquivar" (se status ≠ ARQUIVADO) e "Excluir" (sempre; o servidor decide o 403 e a mensagem aparece no modal). Modais usam o componente de modal já existente nas Etapas 2 a 4 (`components/`); sem campo de justificativa. `ProcessSummary` precisa trazer `version` (verificar se já traz). Após sucesso: atualizar o estado local (arquivar → troca status e version; excluir → remove da lista e totais recalculam).
- **GP-D9 Documentação**: AD-018 em `.specs/STATE.md` (exclusão definitiva de processo passa a existir; revisa a linha "arquivamento em vez de exclusão" da fundacao para processos) e regra 9 em `CLAUDE.md`.

## Riscos

- Esquecer uma tabela dependente → o teste de integração cria um processo com todos os tipos de dependente (documentos com páginas/execuções/tarefas, atividades com evidências, documento gerado com arquivos, rascunho, arranjo, tarefa de redação) e depois confere `count(*) = 0` em cada tabela ligada ao processo e que os arquivos sumiram do disco temporário; um teste de arquitetura/esquema percorre `information_schema` por FKs que apontam para `functional_processes` e falha se aparecer tabela nova sem tratamento.

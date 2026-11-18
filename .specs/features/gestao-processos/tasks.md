# Gestão de processos Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. If the skill cannot be activated, STOP and tell the user.

**Design**: `.specs/features/gestao-processos/design.md` · **Spec**: `.specs/features/gestao-processos/spec.md` · **Status**: Pending

Regras: teste primeiro; só dados sintéticos; `Documentos/` e `Modelos/` nunca são abertos; um commit por tarefa (Conventional Commits, com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`), marcando a tarefa neste arquivo no mesmo commit; sem push nem deploy.

Gates: backend `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`; frontend `cd frontend && npm test -- --run && npm run build && npx eslint .`.

## Tasks

- [x] **T1 Migration 0007 (gatilhos com exceção de exclusão do processo)** — GP-D3. Teste de integração em `tests/integration/`: DELETE direto em `generated_documents`/`generated_files` falha; sob `SET LOCAL app.process_purge='on'` passa; UPDATE segue bloqueado; a configuração some depois do commit; downgrade restaura. Atualizar `test_models_match_migrated_schema` se preciso.
- [x] **T2 Repositório de exclusão** — GP-D2, GP-D4. `busy_reasons`, `counts`, `delete_all` com coleta dos caminhos de arquivo. Testes de integração com processo completo (todas as dependentes) → zero linhas em cada tabela; teste que varre as FKs para `functional_processes`; tudo-ou-nada (falha forçada no meio não apaga nada); ocupado detectado em cada um dos 3 casos.
- [x] **T3 Caso de uso DeleteProcess + prévia** — GP-DEL-03..07, 09, 10; GP-D1, D5, D6, D7. Testes de integração: ADMIN, dono, não dono (403), inexistente (404), ocupado (409), arquivos removidos do disco, falha de remoção só loga, auditoria `DELETE` criada e eventos antigos mantidos, status CONCLUIDO/ARQUIVADO podem ser excluídos.
- [x] **T4 Rotas e schemas** — `DELETE /api/processes/{id}` (204) e `GET /api/processes/{id}/delete-preview`, CSRF exigido, containers ligados (`container.py`), `ProcessSummary.version` se faltar. Testes de API: 204/403/404/409/401/CSRF, rota do processo → 404 depois.
- [ ] **T5 Front: Arquivar no Painel** — GP-ARQ-01..06. Modal, chamada, atualização local, erros 403/409. Testes de componente.
- [ ] **T6 Front: Excluir no Painel** — GP-DEL-01, 02, 08 e Edge (404 = já excluído). Modal com prévia, "Excluir definitivamente", atualização local, erro 403/409 (`OPERACAO_EM_ANDAMENTO` com mensagem legível em `labels.ts`). Testes de componente; eslint + build.
- [ ] **T7 Documentação** — AD-018 em `.specs/STATE.md`, regra 9 em `CLAUDE.md`, rastreabilidade da spec marcada Verified, nota na `fundacao/spec.md` (linha do ciclo de vida).
- [ ] **T8 Verifier independente** — agente diferente do autor confere GP-ARQ-01..06 e GP-DEL-01..10 com evidência (testes + leitura do código) e mutantes (ex.: esquecer uma tabela, não checar dono, não bloquear ocupado); relatório em `.specs/features/gestao-processos/verification.md`.

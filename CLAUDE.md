# ProgressãoDocente UFPA

Sistema que ajuda o docente a montar o processo de progressão funcional: documentos de entrada, atividades, pontuação pela tabela oficial e documentos finais (Tabela de Pontuação, Relatório de Atividades e Comprovante).

Stack: FastAPI (Python 3.12), SQLAlchemy 2.x, Alembic, PostgreSQL, React/TypeScript. A IA é a MariTalk, chamada só pelo backend.

## Metodologia

Use exclusivamente a skill `tlc-spec-driven` (Specify → Design → Tasks → Execute), com validadores, um commit atômico por tarefa e Verifier independente. As especificações ficam em `.specs/features/<feature>/` e as decisões em `.specs/STATE.md`. Valide cada fase com o usuário.

## Regras de negócio

1. **Pontuação determinística.** Os pontos são calculados em Python pelo motor de pontuação, nunca pela IA. A IA só sugere; o usuário valida.
2. **Origem de cada valor.** Todo valor extraído guarda o documento e a página de origem, e só vale se o texto da página o comprova.
3. **Interstício (Etapa 1).** O processo tem um período de interstício; só o que aconteceu dentro dele conta.
4. **Documento fora do interstício (Etapa 2).** O documento cujas atividades com data estão todas fora do interstício aparece na Etapa 2 com um aviso destacado ("Fora do interstício (dd/mm/aaaa a dd/mm/aaaa): não será processado nas próximas etapas"), com o alerta `DOCUMENTO_FORA_DO_INTERSTICIO`. Ele não gera atividade e não aparece nas Etapas 3, 4 e 5 (atividades, pontuação, Tabela, Relatório, Comprovante). Se ao menos uma atividade está dentro do período ou o cruza, o documento é processado normalmente e a atividade fora do período segue como `FORA_DO_INTERSTICIO`. Sem data utilizável, a regra não se aplica. A regra é reavaliada ao reprocessar o documento. Especificação: `inteligencia-documental`, requisitos `FORA-01..09`.
5. **Sem justificativa nas Etapas 2, 3 e 4.** Excluir, validar, rejeitar, classificar, criar atividade e editar pontuação agem na hora, sem campo de justificativa. A justificativa de alterar processo em andamento (Etapa 1) continua.
6. **Confiança.** Confiança do documento acima de 70% só tira o aviso de revisão na tela; nada é validado sozinho.
7. **Pontuação manual.** Quando a pontuação não vem do cálculo automático, o usuário informa o valor unitário à mão (`unit_points_override`).
8. **Conclusão do processo.** Depois de gerar os três documentos finais, o usuário pode concluir e excluir os documentos de entrada para liberar espaço no servidor; os documentos gerados e o histórico ficam.

## Dados e segurança

- Os arquivos de `Documentos/` e `Modelos/` são dados reais do usuário e de terceiros: nunca versionar, copiar para testes ou abrir por agentes. Para checar documentos reais use `scripts/process_corpus.py` (relatórios mascarados em `corpus-reports/`, fora do git).
- Testes usam só dados sintéticos.
- A chave da MariTalk existe só no backend (`.env`); nunca em log, resposta, exceção ou pacote do frontend. Só texto de página mascarado vai à IA.
- `requeriment.txt` e `test/` ficam sem versionar.

## Fluxo de trabalho

- Commits em Conventional Commits, um por tarefa, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Push e deploy só com a autorização do usuário.
- Gate do backend: `cd backend && ruff check . && pytest -q`; do frontend: testes e build em `frontend/`.

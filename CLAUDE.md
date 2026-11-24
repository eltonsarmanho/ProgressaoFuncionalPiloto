# ProgressãoDocente UFPA

Sistema que ajuda o docente a montar o processo de progressão funcional: documentos de entrada, atividades, pontuação pela tabela oficial e documentos finais (Tabela de Pontuação, Relatório de Atividades e Comprovante).

Stack: FastAPI (Python 3.12), SQLAlchemy 2.x, Alembic, PostgreSQL, React/TypeScript. A IA é a MariTalk, chamada só pelo backend.

## Metodologia

Use exclusivamente a skill `tlc-spec-driven` (Specify → Design → Tasks → Execute), com validadores, um commit atômico por tarefa e Verifier independente. As especificações ficam em `.specs/features/<feature>/` e as decisões em `.specs/STATE.md`. Valide cada fase com o usuário.

## Regras de negócio

1. **Pontuação determinística.** Os pontos são calculados em Python pelo motor de pontuação, nunca pela IA. A IA só sugere; o usuário valida.
2. **Origem de cada valor.** Todo valor extraído guarda o documento e a página de origem, e só vale se o texto da página o comprova.
3. **Interstício (Etapa 1).** O processo tem um período de interstício; só o que aconteceu dentro dele conta.
4. **Documento fora do interstício (Etapa 2).** O documento cujas atividades com data estão todas fora do interstício aparece na Etapa 2 com um aviso destacado ("Data do documento dd/mm/aaaa, fora do interstício (dd/mm/aaaa a dd/mm/aaaa): não será processado nas próximas etapas"), com o alerta `DOCUMENTO_FORA_DO_INTERSTICIO`. Nenhuma atividade é criada a partir dele, e ao reprocessar um documento que passa a ficar fora do interstício o sistema rejeita, com auditoria, as atividades ligadas só a ele, mesmo as já editadas ou validadas (decisão do usuário em 2026-11-18); a atividade que também tem evidência de outro documento permanece, sem a evidência do documento fora. A Etapa 3 não oferece o documento para vincular. Se ao menos uma atividade está dentro do período ou o cruza, o documento é processado normalmente e a atividade fora do período fica não válida, com o motivo `FORA_DO_INTERSTICIO` (regra 10). Sem data utilizável, a regra não se aplica. Com precisão de mês a faixa mostra `mm/aaaa`. A regra é reavaliada ao reprocessar o documento. Especificação: `inteligencia-documental`, requisitos `FORA-01..09`.
5. **Sem justificativa nas Etapas 2, 3 e 4.** Excluir, validar, rejeitar, classificar, criar atividade e editar pontuação agem na hora, sem campo de justificativa. A justificativa de alterar processo em andamento (Etapa 1) continua.
6. **Confiança.** Confiança do documento a partir de 70% (0,70) só tira o aviso de revisão na tela; nada é validado sozinho.
7. **Pontuação manual.** Quando a pontuação não vem do cálculo automático, o usuário informa o valor unitário à mão (`unit_points_override`), nos itens por unidade ou por bloco de horas. Exceção: as horas de PIT do Grupo I vêm sempre do cálculo (CH docente ÷ 17 × (1 + preparação)) e não aceitam valor manual nem pontos informados, em qualquer versão da tabela.
8. **Conclusão do processo.** Depois de gerar os três documentos finais, o usuário pode concluir e excluir os documentos de entrada para liberar espaço no servidor; os documentos gerados e o histórico ficam.
9. **Arquivar e excluir processo.** Pelo Painel, o ADMIN ou o dono arquiva (somente leitura) ou exclui o processo. A exclusão é definitiva e pede confirmação com a lista do que sai: apaga documentos, arquivos, atividades e documentos gerados, mantém a auditoria e é recusada enquanto houver leitura, geração ou redação em andamento. Docente e unidade permanecem.
10. **Revisão simplificada das atividades.** Só as atividades válidas seguem para as etapas seguintes e para os documentos gerados; as duplicadas são mescladas numa só, com as provas somadas, e podem ser separadas com "Não é duplicada". "Validar" exige categoria e atividade válida e é o que pontua. As não válidas (fora do interstício, carga horária insuficiente, grupo que não conta, rejeitadas) ficam numa seção fechada, cada uma com o motivo, e voltam às válidas quando corrigidas.
11. **Tabela oficial.** A tabela oficial da UFPA (`backend/app/infrastructure/database/seed_data/ufpa.json`), ligada à FASI e ao IFCH, é a tabela em uso inicial. O ADMIN pode criar outras tabelas e marcar, por unidade, a versão em uso (decisão do usuário em 2026-11-23, AD-028, feature `gestao-tabelas`); as tabelas não oficiais seguem com os avisos de pendente de validação, fora de vigência e de outra unidade, e nenhuma operação muda um processo que já escolheu a tabela. Itens e pontos da tabela oficial seguem o texto da planilha oficial: o VI.14 vale 3 pontos por ano (decisão do usuário em 2026-11-19). O Grupo I tem só os itens I.1 e I.2, em horas de PIT, e conta no Total geral a 1 ponto por hora de PIT na versão "Tabela oficial de pontuação UFPA, Grupo I no total" (decisão do usuário em 2026-11-19, AD-023); a versão anterior, com o Grupo I fora do total e o VI.14 a 6, está substituída: não é sugerida nem escolhível, e os processos em rascunho ou em andamento passam para a nova no deploy, com auditoria. Documento, comentário, rótulo ou teste não cita item que não esteja nessa tabela; teste com outra tabela declara no nome que ela é sintética.

## Dados e segurança

- Os arquivos de `Documentos/` e `Modelos/` são dados reais do usuário e de terceiros: nunca versionar, copiar para testes ou abrir por agentes. Para checar documentos reais use `scripts/process_corpus.py` (relatórios mascarados em `corpus-reports/`, fora do git).
- Testes usam só dados sintéticos.
- A chave da MariTalk existe só no backend (`.env`); nunca em log, resposta, exceção ou pacote do frontend. Só texto de página mascarado vai à IA.
- `requeriment.txt` e `test/` ficam sem versionar.

## Fluxo de trabalho

- Commits em Conventional Commits, um por tarefa, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Push e deploy só com a autorização do usuário.
- Gate do backend: `cd backend && ruff check . && pytest -q`; do frontend: testes e build em `frontend/`.

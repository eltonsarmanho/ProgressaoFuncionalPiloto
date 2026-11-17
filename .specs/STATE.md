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

## Handoff

- **Feature**: projeto ProgressãoDocente UFPA (Complex). Features planejadas, na ordem: `fundacao` → `normativo` → `inteligencia-documental` → `pontuacao` → `documentos-gerados` → `banca-parecer` → `implantacao`
- **Phase / Task**: `fundacao`, Specify. `spec.md` escrita, `validate_spec.py` limpo (0/0); aguardando o usuário confirmar as 12 assumptions
- **Completed**: pesquisa preliminar (Res. 4.644/2015, IN IFCH 01/2026, Lei 12.772 compilada e modelos MariTalk); inventário dos 50 documentos reais em `Documentos/`; leitura de `Modelos/` (tabela IFCH completa e o processo FASI 2022–2024 inteiro, que serve de caso-ouro: tabela, comprovantes, relatório, portaria e parecer). Ver `docs/referencias/normas/FONTES.md`
- **In-progress** (file:line): none
- **Next step**: com a spec aprovada, fazer o Design de `fundacao` (ler `references/design.md` e registrar as ADs de arquitetura em Decisions)
- **Blockers** (nenhum bloqueia `fundacao`): falta o "Modelo Relatorio Atividades 2.docx" e as três URLs da PROGEP/CPPD. Segundo o usuário, não há norma separada da FASI: os arquivos em `Modelos/` são as fontes
- **Deploy**: o usuário ofereceu a VM descrita em AcessoVM.txt para a feature `implantacao`. Ainda não acessada; exige aval no momento do deploy (blast radius)
- **Uncommitted files**: .gitignore, .specs/STATE.md, docs/referencias/normas/*, Modelos/ (não decidido se entra no git: contém dados pessoais)
- **Branch**: main

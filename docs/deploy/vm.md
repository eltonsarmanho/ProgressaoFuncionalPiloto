# Implantação na VM compartilhada

URL: https://progressao.srv1633081.hstgr.cloud. Esta VM é compartilhada com os projetos `dashboard`, `chatwoot` e `tjpa`; por isso a instalação reaproveita o que já existe e limita os recursos.

## Como está montado

| Parte | Decisão | Motivo |
| --- | --- | --- |
| Docker | Reaproveita o Docker e o Compose já instalados (29.4.2 e 5.1.3) | Nada a instalar |
| Banco | PostgreSQL do contêiner `dashboard_db` (16.15), com banco `progressao` e papel `progressao` próprios (sem superusuário, `CONNECTION LIMIT 20`, `CONNECT` fechado ao público) | Poupa um PostgreSQL (49 MB de RAM e um volume); o `dashboard_db` usava 23 MB e 8 das 100 conexões |
| Rede | O backend entra também na rede `dashboard_app_network` (externa) e usa o endereço `dashboard_db:5432` | O banco não é publicado no host |
| Contêineres | `backend`, `frontend` e `nginx` (o serviço `postgres` do compose fica desativado pelo perfil `local-db`) | Mesma estrutura do compose do projeto |
| Porta | O nginx do projeto publica só em `127.0.0.1:8400`; o nginx do servidor (site `progressao`, HTTPS e renovação do certificado pelo certbot) repassa para ela | Uma única porta pública (443) |
| Limites | `backend` 384 MB e 0,75 CPU; `frontend` e `nginx` 32 MB; logs com 3 arquivos de 10 MB | A VM tem 1 CPU e cerca de 1,5 GB de memória livre |

O arquivo de ajustes da VM está em `deploy/docker-compose.vm.yml` e vai para `/opt/progressao/docker-compose.override.yml`.

## Arquivos na VM (`/opt/progressao`)

- `.env` (modo 600): variáveis do compose. `DATABASE_URL` aponta para `dashboard_db`. As variáveis `POSTGRES_*` ficam só porque o compose as exige; o serviço `postgres` não sobe.
- `.admin-credentials` e `.dashdb-password` (modo 600): senha do administrador e do papel `progressao` no banco.
- `releases/<versão>/`: arquivos de cada versão implantada.
- `backups/`: dump do banco anterior e cópia da configuração da versão anterior.

## Atualizar para uma versão nova

1. Construir as imagens a partir de um commit aprovado (`git archive <commit>`), com `docker compose -p progressao-funcional build`.
   Antes disso, conferir que o pacote do frontend não leva segredo: `cd frontend && npm run build && cd .. && scripts/check_bundle_no_secrets.sh` (sai com código diferente de zero se `frontend/dist` contiver `MARITALK`, um cabeçalho `Bearer` com token ou um token com forma de chave; o teste `frontend/tests/bundle.test.ts` roda o mesmo script sobre `dist`; sem `dist` ele é pulado, a menos que `REQUIRE_DIST=1` (ou outro valor diferente de vazio, `0` e `false`), caso em que falha, como no Build gate: `npm run build` antes de `REQUIRE_DIST=1 npm test -- --run`).
2. Enviar: `docker save progressao-funcional-backend:latest progressao-funcional-frontend:latest | gzip | ssh root@<vm> 'gunzip | docker load'`. As imagens são construídas fora da VM para não competir por CPU e memória com os outros sistemas.
3. Antes de carregar, etiquetar as imagens em uso como ponto de retorno: `docker tag $(docker inspect -f '{{.Image}}' progressao-funcional-backend-1) progressao-funcional-backend:<versao-anterior>` (e o mesmo para o `frontend`).
4. Fazer backup do banco: `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/...`.
5. Copiar os arquivos da versão para `/opt/progressao` e rodar `docker compose up -d --no-build`. O backend aplica as migrações e o seed sozinho.
6. Conferir `GET /api/health`, o login e uma leitura da API; só então remover o que ficou para trás.

## Voltar à versão anterior

Trocar as etiquetas das imagens para as da versão anterior (`docker tag progressao-funcional-backend:<versao-anterior> progressao-funcional-backend:latest`), restaurar o banco do dump se houve migração, e `docker compose up -d --no-build`.

Para a versão dos documentos gerados: o dump anterior (`progressao-pre-documentos-gerados-<data>.sql.gz`) é o caminho seguro, porque o `downgrade` da `0007` não retira o valor `DELETE` de `audit_action` e o da `0006` apaga as tabelas de documentos gerados. Restaurar o dump deixa órfãos os arquivos em `storage/generated/` (inofensivos; remover à mão depois). Não voltar de versão depois de uma conclusão real sem ler o aviso de irreversibilidade em "Deploy dos documentos gerados".

## Limite de envio (nginx do servidor)

O envio de documentos aceita até 120 MB por requisição (DOC-03) e 20 MB por arquivo. O nginx do projeto (`nginx/nginx.conf`) já usa `client_max_body_size 120m`. O nginx do servidor, que fica na frente dele e não faz parte deste repositório, tem de aceitar o mesmo tamanho: no bloco `server` (ou no `location /`) da configuração do site `progressao` no nginx do servidor, definir

```
client_max_body_size 120m;
```

e aplicar com `nginx -t && systemctl reload nginx`. Sem isso, o nginx do servidor responde 413 acima do valor dele (1 MB por padrão) antes de a requisição chegar ao projeto. Conferir depois enviando um corpo de 25 MB (não pode dar 413) e outro de 121 MB (tem de dar 413).

## Deploy dos documentos gerados (feature `documentos-gerados`)

Esta seção diz o que a versão com a Etapa 5 (Tabela, Relatório e Comprovante, mais a conclusão do processo) exige além do procedimento de "Atualizar para uma versão nova". Foi executada em 2026-11-19, com a autorização do usuário, a partir do commit `62c9c04` (ver "Deploy executado em 2026-11-19" ao fim desta seção).

### Antes do deploy

Estado da VM antes do deploy de 2026-11-19: migração `0005` no ar (`unit_points_override`), imagens de `b58e276`. O `alembic upgrade head` do `docker-entrypoint.sh` aplica, em ordem, o que a imagem nova trouxer:

| Ordem | Migração | Feature | O que faz |
| --- | --- | --- | --- |
| 1 | `0006_generated_documents` | `documentos-gerados` | Cria os tipos `generated_kind`, `generated_state` e `generated_format`, as tabelas `generated_documents`, `generated_files`, `report_wording_jobs`, `report_drafts` e `comprovante_layouts`, os índices parciais de uma geração e uma redação por vez, os gatilhos que tornam a versão gerada imutável e a coluna `documents.file_deleted_at` (marca de arquivo de entrada excluído) |
| 2 | `0007_process_purge` | `gestao-processos` (excluir processo) | Acrescenta o valor `DELETE` a `audit_action` e troca a função dos gatilhos de `generated_documents` e `generated_files` para deixar passar o `DELETE` só dentro da exclusão de um processo (`app.process_purge`) |

As duas migrações estão commitadas e a `0007` depende da `0006`. Elas entram na VM juntas se a imagem for construída de um commit que contém `b88b178` (o `HEAD` de `feat/inteligencia-documental` contém); construída de um commit anterior a ele, só a `0006` entra. Decidir o commit antes de construir e dizer ao usuário que a `0007` e a exclusão de processo (backend) vêm junto; a tela de arquivar e excluir do Painel (tarefas T5 e T6 de `gestao-processos`) não estava commitada quando esta nota foi escrita. Nenhuma das duas migrações usa dados reais nem reescreve linhas existentes; `ALTER TYPE ... ADD VALUE` da `0007` não pode ser desfeito (ver "Voltar à versão anterior").

Dependências novas em `backend/requirements.txt` (já fixadas, imagem cresce cerca de 24 MB, sem pacote `apt`): `python-docx==1.2.0`, `lxml==6.1.3`, `reportlab==5.1.0` e `charset-normalizer==3.5.2` (exigido pelo reportlab). O `reportlab==5.1.0` é jovem; se a suíte falhar nele, o plano do design é cair para `reportlab==4.5.1`, que tem a mesma API usada. `docker build` precisa baixar as rodas (`lxml` tem roda para `python:3.12-slim`; não instala compilador).

Fonte: o PDF usa Liberation Serif (Regular, Bold, Italic e BoldItalic, SIL OFL 1.1, cerca de 1,5 MB) versionada em `backend/app/infrastructure/documents/fonts/`, com o texto da licença (`OFL.txt`). Como o `Dockerfile` faz `COPY app ./app` e o `backend/.dockerignore` só exclui `.venv`, `tests` e caches, as fontes entram na imagem sem passo novo; a imagem `python:3.12-slim` não tem fontes do sistema. Depois de construir, conferir: `docker run --rm --entrypoint ls progressao-funcional-backend:latest /app/app/infrastructure/documents/fonts` deve listar as quatro `.ttf`.

Limite de envio: o nginx do projeto já usa `client_max_body_size 120m` (`nginx/nginx.conf`) e a seção "Limite de envio" acima já cobre o do servidor. Nada novo a configurar; os downloads gerados usam `GET` e não dependem desse limite.

Volume e espaço: os arquivos gerados ficam em `/app/storage/generated/<id do processo>/<uuid>.<docx|pdf>` (diretórios 0700, arquivos 0600), no mesmo volume nomeado `storage` que já guarda os documentos de entrada; não há volume novo nem mudança em `docker-compose.yml`. O diretório `generated` é criado pelo backend (usuário `app`, uid 10001) na primeira geração.

| Item | Valor | Onde está |
| --- | --- | --- |
| Tabela e Relatório (DOCX e PDF) | dezenas de KB cada | 0,13 s e pico de 32 MB para 140 linhas (design) |
| Comprovante | até 60 MB por versão e até 400 páginas anexadas; acima disso responde `COMPROVANTE_GRANDE_DEMAIS` | `generation_max_output_mb` (60) e `generation_max_pages` (400) |
| PNG de entrada | até 12 megapixels; acima, `IMAGEM_GRANDE_DEMAIS` | `generation_png_max_megapixels` |
| Espaço livre mínimo para aceitar um pedido | 200 MB; abaixo, 422 `ESPACO_INSUFICIENTE` | `generation_min_free_mb` (200) |
| Retenção | nenhuma: toda versão `PRONTO` fica no disco; versão `FALHOU` não deixa arquivo | AD-012 |
| Memória do Comprovante de 400 páginas | pico de 74 MB acima da linha de base, medido; o `mem_limit` de 384 MB do `backend` não muda | design |

Estimativa de uso: um processo com um Comprovante regerado 3 vezes ocupa até 180 MB só nele; o espaço dos documentos de entrada (até 20 MB por arquivo) vem somado até a conclusão do processo, que os libera. Antes do deploy, anotar a linha de base: `df -h /var/lib/docker` e `docker exec progressao-funcional-backend-1 df -h /app/storage` (o volume divide o disco da VM com os outros projetos). Esses limites são variáveis de `Settings` (`GENERATION_MIN_FREE_MB` e as demais), mas o `docker-compose.yml` não as repassa ao contêiner: valem os padrões acima, e mudá-los exige acrescentar a variável em `environment` do `backend` (ou no `docker-compose.override.yml` da VM), o que é outro deploy.

### Ponto de retorno antes de aplicar

Fazer antes de carregar as imagens novas (mesma sequência dos passos 3 e 4 de "Atualizar para uma versão nova"):

1. Etiquetar as imagens em uso: `docker tag $(docker inspect -f '{{.Image}}' progressao-funcional-backend-1) progressao-funcional-backend:docs-pre` e o mesmo para o `frontend` (trocar `docs-pre` por um nome com o commit, como nas etiquetas `round5-d6dca43`).
2. `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/progressao-pre-documentos-gerados-<data>.sql.gz`, e conferir que o arquivo não está vazio (`gzip -t` e `ls -l`).
3. Copiar `docker-compose.override.yml` e `.env` da versão atual para `backups/` (sem imprimir o conteúdo).
4. Só então carregar as imagens (`docker save ... | gzip | ssh ... 'gunzip | docker load'`), copiar os arquivos, rodar `docker compose up -d --no-build` e, em seguida, `docker compose restart nginx` (o nginx do projeto guarda o endereço antigo do contêiner do backend) e conferir `GET /api/health`.

O pacote do frontend continua passando por `scripts/check_bundle_no_secrets.sh` antes do envio, e a imagem é construída com variáveis de ambiente de mentira (a MariTalk só existe no `.env` da VM).

### Depois do deploy: roteiro de fumaça

Usar só dados sintéticos (docente com SIAPE fictício, PDF sintético; nunca `Documentos/` nem `Modelos/`). Anotar os ids e apagar ao final.

1. `GET /api/health` responde 200, o login funciona e `docker logs progressao-funcional-backend-1` não mostra erro de migração (`alembic` deve terminar em `0007`, ou em `0006` se a `0007` não entrou).
2. Num processo sintético A com um interstício e ao menos uma atividade validada com pontos: na Etapa 5, gerar a Tabela, o Relatório e o Comprovante, esperar os três irem a `PRONTO` e baixar cada arquivo (DOCX e PDF). Conferir que o PDF da Tabela abre com acentos corretos (a fonte Liberation Serif embutida), que o número de páginas do Comprovante bate com o sumário e que o histórico mostra o tamanho de cada versão.
3. Pedir uma segunda geração da Tabela e conferir a versão 2 (a 1 continua no histórico e no disco).
4. No volume: `docker exec progressao-funcional-backend-1 ls -l /app/storage/generated` mostra o diretório do processo A com modo `drwx------` e dono `app`; `df -h` confere o espaço usado contra a linha de base.
5. Conclusão, num processo sintético B (não no A, para manter um exemplo com os originais): gerar os três documentos, abrir "Concluir e excluir documentos de entrada", conferir a prévia (número de arquivos e MB), marcar a confirmação e concluir. Esperado: o processo vira `CONCLUIDO` e somente leitura, os arquivos de entrada do B somem do volume, os documentos de entrada aparecem como arquivo excluído, os três documentos gerados continuam baixando, e pedir o Comprovante de novo responde `ORIGINAIS_EXCLUIDOS`.
6. Se a `0007` entrou: excluir o processo B pela API (`DELETE /api/processes/{id}`) ou pelo Painel, se a tela estiver no ar, e conferir que o diretório `generated/<id>` e as linhas dele saem e que a auditoria registra `DELETE`. Apagar também o A.

### Deploy executado em 2026-11-19

- Commit publicado: `62c9c04` (`git archive`; imagens construídas fora da VM com variáveis de ambiente de mentira; quatro `.ttf` Liberation Serif conferidas na imagem; pacote do frontend limpo em `scripts/check_bundle_no_secrets.sh`). Migrações aplicadas pelo entrypoint: `0006` e `0007`; `alembic_version` = `0007`. Como a imagem saiu de `62c9c04`, a exclusão de processo (`DELETE /api/processes/{id}`, `gestao-processos`) está no ar sem a tela do Painel.
- Retorno: imagens `progressao-funcional-backend:docs-pre-62c9c04` e `progressao-funcional-frontend:docs-pre-62c9c04` (as de `b58e276`), dump `backups/progressao-pre-documentos-gerados-2026-11-19.sql.gz` (`gzip -t` ok), cópias de `docker-compose.override.yml` e `.env` em `backups/`. Lembrete: o `ADD VALUE` da `0007` não se desfaz; para voltar à `0005` é preciso restaurar o dump.
- Verificação: `GET /api/health` 200 depois do `docker compose restart nginx`; sem erro de migração nos logs; `generated` com diretórios `drwx------` do usuário `app`.
- Roteiro de fumaça (dados sintéticos, por túnel SSH): Tabela, Relatório e Comprovante do processo A foram a `PRONTO` e baixaram (a Tabela em PDF com acentos e a Liberation Serif embutida); a segunda geração da Tabela virou a versão 2 e a 1 ficou no histórico; no processo B (em andamento) a conclusão levou o processo a `CONCLUIDO`, o arquivo de entrada passou a responder 410 `ARQUIVO_EXCLUIDO`, os gerados continuaram baixando e um novo Comprovante foi recusado; os processos sintéticos foram excluídos pela API e o docente sintético (SIAPE 9999991) foi arquivado.
- Observações: (1) o `DELETE` do processo apaga os arquivos mas deixa os diretórios vazios `uploads/<id>` e `generated/<id>`; removidos à mão com `rmdir` (cosmético, a corrigir em `gestao-processos`); (2) o cookie de sessão é `Secure`: um roteiro por túnel `http` precisa repassar o cookie à mão; (3) a conclusão exige o processo `EM_ANDAMENTO` (de `RASCUNHO` responde "Transição de status não permitida").

### Painel com Arquivar e Excluir, publicado em 2026-11-19

- Só o frontend foi reconstruído e carregado, a partir do commit `d3823fc` (o backend não mudou desde `62c9c04`; sem migração e sem cópia do banco). Pacote sem segredo (`scripts/check_bundle_no_secrets.sh`); `GET /api/health` 200 depois de `docker compose up -d --no-build frontend` e `docker compose restart nginx`; o `index.html` serve `assets/index-CiODvMVC.js`, que contém "Excluir definitivamente".
- Retorno: imagem `progressao-funcional-frontend:painel-pre-d3823fc` (a de `62c9c04`).

### Revisão simplificada das atividades, publicada em 2026-11-19

- Commit publicado: `a136faf` (`git archive`; backend e frontend reconstruídos fora da VM; pacote do frontend limpo em `scripts/check_bundle_no_secrets.sh`; quatro `.ttf` e `0008_activity_merge.py` conferidos na imagem). Migração aplicada pelo entrypoint: `0008`; `alembic current` na VM = `0008 (head)`. `docker-compose.yml`, `deploy/` e os `Dockerfile` não mudaram desde o deploy anterior.
- Antes: nada em processamento (nenhuma geração `GERANDO`, nenhum documento `PROCESSANDO`), pois reiniciar o backend interrompe o que estiver rodando.
- Retorno: imagens `progressao-funcional-backend:merge-pre-a136faf` e `progressao-funcional-frontend:merge-pre-a136faf` (as do deploy anterior), dump `backups/progressao-pre-revisao-simplificada-2026-11-19.sql.gz` (`gzip -t` ok) e cópias de `docker-compose.override.yml` e `.env` em `backups/`. A `0008` só acrescenta `activities.merged_into_id`, o índice parcial e `activity_evidences.origin_activity_id`; o `downgrade` é `DROP COLUMN`, mas depois de mesclagens reais voltar de versão deixa as atividades mescladas visíveis como duplicadas, então o caminho seguro continua sendo o dump.
- Verificação: `GET /api/health` 200 (direto e pelo endereço público) depois de `docker compose up -d --no-build` e `docker compose restart nginx`; sem erro nos logs. Fumaça com dados sintéticos pelo endereço público (docente de SIAPE fictício, processo sintético, ambos removidos ou arquivados ao fim; os dados reais da VM não foram tocados: 1 processo, 76 atividades, 5 documentos gerados): duplicada mesclada ao criar, "Não é duplicada" e a distinta que não volta a mesclar, atividade sem categoria barrada ao validar (422 `categoria`), validar atividade válida, subtotal igual aos pontos previstos, data fora do interstício recusada na edição manual, geração recusada com `ATIVIDADE_SEM_CATEGORIA` e aceita depois da categoria, Tabela em `PRONTO`: 17 de 17.
- Observações: (1) a atividade manual nasce `VALIDADA`; para exercitar "Validar" o roteiro a reabre antes; (2) o arquivamento de docente exige `expected_version` no corpo; (3) os diretórios vazios `generated/<id>` que o `DELETE` do processo deixa foram removidos à mão, e a correção está em andamento.

### Avisos

- **A conclusão é irreversível e a VM não tem backup dos arquivos de entrada.** O `pg_dump` guarda o banco, não o volume `storage`: depois de concluir um processo, os PDFs, as imagens e o texto das páginas dele só existem no computador do docente. Restaurar o dump anterior à conclusão traz de volta a linha do documento sem `file_deleted_at`, mas não o arquivo. Dizer isso ao docente antes de a primeira conclusão real acontecer (a tela já mostra a confirmação "irreversível" com o número de arquivos e o espaço).
- Os arquivos de `generated/` também não têm backup. Se o disco for perdido, as versões geradas somem; a Tabela e o Relatório podem ser regerados enquanto os dados existirem, o Comprovante não depois da conclusão.
- A conclusão não apaga o JSON estruturado das extrações nem os documentos gerados (AD-015).
- Enquanto houver geração ou redação em andamento, a conclusão responde `OPERACAO_EM_ANDAMENTO`; um reinício do backend leva a geração que estava `GERANDO` a `FALHOU` com o código `INTERROMPIDA`, e o usuário pede de novo (AD-012); isso vale também para o `docker compose up -d` do próprio deploy.

## Deploy do Grupo I no total (feature `grupo-i-no-total`)

Esta seção descreve o procedimento, executado em 2026-11-20 (registro em "Deploy executado em 2026-11-20", ao fim da seção). **Push e deploy só com a autorização explícita do usuário**, como nos outros deploys. A versão traz a migração `0009_version_superseded`, a versão nova da tabela oficial (o Grupo I conta no Total geral a 1 ponto por hora de PIT e o VI.14 vale 3 pontos por ano), a troca automática dos processos editáveis e a Tabela de Pontuação em cinco colunas, sem Comprovante nem status.

### O que muda na VM

| Ordem | O que | Como entra |
| --- | --- | --- |
| 1 | Migração `0009_version_superseded` (só esquema: `scoring_table_versions.superseded_by_id`, UUID nulo, chave estrangeira para a própria tabela) | `alembic upgrade head` do `docker-entrypoint.sh`; `alembic current` deve terminar em `0009 (head)` |
| 2 | Versão nova "Tabela oficial de pontuação UFPA, Grupo I no total" (grupos e critérios de `ufpa.json`) | O seed roda em toda partida e insere a versão cujo nome ainda não existe; a migração não copia dados |
| 3 | `AdoptSupersedingVersion`, chamado pelo seed na mesma partida, numa transação | Marca a versão antiga ("Tabela oficial de pontuação UFPA") com `superseded_by_id` = versão nova e passa para a nova todo processo `RASCUNHO` ou `EM_ANDAMENTO` que a usa, com um evento de auditoria `UPDATE` por processo (entidade `process`, justificativa "AD-023: Grupo I no total", sem usuário) |

Processos `CONCLUIDO` e `ARQUIVADO` e todos os documentos já gerados não mudam (AD-012). O seed é idempotente: numa segunda partida não há processo a trocar e a marca já existe.

### Antes do deploy

1. Nada em processamento: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`, pois reiniciar o backend interrompe o que estiver rodando.
2. Ponto de retorno, como em "Atualizar para uma versão nova": etiquetar as imagens em uso (`progressao-funcional-backend:grupo-i-pre-<commit>` e o mesmo para o `frontend`), copiar `docker-compose.override.yml` e `.env` para `backups/` e **fazer o dump do banco antes de subir a imagem nova**: `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/progressao-pre-grupo-i-no-total-<data>.sql.gz`, conferindo `gzip -t` e `ls -l`.
3. Construir as imagens do commit aprovado fora da VM, conferir o pacote do frontend com `scripts/check_bundle_no_secrets.sh` e conferir na imagem que `0009_version_superseded.py` está em `alembic/versions`.
4. Avisar o usuário: o processo real em rascunho muda de total no deploy (o Grupo I passa a somar e o VI.14 vale 3) e a Tabela de Pontuação que ele já gerou continua como foi gerada; a Etapa 5 passa a mostrar "Gerada com outra versão da tabela de pontuação; gere de novo" até ele gerar de novo.

### Depois da partida: conferência

Com `docker exec -it dashboard_db psql -U <superusuario> -d progressao`:

1. `alembic current` no backend termina em `0009 (head)` e `docker logs progressao-funcional-backend-1` não mostra erro de migração nem de seed.
2. Versão antiga marcada: `SELECT v.name, v.superseded_by_id IS NOT NULL AS substituida FROM scoring_table_versions v ORDER BY v.created_at;` mostra a antiga com `substituida` verdadeiro e a nova com falso.
3. Processos editáveis na nova: `SELECT p.status, v.name, count(*) FROM processes p JOIN scoring_table_versions v ON v.id = p.scoring_table_version_id GROUP BY 1, 2;` não pode mostrar `RASCUNHO` nem `EM_ANDAMENTO` com a versão antiga.
4. Um evento de auditoria por processo trocado: `SELECT entity_id, changes, justification FROM audit_logs WHERE entity = 'process' AND justification = 'AD-023: Grupo I no total';` traz uma linha por processo trocado, com `changes->'scoring_table_version_id'` (`before` e `after`).
5. Concluídos e arquivados intocados: o resultado do item 3 ainda mostra os `CONCLUIDO` e `ARQUIVADO` com a versão antiga, e nenhum deles aparece na consulta do item 4.
6. `GET /api/health` 200 depois de `docker compose up -d --no-build` e `docker compose restart nginx`; na Etapa 4 do processo em rascunho o painel diz "Grupos I a VIII" e a lista de tabelas só oferece a versão nova. Fumaça só com dados sintéticos (nunca `Documentos/` nem `Modelos/`): gerar a Tabela e conferir a seção I, as cinco colunas e o Total geral com o Grupo I, no DOCX e no PDF.

### Deploy executado em 2026-11-20

- Commit publicado: `f18f162` (`git archive`; imagens construídas fora da VM com variáveis de mentira; quatro `.ttf`, `0009_version_superseded.py` e o seed novo conferidos na imagem; pacote do frontend limpo em `scripts/check_bundle_no_secrets.sh`). Gate antes do envio: backend `ruff` limpo e 5459 testes passados; frontend `lint`, `build` e 636 testes. `docker-compose.yml`, `deploy/`, `nginx/`, `Dockerfile` e `requirements.txt` não mudaram desde `a136faf`. Estavam junto, sem outra migração, os commits `ec3873a` (o `DELETE` remove diretórios vazios) e `0422ac3` (alerta de data das ofertas do Grupo I), além de `correcoes-auditoria` (Iniciar processo).
- Antes: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`. Retorno: imagens `progressao-funcional-backend:grupo-i-pre-f18f162` e `progressao-funcional-frontend:grupo-i-pre-f18f162` (as de `a136faf`), dump `backups/progressao-pre-grupo-i-no-total-2026-11-20.sql.gz` (modo 600, `gzip -t` ok) e cópias de `docker-compose.override.yml` e `.env` em `backups/`.
- Depois: `alembic current` = `0009 (head)`; `GET /api/health` 200 (direto e pelo endereço público) depois de `docker compose up -d --no-build` e `docker compose restart nginx`; sem erro nos logs. A versão antiga ficou marcada como substituída; o processo real em `RASCUNHO` passou para a versão nova, com um evento de auditoria `AD-023: Grupo I no total`; 1 processo, 76 atividades e 6 documentos gerados seguem como estavam (a Tabela já gerada não mudou, e a Etapa 5 avisa para gerar de novo).
- Fumaça sintética pelo endereço público (docente de SIAPE fictício, processo sintético, removidos ao fim): versão nova existe e a antiga está marcada; Grupo I só com I.1 e I.2 e dentro do total; VI.14 a 3; escolher a versão substituída dá 422 `VERSAO_SUBSTITUIDA`; pontos manuais no Grupo I dão 422; Iniciar processo (`RASCUNHO` para `EM_ANDAMENTO`); Tabela em `PRONTO` com DOCX de cinco colunas, seção I e sem Comprovante nem status, e PDF; a versão nova é a sugerida para a unidade FASI. 23 de 23 (a única falha da primeira rodada foi o roteiro usar a unidade CUNTINS, sem tabela ligada; refeito com a FASI).
- Observação: o `ADD COLUMN` da `0009` desfaz-se com o `downgrade`, mas a troca dos processos é dado; o caminho seguro de volta é o dump.

### Voltar à versão anterior

- **Caminho seguro: restaurar o dump** `progressao-pre-grupo-i-no-total-<data>.sql.gz` e trocar as etiquetas das imagens para as do ponto de retorno. A troca dos processos é dado, então o dump a desfaz; o `downgrade` da `0009` (`DROP COLUMN superseded_by_id`) sozinho não devolve os processos.
- **Sem dump** (só se o dump não existir): desfazer pelos eventos de auditoria da troca. Para cada evento de `audit_logs` com `justification = 'AD-023: Grupo I no total'`, `UPDATE processes SET scoring_table_version_id = (changes->'scoring_table_version_id'->>'before')::uuid WHERE id = entity_id::uuid;` e depois `UPDATE scoring_table_versions SET superseded_by_id = NULL WHERE superseded_by_id IS NOT NULL;`. Isso volta o estado de dados, mas a partida seguinte do backend com a imagem nova repete a troca (o seed é idempotente), então a imagem anterior tem de estar no ar antes. Processos alterados depois do deploy continuam na versão em que foram editados.

## Deploy das normas (feature `normativo`)

Esta seção descreve o procedimento, executado em 2026-11-23 junto com a banca e o Parecer (registro em "Deploy executado em 2026-11-23", ao fim da seção da banca). **Push e deploy só com a autorização explícita do usuário**, como nos outros deploys. A versão traz a migração `0010_norms`, as sete normas semeadas, a ligação das estruturas de carreira e da tabela oficial às normas, a titulação das classes C e D da estrutura da Lei 15.141/2025, os alertas com a norma e a página "Normas". Ver a AD-024 em `.specs/STATE.md`.

### O que muda na VM

| Ordem | O que | Como entra |
| --- | --- | --- |
| 1 | Migração `0010_norms` (só esquema: enum `norm_kind`, tabela `norms`, colunas `career_versions.norm_code` e `scoring_table_versions.norm_code`, nulas e sem chave estrangeira) | `alembic upgrade head` do `docker-entrypoint.sh`; `alembic current` deve terminar em `0010 (head)` |
| 2 | `seed_norms`: as sete normas de `seed_data/norms.json`, sem arquivo anexado | O seed roda em toda partida e insere só o código que ainda não existe, com um evento de auditoria `CREATE` por norma (entidade `norm`, sem usuário); norma existente nunca é alterada |
| 3 | `link_career_norms`: `norm_code` das duas estruturas de carreira e, na da Lei 15.141/2025, `required_titration` das classes C e D (doutorado) e `required_titration_norm_code` | Preenche só o que está nulo, com um evento `UPDATE` por versão (entidade `career_version`, justificativa "Ligação às normas (NLINK-01, NLINK-02, NTIT-06)", sem usuário); não muda classes, níveis nem denominações |
| 4 | `link_table_norms`: `norm_code` `TABELA-OFICIAL-UFPA` nas versões da tabela oficial | Só onde está nulo, com um evento `UPDATE` por versão (entidade `scoring_version`, mesma justificativa); antes da `AdoptSupersedingVersion` |

Processos, atividades e documentos gerados não mudam (AD-012). O seed é idempotente: numa segunda partida nada é inserido nem auditado. A página Normas já mostra as sete normas sem arquivo; o ADMIN anexa depois os PDFs públicos (a URL semeada da Res. 4.644/2015 é uma pasta, não o PDF).

### Antes do deploy

1. Nada em processamento: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`, pois reiniciar o backend interrompe o que estiver rodando.
2. Ponto de retorno, como em "Atualizar para uma versão nova": etiquetar as imagens em uso (`progressao-funcional-backend:normativo-pre-<commit>` e o mesmo para o `frontend`), copiar `docker-compose.override.yml` e `.env` para `backups/` e **fazer o dump do banco antes de subir a imagem nova**: `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/progressao-pre-normativo-<data>.sql.gz`, conferindo `gzip -t` e `ls -l`.
3. Construir as imagens do commit aprovado fora da VM, conferir o pacote do frontend com `scripts/check_bundle_no_secrets.sh` e conferir na imagem que `0010_norms.py` está em `alembic/versions` e que `seed_data/norms.json` está no pacote.
4. O volume `storage/` precisa aceitar o diretório novo `storage/norms/` (criado pelo backend com modo 0700 no primeiro anexo); nenhuma mudança de `docker-compose.yml` é esperada.
5. Avisar o usuário: um salto na carreira deixa de ser `ERRO` e passa a `ALERTA` (`MODALIDADE_INCOMPATIVEL`); o alerta `TITULACAO_INSUFICIENTE` pode aparecer em processos de promoção para as classes C ou D de docente sem doutorado; a Tabela, o Relatório e o Comprovante já gerados não mudam.

### Depois da partida: conferência

Com `docker exec -it dashboard_db psql -U <superusuario> -d progressao`:

1. `alembic current` no backend termina em `0010 (head)` e `docker logs progressao-funcional-backend-1` não mostra erro de migração nem de seed.
2. Sete normas: `SELECT code, kind, archived, file_internal_name IS NOT NULL AS com_arquivo FROM norms ORDER BY code;` traz `CORRELACAO-PROGEP-2025`, `IN-01-2026-IFCH`, `LEI-12772-2012`, `MANUAL-PROGEP-PROGRESSAO`, `RES-4074-2010-CONSEPE`, `RES-4644-2015-CONSEPE` e `TABELA-OFICIAL-UFPA`, todas sem arquivo e não arquivadas.
3. Ligações das estruturas: `SELECT name, norm_code, definition->'required_titration_norm_code' AS norma_titulacao FROM career_versions ORDER BY name;` mostra `RES-4644-2015-CONSEPE` na estrutura antiga e `LEI-12772-2012` na da Lei 15.141/2025, esta com `MANUAL-PROGEP-PROGRESSAO` como norma da titulação; as classes C e D dela têm `"required_titration": "DOUTORADO"` na definição.
4. Ligação da tabela: `SELECT name, norm_code, superseded_by_id IS NOT NULL AS substituida FROM scoring_table_versions ORDER BY created_at;` mostra `TABELA-OFICIAL-UFPA` nas versões da tabela oficial e nulo nas tabelas legadas arquivadas.
5. Auditorias das ligações, uma por registro: `SELECT entity, count(*) FROM audit_logs WHERE user_id IS NULL AND entity IN ('norm', 'career_version', 'scoring_version') AND occurred_at > '<data-do-deploy>' GROUP BY entity;` dá 7 em `norm`, uma por versão de carreira ligada em `career_version` e uma por versão de tabela ligada em `scoring_version`.
6. Idempotência: reiniciar o backend (`docker compose restart backend`) e repetir o item 5: as contagens não mudam.
7. `GET /api/health` 200 depois de `docker compose up -d --no-build` e `docker compose restart nginx`; `GET /api/norms` autenticado devolve as sete normas; a página "Normas" aparece no menu para DOCENTE e ADMIN. Fumaça só com dados sintéticos (nunca `Documentos/` nem `Modelos/`): um processo sintético de promoção B para C com docente de mestrado mostra `TITULACAO_INSUFICIENTE` com o Manual da PROGEP; com doutorado o alerta some; um salto A1 para C1 mostra `MODALIDADE_INCOMPATIVEL` como `ALERTA` e o processo inicia; na Etapa 4 da estrutura nova o mínimo aparece "não definido" com o "Ver norma" da Res. 4.644/2015.

### Voltar à versão anterior

- **Caminho seguro: restaurar o dump** `progressao-pre-normativo-<data>.sql.gz` e trocar as etiquetas das imagens para as do ponto de retorno.
- O `downgrade` da `0010` remove a tabela `norms`, o enum `norm_kind` e as duas colunas `norm_code`; a imagem anterior ignora as chaves novas da definição JSONB (`required_titration`, `required_titration_norm_code`), então nada mais precisa ser desfeito. Os PDFs em `storage/norms/` ficam órfãos (inofensivos; remover à mão depois). Se as normas já foram editadas ou receberam arquivo, voltar pelo `downgrade` perde esse cadastro: o dump anterior ao deploy não o tem, então copiar antes o que importar (`SELECT * FROM norms`).

## Deploy da banca e do Parecer (feature `banca-parecer`)

Esta seção descreve o procedimento, executado em 2026-11-23 (registro em "Deploy executado em 2026-11-23", ao fim da seção). **Push e deploy só com a autorização explícita do usuário**, como nos outros deploys. A versão traz a migração `0011_board_opinion`, a portaria da banca lida pela IA, o Parecer e o Requerimento como documentos gerados, o checklist do dossiê e as Etapas 6 e 7 (o botão Concluir passa da Etapa 5 para a Etapa 7). Ver a AD-025 em `.specs/STATE.md`.

### O que muda na VM

| Ordem | O que | Como entra |
| --- | --- | --- |
| 1 | Migração `0011_board_opinion` (`down_revision = "0010"`): `ALTER TYPE generated_kind ADD VALUE` para `REQUERIMENTO` e `PARECER`; enums `board_role`, `value_source`, `ordinance_reading_state` e `opinion_conclusion`; tabelas `board_ordinances`, `board_opinions`, `request_settings` e `dossier_deliveries` | `alembic upgrade head` do `docker-entrypoint.sh`; `alembic current` deve terminar em `0011 (head)`. **Depois da `0010` do `normativo`**: se a `0010` ainda não está na VM, o `upgrade head` aplica as duas, na ordem |
| 2 | Semeadura | Nenhuma: não há dado novo no seed |
| 3 | `docker-compose.yml`, nginx, `Dockerfile`, `requirements.txt` | Nenhuma mudança. O arquivo da portaria fica em `storage/uploads/<processo>`, como os documentos de entrada |

Processos, atividades e documentos já gerados não mudam (AD-012). A migração só cria objetos; os valores novos de `generated_kind` não são usados dentro dela.

**Os valores de enum não se desfazem.** O `ALTER TYPE ... ADD VALUE` fica no banco mesmo com o `downgrade`, como na `0007`. O `downgrade` da `0011` remove as quatro tabelas e os quatro enums novos, mas `REQUERIMENTO` e `PARECER` continuam em `generated_kind` (inofensivos para a imagem anterior). Por isso o dump antes do deploy é o caminho seguro de volta.

### Antes do deploy

1. Nada em processamento: nenhuma geração `GERANDO`, nenhum documento `PROCESSANDO`, pois reiniciar o backend interrompe o que estiver rodando.
2. Ponto de retorno, como em "Atualizar para uma versão nova": etiquetar as imagens em uso (`progressao-funcional-backend:banca-pre-<commit>` e o mesmo para o `frontend`), copiar `docker-compose.override.yml` e `.env` para `backups/` e **fazer o dump do banco antes de subir a imagem nova**: `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/progressao-pre-banca-parecer-<data>.sql.gz`, conferindo `gzip -t` e `ls -l`.
3. Conferir que a `0010` (normas) já está aplicada ou vai junto: `alembic current` na VM deve mostrar `0009 (head)` ou `0010 (head)` antes de subir; a `0011` não sobe sem a `0010`.
4. Construir as imagens do commit aprovado fora da VM, conferir o pacote do frontend com `scripts/check_bundle_no_secrets.sh` (a chave da MariTalk nunca entra no pacote) e conferir na imagem que `0011_board_opinion.py` está em `alembic/versions`.
5. Avisar o usuário: as Etapas 6 (Banca e Parecer) e 7 (Requerimento e dossiê) aparecem na navegação; o botão **Concluir o processo** sai da Etapa 5 e passa para a Etapa 7; a ordem do dossiê vira um checklist com nove itens; a leitura da portaria usa a IA (texto mascarado) e a pessoa confere os dados.

### Depois da partida: conferência

Com `docker exec -it dashboard_db psql -U <superusuario> -d progressao`:

1. `alembic current` no backend termina em `0011 (head)` e `docker logs progressao-funcional-backend-1` não mostra erro de migração.
2. Cinco valores no tipo: `SELECT unnest(enum_range(NULL::generated_kind));` traz `TABELA`, `RELATORIO`, `COMPROVANTE`, `REQUERIMENTO` e `PARECER`.
3. As quatro tabelas: `SELECT table_name FROM information_schema.tables WHERE table_name IN ('board_ordinances', 'board_opinions', 'request_settings', 'dossier_deliveries') ORDER BY 1;` devolve as quatro, e `SELECT count(*) FROM board_ordinances;` é 0 logo depois do deploy.
4. Executor: o backend sobe sem erro nos logs (`app.documents.worker` não registra `recover error_type` nem `runner error_type`); a ordem do executor é geração, redação, leitura da portaria e OCR, e a leitura interrompida por um reinício volta a `FALHOU` com `INTERROMPIDA` (AD-008, PORT-07).
5. `GET /api/health` 200 depois de `docker compose up -d --no-build` e `docker compose restart nginx`; `GET /api/dossier-order` segue com o formato de antes e `GET /api/processes/<id>/dossier` (autenticado) devolve os nove itens.
6. Fumaça só com dados sintéticos (nunca `Documentos/` nem `Modelos/`): num processo sintético em andamento com Tabela `PRONTO`, enviar uma portaria sintética (lida pela IA ou, se a IA falhar, digitada), conferir número, data e membros com a página de origem; escolher a conclusão e gerar o Parecer (DOCX e PDF pelo modelo oficial, sem Total geral; o resumo da versão guarda o total da Tabela); digitar a cidade e gerar o Requerimento; abrir a Etapa 7 e ver Requerimento, Tabela, Relatório, Comprovante, Portaria da banca e Parecer como gerados ou registrados, marcar "Currículo Lattes" como entregue e recarregar; mudar uma atividade validada e ver `TABELA_DESATUALIZADA`; abrir a confirmação de concluir e ver o aviso dos pendentes. Remover o processo e o docente sintéticos ao fim.

### Deploy executado em 2026-11-23

- Commit publicado: `dd5e21f` (`git archive`; imagens construídas fora da VM; `0010_norms.py`, `0011_board_opinion.py` e `seed_data/norms.json` conferidos na imagem; pacote do frontend limpo em `scripts/check_bundle_no_secrets.sh`). Gate antes do envio: backend `ruff` limpo e 6312 testes passados; frontend `lint`, `build` e 765 testes. `docker-compose.yml`, `deploy/`, `nginx/`, os `Dockerfile` e os `requirements` não mudaram desde `f18f162`. Foram juntos o `normativo` (migração `0010`) e o `banca-parecer` (migração `0011`), mais os commits de `inteligencia-documental` posteriores a `f18f162`, sem outra migração.
- Antes: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`. Retorno: imagens `progressao-funcional-backend:normativo-banca-pre-dd5e21f` e `progressao-funcional-frontend:normativo-banca-pre-dd5e21f` (as de `f18f162`), dump `backups/progressao-pre-normativo-banca-parecer-2026-11-23.sql.gz` (modo 600, `gzip -t` ok) e cópias de `docker-compose.override.yml` e `.env` em `backups/`.
- Depois: `alembic current` = `0011 (head)`; `GET /api/health` 200 (direto e pelo endereço público); sem erro nos logs. Sete normas semeadas, sem arquivo; as duas estruturas de carreira e as versões da tabela oficial ligadas às normas; classes C e D da Lei 15.141 com doutorado; 7 eventos de auditoria de norma, 2 de carreira e 2 de tabela, **iguais depois de reiniciar o backend** (seed idempotente); `generated_kind` com os cinco valores; as quatro tabelas da banca criadas e vazias; 1 processo em `RASCUNHO`, 8 documentos gerados `PRONTO`, 5 `REQUER_REVISAO` e 51 `PROCESSADO` como estavam.
- Fumaça sintética pelo endereço público (docentes de SIAPE fictício 9999101 a 9999103, processos sintéticos excluídos ao fim): 14 de 15 verificações passaram e a 14 passou em parte. Normativo: normas, titulação (`TITULACAO_INSUFICIENTE` com o Manual da PROGEP só para mestrado), salto A1 para C1 como `ALERTA` com início do processo, mínimo não definido com a norma, criar e arquivar norma. Banca: portaria digitada, conclusão sem valor inicial, `CONCLUSAO_AUSENTE`, Parecer com o Total igual ao da Tabela (DOCX, PDF e resumo), Requerimento com a data do Parecer, checklist com nove itens e marca "Entregue", `TABELA_DESATUALIZADA`, aviso de pendentes na conclusão, leitura real da portaria pela IA (`LIDA`), `PORTARIA_EXISTENTE` e substituição, `PROCESSO_SOMENTE_LEITURA` no arquivado. Não exercida: o 404 de um DOCENTE que não é dono do processo (não há rota para excluir usuário). Sem `Traceback`, `ERROR` nem 5xx nos logs.
- Resíduos da fumaça (não há rota de exclusão): a norma arquivada `SMOKE-TESTE-NORMA` e três docentes sintéticos arquivados.

### Voltar à versão anterior

- **Caminho seguro: restaurar o dump** `progressao-pre-banca-parecer-<data>.sql.gz` e trocar as etiquetas das imagens para as do ponto de retorno. Restaurar o dump deixa órfãos os arquivos em `storage/generated/` (Pareceres e Requerimentos) e em `storage/uploads/` (portarias); são inofensivos e podem ser removidos à mão depois.
- O `downgrade` da `0011` remove as tabelas `board_ordinances`, `board_opinions`, `request_settings` e `dossier_deliveries` e os quatro enums, e **perde** as portarias, os Pareceres, as cidades e as marcas "Entregue" já gravados, além dos registros de versões `REQUERIMENTO` e `PARECER`; os valores de `generated_kind` ficam. Se houve uso real, copiar antes o que importar (`SELECT * FROM board_ordinances`, `board_opinions`, `request_settings`, `dossier_deliveries`).
- A imagem anterior ignora os dois valores novos de `generated_kind` desde que nenhuma linha os use; com linhas `REQUERIMENTO` ou `PARECER` no banco, voltar só a imagem pode quebrar a leitura dos documentos gerados. Nesse caso restaurar o dump.

## Deploy do layout oficial (feature `layout-oficial`)

Esta seção descreve o procedimento, executado em 2026-11-23 (registro em "Deploy executado em 2026-11-23", ao fim da seção). **Push e deploy só com a autorização explícita do usuário.**

### O que muda na VM

- Nenhuma migração e nenhuma semeadura: o banco não muda (a coluna `board_opinions.notes` fica, sem uso). Nada a desfazer no banco.
- Imagem do backend nova: o brasão está em `app/infrastructure/documents/assets/ufpa.png`, dentro de `app`, e o `COPY app ./app` do `Dockerfile` o leva; o `Dockerfile` não muda. Também vão as duas fontes `LiberationSans-*.ttf` em `app/infrastructure/documents/fonts/`.
- Imagem do frontend nova: a Etapa 6 perde o campo "Observações da banca".
- Os documentos já gerados não mudam (AD-012): só as versões novas levam o brasão e, no Parecer, o texto do modelo.

### Antes do deploy

1. Nada em geração: nenhuma geração `GERANDO`, pois reiniciar o backend interrompe o que estiver rodando.
2. Ponto de retorno: etiquetar as imagens em uso (`progressao-funcional-backend:layout-pre-<commit>` e o mesmo para o `frontend`).
3. Construir as imagens do commit aprovado fora da VM e conferir o pacote do frontend com `scripts/check_bundle_no_secrets.sh`.

### Depois da partida: conferência

1. O arquivo do brasão está na imagem: `docker compose exec backend ls app/infrastructure/documents/assets/ufpa.png`. Sem ele toda geração falha com `ERRO_INTERNO` e o log traz `error_type=EmblemUnavailable`.
2. `GET /api/health` 200 e nenhum erro nos logs do backend.
3. Fumaça só com dados sintéticos (nunca `Documentos/` nem `Modelos/`): num processo sintético com banca e conclusão, gerar os cinco documentos e abrir cada um: o brasão aparece no topo da primeira página, centralizado (no Comprovante, só na capa), e o Parecer segue o modelo oficial, sem Total geral. Remover o processo e o docente sintéticos ao fim.

### Deploy executado em 2026-11-23

- Commit publicado: `c839d28` (`git archive`; imagens construídas fora da VM; brasão e as duas `LiberationSans-*.ttf` conferidos dentro da imagem; pacote do frontend limpo em `scripts/check_bundle_no_secrets.sh`). Gate antes do envio: backend `ruff` limpo e 6508 testes passados; frontend 764 testes, `lint` e `build`. Nenhuma migração; `docker-compose.yml`, `deploy/`, `nginx/`, os `Dockerfile` e os `requirements` não mudaram desde o deploy anterior.
- Antes: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`. Retorno: imagens `progressao-funcional-backend:layout-pre-c839d28` e `progressao-funcional-frontend:layout-pre-c839d28` (as de `dd5e21f`), dump `backups/progressao-pre-layout-oficial-2026-11-23.sql.gz` (modo 600, `gzip -t` ok) e cópias de `docker-compose.override.yml` e `.env` em `backups/`.
- Depois: `alembic current` = `0011 (head)` (sem migração); backend saudável; `GET /api/health` 200 pelo endereço público; `ufpa.png` presente na imagem; sem erro nos logs. Documentos gerados `PRONTO` iguais antes e depois (11).
- Fumaça sintética (docente de SIAPE fictício 9999998, processo sintético excluído ao fim, executada dentro do contêiner do backend com as credenciais do ambiente dele): Tabela, Relatório, Comprovante, Requerimento e Parecer gerados `PRONTO`; em cada PDF a primeira página tem o brasão centralizado no topo (no Comprovante, na capa) e os DOCX de Tabela, Relatório e Parecer trazem o brasão embutido. O Parecer segue o modelo oficial: cabeçalho de três linhas com campus, "PARECER", local e data, parágrafo único com a data por extenso, portaria, interstício e classe de destino, `APROVARAM` conforme a conclusão, linhas `PRESIDENTE` e `MEMBRO n`, sem suplente, Total geral, mínimo nem observações. 16 de 17 verificações automáticas passaram; a que falhou era a busca por uma frase que a diagramação quebra em duas linhas (o texto está correto, conferido na imagem do PDF). Sem erro nos logs.
- Resíduo da fumaça (não há rota de exclusão de docente): o docente sintético 9999998, arquivado.

### Voltar à versão anterior

Trocar as etiquetas das imagens para as do ponto de retorno; não há nada no banco a desfazer. As versões geradas com a imagem nova continuam abrindo.

## Deploy da gestão de tabelas (feature `gestao-tabelas`)

Esta seção descreve o procedimento; **nada foi executado na VM**. **Push e deploy só com a autorização explícita do usuário**, como nos outros deploys. A versão traz a migração `0012_unit_defaults`, a marcação da versão em uso por unidade (FASI e IFCH partem da versão oficial), arquivar e excluir tabelas e versões, a edição de critérios e a tela "Tabelas de pontuação" em cartões, aberta a todos os perfis para leitura. Ver a AD-028 em `.specs/STATE.md`.

### O que muda na VM

| Ordem | O que | Como entra |
| --- | --- | --- |
| 1 | Migração `0012_unit_defaults` (`down_revision = "0011"`, só esquema): tabela `scoring_unit_defaults` com `unit_id` (chave primária e chave estrangeira para `academic_units`), `version_id` (chave estrangeira para `scoring_table_versions`, sem `ON DELETE`, então o banco barra a exclusão da versão em uso) e `updated_at` | `alembic upgrade head` do `docker-entrypoint.sh`; `alembic current` deve terminar em `0012 (head)` |
| 2 | Semente da marcação (`seed_unit_defaults`, chamada só por `main()`, depois de `seed_scoring_tables`) | Marca a versão "Tabela oficial de pontuação UFPA, Grupo I no total" como em uso de FASI e IFCH, com um evento de auditoria `CREATE` sem usuário por unidade (entidade `unit_scoring_default`). Só age na unidade que tem a tabela oficial associada, nenhuma marcação e nenhum evento de marcação anterior; nunca refaz a marcação que o ADMIN desfez |
| 3 | `seed_scoring_tables` | Deixa de arquivar de novo e de desassociar a tabela antiga (IFCH e FASI) que alguma pessoa já alterou; a que ninguém tocou segue como estava (GTAB-41) |
| 4 | Imagens novas do backend e do frontend | `docker-compose.yml`, `deploy/`, nginx, `Dockerfile` e `requirements.txt` não mudam. Vai junto o que está entre o commit da VM e o publicado, inclusive `processo-enxuto` (AD-027, sem migração) |

Processos que já escolheram tabela, documentos já gerados e a pontuação de qualquer processo não mudam (GTAB-08, AD-012): nenhuma operação desta feature reavalia nem recalcula processo. O seed é idempotente: numa segunda partida a unidade já marcada é pulada.

### Antes do deploy

1. Nada em processamento: nenhuma geração `GERANDO` e nenhum documento `PROCESSANDO`, pois reiniciar o backend interrompe o que estiver rodando.
2. Ponto de retorno, como em "Atualizar para uma versão nova": etiquetar as imagens em uso (`progressao-funcional-backend:tabelas-pre-<commit>` e o mesmo para o `frontend`), copiar `docker-compose.override.yml` e `.env` para `backups/` e **fazer o dump do banco antes de subir a imagem nova**: `docker exec dashboard_db pg_dump -U <superusuario> -d progressao | gzip > backups/progressao-pre-gestao-tabelas-<data>.sql.gz`, conferindo `gzip -t` e `ls -l`.
3. Conferir na VM que `alembic current` mostra `0011 (head)`; a `0012` parte da `0011`.
4. Construir as imagens do commit aprovado fora da VM, conferir o pacote do frontend com `scripts/check_bundle_no_secrets.sh` (a chave da MariTalk nunca entra no pacote) e conferir na imagem que `0012_unit_defaults.py` está em `alembic/versions`.
5. Guardar o "antes" para comparar no fim da fumaça: a lista das tabelas reais, `SELECT t.name, t.archived, count(v.id) AS versoes FROM scoring_tables t LEFT JOIN scoring_table_versions v ON v.table_id = t.id GROUP BY 1, 2 ORDER BY 1;`, e `SELECT count(*), max(id) FROM audit_logs;`.
6. Avisar o usuário: a tela "Tabelas de pontuação" fica aberta a todos os perfis, só para leitura, e só o ADMIN escreve; a etiqueta "Em uso" passa a ser a marcação da unidade e o sentido antigo (algum processo usa a versão) vira "Usada por processo"; FASI e IFCH aparecem com a versão oficial em uso; nenhum processo existente muda.

### Depois da partida: conferência

Com `docker exec -it dashboard_db psql -U <superusuario> -d progressao`:

1. `alembic current` no backend termina em `0012 (head)` e `docker logs progressao-funcional-backend-1` não mostra erro de migração nem de semente, nem os avisos "Versão oficial indisponível" e "sem a tabela oficial associada".
2. Duas marcações: `SELECT u.acronym, v.name FROM scoring_unit_defaults d JOIN academic_units u ON u.id = d.unit_id JOIN scoring_table_versions v ON v.id = d.version_id ORDER BY 1;` traz exatamente FASI e IFCH com "Tabela oficial de pontuação UFPA, Grupo I no total".
3. Dois eventos de auditoria sem usuário: `SELECT entity_id, action, user_id, changes FROM audit_logs WHERE entity = 'unit_scoring_default' ORDER BY id;` traz duas linhas, `action = 'CREATE'`, `user_id` nulo e `changes->'version_id'` com `before` nulo e `after` igual ao id da versão oficial.
4. **Reiniciar o backend e conferir de novo** (`docker compose restart backend`): repetir os itens 2 e 3 e `SELECT count(*), max(id) FROM audit_logs WHERE entity = 'unit_scoring_default';`. As duas marcações e os dois eventos têm de ser **iguais antes e depois do reinício** (mesma contagem e mesmo `max(id)`, nenhum evento novo): a semente é idempotente.
5. `GET /api/health` 200 depois de `docker compose up -d --no-build` e `docker compose restart nginx`; `GET /api/scoring-tables` (autenticado) devolve, na versão oficial, `default_for_unit_ids` com as duas unidades e `process_count`.
6. O `max(id)` e a contagem de `audit_logs` do item 5 de "Antes do deploy" só crescem pelos dois eventos da semente.

### Fumaça sintética

Só com dados sintéticos (nunca `Documentos/` nem `Modelos/`), pelo endereço público ou dentro do contêiner do backend, autenticado como ADMIN. A fumaça **exige uma unidade sintética e uma tabela sintética associadas só a ela** e **nunca marca, arquiva nem exclui FASI, IFCH nem a tabela oficial**; toda escrita abaixo tem como alvo a unidade e a tabela sintéticas.

1. Criar a unidade sintética (`POST /api/units`, sigla `SMKTAB`, tipo `INSTITUTO`) e a tabela sintética (`POST /api/scoring-tables`, nome "Tabela sintética de fumaça", `unit_ids` só com a unidade sintética, vigência e referência sintéticas). A lista (`GET /api/scoring-tables`) mostra a tabela com a sigla `SMKTAB` e nenhuma marcação.
2. Marcar a versão como em uso da unidade sintética (`PUT /api/scoring-units/<unidade>/default-version`, 200); criar uma versão nova a partir dela (`POST /api/scoring-tables/<tabela>/versions`) e marcar a nova: a lista mostra `default_for_unit_ids` só na nova.
3. Recusas com 409: arquivar a tabela sintética enquanto há marcação (`TABELA_COM_VERSAO_EM_USO`); excluir a versão marcada (`VERSAO_EM_USO_DE_UNIDADE`); tirar a unidade sintética da tabela (`UNIDADE_COM_VERSAO_EM_USO`); excluir a tabela (`VERSAO_EM_USO_DE_UNIDADE`). Em todas, `GET .../delete-preview` mostra o bloqueio e nada é apagado.
4. Desmarcar (`DELETE /api/scoring-units/<unidade>/default-version`, 204); arquivar e desarquivar a tabela sintética; com a tabela arquivada, marcar uma versão dela dá 409 `TABELA_ARQUIVADA`.
5. Editar um critério da versão sem processo (`PUT /api/scoring-versions/<versão>/criteria/<grupo>/<item>`, com a referência normativa) e ver `GET /api/scoring-tables/<tabela>/history` com o evento.
6. Excluir a versão sem processo e sem marcação (prévia e `DELETE`, 204) e, por fim, excluir a tabela sintética pela prévia (204; o histórico dela passa a dar 404). Arquivar a unidade sintética (`POST /api/units/<unidade>/archive`).
7. Pela tela, como ADMIN, ver os cartões da tabela sintética antes do passo 6 (etiquetas "Em uso (SMKTAB)", botões com rótulo e botão desabilitado com o motivo) e, como outro perfil, só a leitura.
8. **Terminar com a conferência de que nada real mudou**: as duas marcações de FASI e IFCH (item 2 da conferência), a lista de tabelas reais (consulta do item 5 de "Antes do deploy", sem a tabela sintética) e a contagem de `audit_logs` das entidades reais (`scoring_table`, `scoring_version` e `unit_scoring_default` de FASI e IFCH) iguais ao que eram antes da fumaça.

**Resíduos da fumaça.** Cada marcação, arquivamento e exclusão de teste deixa linhas de auditoria, e elas são imutáveis (gatilho do banco). Não há rota para excluir docente nem unidade sintética: a unidade `SMKTAB` fica arquivada no banco.

### Na próxima versão oficial da tabela

Quando uma versão nova da tabela oficial substituir a atual (AD-023, `AdoptSupersedingVersion`), a versão antiga passa a substituída e **FASI e IFCH perdem a marcação** (um evento `DELETE` sem usuário por unidade), voltando à sugestão por vigência até o ADMIN marcar a versão nova. A semente não remarca (a unidade já tem evento de marcação). Incluir esse passo no roteiro daquele deploy: marcar a versão nova de FASI e IFCH pela tela logo depois da partida.

### Voltar à versão anterior

- **Caminho seguro: restaurar o dump** `progressao-pre-gestao-tabelas-<data>.sql.gz` e trocar as etiquetas das imagens para as do ponto de retorno (`docker tag progressao-funcional-backend:tabelas-pre-<commit> progressao-funcional-backend:latest`, o mesmo para o `frontend`, e `docker compose up -d --no-build`).
- O `downgrade` da `0012` só remove a tabela `scoring_unit_defaults`: **perde as marcações em uso** e deixa as tabelas, as versões e a auditoria como estão. Tabelas excluídas e arquivadas por pessoas depois do deploy não voltam sem o dump; as linhas de auditoria que o dump não tem somem com ele.
- A imagem anterior ignora a tabela nova e volta a sugerir por vigência; não há dado novo em outra tabela, então voltar só a imagem funciona se nenhuma versão ou tabela foi excluída (a imagem anterior também lê o campo `archived`, que já existia).

### Commits a publicar

O `origin/feat/inteligencia-documental` está em `7bb7b84` (registro do deploy do `layout-oficial`) e a VM, em `c839d28`. Para o deploy desta feature, publicar a branch com o que veio depois: `processo-enxuto` (`22fffaf` a `ca3d21d`, sem migração), a especificação, o desenho e as tarefas da `gestao-tabelas` (`c7921dc` a `fa052e0`) e as 37 tarefas da execução: fase 1 (banco, regra e API da marcação, `0b63e33` a `ded9966`), fase 2 (arquivar, excluir e regras vizinhas, `bd5dc0d` a `3f14282`), fase 3 (motivos, semente e aceitação, `6112bad` a `3364c1f`), fases 4 e 5 (a tela, `689f1d6` a `98992b0`) e o commit desta documentação. A lista completa sai de `git log --oneline 7bb7b84..HEAD`.

## Memória do OCR (limite de 384 MB do `backend`)

Medida em 2026-11-17 dentro de `docker run -m 384m --memory-swap 384m`, com a imagem do backend (Tesseract `por`) e PDFs sintéticos só de imagem (cada página é um PNG A4 a 300 dpi). O pico é o `memory.peak` do cgroup do contêiner, que inclui a geração do PDF de teste.

| Páginas escaneadas | Antes, só a extração | Depois, só a extração | Antes, com a aplicação | Depois, com a aplicação |
| --- | --- | --- | --- | --- |
| 1 | 148 MB | 135 MB | não medido | não medido |
| 10 | 297 MB | 139 MB | 342 MB | 191 MB |
| 25 | OOM | 139 MB | OOM | não medido |
| 100 (limite de envio) | OOM | 139 MB | não medido | 186 MB |

OOM: o contêiner foi morto por falta de memória antes de terminar. "Com a aplicação" importa `app.main` (FastAPI, SQLAlchemy e o restante) antes da extração, como no processo do backend.

Causa: o MuPDF guarda toda imagem decodificada num cache global de até 256 MB (cerca de 17 MB por página A4 escaneada), que o processo não devolvia; com 12 páginas de OCR o pico real chegou a 427 MB (execução 2 do corpus). Correção: `render_page` esvazia o cache (`pymupdf.TOOLS.store_shrink(100)`) e fecha as imagens intermediárias depois de cada página; o Tesseract já roda com uma thread (`OMP_THREAD_LIMIT=1`) e a extração já lê uma página por vez. O teste `backend/tests/unit/infrastructure/test_ocr_memory.py` limita o crescimento da memória em 10 páginas (40 MB; antes da correção o crescimento era de cerca de 150 MB).

O pior caso sintético (191 MB) fica abaixo de 320 MB, então não há motivo para subir o `mem_limit` do `backend`. A medida não inclui requisições simultâneas da API nem as conexões com o banco; se o contêiner passar a ser morto por falta de memória com tráfego real, subir o limite para 512 MB (a VM tem cerca de 1,5 GB livres). Para repetir a medida: construir a imagem (`docker build backend`), montar `backend/app` e `backend/tests` em `/app/app` e `/app/tests` e rodar um script que gere o PDF com `tests.support.synthetic_docs.pdf_scanned`, extraia com `DocumentTextExtractor` e leia `/sys/fs/cgroup/memory.peak`.

## Pontos de atenção

- O backend depende da rede e do contêiner do `dashboard`. Se o projeto `dashboard` recriar a rede `dashboard_app_network`, o backend perde o banco até ser reiniciado.
- O banco é compartilhado: consultas pesadas de um projeto afetam o outro. Fazer backup do banco `progressao` junto com o do `dashboard`.
- O `tjpa_backend` usa cerca de 81% do limite de memória dele (727 de 900 MB); vale subir o limite ou investigar.
- O Docker não tem limite de log por padrão (`/etc/docker/daemon.json` ausente). O limite aqui vale só para os contêineres deste projeto.

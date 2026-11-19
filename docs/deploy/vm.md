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

### Avisos

- **A conclusão é irreversível e a VM não tem backup dos arquivos de entrada.** O `pg_dump` guarda o banco, não o volume `storage`: depois de concluir um processo, os PDFs, as imagens e o texto das páginas dele só existem no computador do docente. Restaurar o dump anterior à conclusão traz de volta a linha do documento sem `file_deleted_at`, mas não o arquivo. Dizer isso ao docente antes de a primeira conclusão real acontecer (a tela já mostra a confirmação "irreversível" com o número de arquivos e o espaço).
- Os arquivos de `generated/` também não têm backup. Se o disco for perdido, as versões geradas somem; a Tabela e o Relatório podem ser regerados enquanto os dados existirem, o Comprovante não depois da conclusão.
- A conclusão não apaga o JSON estruturado das extrações nem os documentos gerados (AD-015).
- Enquanto houver geração ou redação em andamento, a conclusão responde `OPERACAO_EM_ANDAMENTO`; um reinício do backend leva a geração que estava `GERANDO` a `FALHOU` com o código `INTERROMPIDA`, e o usuário pede de novo (AD-012); isso vale também para o `docker compose up -d` do próprio deploy.

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

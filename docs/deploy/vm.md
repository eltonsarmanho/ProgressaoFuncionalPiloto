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

## Limite de envio (nginx do servidor)

O envio de documentos aceita até 120 MB por requisição (DOC-03) e 20 MB por arquivo. O nginx do projeto (`nginx/nginx.conf`) já usa `client_max_body_size 120m`. O nginx do servidor, que fica na frente dele e não faz parte deste repositório, tem de aceitar o mesmo tamanho: no bloco `server` (ou no `location /`) da configuração do site `progressao` no nginx do servidor, definir

```
client_max_body_size 120m;
```

e aplicar com `nginx -t && systemctl reload nginx`. Sem isso, o nginx do servidor responde 413 acima do valor dele (1 MB por padrão) antes de a requisição chegar ao projeto. Conferir depois enviando um corpo de 25 MB (não pode dar 413) e outro de 121 MB (tem de dar 413).

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

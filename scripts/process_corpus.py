#!/usr/bin/env python3
"""Local corpus processing: real documents through the real application pipeline (ACC-01, ACC-02).

Runs the files of a folder through the same use cases the API uses (upload, text extraction with
OCR, AI extraction, activity suggestion, scoring) on a throwaway PostgreSQL, then writes a report
(Markdown and JSON) with, per document, the extraction method of each page, status, type,
suggested item, confidence, warnings, activities and alerts, and per process the potential and
validated score. Nothing is sent anywhere except to the MariTalk API, as the application does
(identifiers are masked before the text leaves, EXT-07).

Privacy (LGPD): the documents are real personal data. They are read in place and copied only to
a private temporary directory that is removed at the end; the report carries no document text
(activity titles only with --include-titles) and every string in it is masked for CPF, RG, e-mail
and phone. The output directory is git-ignored. This script is never run by the automated suite.

Usage (from the repository root, with the backend virtualenv):

    backend/.venv/bin/python scripts/process_corpus.py Documentos \\
        --start 2024-11-23 --end 2026-11-23 --professor "Nome do Docente" [--siape 1234567]

The MariTalk credentials come from the environment or the `.env` file (MARITALK_API_KEY,
MARITALK_API_BASE, MARITALK_MODEL; the model falls back to sabia-4-br-sp). The key is never
printed. `--dry-run` skips the AI call (documents end EXTRAIDO_SEM_IA).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.rules.masking import mask_identifiers  # noqa: E402

DEFAULT_OUT_DIR = REPO_ROOT / "corpus-reports"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_UNIT = "FASI"
FALLBACK_MODEL = "sabia-4-br-sp"
POSTGRES_IMAGE = "postgres:16-alpine"
SUPPORTED_SUFFIXES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
# Warnings that say a value the AI returned was not backed by the page text (AD-009).
GROUNDING_CODES = frozenset(
    {"NAO_ENCONTRADO_NO_TEXTO", "DOCENTE_DIVERGENTE", "QUANTIDADE_ESTIMADA", "RESPOSTA_INVALIDA"}
)
_ROMAN = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
_BARE_NUMBER = re.compile(r"(?<![\w.])\d{7,}(?![\w])")
_DOTTED_NUMBER = re.compile(r"(?<!\d)\d{1,3}(?:\.\d{3}){2}(?:-[\dXx])?(?!\d)")
MAX_TITLE_CHARS = 80


class CorpusError(Exception):
    """A usage or configuration problem; the message never carries secrets or document text."""


# --------------------------------------------------------------------------- pure helpers


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data inválida (use AAAA-MM-DD): {value}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="process_corpus.py",
        description="Processa documentos reais pelo pipeline da aplicação e gera um relatório.",
    )
    parser.add_argument("folder", type=Path, help="pasta com os arquivos (PDF, JPG, JPEG, PNG)")
    parser.add_argument("--start", type=parse_iso_date, required=True, help="início do interstício")
    parser.add_argument("--end", type=parse_iso_date, required=True, help="fim do interstício")
    parser.add_argument("--professor", required=True, help="nome completo do docente")
    parser.add_argument("--siape", help="matrícula SIAPE de 7 dígitos (opcional)")
    parser.add_argument(
        "--table", help="nome da tabela de pontuação (padrão: a tabela oficial da UFPA)"
    )
    parser.add_argument(
        "--table-version", help="nome da versão da tabela (padrão: a vigente no fim do interstício)"
    )
    parser.add_argument("--unit", default=DEFAULT_UNIT, help="sigla da unidade do docente")
    parser.add_argument(
        "--database-url",
        help="PostgreSQL descartável (padrão: um contêiner postgres:16-alpine temporário)",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="pasta do relatório")
    parser.add_argument(
        "--env-file", type=Path, default=DEFAULT_ENV_FILE, help="arquivo .env com a MariTalk"
    )
    parser.add_argument(
        "--dry-run",
        "--fake-ai",
        dest="dry_run",
        action="store_true",
        help="não chama a IA (os documentos terminam EXTRAIDO_SEM_IA)",
    )
    parser.add_argument(
        "--include-titles",
        action="store_true",
        help="inclui no relatório o título (mascarado e truncado) de cada atividade",
    )
    parser.add_argument("--limit", type=int, help="processa só os N primeiros arquivos")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Raises CorpusError for arguments the pipeline would refuse later."""
    if args.end <= args.start:
        raise CorpusError("O fim do interstício deve ser posterior ao início")
    if args.siape is not None and not re.fullmatch(r"\d{7}", args.siape):
        raise CorpusError("O SIAPE deve ter exatamente 7 dígitos")
    if not args.professor.strip():
        raise CorpusError("Informe o nome do docente")
    if args.limit is not None and args.limit < 1:
        raise CorpusError("--limit deve ser positivo")
    if not args.folder.is_dir():
        raise CorpusError("A pasta informada não existe")


def list_corpus_files(folder: Path) -> list[Path]:
    """Supported files directly inside `folder`, by name; hidden files and folders are skipped."""
    return sorted(
        (
            p
            for p in folder.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda p: p.name.casefold(),
    )


def load_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE pairs of a .env file (comments, `export` and quotes handled); {} if missing."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        values[key] = value.strip().strip("'\"")
    return values


def maritalk_settings(env: Mapping[str, str]) -> dict[str, str | None]:
    """The MariTalk fields of the application settings; the model falls back when empty."""
    return {
        "maritalk_api_key": (env.get("MARITALK_API_KEY") or "").strip() or None,
        "maritalk_api_base": (env.get("MARITALK_API_BASE") or "").strip() or None,
        "maritalk_model": (env.get("MARITALK_MODEL") or "").strip() or FALLBACK_MODEL,
    }


def mask_text(text: str) -> str:
    """CPF, RG, e-mail and phone masked, plus any bare run of 7+ digits and dotted ID numbers."""
    masked = mask_identifiers(text).text
    masked = _DOTTED_NUMBER.sub("[NUMERO]", masked)
    return _BARE_NUMBER.sub("[NUMERO]", masked)


def mask_deep(value: Any) -> Any:
    """A copy of a JSON-like structure with every string masked."""
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, dict):
        return {key: mask_deep(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask_deep(item) for item in value]
    return value


def roman(group: int) -> str:
    return _ROMAN[group] if 0 < group < len(_ROMAN) else str(group)


def item_label(group: int | None, item: int | None) -> str | None:
    """`VIII.24` for group 8, item 24; None when the activity has no item."""
    if group is None or item is None:
        return None
    return f"{roman(group)}.{item}"


def interstice_summary(states: Sequence[str]) -> str:
    """One word for a document from the period state of each of its activities."""
    if not states:
        return "SEM_ATIVIDADE"
    unique = set(states)
    if len(unique) == 1:
        return states[0]
    return "MISTO"


def decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


@dataclass
class ActivityEntry:
    item: str | None
    status: str
    score_status: str
    points: str
    period: str
    reasons: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    title: str | None = None


@dataclass
class DocumentEntry:
    file: str
    size_bytes: int
    upload_status: int
    upload_error: str | None = None
    status: str | None = None
    status_code: str | None = None
    document_type: str | None = None
    category: str | None = None
    confidence: str | None = None
    pages: int = 0
    page_methods: list[str] = field(default_factory=list)
    ocr_mean_confidence: str | None = None
    ai_returned: int | None = None
    items: list[str] = field(default_factory=list)
    without_item: bool = False
    interstice: str = "SEM_ATIVIDADE"
    activities: list[ActivityEntry] = field(default_factory=list)
    grounding_warnings: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    duration_ms: int | None = None
    wall_seconds: float | None = None


@dataclass
class CorpusReport:
    generated_at: str
    parameters: dict[str, Any]
    process: dict[str, Any]
    documents: list[DocumentEntry]

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready and masked: every string passes through `mask_text`."""
        return mask_deep(asdict(self))


def summarize_documents(documents: Sequence[DocumentEntry]) -> dict[str, Any]:
    """Counters of the corpus: statuses, types, page methods and documents without item."""
    methods = Counter(m for d in documents for m in d.page_methods)
    return {
        "files": len(documents),
        "by_status": dict(Counter(d.status or f"UPLOAD_{d.upload_status}" for d in documents)),
        "by_type": dict(Counter(d.document_type or "-" for d in documents)),
        "page_methods": dict(methods),
        "without_item": sum(1 for d in documents if d.without_item),
        "activities": sum(len(d.activities) for d in documents),
    }


def render_markdown(report: dict[str, Any]) -> str:
    """The Markdown report from `CorpusReport.to_dict()` output."""
    params, process, docs = report["parameters"], report["process"], report["documents"]
    lines = [
        "# Relatório do corpus",
        "",
        f"Gerado em {report['generated_at']}. Dados pessoais mascarados; sem texto dos documentos.",
        "",
        "## Parâmetros",
        "",
        f"- Interstício: {params['start']} a {params['end']}",
        f"- Tabela: {process['table']['name']} / {process['table']['version']}",
        f"- IA: {params['ai']}",
        f"- Arquivos processados: {len(docs)}",
        "",
        "## Pontuação do processo",
        "",
        "| Item | Valor |",
        "| --- | --- |",
        f"| Total validado | {process['score']['validated_total']} |",
        f"| Total potencial | {process['score']['potential_total']} |",
        f"| Atividades | {process['score']['activities']} |",
        f"| Aguardando revisão | {process['score']['pending']} |",
        f"| Não pontuadas | {process['score']['not_scored']} |",
        f"| Alertas do processo | {', '.join(process['score']['alerts']) or '-'} |",
        "",
        "Potencial soma também as atividades ainda não validadas; validado soma só as validadas.",
        "",
        "| Grupo | Subtotal validado |",
        "| --- | --- |",
    ]
    for group, subtotal in process["score"]["group_subtotals"].items():
        lines.append(f"| {group} | {subtotal} |")
    summary = process["documents"]
    lines += [
        "",
        "## Resumo dos documentos",
        "",
        f"- Por status: {_counter_text(summary['by_status'])}",
        f"- Por tipo: {_counter_text(summary['by_type'])}",
        f"- Páginas por método: {_counter_text(summary['page_methods'])}",
        f"- Documentos sem item de pontuação: {summary['without_item']}",
        f"- Atividades criadas: {summary['activities']}",
        f"- Tempo total: {process['elapsed_seconds']} s",
        "",
        "## Documentos",
        "",
        "| # | Arquivo | Tipo | Status | Páginas (método) | Itens | Interstício | Atividades "
        "| Confiança | Avisos de verificação | Alertas | Tempo (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for number, doc in enumerate(docs, start=1):
        lines.append(_document_row(number, doc))
    details = [(n, d) for n, d in enumerate(docs, start=1) if d["activities"]]
    if details:
        lines += ["", "## Atividades por documento", ""]
        for number, doc in details:
            lines.append(f"### {number}. {_cell(doc['file'])}")
            lines.append("")
            lines.append("| Item | Revisão | Cálculo | Pontos | Período | Razões | Alertas |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for act in doc["activities"]:
                title = f" ({_cell(act['title'])})" if act.get("title") else ""
                lines.append(
                    f"| {act['item'] or 'SEM_ITEM'}{title} | {act['status']} "
                    f"| {act['score_status']} | {act['points']} | {act['period']} "
                    f"| {', '.join(act['reasons']) or '-'} | {', '.join(act['alerts']) or '-'} |"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _counter_text(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{key} {value}" for key, value in sorted(counts.items())) or "-"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _document_row(number: int, doc: dict[str, Any]) -> str:
    pages = f"{doc['pages']} ({','.join(doc['page_methods']) or '-'})"
    items = ", ".join(doc["items"]) or ("SEM_ITEM_DE_PONTUACAO" if doc["without_item"] else "-")
    grounding = ", ".join(_warning_text(w) for w in doc["grounding_warnings"]) or "-"
    status = doc["status"] or f"UPLOAD {doc['upload_status']}"
    if doc["status_code"]:
        status += f" ({doc['status_code']})"
    seconds = "-" if doc["wall_seconds"] is None else f"{doc['wall_seconds']:.1f}"
    cells = [
        str(number),
        _cell(doc["file"]),
        doc["document_type"] or "-",
        status,
        pages,
        items,
        doc["interstice"],
        str(len(doc["activities"])),
        doc["confidence"] or "-",
        grounding,
        ", ".join(doc["alerts"]) or "-",
        seconds,
    ]
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def _warning_text(warning: Mapping[str, Any]) -> str:
    suffix = f":{warning['field']}" if warning.get("field") else ""
    return f"{warning['code']}{suffix}"


def write_report(report: CorpusReport, out_dir: Path, moment: datetime) -> tuple[Path, Path]:
    """Writes `corpus-report-<timestamp>.json` and `.md` (mode 600) and returns their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    stem = f"corpus-report-{moment:%Y%m%d-%H%M%S}"
    json_path, md_path = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(data), encoding="utf-8")
    for path in (json_path, md_path):
        path.chmod(0o600)
    return json_path, md_path


# --------------------------------------------------------------------------- pipeline


@dataclass(frozen=True)
class Options:
    folder: Path
    start: date
    end: date
    professor: str
    siape: str | None = None
    table: str | None = None
    table_version: str | None = None
    unit: str = DEFAULT_UNIT
    database_url: str | None = None
    out_dir: Path = DEFAULT_OUT_DIR
    env_file: Path | None = DEFAULT_ENV_FILE
    dry_run: bool = False
    include_titles: bool = False
    limit: int | None = None


def options_from_args(args: argparse.Namespace) -> Options:
    return Options(
        folder=args.folder,
        start=args.start,
        end=args.end,
        professor=args.professor.strip(),
        siape=args.siape,
        table=args.table,
        table_version=args.table_version,
        unit=args.unit,
        database_url=args.database_url,
        out_dir=args.out_dir,
        env_file=args.env_file,
        dry_run=args.dry_run,
        include_titles=args.include_titles,
        limit=args.limit,
    )


@contextmanager
def throwaway_postgres() -> Iterator[str]:
    """A disposable postgres container on a free local port, removed on exit (AD-004)."""
    container = subprocess.run(
        [
            "docker", "run", "-d", "--rm",
            "-e", "POSTGRES_USER=corpus",
            "-e", "POSTGRES_PASSWORD=corpus",
            "-e", "POSTGRES_DB=corpus",
            "-p", "127.0.0.1::5432",
            POSTGRES_IMAGE,
        ],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    try:
        port = subprocess.run(
            ["docker", "port", container, "5432/tcp"], check=True, capture_output=True, text=True
        ).stdout.split()[0].rsplit(":", 1)[1]
        url = f"postgresql+psycopg://corpus:corpus@127.0.0.1:{port}/corpus"
        _wait_ready(url)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", container], capture_output=True)


def _wait_ready(url: str, timeout: float = 60.0) -> None:
    import psycopg

    dsn = url.replace("postgresql+psycopg://", "postgresql://", 1)
    deadline = time.monotonic() + timeout
    while True:
        try:
            with psycopg.connect(dsn, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise CorpusError("O PostgreSQL descartável não ficou pronto") from None
            time.sleep(0.5)


def _migrate(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def official_table_name() -> str:
    """Name of the official UFPA table, read from the seed the application ships."""
    seed = BACKEND_DIR / "app" / "infrastructure" / "database" / "seed_data" / "ufpa.json"
    return json.loads(seed.read_text(encoding="utf-8"))["table_name"]


def pick_version(uow: Any, table_name: str, version_name: str | None, moment: date) -> Any:
    """The scoring table version to use; raises CorpusError naming the available tables."""
    tables = list(uow.scoring_tables.list_tables())
    table = next((t for t in tables if t.name.casefold() == table_name.casefold()), None)
    if table is None:
        names = ", ".join(sorted(t.name for t in tables if not t.archived)) or "nenhuma"
        raise CorpusError(f"Tabela não encontrada. Disponíveis: {names}")
    versions = list(uow.scoring_tables.list_versions(table.id))
    if version_name is not None:
        found = next((v for v in versions if v.name.casefold() == version_name.casefold()), None)
        if found is None:
            names = ", ".join(v.name for v in versions) or "nenhuma"
            raise CorpusError(f"Versão não encontrada. Disponíveis: {names}")
        return found
    covering = [v for v in versions if v.covers(moment)]
    if not (covering or versions):
        raise CorpusError("A tabela não tem versões")
    return (covering or versions)[-1]


class NoAi:
    """The AI port of --dry-run: always unavailable, so no text leaves the machine."""

    def extract(self, document_type: Any, text: str) -> Any:
        from app.domain.entities.document import DocAlertCode
        from app.domain.repositories.ports import AiExtractionError

        raise AiExtractionError(DocAlertCode.IA_INDISPONIVEL)


@dataclass(frozen=True)
class _Setup:
    """The records the pipeline runs on: actor, process and chosen table version."""

    admin: Any
    process: Any
    version: Any
    table_name: str


def _resolve_ai(options: Options, ai_extractor: Any | None, env: Mapping[str, str]) -> Any | None:
    """The AI port: given by the caller, NoAi for --dry-run, or None for the real MariTalk."""
    if ai_extractor is not None:
        return ai_extractor
    if options.dry_run:
        return NoAi()
    ai = maritalk_settings(env)
    if not ai["maritalk_api_key"] or not ai["maritalk_api_base"]:
        raise CorpusError(
            "Credencial da MariTalk ausente: defina MARITALK_API_KEY e MARITALK_API_BASE "
            "no ambiente ou no .env (ou use --dry-run)"
        )
    return None


def _make_settings(
    options: Options, database_url: str, env: Mapping[str, str], storage_dir: str, files: int
) -> Any:
    from pydantic import SecretStr

    from app.core.config import Settings

    ai = maritalk_settings(env)
    email, password = "corpus-admin@local.invalid", secrets.token_urlsafe(18)
    key = SecretStr(ai["maritalk_api_key"]) if ai["maritalk_api_key"] else None
    settings = Settings(
        database_url=database_url,
        admin_email=email,
        admin_password=SecretStr(password),
        cookie_secure=False,
        maritalk_api_key=key,
        maritalk_api_base=ai["maritalk_api_base"],
        maritalk_model=ai["maritalk_model"],
        storage_dir=storage_dir,
        worker_enabled=False,
        max_uploads_per_minute=1_000_000,
        max_documents_per_process=max(200, files),
    )
    return settings


def _create_process(container: Any, engine: Any, settings: Any, options: Options) -> _Setup:
    """Seeds the reference data, then creates the professor and the process through the use
    cases and chooses the scoring table, as a user would in Steps 1 and 2."""
    from app.application.use_cases.processes import ProcessData
    from app.application.use_cases.professors import ProfessorData
    from app.domain.entities.career import Modality
    from app.domain.entities.professor import Titration, WorkRegime
    from app.infrastructure.database.repositories import SqlUnitOfWork
    from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
    from app.infrastructure.database.session import make_session_factory
    from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher

    factory = make_session_factory(engine)
    email = settings.admin_email
    seed_reference_data(
        SqlUnitOfWork(factory),
        email,
        settings.admin_password.get_secret_value(),
        Argon2PasswordHasher(),
    )
    seed_scoring_tables(SqlUnitOfWork(factory))
    with container.uow_factory() as uow:
        admin = uow.users.get_by_email(email)
        unit = next(
            (u for u in uow.units.list() if u.acronym.casefold() == options.unit.casefold()),
            None,
        )
        if unit is None:
            raise CorpusError(f"Unidade {options.unit} não encontrada")
        version = pick_version(
            uow, options.table or official_table_name(), options.table_version, options.end
        )
        table = uow.scoring_tables.get_table(version.table_id)
    professor = container.create_professor.execute(
        admin,
        ProfessorData(
            full_name=options.professor,
            siape=options.siape or "0000000",
            titration=Titration.DOUTORADO,
            position="Professor do Magistério Superior",
            career="MAGISTERIO_SUPERIOR",
            unit_id=unit.id,
            faculty=unit.name,
            campus="Campus",
            work_regime=WorkRegime.DE,
        ),
    ).professor
    process = container.create_process.execute(
        admin,
        professor.id,
        unit.id,
        ProcessData(
            modality=Modality.PROMOCAO,
            current_class="C",
            current_denomination="Adjunto",
            current_level=4,
            target_class="D",
            target_denomination="Associado",
            target_level=1,
            start_date=options.start,
            end_date=options.end,
            opening_date=date.today(),
        ),
    ).process
    container.choose_process_table.execute(
        admin, process.id, version.id, None, "Processamento local do corpus"
    )
    return _Setup(admin, process, version, table.name if table else "")


def _upload_files(
    container: Any, setup: _Setup, files: Sequence[Path]
) -> tuple[list[DocumentEntry], dict[Any, DocumentEntry]]:
    """One upload request per file, as the browser does; returns entries in order and by id."""
    from app.application.use_cases.documents import IncomingFile

    order: list[DocumentEntry] = []
    by_id: dict[Any, DocumentEntry] = {}
    for path in files:
        content = path.read_bytes()
        incoming = IncomingFile(
            path,
            path.name,
            SUPPORTED_SUFFIXES[path.suffix.lower()],
            len(content),
            hashlib.sha256(content).hexdigest(),
        )
        result = container.upload_documents.execute(setup.admin, setup.process.id, [incoming])[0]
        entry = DocumentEntry(
            file=path.name, size_bytes=len(content), upload_status=result.status_code
        )
        if result.document is None:
            entry.upload_error = result.code
        else:
            by_id[result.document.id] = entry
        order.append(entry)
    return order, by_id


def _run_jobs(container: Any, by_id: Mapping[Any, DocumentEntry], progress: Any) -> None:
    """What the background worker does: claim each pending job and process it, timing it."""
    from app.infrastructure.clock import SystemClock

    clock = SystemClock()
    total = len(by_id)
    for index in range(1, total + 1):
        with container.uow_factory() as uow:
            job = uow.jobs.claim_next(clock.now())
            uow.commit()
        if job is None:
            return
        tick = time.monotonic()
        container.process_document.execute(job.id, clock.now())
        entry = by_id[job.document_id]
        entry.wall_seconds = round(time.monotonic() - tick, 2)
        if progress is not None:
            progress(index, total, entry.file, tick)


def _score_block(score: Any) -> dict[str, Any]:
    result = score.result
    return {
        "validated_total": decimal_text(result.total),
        "potential_total": decimal_text(result.potential_total),
        "activities": result.counters.activities,
        "pending": result.counters.pending,
        "not_scored": result.counters.not_scored,
        "alerts": sorted({a.code.value for a in score.alerts}),
        "group_subtotals": {
            roman(group): decimal_text(value)
            for group, value in sorted(result.group_subtotals.items())
        },
    }


def run_corpus(
    options: Options,
    database_url: str,
    ai_extractor: Any | None = None,
    env: Mapping[str, str] | None = None,
    progress: Any = None,
) -> CorpusReport:
    """Runs the pipeline on the database and returns the (still unmasked) report.

    `ai_extractor` None builds the real MariTalk adapter from `env`, as the application does;
    tests pass a fake. `progress(index, total, file_name, started)` gets counters only.
    """
    from app.infrastructure.clock import SystemClock
    from app.infrastructure.database.session import make_engine
    from app.presentation.dependencies import build_container

    files = list_corpus_files(options.folder)
    if options.limit is not None:
        files = files[: options.limit]
    if not files:
        raise CorpusError("Nenhum arquivo PDF, JPG ou PNG na pasta")
    env = env or {}
    ai = _resolve_ai(options, ai_extractor, env)

    started = time.monotonic()
    _migrate(database_url)
    engine = make_engine(database_url)
    try:
        with tempfile.TemporaryDirectory(prefix="corpus-storage-") as storage_dir:
            settings = _make_settings(options, database_url, env, storage_dir, len(files))
            container = build_container(settings, engine, SystemClock(), ai)
            setup = _create_process(container, engine, settings, options)
            order, by_id = _upload_files(container, setup, files)
            _run_jobs(container, by_id, progress)
            score = container.calculate_process_score.execute(setup.admin, setup.process.id)
            rows = {row.activity_id: row for row in score.result.rows}
            for document_id, entry in by_id.items():
                _fill_entry(container, setup.admin, options, document_id, entry, rows)
            model = settings.effective_maritalk_model
            return CorpusReport(
                generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                parameters={
                    "start": options.start.isoformat(),
                    "end": options.end.isoformat(),
                    "ai": "dry-run (sem IA)" if options.dry_run else f"MariTalk, modelo {model}",
                },
                process={
                    "table": {"name": setup.table_name, "version": setup.version.name},
                    "score": _score_block(score),
                    "documents": summarize_documents(order),
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                },
                documents=order,
            )
    finally:
        engine.dispose()


def _fill_entry(
    container: Any, admin: Any, options: Options, document_id: Any, entry: DocumentEntry, rows: Any
) -> None:
    """Copies the stored outcome of one document into its report entry (no text)."""
    from app.domain.rules.interstice import Interstice
    from app.domain.rules.scoring_periods import evaluate_period

    detail = container.get_document.execute(admin, document_id)
    document = detail.document
    entry.status = document.status.value
    entry.status_code = document.status_code
    entry.document_type = document.manual_type or document.suggested_type
    entry.category = document.suggested_category
    entry.confidence = decimal_text(document.confidence)
    entry.pages = len(detail.pages) or document.page_count
    entry.page_methods = [p.method.value for p in detail.pages]
    confidences = [p.ocr_confidence for p in detail.pages if p.ocr_confidence is not None]
    if confidences:
        entry.ocr_mean_confidence = decimal_text(
            (sum(confidences) / len(confidences)).quantize(Decimal("0.01"))
        )
    if detail.run is not None:
        raw = detail.run.raw_json or {}
        returned = raw.get("activities") if isinstance(raw, dict) else None
        entry.ai_returned = len(returned) if isinstance(returned, list) else None
        entry.duration_ms = detail.run.duration_ms
        warnings = [
            {
                "code": w.get("code"),
                "field": w.get("field"),
                "activity_index": w.get("activity_index"),
            }
            for w in detail.run.warnings
        ]
        entry.grounding_warnings = [w for w in warnings if w["code"] in GROUNDING_CODES]
        entry.alerts = [w["code"] for w in warnings if w["code"] not in GROUNDING_CODES]
    interstice = Interstice(options.start, options.end)
    states: list[str] = []
    for linked in detail.activities:
        activity = linked.activity
        row = rows.get(activity.id)
        state = evaluate_period(activity, interstice).value
        states.append(state)
        label = item_label(activity.group_number, activity.item_number)
        if label is not None and label not in entry.items:
            entry.items.append(label)
        title = None
        if options.include_titles:
            title = mask_text(activity.title)[:MAX_TITLE_CHARS]
        entry.activities.append(
            ActivityEntry(
                item=label,
                status=activity.status.value,
                score_status=row.status.value if row else "-",
                points=decimal_text(row.points) if row else "0",
                period=state,
                reasons=[r.value for r in row.reasons] if row else [],
                alerts=[a.code.value for a in row.alerts] if row else [],
                title=title,
            )
        )
    entry.interstice = interstice_summary(states)
    entry.without_item = (
        document.suggested_category == "SEM_ITEM_DE_PONTUACAO"
        or any(a.item is None for a in entry.activities)
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
        options = options_from_args(args)
        env = {**(load_env_file(options.env_file) if options.env_file else {}), **os.environ}

        def progress(index: int, total: int, name: str, tick: float) -> None:
            seconds = time.monotonic() - tick
            print(f"[{index}/{total}] {mask_text(name)} ({seconds:.1f}s)", flush=True)

        if options.database_url:
            report = run_corpus(options, options.database_url, env=env, progress=progress)
        else:
            with throwaway_postgres() as url:
                report = run_corpus(options, url, env=env, progress=progress)
        json_path, md_path = write_report(report, options.out_dir, datetime.now())
    except CorpusError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError:
        print("Erro: não foi possível iniciar o PostgreSQL descartável (Docker disponível?)",
              file=sys.stderr)
        return 2
    summary = report.process["documents"]
    print(f"Arquivos: {summary['files']}; por status: {_counter_text(summary['by_status'])}")
    print(f"Atividades: {summary['activities']}; sem item: {summary['without_item']}")
    print(f"Relatório: {md_path}")
    print(f"Relatório: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

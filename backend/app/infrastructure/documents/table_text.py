"""The words of the Tabela de Pontuação, shared by the PDF and the DOCX so both say the same."""

from app.domain.rules.pt_format import format_interstice
from app.domain.rules.table_document import GroupBand, TableAlert, TableDocument

TITLE = "TABELA DE PONTUAÇÃO"
COLUMNS = (
    "Item", "Atividade", "Quantidade", "Pontuação unitária", "Total", "Comprovante", "Status",
)  # fmt: skip
PIT_HEADING = "Horas de PIT por semestre (Grupo I, fora do total de pontos)"
PIT_COLUMNS = ("Período letivo", "Horas de PIT")
PIT_TOTAL_LABEL = "Total em horas"
ALERTS_HEADING = "Alertas"


def identification_lines(document: TableDocument) -> tuple[str, ...]:
    header = document.header
    return (
        f"Docente: {header.professor_name}",
        f"Classe e nível atuais: {header.current_class}, nível {header.current_level}",
        f"Classe e nível pretendidos: {header.target_class}, nível {header.target_level}",
        f"Unidade: {header.unit_name}",
        f"Interstício: {format_interstice(header.interstice)}",
        f"Tabela de pontuação: {document.table_name}",
        f"Referência normativa: {document.norm_reference}",
    )


def band_title(band: GroupBand) -> str:
    return f"{band.numeral}. {band.name}"


def band_subtotal(band: GroupBand) -> str:
    return f"Subtotal: {band.subtotal}"


def total_line(document: TableDocument) -> str:
    return f"Pontuação geral: {document.total}"


def counters_line(document: TableDocument) -> str:
    c = document.counters
    parts = (
        f"Atividades: {c.activities}",
        f"Com comprovante: {c.with_evidence}",
        f"Pendentes: {c.pending}",
        f"Não pontuadas: {c.not_scored}",
        f"Com divergências: {c.with_alerts}",
    )
    return "   |   ".join(parts)


def alert_line(alert: TableAlert) -> str:
    return f"{alert.subject}: {alert.message}" if alert.subject else alert.message

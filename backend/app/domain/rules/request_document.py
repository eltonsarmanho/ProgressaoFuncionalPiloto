"""The text of the Requerimento at the CPPD, from the public PROGEP model (REQ-02 to REQ-08).

Pure function of the process, the professor, the unit, the city typed in Stage 7 and the date of
the last Parecer. Classes, levels and denominations are the ones the person typed in Stage 1:
nothing is deduced from the career structure (NMOV-01). The "REVISÃO" part of the model is not
reproduced (REQ-07); nothing here reads the clock or calls the AI (REQ-08). The writers (DOCX,
PDF) only draw this model, in the order the fields are declared.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.report import PageSetup
from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import format_date, format_interstice, format_long_date

BLANK_TEXT = "__________"
BLANK_DATE = "___/___/___"
SUPERIOR_CAREER = "MAGISTERIO_SUPERIOR"
_HEADER = (
    "MINISTÉRIO DA EDUCAÇÃO",
    "UNIVERSIDADE FEDERAL DO PARÁ",
    "PRÓ-REITORIA DE DESENVOLVIMENTO E GESTÃO DE PESSOAL",
)
_TITLE = "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)"
_GREETING = "Prezado Sr. Presidente da CPPD,"
_OPTION = "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO"
_CLOSING = "Nestes termos, pede deferimento."
_SIGNATURE_LINE = "__________________________________________"
_SIGNATURE_CAPTION = "Assinatura do (a) requerente"
_LGPD_HEADING = "Observação"
_LGPD_TEXT = (
    "De acordo com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018), "
    "deve-se restringir o acesso a este documento por conter informações pessoais."
)


@dataclass(frozen=True)
class RequestDocument:
    """What a writer draws, in the order of the model."""

    page: PageSetup
    header_lines: tuple[str, ...]
    title: str
    greeting: str
    option: str
    request_paragraph: str
    evaluation_line: str
    place_date_line: str
    closing: str
    signature_line: str
    signature_caption: str
    siape_line: str
    lgpd_heading: str
    lgpd_text: str


def _careers(career_code: str) -> str:
    """Only the Magistério Superior is a known career; any other code marks neither option."""
    superior = "(X)" if career_code == SUPERIOR_CAREER else "(  )"
    return f"{superior} Magistério Superior/ (  ) Ensino Básico e Tecnológico"


def _paragraph(
    process: FunctionalProcess, professor: Professor, unit: AcademicUnit, career_code: str
) -> str:
    noun = "promoção" if process.modality is Modality.PROMOCAO else "progressão"
    interstice = Interstice(process.start_date, process.end_date)
    return (
        f"Eu, {professor.full_name}, Matrícula SIAPE {professor.siape}, docente do "
        f"{_careers(career_code)}, atualmente lotado no (a) {unit.name}, solicito {noun} "
        f"funcional, do nível {process.current_level} da classe {process.current_class} "
        f"({process.current_denomination}) para o nível {process.target_level} da classe "
        f"{process.target_class} ({process.target_denomination}), referente ao interstício "
        f"{format_interstice(interstice)}."
    )


def build_request(
    process: FunctionalProcess,
    professor: Professor,
    unit: AcademicUnit,
    career_code: str,
    city: str | None,
    last_opinion_date: date | None,
    page: PageSetup,
) -> RequestDocument:
    """`career_code` is the code of the career structure of the professor; `last_opinion_date`
    is the date of the last Parecer, none while there is not one."""
    evaluated = format_date(last_opinion_date) if last_opinion_date else BLANK_DATE
    place = (city or "").strip() or BLANK_TEXT
    return RequestDocument(
        page=page,
        header_lines=_HEADER,
        title=_TITLE,
        greeting=_GREETING,
        option=_OPTION,
        request_paragraph=_paragraph(process, professor, unit, career_code),
        evaluation_line=(
            "Em conformidade com a avaliação de desempenho em anexo, realizada na data de "
            f"{evaluated}."
        ),
        place_date_line=f"{place}, {format_long_date(process.opening_date)}.",
        closing=_CLOSING,
        signature_line=_SIGNATURE_LINE,
        signature_caption=_SIGNATURE_CAPTION,
        siape_line=f"Matrícula SIAPE: {professor.siape}",
        lgpd_heading=_LGPD_HEADING,
        lgpd_text=_LGPD_TEXT,
    )

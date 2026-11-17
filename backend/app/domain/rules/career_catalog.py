"""Magistério Superior career versions as pure data (CARR-02, CARR-03).

Sources: docs/referencias/normas/FONTES.md (Res. 4.644/2015-CONSEPE; Lei 12.772/2012,
compiled text after Lei 15.141/2025).
"""

from datetime import date

from app.domain.entities.career import CareerClass, CareerVersion

RES_4644_2015 = CareerVersion(
    name="Res. 4.644/2015-CONSEPE",
    valid_from=None,
    valid_to=date(2024, 12, 31),
    norm_reference="Res. 4.644/2015-CONSEPE, arts. 2º, 4º e 5º",
    classes=(
        CareerClass("A", ("Adjunto A", "Assistente A", "Auxiliar"), (1, 2), None),
        CareerClass("B", ("Assistente",), (1, 2), 24),
        CareerClass("C", ("Adjunto",), (1, 2, 3, 4), 24),
        CareerClass("D", ("Associado",), (1, 2, 3, 4), 24),
        CareerClass("E", ("Titular",), (1,), 24),
    ),
    progression_min_months=24,
)

LEI_15141_2025 = CareerVersion(
    name="Lei 12.772/2012 com redação da Lei 15.141/2025",
    valid_from=date(2025, 1, 1),
    valid_to=None,
    norm_reference=(
        "Lei 12.772/2012 com redação da Lei 15.141/2025, art. 1º, §1º, Anexo I "
        "e art. 12, §§2º e 3º"
    ),
    classes=(
        CareerClass("A", ("Assistente",), (1,), None),
        CareerClass("B", ("Adjunto",), (1, 2, 3, 4), 36),
        CareerClass("C", ("Associado",), (1, 2, 3, 4), 24),
        CareerClass("D", ("Titular",), (1,), 24),
    ),
    progression_min_months=24,
)

MAGISTERIO_SUPERIOR_VERSIONS: tuple[CareerVersion, ...] = (RES_4644_2015, LEI_15141_2025)

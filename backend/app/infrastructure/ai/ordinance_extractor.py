"""The adapter of the `OrdinanceExtractor` port: reads the number, the date and the members of the
board ordinance (PORT-02, PORT-04).

Only the masked text with the `[PÁGINA n]` marks is sent, never the file (PORT-04). The schema is
strict (every property required, `null` for what the text does not say, nothing extra) and the
answer is checked against it again here before it becomes an `OrdinanceAi`, which is still
untrusted until `ground_ordinance` checks each value against its page (AD-009). The key stays in
the client: it is never part of an error, a `repr` or a log line.
"""

import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.entities.board import BoardRole, OrdinanceReadingCode
from app.domain.repositories.ports import OrdinanceExtractionError
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from app.infrastructure.ai.maritalk import ChatError, ChatFailure, MariTalkClient
from app.infrastructure.ai.schemas import validate_against_schema

_SYSTEM_PROMPT = (
    "Você lê a portaria que designa a banca de avaliação de um processo de progressão docente "
    "de uma universidade federal. Extraia somente o que está escrito no texto; não deduza, não "
    "complete e não invente. Quando um dado não consta no texto, use null; se nenhum membro "
    "aparece, devolva a lista vazia. O texto está dividido em páginas marcadas como "
    "[PÁGINA n]; informe em `number_page`, `date_page` e em `page` de cada membro o número da "
    "página de onde veio o dado. Em `number` copie o número da portaria como está escrito. A "
    "data é a de emissão da portaria, no formato AAAA-MM-DD. Em cada membro, copie o nome "
    "completo como está escrito e informe a função: PRESIDENTE, MEMBRO ou SUPLENTE. Responda "
    "somente com o JSON do esquema, sem comentários."
)
_NULLABLE_STRING = {"type": ["string", "null"]}
_NULLABLE_PAGE = {"type": ["integer", "null"]}
_MEMBER: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "role", "page"],
    "properties": {
        "name": {"type": "string", "description": "Nome completo do membro, como escrito."},
        "role": {"type": "string", "enum": [role.value for role in BoardRole]},
        "page": {"type": "integer", "description": "Número da página [PÁGINA n] do nome."},
    },
}
_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["number", "number_page", "ordinance_date", "date_page", "members"],
    "properties": {
        "number": {**_NULLABLE_STRING, "description": "Número da portaria, como escrito."},
        "number_page": {**_NULLABLE_PAGE, "description": "Página do número."},
        "ordinance_date": {**_NULLABLE_STRING, "description": "Data da portaria, AAAA-MM-DD."},
        "date_page": {**_NULLABLE_PAGE, "description": "Página da data."},
        "members": {"type": "array", "items": _MEMBER},
    },
}
_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {"name": "portaria_banca", "strict": True, "schema": _SCHEMA},
}
_CODE_OF = {
    ChatFailure.UNAVAILABLE: OrdinanceReadingCode.IA_INDISPONIVEL,
    ChatFailure.CREDENTIAL_REFUSED: OrdinanceReadingCode.IA_CREDENCIAL_RECUSADA,
    ChatFailure.INVALID_RESPONSE: OrdinanceReadingCode.RESPOSTA_INVALIDA,
}


def _invalid() -> OrdinanceExtractionError:
    return OrdinanceExtractionError(OrdinanceReadingCode.RESPOSTA_INVALIDA)


def _to_ordinance(content: dict[str, Any]) -> OrdinanceAi:
    """The checked answer as an `OrdinanceAi`; anything out of the schema is refused."""
    if validate_against_schema(content, _SCHEMA):
        raise _invalid()
    when = content["ordinance_date"]
    try:
        parsed = None if when is None else date.fromisoformat(when)
    except ValueError:
        raise _invalid() from None
    if when is not None and len(when) != 10:
        raise _invalid()
    members = tuple(
        OrdinanceAiMember(item["name"], item["role"], item["page"]) for item in content["members"]
    )
    return OrdinanceAi(
        number=content["number"],
        number_page=content["number_page"],
        ordinance_date=parsed,
        date_page=content["date_page"],
        members=members,
    )


class MariTalkOrdinanceExtractor:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chat = MariTalkClient(settings, transport, sleep, monotonic)

    def __repr__(self) -> str:
        return "MariTalkOrdinanceExtractor()"

    def extract(self, text: str) -> OrdinanceAi:
        """The ordinance as the AI read it; raises `OrdinanceExtractionError`."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        try:
            result = self._chat.chat(messages, _RESPONSE_FORMAT)
        except ChatError as error:
            raise OrdinanceExtractionError(_CODE_OF[error.failure]) from None
        return _to_ordinance(result.content)

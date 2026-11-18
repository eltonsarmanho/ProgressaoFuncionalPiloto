"""The adapter of the `ReportWriter` port: words the entries of one report section (REL-03,
REL-05, REL-06).

Only the fields of the activities are sent (AD-014): an opaque id, the criterion of the table, the
title, dates, hours, period, quantity and the masked description; never the text of a page, the
name of the professor or an identifier. One call a section, temperature 0, strict JSON, at most
`wording_timeout_seconds` for the whole call, and nothing repeated but the switch to the backup
model (AD-005). Any failure is `AiWritingError(REDACAO_INDISPONIVEL)`: the report falls back to
the template text. The key stays in the client and is never part of an error.
"""

import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings
from app.domain.entities.generated import GenerationAlertCode
from app.domain.repositories.ports import AiWritingError
from app.domain.rules.report_wording import WordingItem
from app.infrastructure.ai.maritalk import ChatError, MariTalkClient

MAX_TOKENS = 4000
_SYSTEM_PROMPT = (
    "Você redige, em português formal e impessoal, a linha de cada atividade de um relatório de "
    "atividades docentes de uma universidade federal. Para cada item recebido escreva um único "
    "texto curto, na terceira pessoa, usando somente os campos informados do próprio item "
    "(tipo, titulo, datas, carga_horaria, carga_horaria_curso, periodo_letivo, quantidade, "
    "descricao). Não acrescente fatos, números, datas, nomes, cursos nem instituições que não "
    "estejam nos campos do item. Não escreva objetivos, resultados, metodologias, impactos, "
    "avaliações nem elogios. Devolva o `id` de cada item sem alterá-lo. Responda somente com o "
    "JSON do esquema, sem comentários."
)
_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "redacao_secao",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["items"],
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "texto"],
                        "properties": {"id": {"type": "string"}, "texto": {"type": "string"}},
                    },
                }
            },
        },
    },
}


def _unavailable() -> AiWritingError:
    return AiWritingError(GenerationAlertCode.REDACAO_INDISPONIVEL)


def _texts(content: Mapping[str, Any]) -> dict[UUID, str]:
    """The text of each item by id; anything out of the schema of the answer is refused."""
    items = content.get("items")
    if not isinstance(items, list):
        raise _unavailable()
    texts: dict[UUID, str] = {}
    for item in items:
        if not isinstance(item, dict):
            raise _unavailable()
        identifier, text = item.get("id"), item.get("texto")
        if not isinstance(identifier, str) or not isinstance(text, str):
            raise _unavailable()
        try:
            texts.setdefault(UUID(identifier), text)
        except ValueError:
            raise _unavailable() from None
    return texts


class MariTalkReportWriter:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chat = MariTalkClient(settings, transport, sleep, monotonic)
        self._deadline = settings.wording_timeout_seconds

    def __repr__(self) -> str:
        return "MariTalkReportWriter()"

    def draft(self, section_title: str, items: Sequence[WordingItem]) -> Mapping[UUID, str]:
        """One text per item id; raises `AiWritingError` when the provider cannot give them."""
        if not items:
            return {}
        user = json.dumps(
            {"secao": section_title, "itens": [item.payload() for item in items]},
            ensure_ascii=False,
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        try:
            result = self._chat.chat(
                messages,
                _RESPONSE_FORMAT,
                max_tokens=MAX_TOKENS,
                deadline_seconds=self._deadline,
                retries=False,
            )
        except ChatError:
            raise _unavailable() from None
        return _texts(result.content)

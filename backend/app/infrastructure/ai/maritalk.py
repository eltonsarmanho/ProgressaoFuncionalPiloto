"""MariTalk adapter for the `AiExtractor` port (EXT-01..06, EXT-09).

Calls the OpenAI-compatible `POST {base}/chat/completions`. Only `choices[0].message.content`
and `finish_reason` are read; `reasoning_content` is never read or stored. The API key goes in
the `Authorization` header of each request only: it is never part of an exception, `repr` or
log line, and logs carry model, status and timing, never text.
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import DocumentType
from app.domain.repositories.ports import AiExtraction, AiExtractionError
from app.infrastructure.ai.schemas import response_format, schema_for

logger = logging.getLogger("app.maritalk")

RETRY_SLEEP_SECONDS = (2, 6)
_MODEL_ERROR_STATUSES = frozenset({400, 404})
_TRANSIENT_STATUSES = frozenset({429})
_SYSTEM_PROMPT = (
    "Você extrai dados de comprovantes acadêmicos de um docente. "
    "Extraia somente o que está escrito no texto; não deduza, não complete e não invente. "
    "Quando um dado não consta no texto, use null. "
    "O texto está dividido em páginas marcadas como [PÁGINA n]; informe em `page` o número "
    "da página de onde veio cada dado e em `evidence_text` o trecho literal dessa página. "
    "Não calcule pontos, quantidades nem horas: copie apenas o que o texto diz. "
    "Datas no formato AAAA-MM-DD. Responda somente com o JSON do esquema, sem comentários. "
    "Tipo provável do documento: {hint}"
)
_PROFESSOR_PROMPT = (
    " O docente deste processo se chama {name}. Em `docente_nome` devolva o nome do docente "
    "como está escrito no texto quando ele aparece; discentes, presidentes, diretores e outros "
    "membros que não sejam esse docente não são o docente. O texto pode citar várias pessoas."
)


class MariTalkExtractor:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = (settings.maritalk_api_base or "").rstrip("/")
        self._key = settings.maritalk_api_key
        self._model = settings.effective_maritalk_model
        self._fallback_model = settings.maritalk_fallback_model
        self._max_tokens = settings.ai_max_tokens
        self._client = httpx.Client(transport=transport, timeout=settings.ai_timeout_seconds)
        self._sleep = sleep
        self._monotonic = monotonic

    def __repr__(self) -> str:
        return f"MariTalkExtractor(model={self._model!r})"

    def extract(
        self, document_type: DocumentType, text: str, professor_name: str | None = None
    ) -> AiExtraction:
        """Raw JSON of the extraction; raises `AiExtractionError` when it cannot be obtained."""
        if not self._base or self._key is None:
            raise AiExtractionError(DocAlertCode.IA_INDISPONIVEL)
        started = self._monotonic()
        model, max_tokens = self._model, self._max_tokens
        used_fallback = used_budget_retry = False
        transient_retries = 0
        while True:
            body = self._body(document_type, text, model, max_tokens, professor_name)
            try:
                response = self._post(body)
            except httpx.HTTPError:
                transient_retries = self._wait_or_give_up(transient_retries)
                continue
            status = response.status_code
            logger.info("maritalk model=%s status=%s", model, status)
            if status == 200:
                parsed = _parse_content(response)
                if parsed is not None:
                    duration_ms = int((self._monotonic() - started) * 1000)
                    return AiExtraction(raw_json=parsed, model=model, duration_ms=duration_ms)
                if used_budget_retry:
                    raise AiExtractionError(DocAlertCode.RESPOSTA_INVALIDA) from None
                used_budget_retry, max_tokens = True, max_tokens * 2
            elif status in (401, 403):
                raise AiExtractionError(DocAlertCode.IA_CREDENCIAL_RECUSADA) from None
            elif status in _TRANSIENT_STATUSES or status >= 500:
                transient_retries = self._wait_or_give_up(transient_retries)
            elif (
                status in _MODEL_ERROR_STATUSES
                and _mentions_model(response)
                and not used_fallback
                and model != self._fallback_model
            ):
                used_fallback, model = True, self._fallback_model
            else:
                raise AiExtractionError(DocAlertCode.IA_INDISPONIVEL) from None

    def _wait_or_give_up(self, retries_done: int) -> int:
        """Sleep before the next retry (2 s, then 6 s); give up after two retries."""
        if retries_done >= len(RETRY_SLEEP_SECONDS):
            raise AiExtractionError(DocAlertCode.IA_INDISPONIVEL) from None
        self._sleep(RETRY_SLEEP_SECONDS[retries_done])
        return retries_done + 1

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        assert self._key is not None
        return self._client.post(
            f"{self._base}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self._key.get_secret_value()}"},
        )

    @staticmethod
    def _body(
        document_type: DocumentType,
        text: str,
        model: str,
        max_tokens: int,
        professor_name: str | None = None,
    ) -> dict[str, Any]:
        hint = schema_for(document_type)["description"]
        system = _SYSTEM_PROMPT.format(hint=hint)
        if professor_name and professor_name.strip():
            system += _PROFESSOR_PROMPT.format(name=" ".join(professor_name.split()))
        return {
            "model": model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "response_format": response_format(document_type),
        }


def _mentions_model(response: httpx.Response) -> bool:
    return "model" in response.text.lower()


def _parse_content(response: httpx.Response) -> dict[str, Any] | None:
    """The JSON object in `choices[0].message.content`, or None for an invalid response."""
    try:
        choice = response.json()["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return None
    if finish_reason == "length" or not isinstance(content, str) or not content.strip():
        return None
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None

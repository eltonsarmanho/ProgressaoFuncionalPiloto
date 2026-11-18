"""MariTalk transport and the adapter for the `AiExtractor` port (EXT-01..06, EXT-09).

`MariTalkClient` is the shared transport: it calls the OpenAI-compatible
`POST {base}/chat/completions`. Only `choices[0].message.content`
and `finish_reason` are read; `reasoning_content` is never read or stored. The API key goes in
the `Authorization` header of each request only: it is never part of an exception, `repr` or
log line, and logs carry model, status and timing, never text.
"""

import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
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
    "O documento pode estar em inglês: copie os campos literalmente do texto, sem traduzir. "
    "Em `term` copie literalmente o prazo de duração da designação quando o texto o traz "
    "(\"por 2 (dois) anos\", \"24 meses\"); nunca calcule a data final. "
    "Em portarias, devolva como atividade somente a designação do docente para a função ou a "
    "comissão; cláusulas que dispensam, exoneram ou destituem o docente, ou encerram um "
    "mandato, não são atividades e não devem ser devolvidas. "
    "Atividades de banca só existem em atas de defesa, declarações ou portarias de banca; "
    "fichas de avaliação de seminário, de disciplina ou de trabalho de aluno não são bancas. "
    "Datas no formato AAAA-MM-DD. Responda somente com o JSON do esquema, sem comentários. "
    "Tipo provável do documento: {hint}"
)
_PROFESSOR_PROMPT = (
    " O docente deste processo se chama {name}. Em `docente_nome` devolva o nome do docente "
    "como está escrito no texto quando ele aparece; discentes, presidentes, diretores e outros "
    "membros que não sejam esse docente não são o docente. O texto pode citar várias pessoas."
)


class ChatFailure(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    CREDENTIAL_REFUSED = "CREDENTIAL_REFUSED"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class ChatError(Exception):
    """A chat call that could not return a content; carries only the kind of failure."""

    def __init__(self, failure: ChatFailure):
        super().__init__(failure.value)
        self.failure = failure


@dataclass(frozen=True)
class ChatResult:
    content: dict[str, Any]
    model: str
    duration_ms: int


class MariTalkClient:
    """One chat call with retries: header, status mapping, fallback model and total deadline."""

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
        self._timeout = settings.ai_timeout_seconds
        self.http = httpx.Client(transport=transport, timeout=settings.ai_timeout_seconds)
        self._sleep = sleep
        self._monotonic = monotonic

    def __repr__(self) -> str:
        return f"MariTalkClient(model={self._model!r})"

    def chat(
        self,
        messages: Sequence[Mapping[str, str]],
        response_format: Mapping[str, Any],
        *,
        max_tokens: int | None = None,
        deadline_seconds: float | None = None,
    ) -> ChatResult:
        """The JSON object of the answer; raises `ChatError` when it cannot be obtained.

        `deadline_seconds` bounds the whole call, repetitions and waits included.
        """
        if not self._base or self._key is None:
            raise ChatError(ChatFailure.UNAVAILABLE)
        started = self._monotonic()
        model, budget = self._model, max_tokens or self._max_tokens
        used_fallback = used_budget_retry = False
        transient_retries = 0
        while True:
            body = {
                "model": model,
                "temperature": 0,
                "max_tokens": budget,
                "messages": list(messages),
                "response_format": dict(response_format),
            }
            try:
                response = self._post(body, self._time_left(started, deadline_seconds))
            except httpx.HTTPError:
                transient_retries = self._wait_or_give_up(
                    transient_retries, started, deadline_seconds
                )
                continue
            status = response.status_code
            logger.info("maritalk model=%s status=%s", model, status)
            if status == 200:
                parsed = _parse_content(response)
                if parsed is not None:
                    duration_ms = int((self._monotonic() - started) * 1000)
                    return ChatResult(content=parsed, model=model, duration_ms=duration_ms)
                if used_budget_retry:
                    raise ChatError(ChatFailure.INVALID_RESPONSE) from None
                used_budget_retry, budget = True, budget * 2
            elif status in (401, 403):
                raise ChatError(ChatFailure.CREDENTIAL_REFUSED) from None
            elif status in _TRANSIENT_STATUSES or status >= 500:
                transient_retries = self._wait_or_give_up(
                    transient_retries, started, deadline_seconds
                )
            elif (
                status in _MODEL_ERROR_STATUSES
                and _mentions_model(response)
                and not used_fallback
                and model != self._fallback_model
            ):
                used_fallback, model = True, self._fallback_model
            else:
                raise ChatError(ChatFailure.UNAVAILABLE) from None

    def _time_left(self, started: float, deadline: float | None) -> float | None:
        if deadline is None:
            return None
        left = deadline - (self._monotonic() - started)
        if left <= 0:
            raise ChatError(ChatFailure.UNAVAILABLE) from None
        return left

    def _wait_or_give_up(self, retries_done: int, started: float, deadline: float | None) -> int:
        """Sleep before the next retry (2 s, then 6 s); give up after two or past the deadline."""
        if retries_done >= len(RETRY_SLEEP_SECONDS):
            raise ChatError(ChatFailure.UNAVAILABLE) from None
        delay = RETRY_SLEEP_SECONDS[retries_done]
        if deadline is not None and self._monotonic() - started + delay >= deadline:
            raise ChatError(ChatFailure.UNAVAILABLE) from None
        self._sleep(delay)
        return retries_done + 1

    def _post(self, body: dict[str, Any], time_left: float | None) -> httpx.Response:
        assert self._key is not None
        timeout = self.http.timeout if time_left is None else min(time_left, self._timeout)
        return self.http.post(
            f"{self._base}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self._key.get_secret_value()}"},
            timeout=timeout,
        )


_ALERT_OF = {
    ChatFailure.UNAVAILABLE: DocAlertCode.IA_INDISPONIVEL,
    ChatFailure.CREDENTIAL_REFUSED: DocAlertCode.IA_CREDENCIAL_RECUSADA,
    ChatFailure.INVALID_RESPONSE: DocAlertCode.RESPOSTA_INVALIDA,
}


class MariTalkExtractor:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chat = MariTalkClient(settings, transport, sleep, monotonic)
        self._client = self._chat.http  # the timeout of the HTTP client is pinned by the tests

    def __repr__(self) -> str:
        return f"MariTalkExtractor(model={self._chat._model!r})"

    def extract(
        self, document_type: DocumentType, text: str, professor_name: str | None = None
    ) -> AiExtraction:
        """Raw JSON of the extraction; raises `AiExtractionError` when it cannot be obtained."""
        try:
            result = self._chat.chat(
                self._messages(document_type, text, professor_name),
                response_format(document_type),
            )
        except ChatError as error:
            raise AiExtractionError(_ALERT_OF[error.failure]) from None
        return AiExtraction(
            raw_json=result.content, model=result.model, duration_ms=result.duration_ms
        )

    @staticmethod
    def _messages(
        document_type: DocumentType, text: str, professor_name: str | None = None
    ) -> list[dict[str, str]]:
        hint = schema_for(document_type)["description"]
        system = _SYSTEM_PROMPT.format(hint=hint)
        if professor_name and professor_name.strip():
            system += _PROFESSOR_PROMPT.format(name=" ".join(professor_name.split()))
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ]

    @staticmethod
    def _body(
        document_type: DocumentType,
        text: str,
        model: str,
        max_tokens: int,
        professor_name: str | None = None,
    ) -> dict[str, Any]:
        """The request as the client sends it; the prompt tests and the live test read it."""
        return {
            "model": model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": MariTalkExtractor._messages(document_type, text, professor_name),
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

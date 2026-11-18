"""Domain errors, mapped to HTTP by the presentation layer."""


class DomainError(Exception):
    """Base class for domain errors."""


class NotFound(DomainError):
    pass


class Conflict(DomainError):
    """A conflict with the current state; `code` is optional and reaches the 409 body."""

    def __init__(self, message: str = "", code: str | None = None):
        super().__init__(message)
        self.code = code


class StaleVersion(Conflict):
    pass


class Forbidden(DomainError):
    pass


class ValidationFailed(DomainError):
    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class _CodedError(DomainError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class GenerationRefused(_CodedError):
    """A document generation refused at the request (422), with a stable code."""


class Gone(_CodedError):
    """A resource that existed and was deliberately removed, such as a purged file (410)."""

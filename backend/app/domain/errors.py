"""Domain errors, mapped to HTTP by the presentation layer."""


class DomainError(Exception):
    """Base class for domain errors."""


class NotFound(DomainError):
    pass


class Conflict(DomainError):
    pass


class StaleVersion(Conflict):
    pass


class Forbidden(DomainError):
    pass


class ValidationFailed(DomainError):
    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message

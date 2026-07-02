class ContinuumError(Exception):
    """Base exception for all Continuum orchestration errors."""


class AgentNotFoundError(ContinuumError):
    """Raised when a caller asks for an agent name that isn't registered."""


class AgentAlreadyRegisteredError(ContinuumError):
    """Raised when registering an agent name that already exists without overwrite=True."""


class ContinuumConfigurationError(ContinuumError):
    """Raised when the Continuum SDK itself is misconfigured (bad model string, missing gateway key, ...)."""


class ContinuumTimeoutError(ContinuumError):
    """Raised when a Continuum agent run times out."""


class ContinuumUnavailableError(ContinuumError):
    """Raised when the Continuum runtime / configured model is unreachable."""


class MalformedResponseError(ContinuumError):
    """Raised when the model's response could not be parsed/validated into the expected schema."""

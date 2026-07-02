class DockerError(Exception):
    """Base exception for Docker integration errors."""


class DockerContainerNotFoundError(DockerError):
    """Raised when a container ID/name doesn't exist on this host."""


class DockerUnavailableError(DockerError):
    """Raised when the Docker daemon is unreachable or returns a server-side error."""


class DockerPermissionError(DockerError):
    """Raised when the process lacks permission to access the Docker socket."""


class DockerTimeoutError(DockerError):
    """Raised when a Docker daemon call times out."""

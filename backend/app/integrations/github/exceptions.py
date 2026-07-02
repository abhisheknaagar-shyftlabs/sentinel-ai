class GitHubError(Exception):
    """Base exception for GitHub integration errors."""


class GitHubAuthError(GitHubError):
    """Raised when the token is invalid, expired, or lacks required scopes."""


class GitHubNotFoundError(GitHubError):
    """Raised when a repository, PR, or other resource doesn't exist or isn't accessible."""


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub's rate limit has been exhausted."""


class GitHubAPIError(GitHubError):
    """Raised for any other non-2xx response from the GitHub API."""

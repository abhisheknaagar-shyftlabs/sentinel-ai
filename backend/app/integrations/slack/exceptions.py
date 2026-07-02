class SlackError(Exception):
    """Base for Slack integration failures."""


class SlackNotConfiguredError(SlackError):
    """Raised when no webhook URL is configured."""

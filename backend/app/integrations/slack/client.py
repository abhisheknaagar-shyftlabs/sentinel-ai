import httpx

from app.integrations.slack.exceptions import SlackError, SlackNotConfiguredError


class SlackClient:
    """Thin wrapper over a Slack Incoming Webhook - the simplest way to post a
    formatted message to a channel with no bot/OAuth setup required. Pure data
    delivery, deliberately not routed through Continuum: posting a message is
    not an AI capability. Takes an injectable transport, same test-seam
    pattern as GitHubClient/DockerClient, so unit tests never need a real
    webhook."""

    def __init__(
        self,
        webhook_url: str | None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self._webhook_url)

    async def post_message(self, text: str, blocks: list[dict] | None = None) -> None:
        if not self._webhook_url:
            raise SlackNotConfiguredError("SLACK_WEBHOOK_URL is not configured")

        payload: dict = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(self._webhook_url, json=payload)

        if response.status_code >= 400:
            raise SlackError(f"Slack webhook returned {response.status_code}: {response.text}")

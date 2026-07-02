import httpx
import pytest

from app.integrations.slack.client import SlackClient
from app.integrations.slack.exceptions import SlackError, SlackNotConfiguredError


def _transport(status_code=200, body="ok"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=body)

    return httpx.MockTransport(handler)


async def test_post_message_raises_when_not_configured():
    client = SlackClient(None)
    assert client.is_configured is False

    with pytest.raises(SlackNotConfiguredError):
        await client.post_message("hello")


async def test_post_message_success():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read()
        return httpx.Response(200, text="ok")

    client = SlackClient("https://hooks.slack.com/services/x", transport=httpx.MockTransport(handler))
    assert client.is_configured is True

    await client.post_message("hello", blocks=[{"type": "section"}])

    assert b"hello" in captured["json"]


async def test_post_message_raises_on_error_status():
    client = SlackClient(
        "https://hooks.slack.com/services/x", transport=_transport(status_code=500, body="boom")
    )

    with pytest.raises(SlackError):
        await client.post_message("hello")

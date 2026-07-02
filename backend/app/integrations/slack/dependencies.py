from app.config.settings import get_settings
from app.integrations.slack.client import SlackClient


def get_slack_client() -> SlackClient:
    settings = get_settings()
    return SlackClient(settings.slack_webhook_url)

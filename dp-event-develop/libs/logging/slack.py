import requests


class Slack:
    def __init__(self, webhook: str):
        """
        Initialize the SlackWebhook.
        Args:
            webhook (str): The Slack incoming webhook URL.
        """
        self.webhook = webhook

    def send_notification(self, message: str) -> None:
        """
        Send a notification to the specified Slack channel using the incoming webhook.
        Args:
            message (str): The message to be sent.
        """
        payload = f"{{'text': '{message}'}}"
        requests.post(self.webhook, data=payload)
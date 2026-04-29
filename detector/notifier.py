import requests
import datetime


class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _format_timestamp(self, ts):
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    def _send(self, message: str):
        """
        Send a message to Slack webhook.
        """
        if not self.webhook_url:
            print("[SLACK] Webhook missing")
            return

        payload = {
            "text": message
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )

            if response.status_code != 200:
                print(f"[SLACK ERROR] {response.status_code} {response.text}")

        except Exception as e:
            print(f"[SLACK EXCEPTION] {e}")

    def send_ban_alert(
        self,
        ip,
        condition,
        current_rate,
        baseline,
        duration,
        timestamp
    ):
        """
        Send Slack message when an IP is blocked.
        """
        if duration is None:
            duration_text = "PERMANENT"
        else:
            minutes = round(duration / 60, 1)
            duration_text = f"{minutes} minutes"

        message = (
            "🚨 *IP Anomaly Detected*\n"
            f"*IP:* `{ip}`\n"
            f"*Condition:* {condition}\n"
            f"*Current Rate:* {current_rate} req/min\n"
            f"*Baseline:* {baseline} req/min\n"
            f"*Ban Duration:* {duration_text}\n"
            f"*Time:* {self._format_timestamp(timestamp)}"
        )

        self._send(message)

    def send_unban_alert(self, ip, timestamp):
        """
        Send Slack message when IP is automatically unbanned.
        """
        message = (
            "✅ *IP Automatically Unbanned*\n"
            f"*IP:* `{ip}`\n"
            f"*Time:* {self._format_timestamp(timestamp)}"
        )

        self._send(message)

    def send_global_alert(
        self,
        condition,
        current_rate,
        baseline,
        timestamp
    ):
        """
        Send Slack message for global traffic spike.
        """
        message = (
            "🌍 *Global Traffic Anomaly*\n"
            f"*Condition:* {condition}\n"
            f"*Current Rate:* {current_rate} req/min\n"
            f"*Baseline:* {baseline} req/min\n"
            f"*Time:* {self._format_timestamp(timestamp)}"
        )

        self._send(message)
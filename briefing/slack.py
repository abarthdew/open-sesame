import os
import requests


def send(text: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        print("[slack] SLACK_WEBHOOK_URL not set — printing instead:\n")
        print(text)
        return
    r = requests.post(url, json={"text": text}, timeout=10)
    if r.status_code != 200:
        print(f"[slack] send failed: {r.status_code} {r.text}")

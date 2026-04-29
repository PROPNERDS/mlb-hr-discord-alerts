import os
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def main():
    message = "🚨 TEST SUCCESS 🚨 Your Discord webhook + GitHub bot are connected! #PropNerds"
    requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)

if __name__ == "__main__":
    main()

import argparse

from app.config import get_settings
from app.providers.nylas_email import create_message_webhook


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register the Nylas message.created webhook."
    )
    parser.add_argument(
        "notification_email",
        help="Address Nylas should notify if webhook delivery fails.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.nylas_api_key or not settings.server_url:
        raise SystemExit("Set NYLAS_API_KEY and SERVER_URL first.")

    webhook = create_message_webhook(
        api_key=settings.nylas_api_key,
        api_uri=settings.nylas_api_uri,
        webhook_url=f"{settings.server_url.rstrip('/')}/events",
        notification_email=args.notification_email,
    )
    print(f"Webhook created: {webhook.id}")
    print(f"WEBHOOK_SECRET={webhook.secret}")


if __name__ == "__main__":
    main()

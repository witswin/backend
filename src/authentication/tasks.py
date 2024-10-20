from django.utils import timezone
from celery import shared_task
from authentication.sign_with_ethereum import SignWithEthereum


@shared_task
def remove_old_nonces() -> None:
    """
    Celery task to remove expired nonce entries from the SignWithEthereum instance.
    Nonces are considered expired if their expiration_time is before the current time.
    """
    sign = SignWithEthereum()  # Get the singleton instance
    current_time = timezone.now()  # Get the current time (timezone-aware)

    expired_addresses = [
        address
        for address, (_, message) in sign.nonces.items()
        if message.expiration_time.to_datetime() < current_time
    ]

    # Remove expired nonces from the dictionary
    for address in expired_addresses:
        del sign.nonces[address]

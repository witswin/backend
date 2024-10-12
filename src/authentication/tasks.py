
from datetime import timezone

from authentication import SignWithEthereum

from celery import shared_task

@shared_task
def remove_old_nonces():
        sign = SignWithEthereum()
        old_items = [k for k, v in sign.nonces.items() if v[1].expiration_time < timezone.now().timestamp()]
        for k in old_items:
            del sign.nonces[k]
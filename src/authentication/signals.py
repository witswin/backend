from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_periodic_task(sender, **kwargs):
    if sender.name == 'authentication':  # Only run for our app
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.get_or_create(
            task='authentication.tasks.remove_old_nonces',
            name='Remove old nonces every 10 minutes',
            interval=schedule,
        )
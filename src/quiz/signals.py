import json
from celery import current_app
from django.utils import timezone
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django_celery_beat.models import (
    PeriodicTask,
    CrontabSchedule,
    ClockedSchedule,
    PeriodicTasks,
)
from quiz.models import Competition
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(pre_delete, sender=Competition)
def clean_competition_task(sender, instance: Competition, **kwargs):
    channel_layer = get_channel_layer()

    current_app.control.revoke(f"start_competition_{instance.pk}", terminate=True)  # type: ignore

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_list",
        {"type": "delete_competition", "data": instance.pk},
    )


@receiver(post_save, sender=Competition)
def trigger_competition_starter_task(sender, instance: Competition, created, **kwargs):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_list",
        {"type": "update_competition_data", "data": instance.pk},
    )

    existing_task_name = f"start_competition_{instance.pk}"

    try:
        old_task = PeriodicTask.objects.get(name=existing_task_name)
        old_task.delete()
        PeriodicTasks.changed(old_task)
    except PeriodicTask.DoesNotExist:
        pass

    if not instance.is_active:
        return

    start_time = instance.start_at

    if start_time < timezone.now():
        return

    # Create a new crontab schedule
    clocked_schedule, created = ClockedSchedule.objects.get_or_create(
        clocked_time=start_time
        - timezone.timedelta(seconds=10)  # or use start_time directly
    )

    # Now create a new PeriodicTask with the new schedule
    task = PeriodicTask.objects.create(
        clocked=clocked_schedule,  # Use ClockedSchedule for one-time execution
        name=existing_task_name,  # Unique task name
        task="quiz.tasks.setup_competition_to_start",  # The task to be executed
        args=json.dumps([instance.pk]),  # Pass the instance ID as an argument
        one_off=True,  # Ensure it's a one-time task
    )

    PeriodicTasks.changed(task)


# This assumes the task is scheduled with a unique name using the competition ID.
# current_app.control.revoke(f"start_competition_{instance.pk}", terminate=True)

# setup_competition_to_start.apply_async(
#     args=[instance.pk],
#     eta=start_time - timezone.timedelta(seconds=10),
#     task_id=f"start_competition_{instance.pk}",
# )  # type: ignore

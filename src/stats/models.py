from django.db import models


class AppSettingManager(models.Manager):
    def get_key(self, key: str):
        return self.get_queryset().filter(key=key).first()


class AppSettting(models.Model):
    key = models.CharField(max_length=1000, unique=True)
    value = models.TextField()
    is_public = models.BooleanField(default=False)

    objects: AppSettingManager = AppSettingManager()

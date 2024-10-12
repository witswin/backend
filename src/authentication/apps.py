from django.apps import AppConfig


from django.db.models.signals import post_migrate
from django.dispatch import receiver


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        import authentication.signals  # Make sure to create this file
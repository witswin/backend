from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from cloudflare_images.field import CloudflareImagesField


class Lower(models.Func):
    function = "LOWER"
    template = "%(function)s(%(expressions)s)"


class UserProfile(models.Model):
    username = models.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message="Username can only contain letters, digits and @/./+/-/_.",
            ),
        ],
        null=True,
        blank=True,
        unique=True,
    )
    wallet_address = models.CharField(max_length=512, db_index=True, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    image = CloudflareImagesField(variant="public", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("wallet_address"), name="unique_wallet_address_case_insensitive"
            ),
            models.UniqueConstraint(
                Lower("username"), name="unique_username_case_insensitive"
            ),
        ]

    def __str__(self) -> str:
        return self.username or self.wallet_address


class PrivyProfile(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=300)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

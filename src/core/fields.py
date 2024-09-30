"""
Contains all the fields related classes to support custom features
such as variants in Cloudflare Images
"""

from django.db.models.base import Model
from django.db.models.fields.files import (
    FileField,
    ImageFieldFile,
    ImageField,
    ImageFileDescriptor,
)
from .storages import CloudflareImagesStorage
from django.db import models
from rest_framework.serializers import CurrentUserDefault


class CurrentUserProfileDefault(CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context["request"].user.profile


class BigNumField(models.Field):
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 200  # or some other number
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return "numeric"

    def get_internal_type(self):
        return "BigNumField"

    def to_python(self, value):
        if isinstance(value, str):
            return int(value)

        return value

    def get_prep_value(self, value):
        return str(value)

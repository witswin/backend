# Generated by Django 5.0 on 2024-09-10 07:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_userprofile_unique_wallet_address_case_insensitive_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrivyProfile',
            fields=[
                ('id', models.CharField(max_length=300, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authentication.userprofile')),
            ],
        ),
    ]

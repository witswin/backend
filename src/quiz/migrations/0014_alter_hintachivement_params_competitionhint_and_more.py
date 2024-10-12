import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0013_hint_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hintachivement",
            name="params",
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        # Create the new CompetitionHint intermediary model
        migrations.CreateModel(
            name="CompetitionHint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("count", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="quiz.Competition",
                    ),
                ),
                (
                    "hint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="quiz.Hint"
                    ),
                ),
            ],
            options={
                "unique_together": {("competition", "hint")},
            },
        ),
        # Remove the old built_in_hints field
        migrations.RemoveField(
            model_name="competition",
            name="built_in_hints",
        ),
        # Add the built_in_hints field back with the correct through model
        migrations.AddField(
            model_name="competition",
            name="built_in_hints",
            field=models.ManyToManyField(
                blank=True,
                related_name="built_in_competitions",
                through="quiz.CompetitionHint",
                to="quiz.Hint",
            ),
        ),
    ]

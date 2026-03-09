"""
Add CustomFormField and RegistrationResponse models.

These allow organizers to define custom registration form fields
and store participant responses per field.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registration", "0002_registration_looking_for_team_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomFormField",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "field_label",
                    models.CharField(max_length=200, verbose_name="field label"),
                ),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("text", "Short Text"),
                            ("textarea", "Long Text"),
                            ("number", "Number"),
                            ("dropdown", "Dropdown"),
                            ("multi_select", "Multi-Select"),
                            ("radio", "Radio Buttons"),
                            ("date", "Date"),
                            ("url", "URL"),
                        ],
                        default="text",
                        max_length=15,
                    ),
                ),
                (
                    "field_options",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='["Option A", "Option B"] — for dropdown/radio/multi-select fields',
                    ),
                ),
                ("is_required", models.BooleanField(default=False)),
                (
                    "display_order",
                    models.PositiveSmallIntegerField(db_index=True, default=0),
                ),
                (
                    "placeholder",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="custom_fields",
                        to="events.event",
                    ),
                ),
            ],
            options={
                "ordering": ["event", "display_order"],
            },
        ),
        migrations.CreateModel(
            name="RegistrationResponse",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("response_value", models.TextField(blank=True, default="")),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="registration.customformfield",
                    ),
                ),
                (
                    "registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="registration.registration",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="registrationresponse",
            constraint=models.UniqueConstraint(
                fields=["registration", "field"],
                name="uniq_response_per_field",
            ),
        ),
    ]

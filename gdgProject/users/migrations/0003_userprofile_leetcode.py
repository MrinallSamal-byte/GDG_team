from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_userprofile_portfolio_userprofile_profile_picture_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="leetcode",
            field=models.URLField(blank=True, default=""),
        ),
    ]

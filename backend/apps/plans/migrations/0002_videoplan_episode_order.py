from django.db import migrations, models


def seed_episode_order(apps, schema_editor):
    SeriesPlan = apps.get_model("plans", "SeriesPlan")
    VideoPlan = apps.get_model("plans", "VideoPlan")

    for series in SeriesPlan.objects.all().iterator():
        episodes = VideoPlan.objects.filter(series=series).order_by("created_at", "id")
        for index, episode in enumerate(episodes, start=1):
            VideoPlan.objects.filter(pk=episode.pk).update(episode_order=index)


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="videoplan",
            name="episode_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(seed_episode_order, migrations.RunPython.noop),
    ]

# Generated by Django 5.2 on 2025-05-24 06:24

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='class',
            name='capacity',
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AlterField(
            model_name='subject',
            name='code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddConstraint(
            model_name='subject',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True), ('is_deleted', False)), fields=('code',), name='code'),
        ),
    ]

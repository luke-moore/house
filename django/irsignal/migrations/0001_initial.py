# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ProntoCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('device', models.CharField(max_length=60)),
                ('button', models.CharField(max_length=60)),
                ('pronto_code', models.TextField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='prontocode',
            unique_together=set([('device', 'button')]),
        ),
    ]

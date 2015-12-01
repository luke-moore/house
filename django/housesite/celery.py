from __future__ import absolute_import

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "housesite.settings")
from django.conf import settings

from celery import Celery

app = Celery("house")
app.config_from_object("django.conf:settings")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

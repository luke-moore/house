from __future__ import absolute_import

# Ensure that the celery app is loaded so that applications can use it.
from .celery import app as celery_app

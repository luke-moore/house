import optparse

from django.core.management.base import BaseCommand

from irsignal import models

class Command(BaseCommand):
    help = "Sends an infrared remote signal."

    def add_arguments(self, parser):
        parser.add_argument("device",
            help="The name of the device the remote controls")
        parser.add_argument("button",
            help="The name of the button on the remote")

    def handle(self, *args, **options):
        models.press_button(options["device"], options["button"])

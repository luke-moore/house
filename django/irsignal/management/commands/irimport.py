import optparse

from django.core.management.base import BaseCommand

from irsignal import models

class Command(BaseCommand):
    help = "Savs an infrared signal given by a device address and key code."

    def add_arguments(self, parser):
        parser.add_argument("device",
            help="The name of the device the remote controls")
        parser.add_argument("button",
            help="The name of the button on the remote")
        parser.add_argument("code_type",
            help="The type of code",
            choices=("NEC", "RC5"))
        parser.add_argument("device_address",
            help="The device address specified by the manufacturer",
            type=int)
        parser.add_argument("key_code",
            help="The key code specified by the manufacturer",
            type=int)

    def handle(self, *args, **options):
        if options["code_type"].lower() == "nec":
            pronto_code = models.nec_code_to_pronto_code(
                options["device_address"], options["key_code"])
        elif options["code_type"].lower() == "rc5":
            pronto_code = models.philips_rc5_to_pronto_code(
                options["device_address"], options["key_code"])
        else:
            assert not "Invalid choices for the code type argument"

        models.save_button(options["device"], options["button"], pronto_code)

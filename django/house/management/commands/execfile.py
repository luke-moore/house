import sys
import os
import traceback
import optparse
import pdb

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Executes a Python file."
    args = "script"

    option_list = BaseCommand.option_list + (
        optparse.make_option("--debug",
            action="store_true", dest="debug", default=False,
            help="Drop into a debugger on an exception"),
    )

    def handle(self, *scripts, **options):
        if len(scripts) < 1:
            print self.style.ERROR("Script file name required")
            return

        script = scripts[0]
        if not os.path.isfile(script):
            print self.style.ERROR("Invalid file name: %s" % script)
            return

        try:
            execfile(
                script, {
                    "__builtins__": __builtins__,
                    "__name__": "__main__",
                    "__doc__": None,
                    "__package__": None,
                })
        except Exception, e:
            if isinstance(e, SyntaxError) or not options["debug"]:
                raise
            info = sys.exc_info()
            traceback.print_exception(*info)
            pdb.post_mortem(info[2])

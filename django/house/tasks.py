from __future__ import absolute_import
import time
import itertools

from celery import shared_task

import irsignal

@shared_task
def press_remote_buttons(devices_and_buttons_and_timeouts):
    for device, button, timeout_in_s in grouper(
            devices_and_buttons_and_timeouts, 3, 0):
        irsignal.press_button(device, button)
        time.sleep(timeout_in_s)

def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks (from the itertools
    recipes).

    grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)

@shared_task
def test():
    print "the test task is running"

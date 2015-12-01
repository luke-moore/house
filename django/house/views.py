from django.template import RequestContext
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

import webapi
import irsignal
import huelights
import wemo
from . import tasks

class HouseAPI(webapi.API):
    @webapi.api_method
    def press_remote(self, request, device, button):
        if not irsignal.is_busy():
            irsignal.press_button(device, button)

    def press_remote_buttons(devices_and_buttons_and_timeouts):
        tasks.press_remote_buttons.delay(devices_and_buttons_and_timeouts)

    @webapi.api_method
    def set_light_scene(self, request, scene_name):
        huelights.set_scene(scene_name)

    @webapi.api_method
    def turn_on_switch(self, request, switch_name):
        wemo.turn_on_switch(switch_name)

    @webapi.api_method
    def turn_off_switch(self, request, switch_name):
        wemo.turn_off_switch(switch_name)

@csrf_exempt
def api_view(request):
    return HouseAPI().dispatch(request)

def index_view(request):
    return render(request, "house/index.html", RequestContext(request))

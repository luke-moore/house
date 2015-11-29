import json
import urllib

from django.db import models
from django.conf import settings

import qhue

_bridge_address = None
def get_bridge_address():
    global _bridge_address
    if _bridge_address is not None:
        return _bridge_address

    _bridge_address = json.load(
            urllib.urlopen("http://www.meethue.com/api/nupnp")
        )[0]["internalipaddress"]
    return _bridge_address

_cached_scene_names_to_ids = {}
def set_scene(scene_name):
    bridge = qhue.Bridge(get_bridge_address(), settings.HUELIGHTS_USERNAME)
    if scene_name not in _cached_scene_names_to_ids:
        for scene_id, scene_info in bridge.scenes().items():
            _cached_scene_names_to_ids[scene_info["name"]] = scene_id

        if scene_name not in _cached_scene_names_to_ids:
            raise RuntimeError("Invalid scene name")

    bridge.groups[0].action(scene=_cached_scene_names_to_ids[scene_name])

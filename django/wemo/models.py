import ouimeaux.environment
import psutil

_cached_environment = None
def _environment():
    global _cached_environment
    if _cached_environment is None:
        _cached_environment = ouimeaux.environment.Environment()
        _cached_environment.start()
        _cached_environment.discover(1)

    return _cached_environment

def _is_ouimeaux_server_running():
    for connection in psutil.net_connections():
        if connection.laddr[1] == 8989 and connection.status == "LISTEN":
            return True

    return False

def _switch(switch_name):
    return _environment().get_switch(switch_name)

def turn_on_switch(switch_name):
    _switch(switch_name).on()

def turn_off_switch(switch_name):
    _switch(switch_name).off()

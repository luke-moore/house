import json
import traceback
import inspect

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

# This decorator is used to flag API methods.
def api_method(method):
    if inspect.getargspec(method).args[:2] != ["self", "request"]:
        raise RuntimeError(
            "%s's first two arguments should be self and request" %
                method.__name__)
    method._is_api_method = True
    return method

class API(object):
    """
    Handle web API requests.
    """
    def dispatch(self, request):
        """
        Dispatch requests for '/api' URLs by:
           1. Unpacking the handler and post data from the JSON in the request.
           2. Looking up the handler method.
           3. Dispatching to it.
           4. Wrapping its response as JSON.
        The handler method must take the user name as its first argument, as
        well as optional extra arguments.  It normally returns a valid
        HttpResponse or raises an StoreError exception when it wants to give the
        user helpful error messages.  However, buggy or malicious callers can
        make a handler raise other exceptions, in which case the production
        server will return a non-descriptive error message.
        """
        try:
            result = self._dispatch_without_catching_api_errors(request)
        except PermissionDenied:
            return _text_http_response(traceback.format_exc(), status=403)
        except Exception:
            return _text_http_response(traceback.format_exc(), status=500)

        # If the API function didn't return an HttpResponse, wrap the result
        # in JSON and convert to an HttpResponse on its behalf.
        if not isinstance(result, HttpResponse):
            result = _json_http_response(result)

        return result

    def _dispatch_without_catching_api_errors(self, request):
        """
        As the name suggests, this help method dispatches without
        looking for or handling errors.
        """
        # Note that request.POST is a magic variable that loads the data on
        # demand when you access it.  For whatever reason, django's engine
        # might not read the post data.  In this case, don't bother to generate
        # an error trigger an email to be sent to the site administrators.
        try:
            json_data = request.POST.get("json")
        except IOError:
            return _text_http_response(
                "Error reading POST data:\n" + traceback.format_exc(), 500)

        if "json" not in request.POST:
            return _text_http_response(
                "'json' not given in the POST data", 500)

        # Look up the API method, making sure that it exists and has been
        # flagged as an API method.
        function_name, args, kwargs = json.loads(json_data)
        handler = getattr(self, function_name, None)
        if handler is None or not hasattr(handler, "_is_api_method"):
            raise PermissionDenied("Invalid API function: %s" % function_name)

        self._validate_arguments(
            function_name, inspect.getargspec(handler).args[2:], args, kwargs)
        return handler(request, *args, **kwargs)

    def _validate_arguments(
            self, function_name, expected_arg_names, args, kwargs):
        if len(args) > len(expected_arg_names):
            raise RuntimeError(
                "%s received %s arguments, but only expects %s" % (
                    function_name, len(args) + len(kwargs),
                    len(expected_arg_names)))

        expected_kwarg_names = expected_arg_names[len(args):]

        missing_arg_names = []
        for name in expected_kwarg_names:
            if name not in kwargs:
                missing_arg_names.append(name)

        extra_arg_names = []
        for name in kwargs.keys():
            if name not in expected_kwarg_names:
                extra_arg_names.append(name)

        if len(missing_arg_names) + len(extra_arg_names) == 0:
            return

        errors = ""
        if len(missing_arg_names) > 0:
            errors += "Missing keyword argument%s %s" % (
                "s" * (len(missing_arg_names) > 0),
                ", ".join(repr(name) for name in missing_arg_names))

        if len(extra_arg_names) > 0:
            errors += "Unknown keyword argument%s %s" % (
                "s" * (len(extra_arg_names) > 0),
                ", ".join(repr(name) for name in extra_arg_names))

        errors += " in call to %s" % function_name
        raise RuntimeError(errors)

def _json_http_response(content, status=200):
    """
    Translate a response JSON and return.
    """
    return _text_http_response(json.dumps(
        _values_to_json(content)), status=status)

def _text_http_response(content, status=200):
    """
    Translate a response into HTML text.
    """
    response = HttpResponse(content, status=status)
    response["Content-Length"] = str(len(response.content))
    return response

def _values_to_json(data):
    if isinstance(data, list):
        return [_values_to_json(item) for item in data]

    if isinstance(data, tuple):
        return tuple(_values_to_json(item) for item in data)

    if isinstance(data, dict):
        return dict(
            (_values_to_json(key), _values_to_json(value))
            for key, value in data.items())

    return data

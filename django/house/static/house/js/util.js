// If an ajax call generates a server error, display it to the user so that
// errors are discovered sooner and aren't silenced and missed.
$(document).ajaxError(function (event, request, settings, thrown_error) {
    alert("Error: " + settings.url + " returned " + thrown_error + "\n" +
        request.responseText);
});

function get_uri_parameter_by_name(name)
{
    // Look through the GET parameters in the URL and retrieve one with the
    // specified name.
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
    var results = regex.exec(location.search);
    return results === null
        ? null : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function remove_parameter_from_url(parameter)
{
    url = window.location.href;
    var url_parts = url.split('?');   
    if (url_parts.length < 2)
        return url;

    var prefix = encodeURIComponent(parameter) + '=';
    var name_value_groups = url_parts[1].split(/[&;]/g);

    // reverse iteration as may be destructive
    for (var i = name_value_groups.length - 1; i >= 0; --i)
    {    
        if (name_value_groups[i].lastIndexOf(prefix, 0) !== -1)
            name_value_groups.splice(i, 1);
    }

    return url_parts[0] + '?' + name_value_groups.join('&');
}

function scope_apply_callback($scope, func)
{
    // Given a function that takes an arbitrary number of arguments, return
    // a function that, when called, will run the function inside a
    // $scope.$apply.
    //
    // Use this function to provide an ajax callback that will call
    // $scope.$apply when the function runs, so that AngularJS will check
    // for updates to the model from the callback.

    return function() {
        var old_this = this;
        args = Array.prototype.slice.call(arguments);
        $scope.$apply(function() {
            func.apply(old_this, args);
        });
    };
}

function run_possible_callback(callback)
{
    if (typeof(callback) == "undefined")
       return;

    args = Array.prototype.slice.call(arguments);
    args.shift();
    callback.apply(this, args);
}

function ajax_call(api_url, function_name, kwargs, callback)
{
    if (typeof api_url == "undefined")
        alert("Error: api_url is undefined.  (Perhaps the data-apiurl" +
            " attribute is missing?)");

    // Make an ajax call to the api url, running the given callback when
    // the server gives a response.
    $.post(
        api_url,
        "json=" + encodeURIComponent(
            JSON.stringify([function_name, [], kwargs])),
        callback);
};

function ajax_call_that_saves($scope, api_url, function_name, kwargs, callback)
{
    // Make an ajax call that saves something, displaying a message in the
    // window until the server comes back with a response.  Note that this
    // function assumes that $scope.is_saving exists.
    if (typeof $scope.num_saves_in_progress == "undefined")
        $scope.num_saves_in_progress = 0;
    $scope.num_saves_in_progress += 1;
    $scope.is_saving = true;

    ajax_call(
        api_url, function_name, kwargs,
        scope_apply_callback($scope, function (data) {
            $scope.num_saves_in_progress -= 1;
            if ($scope.num_saves_in_progress == 0)
                $scope.is_saving = false;

            if (typeof callback != "undefined")
                callback(data);
        }));
}

function queue_autosave($scope, timeout_in_ms, start_save_creation_callback)
{
    // Given an autosave function that will start saving data (or rather, a
    // function that returns a function that will start saving data), queue it
    // to be called when the given timeout expires.  If we've already queued
    // something, though, then don't queue another one.
    if ($scope.waiting_for_autosave)
        return;

    $scope.waiting_for_autosave = true;

    // Build a callback that will start the save.  When it's done the save,
    // it will call our callback to notify that the save completed.
    start_save_callback = start_save_creation_callback(
        function (data) {
            $scope.waiting_for_autosave = false;
        }
    );

    setTimeout(
        scope_apply_callback($scope, start_save_callback),
        timeout_in_ms);
}

function add_warning_for_unsaved_changes($scope, $window)
{
    // Note that this function assumes that $scope.is_saving exists.
    $window.addEventListener("beforeunload", function (e)
    {
        if (!$scope.is_saving)
            return null;

        message = ("Data is still being saved and your changes will" +
            " be lost if you leave.");
        (e || window.event).returnValue = message; // Gecko and IE
        return message; // Gecko and WebKit
    });
}


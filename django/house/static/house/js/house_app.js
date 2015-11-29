angular.module('house_app', [])
    .controller('house_controller',
    ['$scope', '$attrs', function($scope, $attrs)
{
    $scope.ajax_call = function(function_name, kwargs, callback, next_callback)
    {
        ajax_call(
            $attrs.apiurl, function_name, kwargs,
            scope_apply_callback($scope, function(api_result) {
                var callback_result = run_possible_callback(
                    callback, api_result);
                run_possible_callback(next_callback, callback_result);
            })
        );
    }

    $scope.remote_button_press = function (device, button)
    {
	$scope.ajax_call(
	    "press_remote",
	    {"device": device, "button": button}
	);
    }

    $scope.remote_button_down = function (device, button)
    {
	$scope.pressed_device_and_button = [device, button];
	function send_signal()
	{
	    $scope.ajax_call(
		"press_remote",
		{"device": device, "button": button},
		function () {
		    if ($scope.pressed_device_and_button[0] == device &&
			    $scope.pressed_device_and_button[1] == button)
			send_signal();
		}
	    );
	}
	send_signal();
    }

    $scope.remote_button_up = function ()
    {
	$scope.pressed_device_and_button = [null, null];
    }

    $scope.set_light_scene = function (scene_name)
    {
	$scope.ajax_call("set_light_scene", {"scene_name": scene_name});
    }

    $scope.turn_on_switch = function (switch_name)
    {
	$scope.ajax_call("turn_on_switch", {"switch_name": switch_name});
    }

    $scope.turn_off_switch = function (switch_name)
    {
	$scope.ajax_call("turn_off_switch", {"switch_name": switch_name});
    }

    init = function() {
	$scope.pressed_device_and_button = [null, null];
    }

    init();
}]).directive("ngTouchstart", [function() {
    return function (scope, element, attr) {
	element.on("touchstart mousedown", function(event) {
	    scope.$apply(function() { scope.$eval(attr.ngTouchstart); });
	});
    };
}]).directive("ngTouchend", [function() {
    return function (scope, element, attr) {
	element.on("touchend mouseup", function(event) {
	    scope.$apply(function() { scope.$eval(attr.ngTouchend); });
	});
    };
}]);


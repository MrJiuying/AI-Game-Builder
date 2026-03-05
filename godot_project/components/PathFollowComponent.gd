extends Node
class_name PathFollowComponent

@export var path_points: PackedVector2Array = []
@export var move_speed: float = 140.0
@export var arrive_distance: float = 10.0
@export var loop_path: bool = true
@export var follow_enabled: bool = true
@export var use_local_points: bool = true

var _owner_node: Node2D
var _point_index: int = 0

func _ready() -> void:
	_owner_node = get_parent() as Node2D
	if _owner_node == null:
		set_process(false)

func _process(delta: float) -> void:
	if _owner_node == null or not is_instance_valid(_owner_node):
		return
	if not follow_enabled or path_points.is_empty():
		return

	var target := _get_target_point()
	var to_target := target - _owner_node.global_position
	if to_target.length() <= max(arrive_distance, 0.0):
		_advance_point()
		return

	var step := to_target.normalized() * max(move_speed, 0.0) * delta
	if step.length() > to_target.length():
		_owner_node.global_position = target
	else:
		_owner_node.global_position += step

func _get_target_point() -> Vector2:
	var raw := path_points[_point_index]
	if use_local_points:
		return _owner_node.to_global(raw)
	return raw

func _advance_point() -> void:
	if path_points.is_empty():
		return
	_point_index += 1
	if _point_index >= path_points.size():
		_point_index = 0 if loop_path else path_points.size() - 1

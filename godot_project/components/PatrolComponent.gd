extends Node
class_name PatrolComponent

@export var patrol_points: PackedVector2Array = []
@export var move_speed: float = 120.0
@export var acceleration: float = 700.0
@export var friction: float = 600.0
@export var arrive_distance: float = 8.0
@export var wait_time: float = 0.0
@export var loop_patrol: bool = true
@export var use_local_points: bool = true
@export var patrol_enabled: bool = true

var _body: CharacterBody2D
var _index: int = 0
var _wait_left: float = 0.0
var _reverse_dir: int = 1

func _ready() -> void:
	_body = get_parent() as CharacterBody2D
	if _body == null:
		set_physics_process(false)

func _physics_process(delta: float) -> void:
	if _body == null or not is_instance_valid(_body):
		return
	if not patrol_enabled or patrol_points.is_empty():
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
		_body.move_and_slide()
		return

	if _wait_left > 0.0:
		_wait_left = max(_wait_left - delta, 0.0)
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
		_body.move_and_slide()
		return

	var target := _target_point()
	var to_target := target - _body.global_position
	if to_target.length() <= max(arrive_distance, 0.0):
		_wait_left = max(wait_time, 0.0)
		_advance_point()
		return

	var dir := to_target.normalized()
	_body.velocity = _body.velocity.move_toward(dir * max(move_speed, 0.0), acceleration * delta)
	_body.move_and_slide()

func _target_point() -> Vector2:
	var p := patrol_points[_index]
	if use_local_points:
		return _body.to_global(p)
	return p

func _advance_point() -> void:
	if patrol_points.size() <= 1:
		return
	if loop_patrol:
		_index = (_index + 1) % patrol_points.size()
		return
	_index += _reverse_dir
	if _index >= patrol_points.size():
		_reverse_dir = -1
		_index = patrol_points.size() - 2
	elif _index < 0:
		_reverse_dir = 1
		_index = 1

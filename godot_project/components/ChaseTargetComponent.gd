extends Node
class_name ChaseTargetComponent

@export var target_path: NodePath
@export var target_group: StringName = &"player"
@export var max_speed: float = 180.0
@export var acceleration: float = 900.0
@export var friction: float = 700.0
@export var stopping_distance: float = 12.0
@export var chase_enabled: bool = true

var _body: CharacterBody2D
var _target: Node2D

func _ready() -> void:
	_body = get_parent() as CharacterBody2D
	if _body == null:
		set_physics_process(false)

func _physics_process(delta: float) -> void:
	if _body == null or not is_instance_valid(_body):
		return
	if not chase_enabled:
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
		_body.move_and_slide()
		return

	if _target == null or not is_instance_valid(_target):
		_target = _resolve_target()
	if _target == null:
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
		_body.move_and_slide()
		return

	var to_target := _target.global_position - _body.global_position
	if to_target.length() <= max(stopping_distance, 0.0):
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
	else:
		_body.velocity = _body.velocity.move_toward(to_target.normalized() * max_speed, acceleration * delta)
	_body.move_and_slide()

func _resolve_target() -> Node2D:
	if not target_path.is_empty():
		var by_path := get_node_or_null(target_path)
		if by_path is Node2D:
			return by_path as Node2D

	if get_tree() == null:
		return null
	var list := get_tree().get_nodes_in_group(target_group)
	for item in list:
		if item is Node2D and item != _body:
			return item as Node2D
	return null

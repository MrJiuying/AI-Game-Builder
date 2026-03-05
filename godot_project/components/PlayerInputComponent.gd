extends Node
class_name PlayerInputComponent

@export var move_left_action: StringName = &"ui_left"
@export var move_right_action: StringName = &"ui_right"
@export var move_up_action: StringName = &"ui_up"
@export var move_down_action: StringName = &"ui_down"
@export var max_speed: float = 260.0
@export var acceleration: float = 1400.0
@export var friction: float = 1200.0
@export var input_enabled: bool = true

var _body: CharacterBody2D

func _ready() -> void:
	_body = get_parent() as CharacterBody2D
	if _body == null:
		set_physics_process(false)

func _physics_process(delta: float) -> void:
	if _body == null or not is_instance_valid(_body):
		return
	if not input_enabled:
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
		_body.move_and_slide()
		return

	var dir := Input.get_vector(move_left_action, move_right_action, move_up_action, move_down_action)
	if dir != Vector2.ZERO:
		_body.velocity = _body.velocity.move_toward(dir.normalized() * max_speed, acceleration * delta)
	else:
		_body.velocity = _body.velocity.move_toward(Vector2.ZERO, friction * delta)
	_body.move_and_slide()

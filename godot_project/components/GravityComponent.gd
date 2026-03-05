extends Node
class_name GravityComponent

@export var gravity_scale: float = 1.0
@export var base_gravity: float = 980.0
@export var jump_force: float = 360.0
@export var max_fall_speed: float = 1200.0
@export var jump_action: StringName = &"ui_accept"
@export var jump_enabled: bool = true

var _body: CharacterBody2D

func _ready() -> void:
	_body = get_parent() as CharacterBody2D
	if _body == null:
		set_physics_process(false)

func _physics_process(delta: float) -> void:
	if _body == null or not is_instance_valid(_body):
		return

	if jump_enabled and Input.is_action_just_pressed(jump_action) and _body.is_on_floor():
		_body.velocity.y = -abs(jump_force)

	if not _body.is_on_floor():
		_body.velocity.y += base_gravity * max(gravity_scale, 0.0) * delta
		_body.velocity.y = min(_body.velocity.y, max_fall_speed)

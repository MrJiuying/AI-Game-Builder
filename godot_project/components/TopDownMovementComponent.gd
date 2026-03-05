extends Node
class_name TopDownMovementComponent

var max_speed: float = 300.0
var acceleration: float = 1500.0
var friction: float = 1200.0

func _physics_process(delta: float) -> void:
	var parent = get_parent()
	if parent is CharacterBody2D:
		var input_dir = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

		if input_dir != Vector2.ZERO:
			parent.velocity = parent.velocity.move_toward(input_dir * max_speed, acceleration * delta)
		else:
			parent.velocity = parent.velocity.move_toward(Vector2.ZERO, friction * delta)
			
		parent.move_and_slide()

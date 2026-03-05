extends Node
class_name HealthComponent

signal health_changed(previous_health: float, current_health: float)
signal died()

@export var max_health: float = 100.0
@export var current_health: float = 100.0
@export var can_overheal: bool = false
@export var auto_free_on_death: bool = false

func _ready() -> void:
	max_health = max(1.0, max_health)
	current_health = clamp(current_health, 0.0, max_health)
	if current_health <= 0.0:
		current_health = max_health

func take_damage(amount: float) -> void:
	if amount <= 0.0:
		return
	if current_health <= 0:
		return
	
	var previous_health: float = current_health
	current_health = max(0.0, current_health - amount)
	
	health_changed.emit(previous_health, current_health)
	
	if current_health <= 0.0:
		died.emit()
		if auto_free_on_death and get_parent() != null:
			get_parent().queue_free()

func heal(amount: float) -> void:
	if amount <= 0.0:
		return
	if current_health <= 0:
		return
	
	var previous_health: float = current_health
	if can_overheal:
		current_health += amount
	else:
		current_health = min(max_health, current_health + amount)
	
	health_changed.emit(previous_health, current_health)

func set_max_health(value: float, keep_ratio: bool = true) -> void:
	var prev_max: float = max_health
	max_health = max(1.0, value)
	if keep_ratio and prev_max > 0.0:
		var ratio: float = clamp(current_health / prev_max, 0.0, 1.0)
		current_health = max_health * ratio
	else:
		current_health = clamp(current_health, 0.0, max_health)

func get_health_percentage() -> float:
	if max_health <= 0:
		return 0.0
	return current_health / max_health

func is_alive() -> bool:
	return current_health > 0

extends Node
class_name HealthComponent

## 生命数值组件 - 纯粹的数据组件，处理血量增减，不涉及任何物理碰撞

signal health_changed(previous_health: float, current_health: float)
signal died()

@export var max_health: float = 100.0

var current_health: float = max_health

func _ready() -> void:
	current_health = max_health

func take_damage(amount: float) -> void:
	"""
	受到伤害
	参数:
		amount: 伤害数值
	"""
	if current_health <= 0:
		return
	
	var previous_health: float = current_health
	current_health = max(0.0, current_health - amount)
	
	health_changed.emit(previous_health, current_health)
	
	if current_health <= 0:
		died.emit()

func heal(amount: float) -> void:
	"""
	恢复生命值
	参数:
		amount: 恢复数值
	"""
	if current_health <= 0:
		return
	
	var previous_health: float = current_health
	current_health = min(max_health, current_health + amount)
	
	health_changed.emit(previous_health, current_health)

func get_health_percentage() -> float:
	"""获取当前血量百分比 (0.0 - 1.0)"""
	if max_health <= 0:
		return 0.0
	return current_health / max_health

func is_alive() -> bool:
	"""检查是否存活"""
	return current_health > 0

extends Area2D
class_name HitboxComponent

## 攻击判定组件 - 继承自 Area2D，用于对其他实体造成伤害

signal hit_detected(target: Node)

@export var damage: float = 10.0

func _ready() -> void:
	area_entered.connect(_on_area_entered)

func _on_area_entered(area: Area2D) -> void:
	"""
	当其他区域进入该 Hitbox 时触发
	检测是否是 Hurtbox 组件，如果是则造成伤害
	"""
	if area is HurtboxComponent:
		hit_detected.emit(area)
		area.receive_damage(damage)

extends Area2D
class_name HurtboxComponent

## 受击判定组件 - 继承自 Area2D，用于接收伤害

@export var health_component: Node

func _ready() -> void:
	if not health_component:
		health_component = get_parent().get_node_or_null("HealthComponent")

func receive_damage(damage_amount: float) -> void:
	"""
	接收外部调用造成的伤害
	将伤害数值传递给绑定的 HealthComponent
	参数:
		damage_amount: 伤害数值
	"""
	if health_component and health_component.has_method("take_damage"):
		health_component.take_damage(damage_amount)

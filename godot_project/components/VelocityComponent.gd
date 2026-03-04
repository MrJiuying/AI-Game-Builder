extends Node
class_name VelocityComponent

## 移动控制组件 - 处理 2D 俯视角的 8 向移动、加速和摩擦力缓冲

@export var max_speed: float = 300.0
@export var acceleration: float = 1000.0
@export var friction: float = 800.0

var current_velocity: Vector2 = Vector2.ZERO

func move(entity: CharacterBody2D, direction: Vector2) -> void:
	"""
	处理实体移动逻辑
	调用时机：在父节点的 _physics_process 中每帧调用
	
	参数:
		entity: CharacterBody2D 类型的实体节点
		direction: 输入方向向量（归一化）
	"""
	if direction != Vector2.ZERO:
		# 有输入时：应用加速度向目标方向移动
		current_velocity = current_velocity.move_toward(
			direction * max_speed, 
			acceleration * delta_time()
		)
	else:
		# 无输入时：应用摩擦力减速
		current_velocity = current_velocity.move_toward(
			Vector2.ZERO, 
			friction * delta_time()
		)
	
	entity.velocity = current_velocity
	entity.move_and_slide()

func delta_time() -> float:
	"""获取帧时间，确保在不同帧率下运动一致"""
	return get_process_delta_time()

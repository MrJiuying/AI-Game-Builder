extends Node
class_name VelocityComponent

var max_speed: float = 300.0
var acceleration: float = 1500.0
var friction: float = 1200.0

func _ready():
	var parent = get_parent()
	print("【VelocityComponent】🏃 移动大脑已启动！我附身的肉体是: ", parent.name, " | 类型: ", parent.get_class())

func _physics_process(delta: float) -> void:
	var parent = get_parent()
	
	if parent is CharacterBody2D:
		var input_dir = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
		
		if input_dir != Vector2.ZERO:
			print("【VelocityComponent】⌨️ 侦测到键盘输入: ", input_dir)
			parent.velocity = parent.velocity.move_toward(input_dir * max_speed, acceleration * delta)
		else:
			parent.velocity = parent.velocity.move_toward(Vector2.ZERO, friction * delta)
			
		parent.move_and_slide()
		
		if parent.velocity.length() > 0.1:
			print("【VelocityComponent】🚀 狂奔中！当前速度: ", parent.velocity, " | 实时坐标: ", parent.global_position)
			
	else:
		print("【VelocityComponent】❌ 夭寿啦！我没挂在 CharacterBody2D 身上！")
		set_physics_process(false)

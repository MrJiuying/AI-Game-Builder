# 动态碰撞箱生成器组件
# 自动为实体创建碰撞形状
class_name CollisionGeneratorComponent
extends Node

# 导出变量
@export var shape_type: String = "circle"  # 碰撞形状类型：circle 或 rectangle
@export var radius: float = 20.0  # 圆形半径
@export var size_x: float = 40.0  # 矩形宽度
@export var size_y: float = 40.0  # 矩形高度

# 碰撞形状节点
var collision_shape: CollisionShape2D

# 初始化函数
func _ready() -> void:
	# 创建碰撞形状节点
	collision_shape = CollisionShape2D.new()
	
	# 根据形状类型创建对应的碰撞形状
	if shape_type == "circle":
		# 创建圆形碰撞形状
		var circle_shape = CircleShape2D.new()
		circle_shape.radius = radius
		collision_shape.shape = circle_shape
	elif shape_type == "rectangle":
		# 创建矩形碰撞形状
		var rect_shape = RectangleShape2D.new()
		rect_shape.size = Vector2(size_x, size_y)
		collision_shape.shape = rect_shape
	else:
		# 默认使用圆形
		var circle_shape = CircleShape2D.new()
		circle_shape.radius = radius
		collision_shape.shape = circle_shape
	
	# 获取父节点（实体根节点）
	var parent = get_parent()
	if parent:
		# 将碰撞形状添加为父节点的子节点
		parent.add_child(collision_shape)
		# 设置碰撞形状的名称
		collision_shape.name = "CollisionShape2D"
		# 确保碰撞形状在正确的层级
		collision_shape.set_owner(parent)
	else:
		print("警告：CollisionGeneratorComponent 的父节点不存在，无法创建碰撞形状")

# 清理函数
func _exit_tree() -> void:
	# 清理碰撞形状节点
	if collision_shape and is_instance_valid(collision_shape):
		collision_shape.queue_free()

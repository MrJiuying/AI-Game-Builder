class_name EntityAssembler
extends Node

## 实体装配工厂 - 负责从 JSON 配置文件动态组装 Godot 实体节点
##
## 使用示例:
##	var assembler = EntityAssembler.new()
##	var entity = assembler.build_entity_from_json("res://data/entities/CyberAssassin.json")

const COMPONENTS_PATH: String = "res://components/"
const DEFAULT_SPRITE_PATH: String = "res://assets/sprites/"

var _logger: Logger = Logger.new("EntityAssembler")


func _ready() -> void:
	_logger.info("EntityAssembler 已初始化")


func build_entity_from_json(json_path: String) -> Node2D:
	"""
	从 JSON 文件构建实体节点
	参数:
		json_path: JSON 配置文件的 Godot 路径 (如 res://data/entities/Enemy.json)
	返回:
		装配好的实体节点 (Node2D 或子类)，失败返回 null
	"""
	if not _validate_json_file(json_path):
		return null
	
	var json_data = _parse_json_file(json_path)
	if json_data == null:
		return null
	
	var entity: Node2D = _create_base_node(json_data)
	if entity == null:
		return null
	
	_mount_components(entity, json_data)
	_load_sprite(entity, json_data)
	
	_logger.info("实体装配完成: %s" % json_data.get("entity_name", "Unnamed"))
	
	return entity


func _validate_json_file(json_path: String) -> bool:
	"""验证 JSON 文件是否存在"""
	if not FileAccess.file_exists(json_path):
		push_error("[EntityAssembler] 文件不存在: %s" % json_path)
		return false
	return true


func _parse_json_file(json_path: String) -> Dictionary:
	"""解析 JSON 文件内容"""
	var file = FileAccess.open(json_path, FileAccess.READ)
	if file == null:
		push_error("[EntityAssembler] 无法打开文件: %s, 错误: %s" % [json_path, FileAccess.get_open_error()])
		return {}
	
	var json_string: String = file.get_as_text()
	file.close()
	
	var json = JSON.new()
	var parse_result = json.parse(json_string)
	if parse_result != OK:
		push_error("[EntityAssembler] JSON 解析失败: %s" % json_string.left(100))
		return {}
	
	var data = json.get_data()
	if typeof(data) != TYPE_DICTIONARY:
		push_error("[EntityAssembler] JSON 根节点必须是字典对象")
		return {}
	
	return data as Dictionary


func _create_base_node(json_data: Dictionary) -> Node2D:
	"""
	根据 base_type 创建基础节点
	支持的类型: CharacterBody2D, Area2D, StaticBody2D, Node2D
	"""
	var entity_name: String = json_data.get("entity_name", "UnnamedEntity")
	var base_type: String = json_data.get("base_type", "Node2D")
	
	var node: Node2D
	
	match base_type:
		"CharacterBody2D":
			node = CharacterBody2D.new()
		"Area2D":
			node = Area2D.new()
		"StaticBody2D":
			node = StaticBody2D.new()
		"Node2D":
			node = Node2D.new()
		_:
			push_warning("[EntityAssembler] 未知的 base_type: %s，使用默认 Node2D" % base_type)
			node = Node2D.new()
	
	node.name = entity_name
	_logger.info("已创建基础节点: %s (类型: %s)" % [entity_name, base_type])
	
	return node


func _mount_components(entity: Node2D, json_data: Dictionary) -> void:
	"""
	动态挂载组件到实体上
	遍历 components 列表，从 COMPONENTS_PATH 加载脚本并实例化
	"""
	var components: Array = json_data.get("components", [])
	var component_params: Dictionary = json_data.get("component_params", {})
	
	if components.is_empty():
		_logger.info("实体 %s 未定义任何组件" % entity.name)
		return
	
	for comp_name in components:
		if typeof(comp_name) != TYPE_STRING:
			push_warning("[EntityAssembler] 组件名必须是字符串，跳过: %s" % str(comp_name))
			continue
		
		_load_component(entity, comp_name, component_params)


func _load_component(entity: Node2D, comp_name: String, all_params: Dictionary) -> void:
	"""加载单个组件脚本并挂载到实体"""
	var script_path: String = COMPONENTS_PATH + comp_name + ".gd"
	
	if not ResourceLoader.exists(script_path):
		push_warning("[EntityAssembler] 组件脚本不存在: %s" % script_path)
		return
	
	var script: GDScript = load(script_path)
	if script == null:
		push_warning("[EntityAssembler] 脚本加载失败: %s" % script_path)
		return
	
	var component_node: Node = script.new()
	if component_node == null:
		push_warning("[EntityAssembler] 组件实例化失败: %s" % comp_name)
		return
	
	component_node.name = comp_name
	entity.add_child(component_node)
	
	_inject_parameters(component_node, all_params.get(comp_name, {}))
	
	_logger.info("已挂载组件: %s -> %s" % [comp_name, entity.name])


func _inject_parameters(component: Node, params: Dictionary) -> void:
	"""
	将 JSON 中的参数注入到组件节点
	使用 set() 方法动态设置属性
	"""
	if params.is_empty():
		return
	
	for prop_name in params:
		var value = params[prop_name]
		
		if component.has_method("set_" + prop_name):
			component.call("set_" + prop_name, value)
		elif component.has_property(prop_name):
			component.set(prop_name, value)
		else:
			push_warning("[EntityAssembler] 组件 %s 没有属性: %s" % [component.name, prop_name])


func _load_sprite(entity: Node2D, json_data: Dictionary) -> void:
	"""
	如果 JSON 中指定了 sprite_path，则动态加载并挂载 Sprite2D
	支持两种路径格式：
	1. res://xxx.png - Godot 资源路径（需要 .import 文件）
	2. 绝对路径如 C:/xxx/xxx.png 或包含 res:// 的路径（动态加载）
	"""
	var sprite_path: Variant = json_data.get("sprite_path")
	
	if sprite_path == null or sprite_path == "":
		return
	
	if typeof(sprite_path) != TYPE_STRING:
		push_warning("[EntityAssembler] sprite_path 必须是字符串")
		return
	
	var sprite: Sprite2D = Sprite2D.new()
	sprite.name = "Sprite"
	
	# 检测是否是外部绝对路径（需要动态加载）
	if sprite_path.begins_with("/") or (sprite_path.length() > 2 and sprite_path[1] == ":"):
		# 绝对路径
		var real_path = sprite_path
		var img = Image.new()
		var err = img.load(real_path)
		if err == OK:
			sprite.texture = ImageTexture.create_from_image(img)
			if sprite.texture.get_size() != Vector2.ZERO:
				sprite.position = sprite.texture.get_size() / 2.0
			_logger.info("动态加载外部图片: %s" % real_path)
		else:
			push_warning("[EntityAssembler] 外部图片加载失败: %s，尝试使用 Godot 资源路径" % real_path)
			sprite_path = ""  # 回退到 res:// 路径检查
	elif sprite_path.begins_with("res://"):
		# Godot 资源路径
		if not ResourceLoader.exists(sprite_path):
			push_warning("[EntityAssembler] sprite_path 不存在: %s" % sprite_path)
			sprite_path = ""
	
	# 如果没有有效的 sprite_path，加载默认图标
	if sprite_path == "" or sprite_path == null:
		sprite.texture = _make_fallback_texture()
	else:
		# 尝试使用 load() 加载 Godot 资源
		var texture: Texture2D = load(sprite_path)
		if texture != null:
			sprite.texture = texture
			if texture.get_size() != Vector2.ZERO:
				sprite.position = texture.get_size() / 2.0
		else:
			push_warning("[EntityAssembler] 纹理加载失败: %s，使用默认图标" % sprite_path)
			sprite.texture = _make_fallback_texture()
	
	entity.add_child(sprite)
	_logger.info("已设置精灵纹理: %s -> %s" % [sprite.texture, entity.name])


func _make_fallback_texture() -> Texture2D:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.2, 0.55, 0.95, 1.0))
	return ImageTexture.create_from_image(img)


func build_entity_from_dict(json_data: Dictionary) -> Node2D:
	"""
	从字典数据直接构建实体（不读取文件）
	适用于运行时动态生成的数据
	"""
	if json_data.is_empty():
		push_error("[EntityAssembler] 空字典无法构建实体")
		return null

	var entity: Node2D = _create_base_node(json_data)
	if entity == null:
		return null

	_mount_components(entity, json_data)
	_load_sprite(entity, json_data)
	
	# 强制居中到屏幕中央
	if Engine.get_main_loop() != null:
		entity.global_position = Engine.get_main_loop().get_root().get_viewport_rect().size / 2.0
	
	return entity


class Logger:
	var _tag: String
	
	func _init(tag: String) -> void:
		_tag = tag
	
	func info(msg: String) -> void:
		print("[%s] [INFO] %s" % [_tag, msg])
	
	func warning(msg: String) -> void:
		print("[%s] [WARN] %s" % [_tag, msg])
	
	func error(msg: String) -> void:
		push_error("[%s] [ERROR] %s" % [_tag, msg])

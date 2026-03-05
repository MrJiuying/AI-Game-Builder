extends Node2D

var socket = WebSocketPeer.new()
var websocket_url = "ws://127.0.0.1:8000/ws"
var was_connected = false
var current_entity: Node2D = null

const _COMPONENT_DIR_CANDIDATES: Array[String] = [
	"res://components/",
	"res://scripts/components/",
]

func _ready():
	print("【LiveLink】🚀 准备连接到中枢大脑: ", websocket_url)
	var err = socket.connect_to_url(websocket_url)
	if err != OK:
		print("【LiveLink】❌ 初始连接请求失败，错误码: ", err)

func _process(delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not was_connected:
			print("【LiveLink】🟢 已成功连入 AI 中枢！等待指令...")
			was_connected = true
		
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			var msg = packet.get_string_from_utf8()
			print("【LiveLink】📩 收到神谕: ", msg.substr(0, 60), "...")
			handle_message(msg)
			
	elif state == WebSocketPeer.STATE_CLOSED:
		if was_connected:
			print("【LiveLink】🔴 连接断开，尝试重连...")
			was_connected = false
		socket.connect_to_url(websocket_url)

func handle_message(msg: String):
	print("【LiveLink】📦 开始拆解神谕快递...")
	var data = JSON.parse_string(msg)
	if data == null:
		print("【LiveLink】❌ JSON 解析失败！收到的字符串有问题。")
		return
	
	if not data is Dictionary:
		print("【LiveLink】❌ 解析结果不是字典！")
		return
	
	var action: String = data.get("action", "") as String
	if action == "spawn_entity":
		spawn_entity(data)
	elif action == "update_component":
		update_entity_component(data)
	else:
		print("【LiveLink】⚠️ 未知 action: ", action)

func spawn_entity(data: Dictionary):
	print("【LiveLink】🏗️ 开始装配实体...")
	
	var config_path = data.get("config_path", "")
	var sprite_path = data.get("sprite_path", "")
	
	if config_path == "":
		print("【LiveLink】❌ 消息中没有 config_path，无法装配！")
		return
	
	var global_config_path = ProjectSettings.globalize_path(config_path)
	if not FileAccess.file_exists(global_config_path):
		print("【LiveLink】❌ 找不到图纸文件: ", global_config_path)
		return
	
	var file = FileAccess.open(global_config_path, FileAccess.READ)
	if file == null:
		print("【LiveLink】❌ 无法打开图纸文件: ", global_config_path)
		return
	
	var entity_data_text = file.get_as_text()
	file.close()
	
	if entity_data_text == "":
		print("【LiveLink】❌ 图纸文件内容为空！")
		return
	
	var entity_data = JSON.parse_string(entity_data_text)
	if entity_data == null:
		print("【LiveLink】❌ 图纸 JSON 解析失败！")
		return
	
	print("【LiveLink】✅ 图纸读取成功，准备构建实体！")
	
	# 1. 创建根节点
	if current_entity and is_instance_valid(current_entity):
		current_entity.queue_free()
	
	current_entity = CharacterBody2D.new()
	current_entity.name = str(entity_data.get("entity_name", "PreviewEntity"))
	add_child(current_entity)
	
	# 2. 强力动态加载贴图
	var sprite = Sprite2D.new()
	sprite.name = "Sprite"
	var texture_loaded = false
	
	sprite_path = entity_data.get("sprite_path", "")
	if sprite_path != "":
		var real_img_path = ProjectSettings.globalize_path(sprite_path)
		print("【LiveLink】尝试加载图片: ", real_img_path)
		if not FileAccess.file_exists(real_img_path):
			print("【LiveLink】❌ 立绘文件不存在，路径: ", real_img_path)
		else:
			var img = Image.new()
			if img.load(real_img_path) == OK:
				sprite.texture = ImageTexture.create_from_image(img)
				texture_loaded = true
				sprite.scale = Vector2(0.25, 0.25)
				print("【LiveLink】✅ 成功加载 AI 专属立绘！")
			else:
				print("【LiveLink】❌ 立绘加载失败，路径: ", real_img_path)
	
	# 兜底贴图
	if not texture_loaded:
		print("【LiveLink】⚠️ 启用兜底贴图！")
		sprite.texture = _make_fallback_texture()
	
	# 设置精灵位置
	if sprite.texture != null:
		sprite.position = sprite.texture.get_size() / 2.0
	
	current_entity.add_child(sprite)
	
	# 3. 动态挂载组件
	var components = entity_data.get("components", [])
	var component_params = entity_data.get("component_params", {})
	print("【LiveLink】📋 需要挂载的组件: ", components)
	
	for comp_name in components:
		print("【LiveLink】🔧 尝试挂载组件: ", comp_name)
		var loaded_script := _load_component_script(comp_name)
		if loaded_script == null:
			print("【LiveLink】⚠️ 组件脚本不存在或无法编译: ", comp_name)
			continue
		
		var comp_node = loaded_script.new()
		if comp_node == null:
			print("【LiveLink】❌ 组件脚本实例化失败: ", comp_name)
			continue
		
		comp_node.name = comp_name
		
		# 应用组件参数
		var params = component_params.get(comp_name, {})
		for param_key in params.keys():
			comp_node.set(param_key, params[param_key])
			print("【LiveLink】  设置参数 ", param_key, " = ", params[param_key])
		
		current_entity.add_child(comp_node)
		print("【LiveLink】✅ 组件 ", comp_name, " 挂载成功！")
	
	# 4. 挂载到舞台并强制居中！
	current_entity.global_position = get_viewport_rect().size / 2.0
	print("【LiveLink】🎉 实体降临！坐标: ", current_entity.global_position)


func update_entity_component(data: Dictionary) -> void:
	# 给实体名、组件名、参数字典都加上明确类型
	var entity_name: String = data.get("entity_name", "") as String
	var component_name: String = data.get("component_name", "") as String
	var parameters: Dictionary = data.get("parameters", {}) as Dictionary
	
	if entity_name == "" or component_name == "":
		print("【LiveLink】❌ update_component 缺少 entity_name/component_name: ", data)
		return
	if not (parameters is Dictionary):
		print("【LiveLink】❌ update_component.parameters 必须是字典: ", data)
		return
	
	var entity: Node = get_tree().get_root().find_child(entity_name, true, false)
	if entity == null and current_entity != null and is_instance_valid(current_entity) and current_entity.name == entity_name:
		entity = current_entity
	
	if entity == null:
		print("【LiveLink】❌ 找不到实体节点: ", entity_name)
		return
	
	var comp: Node = entity.find_child(component_name, true, false)
	if comp == null:
		print("【LiveLink】❌ 找不到组件节点: ", component_name, " under ", entity_name)
		return
	
	for k in parameters.keys():
		comp.set(k, parameters[k])
		print("【LiveLink】  热更参数 ", k, " = ", parameters[k])
	
	print("【LiveLink】⚡ 属性热更成功！ entity=", entity_name, " component=", component_name)

func _create_fallback_sprite() -> Sprite2D:
	var sprite = Sprite2D.new()
	sprite.name = "FallbackSprite"
	sprite.texture = _make_fallback_texture()
	return sprite


func _make_fallback_texture() -> Texture2D:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.2, 0.55, 0.95, 1.0))
	return ImageTexture.create_from_image(img)


func _candidate_component_paths(comp_name: String) -> Array[String]:
	var paths: Array[String] = []
	for dir_path in _COMPONENT_DIR_CANDIDATES:
		paths.append(dir_path + comp_name + ".gd")
	return paths


func _try_load_script_res(script_path: String) -> Script:
	if ResourceLoader.exists(script_path):
		# Ignore cache so edits/new files can be picked up more reliably.
		var s: Resource = ResourceLoader.load(script_path, "", ResourceLoader.CACHE_MODE_IGNORE)
		if s is Script:
			return s as Script
	return null


func _try_compile_gd_from_disk(res_path: String) -> GDScript:
	var abs_path := ProjectSettings.globalize_path(res_path)
	if not FileAccess.file_exists(abs_path):
		return null
	
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null:
		return null
	
	var code := f.get_as_text()
	f.close()
	
	if code.strip_edges() == "":
		return null
	
	var gd := GDScript.new()
	gd.source_code = code
	var err := gd.reload()
	if err != OK:
		print("【LiveLink】❌ 运行时编译组件脚本失败: ", res_path, " err=", err)
		return null
	return gd


func _load_component_script(comp_name: String) -> Script:
	for script_path in _candidate_component_paths(comp_name):
		var s := _try_load_script_res(script_path)
		if s != null:
			return s
		
		# For scripts created while preview is running, the resource FS may not notice immediately.
		var compiled := _try_compile_gd_from_disk(script_path)
		if compiled != null:
			return compiled
	
	return null

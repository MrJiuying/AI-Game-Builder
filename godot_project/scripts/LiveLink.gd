extends Node2D

var socket = WebSocketPeer.new()
var websocket_url = "ws://127.0.0.1:8000/ws"
var was_connected = false
var current_entity: Node2D = null

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
	
	var action = data.get("action", "")
	if action == "spawn_entity":
		spawn_entity(data)
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
	current_entity.name = "PreviewEntity"
	add_child(current_entity)
	
	# 2. 强力动态加载贴图
	var sprite = Sprite2D.new()
	sprite.name = "Sprite"
	var texture_loaded = false
	
	sprite_path = entity_data.get("sprite_path", "")
	if sprite_path != "":
		var real_img_path = ProjectSettings.globalize_path(sprite_path)
		print("【LiveLink】尝试加载图片: ", real_img_path)
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
		print("【LiveLink】⚠️ 启用兜底蓝色机器人图标！")
		sprite.texture = load("res://icon.svg")
	
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
		var script_path = "res://components/" + comp_name + ".gd"
		if ResourceLoader.exists(script_path):
			var loaded_script = load(script_path)
			if loaded_script:
				var comp_node = loaded_script.new()
				comp_node.name = comp_name
				
				# 应用组件参数
				var params = component_params.get(comp_name, {})
				for param_key in params.keys():
					comp_node.set(param_key, params[param_key])
					print("【LiveLink】  设置参数 ", param_key, " = ", params[param_key])
				
				current_entity.add_child(comp_node)
				print("【LiveLink】✅ 组件 ", comp_name, " 挂载成功！")
			else:
				print("【LiveLink】❌ 组件脚本加载失败: ", script_path)
		else:
			print("【LiveLink】⚠️ 组件脚本不存在: ", script_path)
	
	# 4. 挂载到舞台并强制居中！
	current_entity.global_position = get_viewport_rect().size / 2.0
	print("【LiveLink】🎉 实体降临！坐标: ", current_entity.global_position)

func _create_fallback_sprite() -> Sprite2D:
	var sprite = Sprite2D.new()
	sprite.name = "FallbackSprite"
	sprite.texture = load("res://icon.svg")
	return sprite

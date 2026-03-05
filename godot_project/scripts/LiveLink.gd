extends Node2D

var socket = WebSocketPeer.new()
var websocket_url = "ws://127.0.0.1:8000/ws"
var was_connected = false
var active_entities = {}
var _world_canvas: CanvasLayer
var _world_color_rect: ColorRect
var _world_bg_texture: TextureRect

# 这里定义了我们要上报给 AI 的属性白名单
var _SYNC_PARAM_KEYS = ["max_speed", "acceleration", "friction", "max_health", "damage"]

func _ready():
	print("【LiveLink】🚀 准备连接到中枢大脑: ", websocket_url)
	var err = socket.connect_to_url(websocket_url)
	if err != OK:
		print("【LiveLink】❌ 初始连接请求失败，错误码: ", err)

func _process(delta):
	socket.poll()
	var state: int = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not was_connected:
			print("【LiveLink】🟢 已成功连入 AI 中枢！等待指令...")
			was_connected = true
		
		while socket.get_available_packet_count() > 0:
			var packet: PackedByteArray = socket.get_packet()
			var msg: String = packet.get_string_from_utf8()
			print("【LiveLink】📩 收到神谕...")
			handle_message(msg)
			
	elif state == WebSocketPeer.STATE_CLOSED:
		if was_connected:
			print("【LiveLink】🔴 连接断开，尝试重连...")
			was_connected = false
		socket.connect_to_url(websocket_url)

func handle_message(msg: String):
	var data: Variant = JSON.parse_string(msg)
	if data == null or not data is Dictionary:
		return
	
	var action: String = data.get("action", "") as String
	if action == "spawn_entity":
		spawn_entity(data)
	elif action == "update_component":
		update_entity_component(data)
	elif action == "update_scene_config":
		update_scene_config(data)

func spawn_entity(data: Dictionary):
	print("【LiveLink】🏗️ 开始装配实体...")
	var entity_data: Dictionary = {}
	if data.has("entity_config") and data["entity_config"] is Dictionary:
		entity_data = data["entity_config"] as Dictionary
	else:
		var config_path: String = data.get("config_path", "") as String
		if config_path == "":
			return
		var global_config_path: String = ProjectSettings.globalize_path(config_path)
		if not FileAccess.file_exists(global_config_path):
			return
		var file: FileAccess = FileAccess.open(global_config_path, FileAccess.READ)
		var entity_data_text: String = file.get_as_text()
		file.close()
		var parsed: Variant = JSON.parse_string(entity_data_text)
		if typeof(parsed) != TYPE_DICTIONARY:
			return
		entity_data = parsed as Dictionary

	var e_name: String = entity_data.get("entity_name", "PreviewEntity") as String
	if active_entities.has(e_name):
		var old_entity: Node = active_entities[e_name] as Node
		if old_entity and is_instance_valid(old_entity):
			old_entity.queue_free()

	var entity_node: CharacterBody2D = CharacterBody2D.new()
	entity_node.name = e_name
	add_child(entity_node)
	
	var sprite: Sprite2D = Sprite2D.new()
	sprite.name = "Sprite"
	var texture_loaded: bool = false
	
	var json_sprite_path: String = entity_data.get("sprite_path", "") as String
	if json_sprite_path != "":
		var real_img_path: String = ProjectSettings.globalize_path(json_sprite_path)
		var img: Image = Image.new()
		if img.load(real_img_path) == OK:
			sprite.texture = ImageTexture.create_from_image(img)
			texture_loaded = true
			sprite.scale = Vector2(0.25, 0.25)
	
	if not texture_loaded:
		var placeholder: PlaceholderTexture2D = PlaceholderTexture2D.new()
		placeholder.size = Vector2(64, 64)
		sprite.texture = placeholder
		sprite.modulate = Color(1.0, 0.2, 0.2, 0.8)
	
	if sprite.texture != null:
		sprite.position = sprite.texture.get_size() / 2.0
	
	entity_node.add_child(sprite)
	
	var components: Array = entity_data.get("components", []) as Array
	var component_params: Dictionary = entity_data.get("component_params", {}) as Dictionary
	
	for comp_name in components:
		var script_path = "res://components/" + comp_name + ".gd"
		if ResourceLoader.exists(script_path):
			var loaded_script: Variant = load(script_path)
			if loaded_script:
				var comp_node: Node = loaded_script.new()
				comp_node.name = comp_name
				var params: Dictionary = component_params.get(comp_name, {}) as Dictionary
				for param_key in params.keys():
					comp_node.set(param_key, params[param_key])
				entity_node.add_child(comp_node)
	
	entity_node.global_position = get_viewport_rect().size / 2.0
	active_entities[e_name] = entity_node
	print("【LiveLink】🎉 实体降临！")
	sync_scene_state()

func update_entity_component(data: Dictionary):
	print("【LiveLink】⚡ 开始热更实体属性...")
	var target_entity: String = data.get("entity_name", "") as String
	var comp_name: String = data.get("component_name", "") as String
	var params: Dictionary = data.get("parameters", {}) as Dictionary

	if not active_entities.has(target_entity):
		return
	var entity_node: Node = active_entities[target_entity] as Node
	if not entity_node or not is_instance_valid(entity_node):
		return
	var comp_node: Node = entity_node.get_node_or_null(comp_name)
	if comp_node:
		for param_key in params.keys():
			comp_node.set(param_key, params[param_key])
		print("【LiveLink】⚡ 属性热更成功！")
		sync_scene_state()

func update_scene_config(data: Dictionary) -> void:
	var config: Dictionary = data.get("config", {}) as Dictionary
	if not (config is Dictionary):
		return
	_ensure_world_background_nodes()

	if config.has("background_color"):
		var color_text: String = str(config.get("background_color", ""))
		if color_text != "":
			_world_color_rect.color = Color.from_string(color_text, Color(0.06, 0.09, 0.13, 1.0))

	if config.has("background_image"):
		var bg_path: String = str(config.get("background_image", ""))
		if bg_path == "":
			_world_bg_texture.texture = null
		else:
			var image = Image.new()
			if image.load(ProjectSettings.globalize_path(bg_path)) == OK:
				_world_bg_texture.texture = ImageTexture.create_from_image(image)
			else:
				_world_bg_texture.texture = null

	if config.has("physics_gravity"):
		var gravity_value: Variant = config.get("physics_gravity", 980.0)
		if gravity_value is float or gravity_value is int:
			ProjectSettings.set_setting("physics/2d/default_gravity", float(gravity_value))

func _ensure_world_background_nodes() -> void:
	if _world_canvas != null and is_instance_valid(_world_canvas):
		return
	_world_canvas = CanvasLayer.new()
	_world_canvas.layer = -100
	_world_canvas.name = "WorldCanvasLayer"
	add_child(_world_canvas)

	_world_color_rect = ColorRect.new()
	_world_color_rect.name = "WorldColorRect"
	_world_color_rect.color = Color(0.06, 0.09, 0.13, 1.0)
	_world_color_rect.anchor_left = 0.0
	_world_color_rect.anchor_top = 0.0
	_world_color_rect.anchor_right = 1.0
	_world_color_rect.anchor_bottom = 1.0
	_world_color_rect.offset_left = 0.0
	_world_color_rect.offset_top = 0.0
	_world_color_rect.offset_right = 0.0
	_world_color_rect.offset_bottom = 0.0
	_world_canvas.add_child(_world_color_rect)

	_world_bg_texture = TextureRect.new()
	_world_bg_texture.name = "WorldBackgroundTexture"
	_world_bg_texture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_world_bg_texture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_world_bg_texture.anchor_left = 0.0
	_world_bg_texture.anchor_top = 0.0
	_world_bg_texture.anchor_right = 1.0
	_world_bg_texture.anchor_bottom = 1.0
	_world_bg_texture.offset_left = 0.0
	_world_bg_texture.offset_top = 0.0
	_world_bg_texture.offset_right = 0.0
	_world_bg_texture.offset_bottom = 0.0
	_world_canvas.add_child(_world_bg_texture)

func sync_scene_state() -> void:
	var entities_packet: Array = []
	for entity_name in active_entities.keys():
		var entity_node: Node2D = active_entities[entity_name] as Node2D
		if entity_node == null or not is_instance_valid(entity_node):
			continue
		var sync_data_packet: Dictionary = {
			"name": entity_node.name,
			"x": entity_node.global_position.x,
			"y": entity_node.global_position.y,
			"components": {},
		}
		for child in entity_node.get_children():
			if child is Sprite2D:
				continue
			var comp_node: Node = child as Node
			var comp_params: Dictionary = {}
			for k in _SYNC_PARAM_KEYS:
				if k in comp_node:
					comp_params[k] = comp_node.get(k)
			sync_data_packet["components"][comp_node.name] = comp_params
		entities_packet.append(sync_data_packet)
	if entities_packet.is_empty():
		return
	var final_sync_msg: Dictionary = {
		"action": "sync_state",
		"data": {
			"entities": entities_packet,
			"viewport_width": get_viewport_rect().size.x,
			"viewport_height": get_viewport_rect().size.y
		}
	}
	
	_ws_send_text(JSON.stringify(final_sync_msg))
	print("【LiveLink】🧠 已同步场景状态到后端！")

func _ws_send_text(text: String) -> void:
	if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		socket.send_text(text)

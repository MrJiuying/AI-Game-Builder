extends Node2D

var socket = WebSocketPeer.new()
var websocket_url = "ws://127.0.0.1:8000/ws"
var was_connected = false
var active_entities = {}

# 这里定义了我们要上报给 AI 的属性白名单
var _SYNC_PARAM_KEYS = ["max_speed", "acceleration", "friction", "max_health", "damage"]

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
			print("【LiveLink】📩 收到神谕...")
			handle_message(msg)
			
	elif state == WebSocketPeer.STATE_CLOSED:
		if was_connected:
			print("【LiveLink】🔴 连接断开，尝试重连...")
			was_connected = false
		socket.connect_to_url(websocket_url)

func handle_message(msg: String):
	var data = JSON.parse_string(msg)
	if data == null or not data is Dictionary:
		return
	
	var action: String = data.get("action", "") as String
	if action == "spawn_entity":
		spawn_entity(data)
	elif action == "update_component":
		update_entity_component(data)

func spawn_entity(data: Dictionary):
	print("【LiveLink】🏗️ 开始装配实体...")
	var entity_data: Dictionary = {}
	if data.has("entity_config") and data["entity_config"] is Dictionary:
		entity_data = data["entity_config"] as Dictionary
	else:
		var config_path: String = data.get("config_path", "") as String
		if config_path == "":
			return
		var global_config_path = ProjectSettings.globalize_path(config_path)
		if not FileAccess.file_exists(global_config_path):
			return
		var file = FileAccess.open(global_config_path, FileAccess.READ)
		var entity_data_text = file.get_as_text()
		file.close()
		var parsed = JSON.parse_string(entity_data_text)
		if typeof(parsed) != TYPE_DICTIONARY:
			return
		entity_data = parsed as Dictionary

	var e_name: String = entity_data.get("entity_name", "PreviewEntity") as String
	if active_entities.has(e_name):
		var old_entity = active_entities[e_name]
		if old_entity and is_instance_valid(old_entity):
			old_entity.queue_free()

	var entity_node = CharacterBody2D.new()
	entity_node.name = e_name
	add_child(entity_node)
	
	var sprite = Sprite2D.new()
	sprite.name = "Sprite"
	var texture_loaded = false
	
	var json_sprite_path: String = entity_data.get("sprite_path", "") as String
	if json_sprite_path != "":
		var real_img_path = ProjectSettings.globalize_path(json_sprite_path)
		var img = Image.new()
		if img.load(real_img_path) == OK:
			sprite.texture = ImageTexture.create_from_image(img)
			texture_loaded = true
			sprite.scale = Vector2(0.25, 0.25)
	
	if not texture_loaded:
		var placeholder = PlaceholderTexture2D.new()
		placeholder.size = Vector2(64, 64)
		sprite.texture = placeholder
		sprite.modulate = Color(1.0, 0.2, 0.2, 0.8)
	
	if sprite.texture != null:
		sprite.position = sprite.texture.get_size() / 2.0
	
	entity_node.add_child(sprite)
	
	var components = entity_data.get("components", [])
	var component_params = entity_data.get("component_params", {})
	
	for comp_name in components:
		var script_path = "res://components/" + comp_name + ".gd"
		if ResourceLoader.exists(script_path):
			var loaded_script = load(script_path)
			if loaded_script:
				var comp_node = loaded_script.new()
				comp_node.name = comp_name
				var params = component_params.get(comp_name, {})
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
	var entity_node = active_entities[target_entity]
	if not entity_node or not is_instance_valid(entity_node):
		return
	var comp_node = entity_node.get_node_or_null(comp_name)
	if comp_node:
		for param_key in params.keys():
			comp_node.set(param_key, params[param_key])
		print("【LiveLink】⚡ 属性热更成功！")
		sync_scene_state()

func sync_scene_state() -> void:
	var entities_packet: Array = []
	for entity_name in active_entities.keys():
		var entity_node = active_entities[entity_name]
		if entity_node == null or not is_instance_valid(entity_node):
			continue
		var sync_data_packet: Dictionary = {
			"name": entity_node.name,
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
			"entities": entities_packet
		}
	}
	
	_ws_send_text(JSON.stringify(final_sync_msg))
	print("【LiveLink】🧠 已同步场景状态到后端！")

func _ws_send_text(text: String) -> void:
	if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		socket.send_text(text)
